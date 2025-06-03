import PySimpleGUI as sg
from os_core.memory_manager import MemoryManager
from os_core.process import PCB

class MemoryVisualizerApp:
    def _show_settings_dialog(self):
        default_settings = {'page_size': 4096, 'num_frames': 32, 'num_disk_frames': 64}
        layout = [
            [sg.Text("Initial Simulation Settings", font=("Helvetica", 14))],
            [sg.Text("Page Size (bytes):"), sg.Input(default_settings['page_size'], size=(10, 1), key='-PAGE_SIZE-')],
            [sg.Text("Memory Frames:"), sg.Input(default_settings['num_frames'], size=(10, 1), key='-NUM_FRAMES-')],
            [sg.Text("Disk Blocks:"), sg.Input(default_settings['num_disk_frames'], size=(10, 1), key='-NUM_DISK_FRAMES-')],
            [sg.Button("Apply Settings"), sg.Button("Reset Defaults"), sg.Button("Close Settings")]
        ]
        window = sg.Window("Configure Simulation", layout, modal=True, finalize=True)
        
        parsed_settings = None
        while True:
            event, values = window.read()
            if event in (sg.WIN_CLOSED, "Close Settings"):
                # Ensure parsed_settings remains None if dialog is closed without applying
                parsed_settings = None 
                break 
            elif event == "Reset Defaults":
                window['-PAGE_SIZE-'].update(default_settings['page_size'])
                window['-NUM_FRAMES-'].update(default_settings['num_frames'])
                window['-NUM_DISK_FRAMES-'].update(default_settings['num_disk_frames'])
            elif event == "Apply Settings":
                try:
                    ps = int(values['-PAGE_SIZE-'])
                    nf = int(values['-NUM_FRAMES-'])
                    ndf = int(values['-NUM_DISK_FRAMES-'])
                    if ps <= 0 or nf <= 0 or ndf < 0: 
                        sg.popup_error("Page Size and Memory Frames must be positive. Disk Blocks must be non-negative.", title="Input Error")
                        continue
                    parsed_settings = {'page_size': ps, 'num_frames': nf, 'num_disk_frames': ndf}
                    break 
                except ValueError:
                    sg.popup_error("Please enter valid numbers for all settings.", title="Input Error")
                    # No need to continue here, loop will naturally continue
        
        window.close()
        return parsed_settings

    def _update_process_list_display(self):
        process_display_list = []
        for pid, pcb in self.simulated_processes.items():
            process_display_list.append(f"PID: {pid} - {pcb.name} ({pcb.state})")
        self.window['-PROCESS_LIST-'].update(values=process_display_list)

    def _update_selected_process_info(self, pid):
        pcb = self.simulated_processes.get(pid)
        if pcb:
            info_str = f"PID: {pcb.pid}\nName: {pcb.name}\nState: {pcb.state}\nPages Req: {pcb.num_pages_required}"
            self.window['-PROCESS_INFO-'].update(info_str)
            
            pt_str = "Page Table:\nVP | Frame | Valid | OnDisk | DiskBlk | UseBit\n--------------------------------------------------\n"
            for vp, pte in sorted(pcb.page_table.items()):
                pt_str += f"{vp:<2} | {str(pte.frame_number):<5} | {str(pte.valid):<5} | {str(pte.on_disk):<6} | {str(pte.disk_block_number):<7} | {pte.use_bit}\n"
            self.window['-PAGE_TABLE_DISPLAY-'].update(pt_str)
        else:
            self.window['-PROCESS_INFO-'].update("")
            self.window['-PAGE_TABLE_DISPLAY-'].update("")

    def __init__(self):
        PCB.reset_pid_counter()

        initial_settings = self._show_settings_dialog()

        if initial_settings is None:
            print("Memory Visualizer setup cancelled by user or failed.")
            self.window = None
            return

        self.mm = MemoryManager(page_size=initial_settings['page_size'],
                                num_frames=initial_settings['num_frames'],
                                num_disk_frames=initial_settings['num_disk_frames'])
        self.simulated_processes = {}

        self.items_per_row = 8
        self.item_box_size = (60, 40)
        
        ram_layout = [
            [sg.Frame("Memory Frames", self._create_ram_display_layout(), key='-RAM_FRAME_DISPLAY-')],
            [sg.Text(f"Page Size: {self.mm.page_size} bytes", key='-PAGE_SIZE_INFO-')],
            [sg.Text(f"Total RAM Frames: {self.mm.num_frames}, Free: {self.mm.get_free_frames_count()}", key='-MEM_STATS-')]
        ]

        disk_layout = [
            [sg.Frame("Disk Blocks", self._create_disk_display_layout(), key='-DISK_BLOCK_DISPLAY-')],
            [sg.Text(f"Block Size (same as Page): {self.mm.page_size} bytes", key='-DISK_BLOCK_INFO-')],
            [sg.Text(f"Total Disk Blocks: {self.mm.num_disk_frames}, Free: {self.mm.get_free_disk_blocks_count()}", key='-DISK_STATS-')]
        ]

        process_management_layout = [
            [sg.Text("Process Name Prefix:"), sg.Input("Proc", size=(10,1), key='-PROC_NAME_PREFIX-'),
             sg.Text("Mem Req (bytes):"), sg.Input("8192", size=(10,1), key='-MEM_REQ-'),
             sg.Button("Create Process", key='-CREATE_PROC-')],
            [sg.Text("Logical Address:"), sg.Input("0", size=(10,1), key='-LOGICAL_ADDR-'),
             sg.Button("Access Address", key='-ACCESS_ADDR-'),
             sg.Button("Release Memory", key='-RELEASE_MEM-')],
            [sg.Listbox(values=[], size=(40, 5), key='-PROCESS_LIST-', enable_events=True)],
            [sg.Text("Selected Process Info:", size=(60,1), key='-PROCESS_INFO-')],
            [sg.Multiline(size=(60, 10), key='-PAGE_TABLE_DISPLAY-', disabled=True, autoscroll=True)],
        ]

        logging_layout = [
            [sg.Multiline(size=(80,10), key='-LOG_OUTPUT-', reroute_stdout=True, write_only=True, autoscroll=True)]
        ]
        
        # Main layout with tabs
        tab_group_layout = [[sg.TabGroup([
            [sg.Tab('RAM', ram_layout)],
            [sg.Tab('Disk', disk_layout)],
            [sg.Tab('Process Management', process_management_layout)],
            [sg.Tab('Logs', logging_layout)]
        ])]]

        # Layout without the "Change Settings" button
        full_layout = [
            tab_group_layout
        ]

        self.window = sg.Window("Memory Management Visualizer", full_layout, finalize=True)
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

    def handle_event(self, event, values):
        if event in (sg.WIN_CLOSED, 'Close'):
            return 'close'

        if event == '-CREATE_PROC-':
            try:
                mem_req_bytes = int(values['-MEM_REQ-'])
                name_prefix = values['-PROC_NAME_PREFIX-']
                if mem_req_bytes <= 0:
                    sg.popup_error("Memory requirement must be positive.", title="Input Error")
                    return
                new_pcb = PCB(name=name_prefix, memory_requirements_bytes=mem_req_bytes, page_size=self.mm.page_size)
                if self.mm.allocate_memory(new_pcb):
                    self.simulated_processes[new_pcb.pid] = new_pcb
                    self._update_process_list_display()
                else:
                    sg.popup_error(f"Failed to allocate memory for PID {new_pcb.pid}.\nNot enough memory or other issue.", title="Allocation Error")
            except ValueError:
                sg.popup_error("Invalid memory requirement. Must be an integer.", title="Input Error")
            self._full_refresh()

        elif event == '-RELEASE_MEM-':
            selected_process_str = values['-PROCESS_LIST-']
            if not selected_process_str:
                sg.popup_error("Please select a process from the list to release memory.", title="Input Error")
                return
            try:
                pid_to_dealloc = int(selected_process_str[0].split(" ")[1])
                if pid_to_dealloc not in self.simulated_processes:
                    sg.popup_error(f"PID {pid_to_dealloc} not found.", title="Error")
                else:
                    if self.mm.deallocate_memory(pid_to_dealloc):
                        if pid_to_dealloc in self.simulated_processes:
                            del self.simulated_processes[pid_to_dealloc]
                        self._update_process_list_display()
                        self._update_selected_process_info(None)
                    else:
                        sg.popup_error(f"Failed to deallocate memory for PID {pid_to_dealloc}.", title="Deallocation Error")
            except (ValueError, IndexError):
                sg.popup_error("Invalid selection or PID format for deallocation.", title="Input Error")
            self._full_refresh()

        elif event == '-ACCESS_ADDR-':
            selected_process_str = values['-PROCESS_LIST-']
            if not selected_process_str:
                sg.popup_error("Please select a process from the list to access an address.", title="Input Error")
                return
            try:
                pid = int(selected_process_str[0].split(" ")[1])
                va = int(values['-LOGICAL_ADDR-'])
                if pid not in self.simulated_processes:
                    sg.popup_error(f"PID {pid} not found.", title="Error")
                    return
                result = self.mm.translate(pid, va)
                if "Error:" in result or "Page fault handled: False" in result:
                    sg.popup_error(f"Address Access Error for PID {pid}, VA {va}:\n{result}", title="Access Error")
                self._full_refresh()
                self._update_selected_process_info(pid)
            except (ValueError, IndexError):
                sg.popup_error("PID or Virtual Address must be valid integers and a process selected.", title="Input Error")
            except Exception as e:
                sg.popup_error(f"An unexpected error occurred during address access: {e}", title="Access Error")
                self._full_refresh()

        elif event == '-PROCESS_LIST-':
            if values['-PROCESS_LIST-']:
                selected_process_str = values['-PROCESS_LIST-'][0]
                try:
                    pid = int(selected_process_str.split(" ")[1])
                    self._update_selected_process_info(pid)
                except (IndexError, ValueError):
                    self._update_selected_process_info(None)
            else:
                self._update_selected_process_info(None)

        elif event == "Refresh View":
            self._full_refresh()

        return None

