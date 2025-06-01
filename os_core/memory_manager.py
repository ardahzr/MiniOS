class PageTableEntry:
    def __init__(self):
        self.frame_number = None
        self.valid = False
        self.on_disk = False
        self.disk_block_number = None
        self.use_bit = False

class MemoryManager:
    def __init__(self, page_size, num_frames, num_disk_frames): # MODIFIED
        self.page_size = int(page_size) 
        self.num_frames = int(num_frames) 
        self.num_disk_frames = int(num_disk_frames)
        
        # frame_table[frame_idx] = {'pid': pid, 'vpage': virtual_page_num} or None if free
        self.frame_table = [None] * self.num_frames
        self.disk_blocks = [None] * self.num_disk_frames
        self.free_frames = list(range(self.num_frames)) # List of free frame indices
        self.free_disk_blocks = list(range(self.num_disk_frames))
        self.pid_to_pcb_map = {} # Helper to get PCB from PID for deallocation if needed
        self.clockPointer = None

    def allocate_memory(self, pcb):
        """Allocates memory frames to a process, swapping if necessary."""
        # If pid already in map, it means memory is already allocated or PID was reused without deallocation.
        if pcb.pid in self.pid_to_pcb_map:
            print(f"Error: PID {pcb.pid} already has memory allocated or PID reused without deallocation.")
            return False

        # Check if the process is too large for total RAM, even with swapping.
        if pcb.num_pages_required > self.num_frames:
            print(f"Error: Process PID {pcb.pid} requires {pcb.num_pages_required} pages, but total RAM capacity is only {self.num_frames} frames. Cannot allocate.")
            return False

        allocated_frames_for_pcb = []
        original_pcb_page_table = pcb.page_table.copy() # For potential rollback

        # Ensure enough free frames before allocation
        needed = pcb.num_pages_required - len(self.free_frames)
        while needed > 0:
            victim_pcb, victim_vpage = self.clockHand()
            if victim_pcb is None:
                print(f"Error: clockHand failed to select a victim. Cannot make space for PID {pcb.pid}.")
                return False
            if not self.free_disk_blocks:
                print(f"Error: No disk space to swap out victim (PID {victim_pcb.pid}, VPage {victim_vpage}). Cannot make space for PID {pcb.pid}.")
                return False
            victim_target_disk_block = self.free_disk_blocks.pop(0)
            victim_pte = victim_pcb.page_table[victim_vpage]
            victim_ram_frame_idx = victim_pte.frame_number

            print(f"Swapping out victim: PID {victim_pcb.pid}, VPage {victim_vpage} from RAM Frame {victim_ram_frame_idx} to Disk Block {victim_target_disk_block}.")

            victim_pte.valid = False
            victim_pte.on_disk = True
            victim_pte.disk_block_number = victim_target_disk_block
            victim_pte.frame_number = None

            self.disk_blocks[victim_target_disk_block] = {'pid': victim_pcb.pid, 'vpage': victim_vpage}
            self.frame_table[victim_ram_frame_idx] = None
            self.free_frames.append(victim_ram_frame_idx)
            self.free_frames.sort()
            needed -= 1

        # Now we have enough free frames, proceed with allocation
        for i in range(pcb.num_pages_required):
            frame_idx = self.free_frames.pop(0)
            pte = PageTableEntry()
            pte.frame_number = frame_idx
            pte.valid = True
            pte.use_bit = True # Page is immediately "used" or "referenced" upon allocation
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
            faulting_pte.use_bit = True    # Specifically for Clock algorithm, set on load

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
            faulting_pte.use_bit = True    # Specifically for Clock algorithm, set on load

            self.frame_table[target_ram_frame_idx] = {'pid': pcb.pid, 'vpage': virtual_page_number}
            # print(f"Successfully loaded true-fault page PID {pcb.pid}, VPage {virtual_page_number} to RAM Frame {target_ram_frame_idx}.")
            return target_ram_frame_idx # Success

    def clockHand(self):
        if self.clockPointer is None:
            self.clockPointer = 0
        hand = self.clockPointer
        start_hand = hand
        cycles = 0
        while True:
            current_frame_content = self.frame_table[hand]
            if current_frame_content is None:
                pass  # skip
            else:
                pid_in_frame = current_frame_content["pid"]
                vpage_in_frame = current_frame_content["vpage"]
                pcb = self.pid_to_pcb_map.get(pid_in_frame)
                if pcb is None:
                    print(f"ClockHand Warning: Inconsistent state! PID {pid_in_frame} in frame_table (frame {hand}) but not in pid_to_pcb_map. Clearing frame.")
                    self.frame_table[hand] = None
                    if hand not in self.free_frames:
                        self.free_frames.append(hand)
                        self.free_frames.sort()
                else:
                    pte = pcb.page_table.get(vpage_in_frame)
                    if pte is None:
                        print(f"ClockHand Warning: Inconsistent state! VPage {vpage_in_frame} for PID {pid_in_frame} (frame {hand}) not in its page_table. Clearing frame.")
                        self.frame_table[hand] = None
                        if hand not in self.free_frames:
                            self.free_frames.append(hand)
                            self.free_frames.sort()
                    else:
                        if not pte.use_bit:
                            self.clockPointer = (hand + 1) % self.num_frames
                            return pcb, vpage_in_frame
                        else:
                            pte.use_bit = False
            # Always advance hand
            hand = (hand + 1) % self.num_frames
            self.clockPointer = hand
            if hand == start_hand:
                cycles += 1
                if cycles == 2:
                    print("ClockHand: Cycled through all frames twice, no suitable victim found.")
                    return None, None

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

        page_number = virtual_address // self.page_size # USE self.page_size
        offset = virtual_address % self.page_size # USE self.page_size

        # Check if page_number is out of process's logical address space defined by num_pages_required
        if not (0 <= page_number < pcb.num_pages_required):
            return f"Error: Segmentation Fault - Page {page_number} is outside PID {pid}'s address space (0-{pcb.num_pages_required-1})."

        pte = pcb.page_table.get(page_number)

        if pte is None or not pte.valid:
            # Page fault occurred
            
            if pte is None: 
                pte = PageTableEntry()
                # pte.use_bit is already False by default from __init__
                pcb.page_table[page_number] = pte
            
            allocated_frame = self.handle_page_fault(pcb, page_number)
            
            if allocated_frame is False: 
                return f"Error: Page fault handling failed for PID {pid}, VPage {page_number}."
            
            # After successful page fault handling, pte is updated by handle_page_fault.
            # handle_page_fault should have set use_bit = True for the loaded page.
        
        # At this point, pte is valid and pte.frame_number is the physical frame
        # Set use_bit on any successful access (hit or resolved miss)
        pte.use_bit = True # This is the key part for simulating access for Clock
        physical_address = pte.frame_number * self.page_size + offset # USE self.page_size
        return f"PID {pid}: VA {virtual_address} (Page {page_number}, Offset {offset}) -> PA {physical_address} (Frame {pte.frame_number})"