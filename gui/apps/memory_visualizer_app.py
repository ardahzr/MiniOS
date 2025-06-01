import PySimpleGUI as sg
from os_core.memory_manager import MemoryManager, PAGE_SIZE
from os_core.process import PCB

class MemoryVisualizerApp:
    def __init__(self): 
        PCB.reset_pid_counter() # Reset PID counter for this app session
        self.mm = MemoryManager()
        self.simulated_processes = {} # pid: PCB

        # Display settings (can be shared or specific)
        self.items_per_row = 8 # Used for both RAM frames and Disk blocks
        self.item_box_size = (60, 40) # width, height for each box

        # RAM Tab Layout
        ram_layout = [
            [sg.Frame("Memory Frames", self._create_ram_display_layout(), key='-RAM_FRAME_DISPLAY-')],
            [sg.Text(f"Page Size: {PAGE_SIZE} bytes", key='-PAGE_SIZE_INFO-')],
            [sg.Text(f"Total RAM Frames: {self.mm.num_frames}, Free: {self.mm.get_free_frames_count()}", key='-MEM_STATS-')]
        ]

        # Disk Tab Layout
        disk_layout = [
            [sg.Frame("Disk Blocks", self._create_disk_display_layout(), key='-DISK_BLOCK_DISPLAY-')],
            [sg.Text(f"Block Size (same as Page): {PAGE_SIZE} bytes")],
            [sg.Text(f"Total Disk Blocks: {self.mm.num_disk_frames}, Free: {self.mm.get_free_disk_blocks_count()}", key='-DISK_STATS-')]
        ]

        tab_group_layout = [[
            sg.Tab('RAM View', ram_layout, key='-RAM_TAB-'),
            sg.Tab('Disk View', disk_layout, key='-DISK_TAB-')
        ]]

        controls_layout = [
            [
                sg.Text("Proc Name:"), sg.Input("P", size=(5,1), key='-PROC_NAME_PREFIX-'),
                sg.Text("Mem (bytes):"), sg.Input("8192", size=(8,1), key='-MEM_REQ-'),
                sg.Button("Create & Allocate", key='-ALLOCATE-')
            ],
            [
                sg.Text("PID to Dealloc:"), sg.Input(size=(5,1), key='-PID_DEALLOC-'),
                sg.Button("Deallocate", key='-DEALLOCATE-')
            ],
            [
                sg.Text("PID:"), sg.Input(size=(5,1), key='-PID_TRANSLATE-'),
                sg.Text("VA:"), sg.Input(size=(8,1), key='-VA_TRANSLATE-'),
                sg.Button("Translate Addr", key='-TRANSLATE-')
            ],
            [sg.Multiline(size=(80, 5), key='-LOG-', autoscroll=True, reroute_stdout=True, write_only=True, disabled=True)], # Increased width
            [sg.Button("Refresh View"), sg.Button("Close")]
        ]
        
        layout = [
            [sg.Text("Memory Visualizer", font=("Helvetica", 16))],
            [sg.TabGroup(tab_group_layout, enable_events=True, key='-TABGROUP-')],
            [sg.Column(controls_layout, element_justification='center')]
        ]

        self.window = sg.Window("Memory Management Demo", layout, modal=True, finalize=True)
        self._update_ram_display() 
        self._update_disk_display()

    def _create_ram_display_layout(self):
        layout = []
        num_items = self.mm.num_frames
        for i in range(0, num_items, self.items_per_row):
            row = []
            for j in range(self.items_per_row):
                item_idx = i + j
                if item_idx < num_items:
                    row.append(sg.Text(f"F{item_idx}\nFree", size=(self.item_box_size[0]//8, 2), key=f'-RAM_FRAME_{item_idx}-', relief=sg.RELIEF_SOLID, border_width=1, justification='center', pad=(2,2), background_color='lightgreen'))
            layout.append(row)
        return layout

    def _create_disk_display_layout(self):
        layout = []
        num_items = self.mm.num_disk_frames
        for i in range(0, num_items, self.items_per_row):
            row = []
            for j in range(self.items_per_row):
                item_idx = i + j
                if item_idx < num_items:
                    row.append(sg.Text(f"DB{item_idx}\nFree", size=(self.item_box_size[0]//8, 2), key=f'-DISK_BLOCK_{item_idx}-', relief=sg.RELIEF_SOLID, border_width=1, justification='center', pad=(2,2), background_color='lightgray'))
            layout.append(row)
        return layout
    
    def _update_ram_display(self):
        memory_map = self.mm.get_memory_map()
        for i, frame_info in enumerate(memory_map):
            frame_elem = self.window[f'-RAM_FRAME_{i}-']
            if frame_elem:
                if frame_info:
                    pid = frame_info['pid']
                    vpage = frame_info['vpage']
                    frame_elem.update(f"F{i}\nPID:{pid}\nVP:{vpage}", background_color='lightblue')
                else:
                    frame_elem.update(f"F{i}\nFree", background_color='lightgreen')
        self.window['-MEM_STATS-'].update(f"Total RAM Frames: {self.mm.num_frames}, Free: {self.mm.get_free_frames_count()}")

    def _update_disk_display(self):
        disk_map = self.mm.get_disk_map()
        for i, block_info in enumerate(disk_map):
            block_elem = self.window[f'-DISK_BLOCK_{i}-']
            if block_elem:
                if block_info:
                    pid = block_info['pid']
                    vpage = block_info['vpage']
                    block_elem.update(f"DB{i}\nPID:{pid}\nVP:{vpage}", background_color='tan')
                else:
                    block_elem.update(f"DB{i}\nFree", background_color='lightgray')
        self.window['-DISK_STATS-'].update(f"Total Disk Blocks: {self.mm.num_disk_frames}, Free: {self.mm.get_free_disk_blocks_count()}")

    def _full_refresh(self):
        self._update_ram_display()
        self._update_disk_display()

    def run(self):
        while True:
            event, values = self.window.read()
            if event in (sg.WIN_CLOSED, "Close"):
                # Clean up simulated processes if necessary (deallocate all)
                for pid_key in list(self.simulated_processes.keys()): # Use pid_key to avoid confusion with pid var
                    self.mm.deallocate_memory(pid_key)
                self.simulated_processes.clear()
                break

            if event == '-ALLOCATE-':
                try:
                    mem_req_bytes = int(values['-MEM_REQ-'])
                    name_prefix = values['-PROC_NAME_PREFIX-']
                    if mem_req_bytes <= 0:
                        print("Error: Memory requirement must be positive.")
                        continue
                    
                    new_pcb = PCB(name=name_prefix, memory_requirements_bytes=mem_req_bytes)
                    
                    print(f"Attempting to allocate {new_pcb.num_pages_required} pages ({mem_req_bytes} bytes) for new process {new_pcb.name} (PID {new_pcb.pid})...")
                    if self.mm.allocate_memory(new_pcb):
                        self.simulated_processes[new_pcb.pid] = new_pcb
                        print(f"Successfully allocated memory for PID {new_pcb.pid}.")
                    else:
                        print(f"Failed to allocate memory for PID {new_pcb.pid}. Not enough memory or other issue.")
                except ValueError:
                    print("Error: Invalid memory requirement. Must be an integer.")
                self._full_refresh()

            elif event == '-DEALLOCATE-':
                try:
                    pid_to_dealloc = int(values['-PID_DEALLOC-'])
                    if pid_to_dealloc not in self.simulated_processes:
                        print(f"Error: PID {pid_to_dealloc} not found among simulated processes.")
                    else:
                        print(f"Attempting to deallocate memory for PID {pid_to_dealloc}...")
                        if self.mm.deallocate_memory(pid_to_dealloc):
                            del self.simulated_processes[pid_to_dealloc]
                            print(f"Successfully deallocated memory for PID {pid_to_dealloc}.")
                        else:
                            print(f"Failed to deallocate memory for PID {pid_to_dealloc} (it might not have been allocated or already deallocated).")
                except ValueError:
                    print("Error: Invalid PID for deallocation. Must be an integer.")
                self._full_refresh()
            
            elif event == '-TRANSLATE-':
                try:
                    pid = int(values['-PID_TRANSLATE-'])
                    va = int(values['-VA_TRANSLATE-'])
                    result = self.mm.translate(pid, va)
                    print(f"Translation: {result}")
                    # Translation might cause swapping, so refresh displays
                    self._full_refresh() 
                except ValueError:
                    print("Error: PID and Virtual Address must be integers.")
                except Exception as e:
                    print(f"Translation error: {e}")
                    self._full_refresh() # Refresh even on error, state might have changed partially


            elif event == "Refresh View":
                self._full_refresh()
                print("View refreshed.")
        
        self.window.close()

