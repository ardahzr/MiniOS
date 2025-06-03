import PySimpleGUI as sg
from os_core.process import PCB
from os_core.scheduler import FIFOScheduler, RoundRobinScheduler, MLFQScheduler

class ProcessManagerVisualizerApp:
    def __init__(self):
        PCB.reset_pid_counter()
        self.processes = {} # pid: PCB
        self.scheduler = FIFOScheduler()
        self.current_scheduler_type = "FIFO"
        self.running_process = None
        self.current_time_slice = 0
        self.time_slice_elapsed = 0
        self.simulation_time = 0

        sg.theme('DarkBlue')

        scheduler_selection_layout = [
            sg.Radio("FIFO", "SCHEDULER", key="-FIFO-", default=True, enable_events=True),
            sg.Radio("Round Robin", "SCHEDULER", key="-RR-", enable_events=True),
            sg.Radio("MLFQ", "SCHEDULER", key="-MLFQ-", enable_events=True)
        ]

        process_creation_layout = [
            sg.Text("Name:"), sg.Input("P", size=(3,1), key="-PROC_NAME_PREFIX-"),
            sg.Text("Burst:"), sg.Input("10", size=(4,1), key="-PROC_BURST-"),
            sg.Button("Create Process", key="-CREATE_PROC-")
        ]

        simulation_controls_layout = [
            sg.Button("Next Step", key="-NEXT_STEP-"),
            sg.Button("Reset Sim", key="-RESET_SIM-"),
            sg.Text(f"Time: {self.simulation_time}", key="-SIM_TIME-", size=(10,1))
        ]

        status_layout = [
            [sg.Text("Running: None", key="-RUNNING_PROC-", size=(40,1))],
            [sg.Text("Finished Processes:", key="-FINISHED_HEADER-")],
            [sg.Multiline("", key="-FINISHED_PROCS-", size=(40,3), disabled=True, autoscroll=True)],
            [sg.Text("Ready Queues:", key="-QUEUES_HEADER-")],
            [sg.Multiline("", key="-QUEUES-", size=(40, 5), disabled=True, autoscroll=True)]
        ]

        layout = [
            [sg.Text("Process Scheduling Visualizer", font=("Helvetica", 16))],
            [scheduler_selection_layout],
            [process_creation_layout],
            [sg.Frame("Status", status_layout)],
            [simulation_controls_layout],
            [sg.Button("Close")]
        ]

        self.window = sg.Window("Scheduler Visualizer", layout, modal=True, finalize=True)
        self._update_queue_display()

    def _select_scheduler(self, scheduler_type):
        if scheduler_type == self.current_scheduler_type:
            return

        self.current_scheduler_type = scheduler_type
        if scheduler_type == "FIFO":
            self.scheduler = FIFOScheduler()
        elif scheduler_type == "Round Robin":
            self.scheduler = RoundRobinScheduler(time_quantum=5) # Default TQ for RR
        elif scheduler_type == "MLFQ":
            self.scheduler = MLFQScheduler(levels=3, time_quanta=[3, 6, 9]) # Default TQs for MLFQ

        # Re-add existing non-terminated processes to the new scheduler
        # Terminated processes should not be re-added.
        # Running process needs special handling if scheduler changes mid-run.
        # For simplicity, we'll clear running and re-add all non-finished.
        
        temp_processes_to_readd = []
        if self.running_process:
            self.running_process.state = 'READY' # Mark as ready to be re-added
            self.running_process.time_in_current_quantum = 0
            temp_processes_to_readd.append(self.running_process)
            self.running_process = None
            self.current_time_slice = 0
            self.time_slice_elapsed = 0
            self.window["-RUNNING_PROC-"].update("Running: None")


        for pid, pcb in list(self.processes.items()): # Iterate over a copy for modification
            if pcb.state != 'TERMINATED':
                temp_processes_to_readd.append(pcb)
        
        # Clear internal queues of the old scheduler if possible (or just let it be GC'd)
        # Then add to new scheduler
        for pcb in temp_processes_to_readd:
            if pcb.state != 'TERMINATED': # Double check
                 # For MLFQ, add to the highest priority queue by default when switching
                if isinstance(self.scheduler, MLFQScheduler):
                    self.scheduler.add_process(pcb, level=0)
                else:
                    self.scheduler.add_process(pcb)

        self._update_queue_display()


    def _update_queue_display(self):
        if hasattr(self.scheduler, 'get_all_queues_str_list'):
            queues_str = "\n".join(self.scheduler.get_all_queues_str_list())
            self.window["-QUEUES-"].update(queues_str)
        else: # Fallback for schedulers not implementing the new method
            self.window["-QUEUES-"].update("Queue display not available for this scheduler.")

    def _update_finished_display(self):
        finished_text = "\n".join([f"PID {pid}: {pcb.name}" for pid, pcb in self.processes.items() if pcb.state == 'TERMINATED'])
        self.window["-FINISHED_PROCS-"].update(finished_text)

    def _reset_simulation(self):
        PCB.reset_pid_counter()
        self.processes.clear()
        self.running_process = None
        self.current_time_slice = 0
        self.time_slice_elapsed = 0
        self.simulation_time = 0
        # Re-initialize scheduler based on current selection
        self._select_scheduler(self.current_scheduler_type) # This will clear and set up the chosen scheduler
        # If _select_scheduler doesn't re-instantiate, do it manually:
        # if self.current_scheduler_type == "FIFO": self.scheduler = FIFOScheduler()
        # elif self.current_scheduler_type == "Round Robin": self.scheduler = RoundRobinScheduler(time_quantum=5)
        # elif self.current_scheduler_type == "MLFQ": self.scheduler = MLFQScheduler(levels=3, time_quanta=[3, 6, 9])

        self.window["-RUNNING_PROC-"].update("Running: None")
        self.window["-SIM_TIME-"].update(f"Time: {self.simulation_time}")
        self._update_queue_display()
        self._update_finished_display()


    def run(self):
        while True:
            event, values = self.window.read()

            if event in (sg.WIN_CLOSED, "Close"):
                break

            if event == "-FIFO-":
                self._select_scheduler("FIFO")
            elif event == "-RR-":
                self._select_scheduler("Round Robin")
            elif event == "-MLFQ-":
                self._select_scheduler("MLFQ")

            elif event == "-CREATE_PROC-":
                try:
                    burst_time = int(values["-PROC_BURST-"])
                    if burst_time <= 0:
                        sg.popup_error("Burst time must be positive.")
                        continue
                    
                    # Create unique name for process using current PID count before creating PCB
                    # This is a bit of a hack as PCB increments its counter upon init.
                    # A better way would be to get the *next* PID without incrementing.
                    # For now, we can use the length of self.processes or similar uniqueifier.
                    # Or, let PCB handle PID and use that.
                    
                    pcb = PCB(name=f"{values['-PROC_NAME_PREFIX-']}{PCB._pid_counter.__reduce__()[1][0]}", # Gets current value of counter
                              memory_requirements_bytes=0, # Not used in this sim
                              burst_time=burst_time)
                    self.processes[pcb.pid] = pcb
                    
                    if isinstance(self.scheduler, MLFQScheduler):
                        self.scheduler.add_process(pcb, level=0) # New processes to highest priority
                    else:
                        self.scheduler.add_process(pcb)
                    self._update_queue_display()
                except ValueError:
                    sg.popup_error("Invalid burst time. Must be an integer.")

            elif event == "-RESET_SIM-":
                self._reset_simulation()

            elif event == "-NEXT_STEP-":
                self.simulation_time += 1
                self.window["-SIM_TIME-"].update(f"Time: {self.simulation_time}")

                # If a process is running
                if self.running_process:
                    self.running_process.remaining_time -= 1
                    self.running_process.time_in_current_quantum +=1
                    self.time_slice_elapsed +=1

                    if self.running_process.remaining_time <= 0:
                        self.running_process.state = 'TERMINATED'
                        self.window["-RUNNING_PROC-"].update(f"Running: {self.running_process.name} (PID {self.running_process.pid}) - Finished!")
                        self._update_finished_display()
                        self.running_process = None
                        self.time_slice_elapsed = 0
                    # Check for time slice expiry for RR and MLFQ
                    elif self.time_slice_elapsed >= self.current_time_slice:
                        if isinstance(self.scheduler, RoundRobinScheduler):
                            self.running_process.state = 'READY'
                            self.running_process.time_in_current_quantum = 0
                            self.scheduler.add_process(self.running_process) # Add to end of RR queue
                        elif isinstance(self.scheduler, MLFQScheduler):
                            self.running_process.state = 'READY'
                            current_level = -1
                            # Find which queue it might have come from (not perfectly stored, infer or add to PCB)
                            # For simplicity, demote if it used its full slice.
                            # A more accurate MLFQ would track which queue it was in.
                            # Here, we determine new level based on scheduler's logic.
                            # If it used full quantum, demote (if not at lowest level)
                            # This logic is simplified: assume it was from a queue that matches current_time_slice
                            original_level = -1
                            for i, tq in enumerate(self.scheduler.time_quanta):
                                if tq == self.current_time_slice: # This assumes unique time quanta
                                    original_level = i
                                    break
                            
                            new_level = min(original_level + 1, self.scheduler.levels - 1) if original_level != -1 else 0
                            self.running_process.time_in_current_quantum = 0
                            self.scheduler.add_process(self.running_process, level=new_level)

                        self.window["-RUNNING_PROC-"].update(f"Running: {self.running_process.name} (PID {self.running_process.pid}) - Quantum Expired")
                        self.running_process = None
                        self.time_slice_elapsed = 0
                    else:
                        self.window["-RUNNING_PROC-"].update(f"Running: {self.running_process.name} (PID {self.running_process.pid}) - Rem: {self.running_process.remaining_time}, SliceRem: {self.current_time_slice - self.time_slice_elapsed}")

                # If no process is running, try to get one
                if not self.running_process:
                    next_proc, time_slice = self.scheduler.get_next()
                    if next_proc:
                        self.running_process = next_proc
                        self.current_time_slice = time_slice if time_slice != float('inf') else self.running_process.remaining_time
                        self.time_slice_elapsed = 0
                        self.running_process.time_in_current_quantum = 0
                        self.window["-RUNNING_PROC-"].update(f"Running: {self.running_process.name} (PID {self.running_process.pid}) - Rem: {self.running_process.remaining_time}, SliceRem: {self.current_time_slice - self.time_slice_elapsed}")
                    else:
                        self.window["-RUNNING_PROC-"].update("Running: None (Idle)")
                
                self._update_queue_display()

        self.window.close()

if __name__ == '__main__':
    # This is for testing the app standalone
    # In your MiniOS, you would launch it from the main_window
    app = ProcessManagerVisualizerApp()
    app.run()