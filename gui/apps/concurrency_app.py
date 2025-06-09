import PySimpleGUI as sg
import threading
import time
import random
from typing import List, Dict, Any
# import queue # Not strictly needed if only using list for buffer_list_for_draw
from os_core.concurrency import ProducerConsumerSimulation, ThreadAPI

class ConcurrencyApp:
    """Real-time concurrency simulation visualization app"""
    
    def __init__(self):
        self.window = None
        self.simulation = None
        self.thread_api = ThreadAPI() # This seems to be for app-level threads, not simulation threads
        self.running = False
        self.log_messages = []
        self.max_log_messages = 50
        self.update_thread = None # Initialize update_thread
        self.sim_thread = None    # Initialize sim_thread (optional, but good for consistency)
        
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

    def log_message(self, message: str):
        """Thread-safe message logging that can be called from any thread."""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # Always add to log messages (thread-safe)
        self.log_messages.append(log_entry)
        if len(self.log_messages) > self.max_log_messages:
            self.log_messages.pop(0)
        
        # For console fallback and worker threads
        print(log_entry)
        
        # Only try to update GUI if we're in the main thread
        if threading.current_thread() is threading.main_thread():
            try:
                if (self.window and hasattr(self.window, 'TKroot') and 
                    self.window.TKroot and self.window.TKroot.winfo_exists()):
                    # Additional safety check
                    if (self.window.key_dict and '-LOG-' in self.window.key_dict and 
                        self.window['-LOG-'].Widget):
                        log_text = '\n'.join(self.log_messages)
                        self.window['-LOG-'].update(log_text)
            except (sg.tk.TclError, AttributeError, RuntimeError) as e:
                # Silently handle GUI errors - message is already printed to console
                pass
            except Exception as e:
                print(f"Unexpected error updating log GUI: {type(e).__name__}: {e}")

    def update_log_display(self):
        """Safely update the log display from monitoring thread"""
        try:
            if (self.window and hasattr(self.window, 'TKroot') and 
                self.window.TKroot and self.window.TKroot.winfo_exists()):
                # Additional safety check for the log element
                if (self.window.key_dict and '-LOG-' in self.window.key_dict and 
                    self.window['-LOG-'].Widget):
                    log_text = '\n'.join(self.log_messages)
                    self.window['-LOG-'].update(log_text)
        except (sg.tk.TclError, AttributeError, RuntimeError) as e:
            # Silently handle GUI errors - message is already printed to console
            pass
        except Exception as e:
            print(f"Unexpected error updating log display: {type(e).__name__}: {e}")

    def safe_log_message(self, message: str):
        """Alternative logging method that only logs to console - safe for worker threads."""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        
        # Still add to messages list for later GUI update
        self.log_messages.append(log_entry)
        if len(self.log_messages) > self.max_log_messages:
            self.log_messages.pop(0)

    def create_layout(self):
        """Create the GUI layout"""
        
        # Control panel
        control_frame = [
            [sg.Text('Concurrency & Synchronization Simulator', font=('Arial', 16, 'bold'), justification='center', expand_x=True)],
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
            [sg.Column([ [
                sg.Button('Start Simulation', key='-START-', button_color=('white', self.producer_color)),
                sg.Button('Stop Simulation', key='-STOP-', button_color=('white', '#f44336'), disabled=True),
                sg.Button('Reset', key='-RESET-', button_color=('white', '#9E9E9E'))
            ]], justification='center', expand_x=True)]
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
            [sg.Frame('Control Panel', control_frame, expand_x=True, element_justification='center')],
            [sg.Frame('Statistics', stats_frame, expand_x=True, element_justification='center')],
            [sg.Frame('Buffer State', buffer_frame, expand_x=True, element_justification='center')],
            [sg.Frame('Thread Activity', thread_frame, expand_x=True, element_justification='center')]
        ]
        
        right_column = [
            [sg.Frame('Activity Log', log_frame, expand_x=True, expand_y=True, element_justification='center')]
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
    
    def draw_thread_visualization(self):
        if not self.running or not self.window or not self.simulation or not self.simulation.thread_api:
            return

        try:
            # Ensure window and graph element are valid before proceeding
            if not self.window or not self.window.TKroot or not self.window.TKroot.winfo_exists():
                return
            
            graph = self.window['-THREAD_GRAPH-'] 
            if not graph or not graph.TKCanvas:
                return

            graph.erase()
            threads_data = []
            if self.simulation and self.simulation.thread_api:
                with self.simulation.thread_api.lock: # Ensure thread-safe access
                    # Use .thread_states.values() to get ThreadInfo objects
                    threads_data = list(self.simulation.thread_api.thread_states.values())

            graph_width, graph_height = graph.CanvasSize 
            bar_height = 20
            bar_margin = 5
            start_x = 10
            start_y = 10 # Top padding for the first bar

            if not threads_data:
                graph.draw_text("No threads to visualize.", (graph_width / 2, graph_height / 2), font=("Helvetica", 10))
                return

            drawable_graph_width = graph_width - 2 * start_x # Usable width for bars

            for i, thread_info in enumerate(threads_data):
                y_pos = start_y + i * (bar_height + bar_margin)
                if y_pos + bar_height > graph_height: # Avoid drawing outside canvas
                    break 
                
                progress_value = 0.0
                if hasattr(thread_info, 'progress') and thread_info.progress is not None:
                    try:
                        progress_value = float(thread_info.progress)
                    except ValueError:
                        progress_value = 0.0 
                
                progress_value = max(0.0, min(100.0, progress_value))

                bar_width_pixels = 0
                if thread_info.state == "Running":
                    bar_width_pixels = int(drawable_graph_width * (progress_value / 100.0))
                elif thread_info.state == "Finished":
                    bar_width_pixels = drawable_graph_width # Full bar for finished

                color = self.empty_color
                if thread_info.state == "Running":
                    color = self.producer_color if "Producer" in thread_info.name else self.consumer_color
                elif thread_info.state == "Finished":
                     color = '#BDBDBD' # Grey for finished
                
                graph.draw_rectangle((start_x, y_pos), (start_x + bar_width_pixels, y_pos + bar_height), 
                                   fill_color=color, line_color='black')

                text_x_pos = start_x + 5 
                label_y_pos = y_pos + bar_height / 2
                graph.draw_text(f"{thread_info.name} ({thread_info.state} {int(progress_value)}%)", 
                                (text_x_pos, label_y_pos), font=("Helvetica", 8), text_location=sg.TEXT_LOCATION_LEFT)

        except (TypeError, AttributeError, sg.tk.TclError, RuntimeError) as e:
            err_msg = str(e).lower()
            if "window was closed" in err_msg or \
               "application has been destroyed" in err_msg or \
               "invalid command name" in err_msg or \
               (hasattr(self, 'window') and self.window and (not hasattr(self.window, 'TKroot') or not self.window.TKroot)):
                return 
            else:
                self.log_message(f"Draw_thread_visualization: Unexpected GUI error: {type(e).__name__}: {e}")
        except Exception as e:
            self.log_message(f"Draw_thread_visualization: Generic error: {type(e).__name__}: {e}")

    def update_statistics(self):
        if not self.running or not self.window or not self.simulation:
            return

        # Initialize default values for GUI update
        produced_val = '0'
        consumed_val = '0'
        buffer_str = '0/0'
        active_threads_val = '0'
        buffer_list_for_draw = []

        try:
            if not self.window or not hasattr(self.window, 'TKroot') or not self.window.TKroot or not self.window.TKroot.winfo_exists():
                return

            if self.simulation and hasattr(self.simulation, 'get_stats'):
                stats = self.simulation.get_stats()
                produced_val = str(stats.get('produced', 0))
                consumed_val = str(stats.get('consumed', 0))
                buffer_str = f"{stats.get('buffer_size', 0)}/{stats.get('buffer_capacity', self.buffer_size)}"

                if hasattr(self.simulation, 'thread_api') and self.simulation.thread_api and \
                   hasattr(self.simulation.thread_api, 'thread_states'): # Check for thread_states
                    active_count = 0
                    with self.simulation.thread_api.lock: 
                        # Use .thread_states.values() to get ThreadInfo objects
                        for t_info in self.simulation.thread_api.thread_states.values():
                            if t_info.state not in ["Finished", "Error", "Terminated"]: 
                                active_count +=1
                    active_threads_val = str(active_count)
                
                buffer_contents = getattr(self.simulation, 'buffer', [])
                if hasattr(buffer_contents, 'queue'): 
                    buffer_list_for_draw = list(buffer_contents.queue)
                elif isinstance(buffer_contents, list): 
                    buffer_list_for_draw = buffer_contents
            
            # Attempt to update GUI elements
            self.window['-STAT_PRODUCED-'].update(produced_val)
            self.window['-STAT_CONSUMED-'].update(consumed_val)
            self.window['-STAT_BUFFER-'].update(buffer_str)
            self.window['-STAT_THREADS-'].update(active_threads_val)
            
            self.draw_buffer_visualization(buffer_list_for_draw)

        except (TypeError, AttributeError, sg.tk.TclError, RuntimeError) as e:
            err_msg = str(e).lower()
            if "window was closed" in err_msg or \
               "application has been destroyed" in err_msg or \
               "invalid command name" in err_msg or \
               (hasattr(self, 'window') and self.window and (not hasattr(self.window, 'TKroot') or not self.window.TKroot)):
                return
            else:
                self.log_message(f"Update_statistics: Unexpected GUI error: {type(e).__name__}: {e}")
        except Exception as e:
            self.log_message(f"Update_statistics: Generic error: {type(e).__name__}: {e}")

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
            
            self.running = True # Set app-level running flag for simulation_monitor
            if self.window: # Check window exists before updating elements
                self.window['-START-'].update(disabled=True)
                self.window['-STOP-'].update(disabled=False)
            
            self.log_message("Starting simulation...")
            
            # Start simulation in separate thread
            self.sim_thread = threading.Thread(target=self.run_simulation, daemon=True)
            self.sim_thread.start()
            
            # Start GUI update thread
            if self.update_thread and self.update_thread.is_alive():
                # Should not happen if logic is correct, but as a safeguard
                self.update_thread.join(timeout=0.5)
            self.update_thread = threading.Thread(target=self.simulation_monitor, daemon=True)
            self.update_thread.start()
            
        except ValueError as e:
            sg.popup_error(f"Invalid parameter: {e}")
        except Exception as e:
            sg.popup_error(f"Error starting simulation: {e}")
            
    def run_simulation(self):
        """Run the actual simulation"""
        try:
            # Start the simulation threads (non-blocking)
            self.simulation.start_simulation(
                num_producers=self.num_producers,
                num_consumers=self.num_consumers,
                items_per_producer=self.items_per_producer,
                items_per_consumer=self.items_per_consumer,
                producer_delay=self.producer_delay,
                consumer_delay=self.consumer_delay
            )
            
            # Wait for completion and then log final results
            self.simulation.wait_for_completion()
            
        except Exception as e:
            self.log_message(f"Simulation error: {e}")
    def simulation_monitor(self):
        self.log_message("Simulation monitor thread started.")
        while self.running and self.simulation and self.simulation.running:
            try:
                if not self.window or not hasattr(self.window, 'TKroot') or not self.window.TKroot or not self.window.TKroot.winfo_exists():
                    self.log_message("Simulation_monitor: Window closed or invalid, exiting monitor loop.")
                    break
                
                self.update_statistics()
                self.draw_thread_visualization()
                
                # Update the log display with recent messages
                self.update_log_display()

                # Check if simulation has completed naturally
                if self.simulation and self.simulation.is_simulation_complete():
                    self.log_message("Simulation completed naturally - updating GUI state.")
                    self.running = False
                    # Update button states to reflect completion
                    if self.window:
                        self.window['-START-'].update(disabled=False)
                        self.window['-STOP-'].update(disabled=True)

                if not self.window or not hasattr(self.window, 'TKroot') or not self.window.TKroot or not self.window.TKroot.winfo_exists(): # Re-check before refresh
                    self.log_message("Simulation_monitor: Window closed before refresh, exiting monitor loop.")
                    break
                self.window.refresh()

            except (sg.tk.TclError, TypeError, AttributeError, RuntimeError) as e: 
                err_msg = str(e).lower()
                if "window was closed" in err_msg or "application has been destroyed" in err_msg or "invalid command name" in err_msg:
                    self.log_message("Simulation_monitor: Breaking loop due to window destruction error.")
                    break 
                else:
                    self.log_message(f"Simulation_monitor: Error in main loop (GUI related): {type(e).__name__}: {e}")
                    # Depending on the error, might still be safe to continue if not window destruction
            except Exception as e:
                self.log_message(f"Simulation_monitor: Generic error in main loop: {type(e).__name__}: {e}")
                # For truly unexpected errors, breaking might be safer
                # break 

            if not self.running: 
                break
            time.sleep(0.1) 
        
        self.log_message(f"Simulation_monitor main loop exited. self.running: {self.running}, sim valid: {self.simulation is not None}")

        try:
            if self.window and hasattr(self.window, 'TKroot') and self.window.TKroot and self.window.TKroot.winfo_exists():
                self.log_message("Simulation_monitor: Attempting final GUI update post-loop.")
                if self.simulation: 
                    self.update_statistics()
                    self.draw_thread_visualization() 
                elif hasattr(self, 'draw_initial_displays'): 
                    self.draw_initial_displays(self.window)
                
                self.window.refresh()
                self.log_message("Simulation_monitor: Final GUI update post-loop completed.")
            # else:
                # self.log_message("Simulation_monitor: Window or TKroot destroyed, skipping final update post-loop.")
        except (sg.tk.TclError, TypeError, AttributeError, RuntimeError) as e:
            err_msg = str(e).lower()
            if "window was closed" in err_msg or "application has been destroyed" in err_msg or "invalid command name" in err_msg or "none" in err_msg:
                # self.log_message(f"Simulation_monitor: Final update skipped, window closed/destroyed. ({type(e).__name__}: {e})")
                pass
            else:
                self.log_message(f"Simulation_monitor: Error during final GUI update (specific): {type(e).__name__}: {e}")
        except Exception as e:
            self.log_message(f"Simulation_monitor: Error during final GUI update (generic): {type(e).__name__}: {e}")
        
        self.log_message(f"Simulation_monitor thread exiting. self.running: {self.running}")

    def stop_simulation(self):
        """Stop the current simulation"""
        self.log_message("Stopping simulation...")
        self.running = False # Signal simulation_monitor to stop its loop

        if self.simulation:
            self.simulation.stop_simulation() # Signal ProducerConsumerSimulation to stop its threads

        # Wait for the actual simulation logic thread (sim_thread) to finish
        # This ensures ProducerConsumerSimulation.join_all() completes.
        if self.sim_thread and self.sim_thread.is_alive():
            self.sim_thread.join(timeout=1.0) # Adjust timeout as needed
        self.sim_thread = None
        
        if self.window and hasattr(self.window, 'TKroot') and self.window.TKroot and self.window.TKroot.winfo_exists(): 
            try:
                self.window['-START-'].update(disabled=False)
                self.window['-STOP-'].update(disabled=True)
            except (sg.tk.TclError, AttributeError, RuntimeError) as e: 
                # print(f"Debug: Error updating buttons in stop_simulation (likely window closed): {e}")
                pass # Suppress error if window is closing
            except Exception as e:
                self.log_message(f"Error updating buttons in stop_simulation: {type(e).__name__}: {e}")
        # else:
            # print("Debug: Window closed or invalid in stop_simulation, skipping button update.")

        self.log_message("Simulation stopped.")

    def reset_simulation(self):
        """Reset the simulation"""
        self.log_message("Resetting simulation...")
        self.stop_simulation() # This now handles stopping self.running, self.simulation.running, and joining sim_thread

        # Wait for the simulation_monitor thread to finish its current operations and exit its loop.
        # self.running is already False.
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1.0) # Wait for simulation_monitor to finish its post-loop cleanup
        self.update_thread = None

        # At this point, simulation_monitor and sim_thread are no longer running.
        # It's safe to modify self.simulation and update GUI from the main thread.

        self.simulation = None # Clear the simulation object
        self.log_messages.clear()

        if self.window and hasattr(self.window, 'TKroot') and self.window.TKroot and self.window.TKroot.winfo_exists():
            try:
                self.draw_initial_displays(self.window) # Reset graphs

                # Reset statistics text
                self.window['-STAT_PRODUCED-'].update('0')
                self.window['-STAT_CONSUMED-'].update('0')
                self.window['-STAT_BUFFER-'].update('0/0')
                self.window['-STAT_THREADS-'].update('0')
                self.window['-LOG-'].update('')

                # Ensure buttons are in correct state after reset (already done by stop_simulation, but good to be sure)
                self.window['-START-'].update(disabled=False)
                self.window['-STOP-'].update(disabled=True)

            except (sg.tk.TclError, AttributeError, RuntimeError) as e: 
                # print(f"Debug: Error resetting GUI elements in reset_simulation (likely window closed): {e}")
                pass # Suppress error if window is closing
            except Exception as e:
                 self.log_message(f"Error resetting GUI elements: {type(e).__name__}: {e}")
        # else:
            # print("Debug: Window closed or invalid in reset_simulation, skipping GUI reset.")
        
        self.log_message("Simulation reset complete.")

    def handle_event(self, event, values):
        """Handle GUI events"""
        if event == sg.WIN_CLOSED:
            self.log_message("Window closed event received.")
            self.stop_simulation() # Try to gracefully stop threads
            # Wait for monitor thread before allowing window to close, to avoid GUI update errors
            if self.update_thread and self.update_thread.is_alive():
                self.update_thread.join(timeout=0.5) 
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