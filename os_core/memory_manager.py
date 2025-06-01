PAGE_SIZE = 4 * 1024  # 4 KB pages
MEMORY_SIZE = 128 * 1024  # 128 KB memory
DISK_SIZE = 256 * 1024 # 256 KB disk

class PageTableEntry:
    def __init__(self):
        self.frame_number = None
        self.valid = False
        self.dirty = False
        self.referenced = False
        self.on_disk = False
        self.disk_block_number = None
        self.use_bit = True

class MemoryManager:
    def __init__(self):
        self.num_frames = MEMORY_SIZE // PAGE_SIZE
        self.num_disk_frames = DISK_SIZE // PAGE_SIZE
        # frame_table[frame_idx] = {'pid': pid, 'vpage': virtual_page_num} or None if free
        self.frame_table = [None] * self.num_frames
        self.disk_blocks = [None] * (self.num_disk_frames)
        self.free_frames = list(range(self.num_frames)) # List of free frame indices
        self.free_disk_blocks = list(range(self.num_disk_frames))
        self.pid_to_pcb_map = {} # Helper to get PCB from PID for deallocation if needed
        self.clockPointer = None

    def allocate_memory(self, pcb):
        """Allocates memory frames to a process, swapping if necessary."""
        if pcb.pid in self.pid_to_pcb_map:
            print(f"Error: PID {pcb.pid} already has memory allocated or PID reused without deallocation.")
            return False

        # Check if the process is too large for total RAM, even with swapping.
        if pcb.num_pages_required > self.num_frames:
            print(f"Error: Process PID {pcb.pid} requires {pcb.num_pages_required} pages, but total RAM capacity is only {self.num_frames} frames. Cannot allocate.")
            return False

        allocated_frames_for_pcb = []
        original_pcb_page_table = pcb.page_table.copy() # For potential rollback

        for i in range(pcb.num_pages_required):
            if not self.free_frames: # RAM is full, need to make space
                print(f"RAM is full while allocating page {i} for new PID {pcb.pid}. Attempting to swap out a victim.")
                
                # 1. Select a victim page from an existing process
                victim_pcb, victim_vpage = self.clockHand()
                if victim_pcb is None: # Should ideally not happen if clockHand is robust and RAM is truly full of swappable pages
                    print(f"Error: clockHand failed to select a victim. Cannot make space for PID {pcb.pid}.")
                    # Rollback pages already allocated for this new PCB
                    for v_page_idx, pte_to_remove in pcb.page_table.items():
                        if pte_to_remove.valid and pte_to_remove.frame_number is not None:
                            self.frame_table[pte_to_remove.frame_number] = None
                            self.free_frames.append(pte_to_remove.frame_number)
                    pcb.page_table = original_pcb_page_table # Restore original (likely empty) page table
                    self.free_frames.sort() # Keep consistent
                    return False

                # 2. Check if there's disk space for the victim
                if not self.free_disk_blocks:
                    print(f"Error: No disk space to swap out victim (PID {victim_pcb.pid}, VPage {victim_vpage}). Cannot make space for PID {pcb.pid}.")
                    # Rollback logic as above
                    for v_page_idx, pte_to_remove in pcb.page_table.items():
                        if pte_to_remove.valid and pte_to_remove.frame_number is not None:
                            self.frame_table[pte_to_remove.frame_number] = None
                            self.free_frames.append(pte_to_remove.frame_number)
                    pcb.page_table = original_pcb_page_table
                    self.free_frames.sort()
                    return False

                # 3. Perform the swap-out of the victim
                victim_target_disk_block = self.free_disk_blocks.pop(0)
                victim_pte = victim_pcb.page_table[victim_vpage]
                victim_ram_frame_idx = victim_pte.frame_number
                
                print(f"Swapping out victim: PID {victim_pcb.pid}, VPage {victim_vpage} from RAM Frame {victim_ram_frame_idx} to Disk Block {victim_target_disk_block}.")

                victim_pte.valid = False
                victim_pte.on_disk = True
                victim_pte.disk_block_number = victim_target_disk_block
                victim_pte.frame_number = None
                # Consider pte.dirty here for actual write to disk in a real system

                self.disk_blocks[victim_target_disk_block] = {'pid': victim_pcb.pid, 'vpage': victim_vpage}
                self.frame_table[victim_ram_frame_idx] = None
                self.free_frames.append(victim_ram_frame_idx) # CRITICAL: Add freed frame back
                self.free_frames.sort() # Keep consistent if pop(0) relies on order

            # Now, a frame should be available (either was already free or just made free)
            if not self.free_frames:
                # This should not be reached if the logic above is correct and clockHand always finds a victim when RAM is full.
                # It's a safeguard.
                print(f"Critical Error: Still no free frames after attempting to make space for PID {pcb.pid}, page {i}. Allocation failed.")
                # Rollback logic
                for v_page_idx, pte_to_remove in pcb.page_table.items():
                    if pte_to_remove.valid and pte_to_remove.frame_number is not None:
                        self.frame_table[pte_to_remove.frame_number] = None
                        self.free_frames.append(pte_to_remove.frame_number)
                pcb.page_table = original_pcb_page_table
                self.free_frames.sort()
                return False
            
            frame_idx = self.free_frames.pop(0) # Get a free frame
            
            pte = PageTableEntry()
            pte.frame_number = frame_idx
            pte.valid = True
            # pcb.page_table maps virtual page number to its PageTableEntry
            # For a new process, its page table is initially empty or being built.
            # We are allocating page 'i' (0-indexed virtual page for this new process)
            pcb.page_table[i] = pte 
            
            self.frame_table[frame_idx] = {'pid': pcb.pid, 'vpage': i}
            allocated_frames_for_pcb.append(frame_idx)
        
        self.pid_to_pcb_map[pcb.pid] = pcb
        pcb.state = 'READY'
        print(f"Allocated {pcb.num_pages_required} pages ({len(allocated_frames_for_pcb)} frames: {allocated_frames_for_pcb}) to PID {pcb.pid} ({pcb.name}).")
        return True

    def deallocate_memory(self, pid_to_deallocate):
        """Deallocates all memory frames associated with a PID."""
        pcb = self.pid_to_pcb_map.get(pid_to_deallocate)
        if not pcb:
            print(f"Error: PID {pid_to_deallocate} not found for deallocation.")
            return False

        deallocated_count = 0
        for virtual_page, pte in list(pcb.page_table.items()): # Iterate over a copy
            if pte.valid and pte.frame_number is not None:
                frame_idx = pte.frame_number
                if 0 <= frame_idx < self.num_frames and self.frame_table[frame_idx] is not None:
                    self.frame_table[frame_idx] = None
                    self.free_frames.append(frame_idx)
                    self.free_frames.sort() # Keep it sorted for consistent pop
                    pte.valid = False
                    pte.frame_number = None
                    deallocated_count +=1
                else:
                    print(f"Warning: Frame {frame_idx} for PID {pid_to_deallocate} vpage {virtual_page} was already free or invalid.")
            # Remove entry from page table or just mark invalid
            if pte.on_disk == True and pte.disk_block_number is not None:
                self.disk_blocks[pte.disk_block_number] = None
                self.free_disk_blocks.append(pte.disk_block_number)
                pte.on_disk = False
                pte.disk_block_number = None

            del pcb.page_table[virtual_page]

        if pid_to_deallocate in self.pid_to_pcb_map:
            del self.pid_to_pcb_map[pid_to_deallocate]
        
        pcb.state = 'TERMINATED' # Or some other appropriate state
        print(f"Deallocated {deallocated_count} pages/frames from PID {pid_to_deallocate} ({pcb.name}).")
        return True
    
    def handle_page_fault(self, pcb, virtual_page_number):
        # Ensure the PTE exists for the given virtual_page_number for this PCB
        # This should be guaranteed by `translate` before calling handle_page_fault
        faulting_pte = pcb.page_table[virtual_page_number]

        if faulting_pte.on_disk == True: # Page is on disk, needs to be swapped IN
            print(f"Page fault: PID {pcb.pid}, VPage {virtual_page_number}. Page is ON DISK. Swapping IN.")
            target_ram_frame_idx = -1
            original_faulting_page_disk_block = faulting_pte.disk_block_number # Store before it's cleared

            if len(self.free_frames) == 0: # RAM is full, need to swap OUT a victim
                print(f"RAM full. Selecting victim to swap out for PID {pcb.pid}, VPage {virtual_page_number}.")
                victim_pcb, victim_vpage = self.clockHand()
                if victim_pcb is None: # Should not happen if RAM is full and clockHand works
                    print("Error: clockHand failed to select a victim when RAM is full.")
                    return False

                if not self.free_disk_blocks:
                    print(f"Error: No disk space to swap out victim (PID {victim_pcb.pid}, VPage {victim_vpage}). Page fault handling failed.")
                    return False
                
                victim_target_disk_block = self.free_disk_blocks.pop(0)
                # print(f"Victim: PID {victim_pcb.pid}, VPage {victim_vpage}. Swapping to Disk Block {victim_target_disk_block}.")
                
                victim_pte = victim_pcb.page_table[victim_vpage]
                victim_ram_frame_idx = victim_pte.frame_number
                
                # Update victim PTE (now on disk)
                victim_pte.valid = False
                victim_pte.on_disk = True
                victim_pte.disk_block_number = victim_target_disk_block
                victim_pte.frame_number = None
                # victim_pte.dirty should be considered here if implementing write-back

                self.disk_blocks[victim_target_disk_block] = {'pid': victim_pcb.pid, 'vpage': victim_vpage}
                self.frame_table[victim_ram_frame_idx] = None
                self.free_frames.append(victim_ram_frame_idx)
                self.free_frames.sort() # Optional: keep sorted if pop(0) relies on it

                target_ram_frame_idx = victim_ram_frame_idx
            
            else: # RAM has free frames
                target_ram_frame_idx = self.free_frames.pop(0)
                # print(f"RAM has free frame {target_ram_frame_idx} for PID {pcb.pid}, VPage {virtual_page_number}.")

            # Load faulting page into target_ram_frame_idx
            faulting_pte.valid = True
            faulting_pte.on_disk = False 
            faulting_pte.frame_number = target_ram_frame_idx
            faulting_pte.disk_block_number = None # Was on disk, now in RAM
            faulting_pte.referenced = True # Mark as referenced

            self.frame_table[target_ram_frame_idx] = {'pid': pcb.pid, 'vpage': virtual_page_number}
            
            # Free the disk block that the faulting page occupied
            if original_faulting_page_disk_block is not None:
                self.disk_blocks[original_faulting_page_disk_block] = None
                self.free_disk_blocks.append(original_faulting_page_disk_block)
                self.free_disk_blocks.sort() # Optional
            
            # print(f"Successfully swapped IN PID {pcb.pid}, VPage {virtual_page_number} to RAM Frame {target_ram_frame_idx}.")
            return target_ram_frame_idx # Success, return frame number
        
        else: # Page is NOT on disk (faulting_pte.on_disk == False). This is a "true" fault.
            print(f"Page fault: PID {pcb.pid}, VPage {virtual_page_number}. Page is NOT ON DISK (true fault). Loading into RAM.")
            target_ram_frame_idx = -1

            if len(self.free_frames) == 0: # RAM is full, need to swap OUT a victim
                print(f"RAM full. Selecting victim to swap out for true fault of PID {pcb.pid}, VPage {virtual_page_number}.")
                victim_pcb, victim_vpage = self.clockHand()
                if victim_pcb is None:
                    print("Error: clockHand failed to select a victim when RAM is full for a true fault.")
                    return False

                if not self.free_disk_blocks:
                    print(f"Error: No disk space to swap out victim (PID {victim_pcb.pid}, VPage {victim_vpage}) for true fault. Page fault handling failed.")
                    return False
                
                victim_target_disk_block = self.free_disk_blocks.pop(0)
                # print(f"Victim for true fault: PID {victim_pcb.pid}, VPage {victim_vpage}. Swapping to Disk Block {victim_target_disk_block}.")

                victim_pte = victim_pcb.page_table[victim_vpage]
                victim_ram_frame_idx = victim_pte.frame_number

                victim_pte.valid = False
                victim_pte.on_disk = True
                victim_pte.disk_block_number = victim_target_disk_block
                victim_pte.frame_number = None

                self.disk_blocks[victim_target_disk_block] = {'pid': victim_pcb.pid, 'vpage': victim_vpage}
                self.frame_table[victim_ram_frame_idx] = None
                self.free_frames.append(victim_ram_frame_idx)
                self.free_frames.sort()

                target_ram_frame_idx = victim_ram_frame_idx
            
            else: # RAM has free frames
                target_ram_frame_idx = self.free_frames.pop(0)
                # print(f"RAM has free frame {target_ram_frame_idx} for true fault of PID {pcb.pid}, VPage {virtual_page_number}.")
            
            # "Load" the true-faulting page into RAM (it wasn't on disk)
            faulting_pte.valid = True
            faulting_pte.on_disk = False # It's not coming from disk, it's new to memory system
            faulting_pte.frame_number = target_ram_frame_idx
            faulting_pte.disk_block_number = None # Ensure this is None
            faulting_pte.referenced = True

            self.frame_table[target_ram_frame_idx] = {'pid': pcb.pid, 'vpage': virtual_page_number}
            # print(f"Successfully loaded true-fault page PID {pcb.pid}, VPage {virtual_page_number} to RAM Frame {target_ram_frame_idx}.")
            return target_ram_frame_idx # Success

    def clockHand(self):
        if self.clockPointer is None: # Initialize pointer if first time
            self.clockPointer = 0
        
        hand = self.clockPointer
        start_hand = hand # To detect a full cycle without finding a victim (e.g., all pages pinned or error state)
        
        while True:
            current_frame_content = self.frame_table[hand]

            if current_frame_content is None: # Frame is free, skip
                hand = (hand + 1) % self.num_frames
                self.clockPointer = hand
                if hand == start_hand: # Cycled through all frames, all were free or became free
                    print("ClockHand: Cycled through all frames, none occupied or suitable found.")
                    return None, None # Should not happen if called when RAM is full
                continue

            # Frame is occupied
            pid_in_frame = current_frame_content["pid"]
            vpage_in_frame = current_frame_content["vpage"]

            pcb = self.pid_to_pcb_map.get(pid_in_frame)
            if pcb is None:
                print(f"ClockHand Warning: Inconsistent state! PID {pid_in_frame} in frame_table (frame {hand}) but not in pid_to_pcb_map. Clearing frame.")
                self.frame_table[hand] = None
                if hand not in self.free_frames: # Ensure it's added if somehow missed
                    self.free_frames.append(hand)
                    self.free_frames.sort()
                # Advance hand and continue search
                hand = (hand + 1) % self.num_frames
                self.clockPointer = hand
                if hand == start_hand: # Avoid infinite loop if this is the only frame
                    print("ClockHand: Cycled after clearing inconsistent frame, no other victim found.")
                    return None, None
                continue

            pte = pcb.page_table.get(vpage_in_frame)
            if pte is None:
                print(f"ClockHand Warning: Inconsistent state! VPage {vpage_in_frame} for PID {pid_in_frame} (frame {hand}) not in its page_table. Clearing frame.")
                self.frame_table[hand] = None
                if hand not in self.free_frames:
                    self.free_frames.append(hand)
                    self.free_frames.sort()
                # Advance hand and continue search
                hand = (hand + 1) % self.num_frames
                self.clockPointer = hand
                if hand == start_hand:
                    print("ClockHand: Cycled after clearing inconsistent frame (PTE missing), no other victim found.")
                    return None, None
                continue
            
            # Actual clock algorithm logic
            if not pte.use_bit: # Found a victim (use_bit is False)
                self.clockPointer = (hand + 1) % self.num_frames # Next search starts after this victim
                return pcb, vpage_in_frame
            else: # use_bit is True
                pte.use_bit = False # Give it a second chance
                hand = (hand + 1) % self.num_frames
                self.clockPointer = hand # Move hand

            if hand == start_hand:
                # Made a full circle, all use_bits were true and now set to false.
                # The loop will continue and on the next pass, it's guaranteed to find a victim
                # (unless pages are actively being referenced and use_bits set to true again,
                # or pages are deallocated making frames None).
                # No special action needed here, the while True continues.
                # However, if after a full circle, we still haven't returned, and all frames were occupied
                # and had their use_bit set, the next iteration *must* find one.
                # This check is more for breaking if something unexpected happens like all pages are unswappable.
                # For now, let the loop continue. If it becomes an infinite loop, it means
                # clockHand is called when no swappable page exists or state is very broken.
                pass


    def get_memory_map(self):
        """Returns a representation of the frame table for display."""
        return self.frame_table

    def get_disk_map(self):
        """Returns a representation of the disk blocks for display."""
        return self.disk_blocks

    def get_free_frames_count(self):
        return len(self.free_frames)

    def get_free_disk_blocks_count(self):
        return len(self.free_disk_blocks)

    def translate(self, pid, virtual_address):
        pcb = self.pid_to_pcb_map.get(pid)
        if not pcb:
            return f"Error: Process PID {pid} not found."

        page_number = virtual_address // PAGE_SIZE
        offset = virtual_address % PAGE_SIZE

        # Check if page_number is out of process's logical address space defined by num_pages_required
        if not (0 <= page_number < pcb.num_pages_required):
            return f"Error: Segmentation Fault - Page {page_number} is outside PID {pid}'s address space (0-{pcb.num_pages_required-1})."

        pte = pcb.page_table.get(page_number)

        if pte is None or not pte.valid:
            # Page fault occurred
            # print(f"Translate: Page Fault for PID {pid}, VPage {page_number}. PTE exists: {pte is not None}. PTE valid: {pte.valid if pte else 'N/A'}.")
            
            if pte is None: # Page was never in page table, true fault
                # print(f"Translate: Page {page_number} not in page table for PID {pid}. Creating new PTE.")
                pte = PageTableEntry()
                pcb.page_table[page_number] = pte
                # The new PTE is valid=False, on_disk=False by default.
            
            # Now pte is guaranteed to exist, call handle_page_fault
            # handle_page_fault returns target_ram_frame_idx on success, False on failure
            allocated_frame = self.handle_page_fault(pcb, page_number)
            
            if allocated_frame is False: # Check explicitly for False, as 0 is a valid frame index
                return f"Error: Page fault handling failed for PID {pid}, VPage {page_number}."
            
            # After successful page fault handling, pte is updated by handle_page_fault
            # and pte.frame_number should be the allocated_frame.
            # No need to use allocated_frame directly here if pte is correctly updated.
            # print(f"Translate: Page fault handled for PID {pid}, VPage {page_number}. Page now in Frame {pte.frame_number}.")
        
        # At this point, pte is valid and pte.frame_number is the physical frame
        # Set referenced bit on access
        pte.referenced = True 
        physical_address = pte.frame_number * PAGE_SIZE + offset
        return f"PID {pid}: VA {virtual_address} (Page {page_number}, Offset {offset}) -> PA {physical_address} (Frame {pte.frame_number})"