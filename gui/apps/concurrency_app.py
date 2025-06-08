import PySimpleGUI as sg
import threading
import time
import random
from typing import List, Dict, Any
import queue
from os_core.concurrency import ProducerConsumerSimulation, ThreadAPI

class ConcurrencyApp:
    """Real-time concurrency simulation visualization app"""
    
    def __init__(self):
        self.window = None
        self.simulation = None
        self.thread_api = ThreadAPI()
        self.running = False
        self.log_messages = []
        self.max_log_messages = 50
        
        # Simulation parameters
        self.num_producers = 2
        self.num_consumers = 2
        self.buffer_size = 5
        self.items_per_producer = 8
        self.items_per_consumer = 8
        self.producer_delay = 0.5
        self.consumer_delay = 0.7
        
        # GUI colors
        self.producer_color = '#4CAF50'  # Green
        self.consumer_color = '#2196F3'  # Blue
        self.buffer_color = '#FF9800'    # Orange
        self.empty_color = '#E0E0E0'     # Light gray
        
        # Create the window immediately
        self.window = self.create_window()
        
    def create_layout(self):
        """Create the GUI layout"""
        
        # Control panel
        control_frame = [
            [sg.Text('Concurrency & Synchronization Simulator', font=('Arial', 16, 'bold'))],
            [sg.HSeparator()],
            [sg.Text('Simulation Parameters:')],
            [
                sg.Text('Producers:'), 
                sg.Input(str(self.num_producers), size=(5,1), key='-PRODUCERS-'),
                sg.Text('Consumers:'), 
                sg.Input(str(self.num_consumers), size=(5,1), key='-CONSUMERS-'),
                sg.Text('Buffer Size:'), 
                sg.Input(str(self.buffer_size), size=(5,1), key='-BUFFER_SIZE-')
            ],
            [
                sg.Text('Items/Producer:'), 
                sg.Input(str(self.items_per_producer), size=(5,1), key='-ITEMS_PROD-'),
                sg.Text('Items/Consumer:'), 
                sg.Input(str(self.items_per_consumer), size=(5,1), key='-ITEMS_CONS-')
            ],
            [
                sg.Text('Producer Delay (s):'), 
                sg.Input(str(self.producer_delay), size=(5,1), key='-PROD_DELAY-'),
                sg.Text('Consumer Delay (s):'), 
                sg.Input(str(self.consumer_delay), size=(5,1), key='-CONS_DELAY-')
            ],
            [
                sg.Button('Start Simulation', key='-START-', button_color=('white', self.producer_color)),
                sg.Button('Stop Simulation', key='-STOP-', button_color=('white', '#f44336'), disabled=True),
                sg.Button('Reset', key='-RESET-', button_color=('white', '#9E9E9E'))
            ]
        ]
        
        # Buffer visualization
        buffer_frame = [
            [sg.Text('Buffer Visualization', font=('Arial', 14, 'bold'))],
            [sg.Graph(canvas_size=(600, 100), graph_bottom_left=(0, 0), 
                     graph_top_right=(600, 100), key='-BUFFER_GRAPH-', 
                     background_color='white', enable_events=False)]
        ]
        
        # Statistics
        stats_frame = [
            [sg.Text('Statistics', font=('Arial', 14, 'bold'))],
            [
                sg.Column([
                    [sg.Text('Produced:', font=('Arial', 10, 'bold'))],
                    [sg.Text('0', key='-STAT_PRODUCED-', font=('Arial', 12))],
                    [sg.Text('Consumed:', font=('Arial', 10, 'bold'))],
                    [sg.Text('0', key='-STAT_CONSUMED-', font=('Arial', 12))],
                ]),
                sg.Column([
                    [sg.Text('Buffer Usage:', font=('Arial', 10, 'bold'))],
                    [sg.Text('0/0', key='-STAT_BUFFER-', font=('Arial', 12))],
                    [sg.Text('Active Threads:', font=('Arial', 10, 'bold'))],
                    [sg.Text('0', key='-STAT_THREADS-', font=('Arial', 12))],
                ])
            ]
        ]
        
        # Thread status
        thread_frame = [
            [sg.Text('Thread Status', font=('Arial', 14, 'bold'))],
            [sg.Graph(canvas_size=(600, 200), graph_bottom_left=(0, 0), 
                     graph_top_right=(600, 200), key='-THREAD_GRAPH-', 
                     background_color='white', enable_events=False)]
        ]
        
        # Activity log
        log_frame = [
            [sg.Text('Activity Log', font=('Arial', 14, 'bold'))],
            [sg.Multiline('', size=(80, 15), key='-LOG-', disabled=True, 
                         autoscroll=True, font=('Courier', 9))]
        ]
        
        # Main layout
        left_column = [
            [sg.Frame('Control Panel', control_frame, expand_x=True)],
            [sg.Frame('Statistics', stats_frame, expand_x=True)],
            [sg.Frame('Buffer State', buffer_frame, expand_x=True)],
            [sg.Frame('Thread Activity', thread_frame, expand_x=True)]
        ]
        
        right_column = [
            [sg.Frame('Activity Log', log_frame, expand_x=True, expand_y=True)]
        ]
        
        layout = [
            [
                sg.Column(left_column, vertical_alignment='top', expand_y=True),
                sg.VSeparator(),
                sg.Column(right_column, vertical_alignment='top', expand_x=True, expand_y=True)
            ]
        ]
        
        return layout
    
    def create_window(self):
        """Create the main window"""
        layout = self.create_layout()
        window = sg.Window(
            'Concurrency Simulation',
            layout,
            finalize=True,
            resizable=True,
            size=(1200, 800),
            location=(100, 100)
        )
        
        # Initialize with empty simulation for display
        self.draw_initial_displays(window)
        
        return window
        
    def draw_initial_displays(self, window):
        """Draw initial empty displays"""
        # Draw empty buffer
        graph = window['-BUFFER_GRAPH-']
        graph.erase()
        graph.draw_text("Start simulation to see buffer visualization", (300, 50), font=('Arial', 12), color='gray')
        
        # Draw empty thread display
        thread_graph = window['-THREAD_GRAPH-']
        thread_graph.erase()
        thread_graph.draw_text("Start simulation to see thread activity", (300, 100), font=('Arial', 12), color='gray')
    
    def draw_buffer_visualization(self, buffer_contents):
        """Draw the buffer state visualization"""
        if not self.window:
            return
            
        graph = self.window['-BUFFER_GRAPH-']
        graph.erase()
        
        if not self.simulation:
            graph.draw_text("No simulation running", (300, 50), font=('Arial', 12), color='gray')
            return
            
        buffer_size = self.simulation.buffer_size
        slot_width = 80
        slot_height = 60
        margin = 20
        start_x = 50
        start_y = 20
        
        # Draw buffer slots
        for i in range(buffer_size):
            x1 = start_x + i * (slot_width + margin)
            y1 = start_y
            x2 = x1 + slot_width
            y2 = y1 + slot_height
            
            # Determine slot content and color
            if i < len(buffer_contents):
                color = self.buffer_color
                text = str(buffer_contents[i])
            else:
                color = self.empty_color
                text = 'Empty'
            
            # Draw slot
            graph.draw_rectangle((x1, y1), (x2, y2), fill_color=color, line_color='black')
            graph.draw_text(text, (x1 + slot_width//2, y1 + slot_height//2), font=('Arial', 10), color='black')
    
    def draw_thread_visualization(self, thread_states):
        """Draw thread activity visualization"""
        if not self.window:
            return
            
        graph = self.window['-THREAD_GRAPH-']
        graph.erase()
        
        if not thread_states:
            graph.draw_text("No thread activity", (300, 100), font=('Arial', 12), color='gray')
            return
        
        # Separate producers and consumers
        producers = [(name, status, progress) for name, status, progress in thread_states if 'Producer' in name]
        consumers = [(name, status, progress) for name, status, progress in thread_states if 'Consumer' in name]
        
        # Box dimensions and layout
        box_width = 80
        box_height = 40
        box_margin = 10
        row_spacing = 60
        start_x = 110 # Adjusted from 50 to 65 to provide more left margin
        start_y = 50
        
        # Draw producers row
        if producers:
            # Row label
            graph.draw_text("Producers:", (start_x - 40, start_y + box_height//2), 
                          font=('Arial', 10, 'bold'), color='black')
            
            for i, (name, status, progress) in enumerate(producers):
                x_pos = start_x + i * (box_width + box_margin)
                
                # Determine color based on status - green for producers
                if status.lower() == 'running':
                    color = self.producer_color  # Green for running producers
                else:
                    color = self.empty_color     # Light gray for waiting/finished producers
                
                # Draw box
                graph.draw_rectangle((x_pos, start_y), (x_pos + box_width, start_y + box_height), 
                                   fill_color=color, line_color='black')
                
                # Draw progress bar (optional)
                if status.lower() == 'running' and progress > 0:
                    progress_width = int(box_width * progress)
                    graph.draw_rectangle((x_pos, start_y), (x_pos + progress_width, start_y + box_height),
                                       fill_color='#A5D6A7', line_color=None) # Lighter green for progress

                # Draw producer number
                producer_num = name.split('-')[-1] if '-' in name else str(i)
                graph.draw_text(f"P{producer_num}", (x_pos + box_width//2, start_y + box_height//2), 
                              font=('Arial', 12, 'bold'), color='white' if status.lower() == 'running' else 'black')
        
        # Draw consumers row
        if consumers:
            consumer_y = start_y + row_spacing
            
            # Row label
            graph.draw_text("Consumers:", (start_x - 40, consumer_y + box_height//2), 
                          font=('Arial', 10, 'bold'), color='black')
            
            for i, (name, status, progress) in enumerate(consumers):
                x_pos = start_x + i * (box_width + box_margin)
                
                # Determine color based on status - blue for consumers
                if status.lower() == 'running':
                    color = self.consumer_color  # Blue for running consumers
                else:
                    color = self.empty_color     # Light gray for waiting/finished consumers
                
                # Draw box
                graph.draw_rectangle((x_pos, consumer_y), (x_pos + box_width, consumer_y + box_height), 
                                   fill_color=color, line_color='black')

                # Draw progress bar (optional)
                if status.lower() == 'running' and progress > 0:
                    progress_width = int(box_width * progress)
                    graph.draw_rectangle((x_pos, consumer_y), (x_pos + progress_width, consumer_y + box_height),
                                       fill_color='#90CAF9', line_color=None) # Lighter blue for progress
                
                # Draw consumer number
                consumer_num = name.split('-')[-1] if '-' in name else str(i)
                graph.draw_text(f"C{consumer_num}", (x_pos + box_width//2, consumer_y + box_height//2), 
                              font=('Arial', 12, 'bold'), color='white' if status.lower() == 'running' else 'black')
    
    def log_message(self, message):
        """Add a message to the activity log"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        self.log_messages.append(log_entry)
        if len(self.log_messages) > self.max_log_messages:
            self.log_messages.pop(0)
        
        if self.window:
            log_text = '\n'.join(self.log_messages)
            self.window['-LOG-'].update(log_text)
    
    def update_statistics(self):
        """Update the statistics display"""
        if not self.window:
            return

        # Prepare default values
        produced_val = '0'
        consumed_val = '0'
        buffer_str = '0/0'
        active_threads_val = '0'
        buffer_list_for_draw = []

        if self.simulation and hasattr(self.simulation, 'get_stats'):
            try:
                stats = self.simulation.get_stats() # This call should be safe
                produced_val = str(stats['produced'])
                consumed_val = str(stats['consumed'])
                buffer_str = f"{stats['buffer_size']}/{stats['buffer_capacity']}"

                # Correctly reference threads from the simulation's thread_api
                if hasattr(self.simulation, 'thread_api') and self.simulation.thread_api and \
                   hasattr(self.simulation.thread_api, 'threads'):
                    active_threads_val = str(len([
                        t for t in self.simulation.thread_api.threads if t.is_alive()
                    ]))
                
                buffer_contents = getattr(self.simulation, 'buffer', [])
                if hasattr(buffer_contents, 'queue'): # Handle if buffer is a queue.Queue
                    buffer_list_for_draw = list(buffer_contents.queue)
                elif isinstance(buffer_contents, list): # Handle if buffer is already a list
                    buffer_list_for_draw = buffer_contents
                else: # Default to empty list if type is unknown or not iterable directly
                    buffer_list_for_draw = []

            except Exception as e:
                # Log error in fetching stats, GUI will show defaults
                # Using print for debug as self.log_message might also fail if window is closing
                print(f"Debug: Error fetching stats in update_statistics: {e}")
        
        try:
            # Attempt to update GUI elements
            self.window['-STAT_PRODUCED-'].update(produced_val)
            self.window['-STAT_CONSUMED-'].update(consumed_val)
            self.window['-STAT_BUFFER-'].update(buffer_str)
            self.window['-STAT_THREADS-'].update(active_threads_val)
            
            # This call to another GUI updating method should also be robust
            # or its errors handled within that method or caught here if it propagates.
            self.draw_buffer_visualization(buffer_list_for_draw)

        except TypeError as e:
            if "window was closed" in str(e).lower():
                # This is an expected condition when shutting down.
                print(f"Debug: update_statistics - GUI update skipped, window closed: {e}")
            else:
                # An unexpected TypeError
                print(f"Debug: update_statistics - Unexpected TypeError: {e}")
                if hasattr(self, 'log_message') and callable(self.log_message):
                    # Try to log to GUI if log_message itself is safe
                    try:
                        self.log_message(f"Unexpected TypeError in update_statistics: {e}")
                    except Exception as log_e:
                        print(f"Debug: Failed to log TypeError to GUI: {log_e}")
        except Exception as e:
            # Other unexpected errors during GUI update
            print(f"Debug: update_statistics - Generic error during GUI update: {e}")
            if hasattr(self, 'log_message') and callable(self.log_message):
                try:
                    self.log_message(f"Generic error in update_statistics GUI update: {e}")
                except Exception as log_e:
                    print(f"Debug: Failed to log generic error to GUI: {log_e}")
    
    def start_simulation(self):
        """Start the producer-consumer simulation"""
        try:
            # Get parameters from GUI
            self.num_producers = int(self.window['-PRODUCERS-'].get())
            self.num_consumers = int(self.window['-CONSUMERS-'].get())
            self.buffer_size = int(self.window['-BUFFER_SIZE-'].get())
            self.items_per_producer = int(self.window['-ITEMS_PROD-'].get())
            self.items_per_consumer = int(self.window['-ITEMS_CONS-'].get())
            self.producer_delay = float(self.window['-PROD_DELAY-'].get())
            self.consumer_delay = float(self.window['-CONS_DELAY-'].get())
            
            # Create new simulation, passing the ConcurrencyApp's log_message method
            self.simulation = ProducerConsumerSimulation(
                buffer_size=self.buffer_size,
                logger=self.log_message  # Pass the GUI logger to the simulation
            )
            
            
            # Start simulation
            self.running = True
            self.window['-START-'].update(disabled=True)
            self.window['-STOP-'].update(disabled=False)
            
            self.log_message("Starting simulation...")
            
            # Start simulation in separate thread
            sim_thread = threading.Thread(target=self.run_simulation, daemon=True)
            sim_thread.start()
            
            # Start GUI update thread
            update_thread = threading.Thread(target=self.simulation_monitor, daemon=True)
            update_thread.start()
            
        except ValueError as e:
            sg.popup_error(f"Invalid parameter: {e}")
        except Exception as e:
            sg.popup_error(f"Error starting simulation: {e}")
    
    def run_simulation(self):
        """Run the actual simulation"""
        try:
            self.simulation.start_simulation(
                num_producers=self.num_producers,
                num_consumers=self.num_consumers,
                items_per_producer=self.items_per_producer,
                items_per_consumer=self.items_per_consumer,
                producer_delay=self.producer_delay,
                consumer_delay=self.consumer_delay
            )
        except Exception as e:
            self.log_message(f"Simulation error: {e}")
    
    def simulation_monitor(self):
        """Monitor simulation and update GUI"""
        while self.running:  # Loop controlled by ConcurrencyApp's self.running
            if not self.simulation:
                if self.window and hasattr(self, 'draw_initial_displays'):
                    # If no simulation, ensure graphs are in initial state
                    self.draw_initial_displays(self.window) 
                try:
                    time.sleep(0.5)
                except AttributeError: pass # time module might be gone during shutdown
                continue

            # Simulation exists, get its current logical running state
            simulation_is_logically_running = getattr(self.simulation, 'running', False)

            thread_states = []
            if hasattr(self.simulation, 'thread_api') and \
               self.simulation.thread_api and \
               hasattr(self.simulation.thread_api, 'threads'):
                for thread_obj in self.simulation.thread_api.threads:
                    name = thread_obj.name
                    if not name: 
                        continue

                    progress = 0.0  # Default progress
                    if thread_obj.is_alive():
                        if simulation_is_logically_running:
                            status = "Running"
                            progress = random.uniform(0.2, 0.9)
                        else:
                            # Simulation told to stop, but thread still alive (cleaning up)
                            status = "Stopping"
                            # progress remains 0.0
                    else:  # Thread is not alive
                        status = "Finished"
                        # progress remains 0.0
                    thread_states.append((name, status, progress))
            
            if hasattr(self, 'update_statistics'):
                self.update_statistics()
            if hasattr(self, 'draw_thread_visualization'):
                self.draw_thread_visualization(thread_states)
            
            try:
                time.sleep(0.5)
            except AttributeError: pass # time module might be gone during shutdown
            except NameError: pass


        # ---- Main monitor loop (controlled by self.running) has exited ----
        # Perform a final GUI update to reflect the definitive end state of threads.
        # This is crucial for when self.stop_simulation() was called.
        if self.simulation and self.window:
            final_thread_states = []
            if hasattr(self.simulation, 'thread_api') and \
               self.simulation.thread_api and \
               hasattr(self.simulation.thread_api, 'threads'):
                for thread_obj in self.simulation.thread_api.threads:
                    name = thread_obj.name
                    if not name: continue
                    # At this stage, all producer/consumer threads managed by
                    # ProducerConsumerSimulation should have finished because its
                    # 'running' flag is set to False *after* internal join_all().
                    status = "Finished" 
                    progress = 0.0
                    final_thread_states.append((name, status, progress))

            if hasattr(self, 'update_statistics'): 
                self.update_statistics() # Update stats one last time
            if hasattr(self, 'draw_thread_visualization'):
                self.draw_thread_visualization(final_thread_states)
        elif self.window and hasattr(self, 'draw_initial_displays'):
            # If simulation was cleared or never ran, ensure initial display
             self.draw_initial_displays(self.window)

    def stop_simulation(self):
        """Stop the current simulation"""
        self.running = False
        if self.simulation:
            self.simulation.stop_simulation()
        
        self.window['-START-'].update(disabled=False)
        self.window['-STOP-'].update(disabled=True)
        
        self.log_message("Simulation stopped.")
    
    def reset_simulation(self):
        """Reset the simulation"""
        self.stop_simulation()
        time.sleep(0.5)  # Give time for threads to stop
        
        self.simulation = None
        self.log_messages.clear()
        
        # Reset displays
        self.draw_initial_displays(self.window)
        
        # Reset statistics
        self.window['-STAT_PRODUCED-'].update('0')
        self.window['-STAT_CONSUMED-'].update('0')
        self.window['-STAT_BUFFER-'].update('0/0')
        self.window['-STAT_THREADS-'].update('0')
        self.window['-LOG-'].update('')
        
        self.log_message("Simulation reset.")
    
    def handle_event(self, event, values):
        """Handle GUI events"""
        if event == sg.WIN_CLOSED:
            self.stop_simulation()
            return 'close'
        elif event == '-START-':
            self.start_simulation()
        elif event == '-STOP-':
            self.stop_simulation()
        elif event == '-RESET-':
            self.reset_simulation()
        
        return None
    
    def run(self):
        """Main event loop for standalone running"""
        while True:
            event, values = self.window.read(timeout=100)
            
            result = self.handle_event(event, values)
            if result == 'close':
                break
        
        self.window.close()


if __name__ == "__main__":
    app = ConcurrencyApp()
    app.run()
