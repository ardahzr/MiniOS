import PySimpleGUI as sg
import random
import numpy as np
from sklearn.tree import DecisionTreeClassifier
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class MLSchedulerSim:
    def __init__(self):
        self.processes = []
        self.completed_processes_stats = []
        self.time = 0
        self.pid_counter = 1
        self.model = DecisionTreeClassifier(random_state=42)
        self.trained = False
        self.timeline = []

        sg.theme('DarkBlue3')

        table_frame_layout = [
            [sg.Table(values=[], headings=['PID', 'Priority', 'Burst', 'State', 'Arrival'],
                      key='-TABLE-', auto_size_columns=False,
                      col_widths=[5, 8, 7, 10, 7],
                      justification='center', num_rows=8, font=('Arial', 11), expand_x=True)]
        ]
        log_frame_layout = [
            [sg.Text('Log:', font=('Arial', 10, 'bold'))],
            [sg.Multiline('', size=(60, 8), key='-LOG-', disabled=True, font=('Consolas', 11),
                          autoscroll=True, background_color='#181c24', text_color='#80c8ff')]
        ]
        graph_frame_layout = [
            [sg.Canvas(key='-CANVAS-', size=(450, 220))]
        ]
        status_bar = [sg.Text(f'Time: {self.time}', key='-TIME_STATUS-', font=('Arial', 10)),
                      sg.Text('Model: Not Trained', key='-MODEL_STATUS-', font=('Arial', 10), justification='right', expand_x=True)]

        button_row = [
            sg.Button('Add Process', size=(12, 1), font=('Arial', 10)),
            sg.Button('Train Model', size=(12, 1), font=('Arial', 10)),
            sg.Button('Step Simulation', size=(14, 1), font=('Arial', 10)),
            sg.Button('Reset', size=(10, 1), font=('Arial', 10)),
            sg.Button('Close', size=(10, 1), font=('Arial', 10))
        ]

        layout_col1 = [
            [sg.Frame('Processes', table_frame_layout, expand_x=True, expand_y=True)],
            [sg.Frame('Simulation Log', log_frame_layout, expand_x=True, expand_y=True)],
        ]
        layout_col2 = [
            [sg.Frame('CPU Timeline Gantt Chart', graph_frame_layout, expand_x=True, expand_y=True)]
        ]

        layout = [
            [sg.Text('ML-Powered CPU Scheduler Simulation', font=('Arial', 18, 'bold'), justification='center', expand_x=True)],
            status_bar,
            [sg.Column(layout_col1, expand_x=True, expand_y=True), sg.Column(layout_col2, expand_x=True, expand_y=True)],
            button_row
        ]
        self.window = sg.Window('ML Scheduler Simulator', layout, finalize=True, keep_on_top=False, resizable=True)

        # Matplotlib Figure
        self.fig, self.ax = plt.subplots(figsize=(5, 2.5))
        self.fig.patch.set_alpha(0)
        self.ax.patch.set_alpha(0)
        plt.style.use('dark_background')
        self.ax.tick_params(colors='white', labelsize=12)
        self.ax.xaxis.label.set_color('white')
        self.ax.title.set_color('white')

        self.fig_canvas_agg = FigureCanvasTkAgg(self.fig, master=self.window['-CANVAS-'].TKCanvas)
        self.fig_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
        self.draw_timeline()
        self.update_status_bar()
        self.update_table()

    def add_process(self):
        priority = random.randint(1, 10)
        burst = random.randint(2, 10)
        new_pid = self.pid_counter
        self.processes.append({
            'pid': new_pid,
            'priority': priority,
            'burst': burst,
            'initial_burst': burst,
            'state': 'Ready',
            'arrival_time': self.time
        })
        self.pid_counter += 1
        self.update_table()
        self.log_message(f"Process PID {new_pid} added (Priority: {priority}, Burst: {burst}, Arrival: {self.time}).")

    def train_model(self):
        trainable_processes = [p for p in self.processes if p['state'] != 'Finished']
        if not trainable_processes:
            self.log_message("No suitable process to train the model (all finished or none exist).")
            self.trained = False
            self.update_status_bar()
            return

        X_train_local = []
        y_train_local = []
        for p in trainable_processes:
            X_train_local.append([p['priority'], p['burst']])
            y_train_local.append(1 if p['burst'] < 5 and p['priority'] > 7 else 0)

        if not X_train_local:
            self.log_message("No valid data for training.")
            self.trained = False
            self.update_status_bar()
            return

        if len(set(y_train_local)) < 2:
            self.log_message("Warning: All training labels are the same. Model learning may be limited.")

        try:
            self.model.fit(np.array(X_train_local), np.array(y_train_local))
            self.trained = True
            self.log_message("Model trained successfully!")
        except Exception as e:
            self.log_message(f"Model training error: {e}")
            self.trained = False
        self.update_status_bar()

    def ml_select(self):
        ready_processes = [p for p in self.processes if p['state'] == 'Ready']
        if not ready_processes:
            return None

        if not self.trained:
            self.log_message("Model not trained, selecting highest priority (then FIFO) process.", is_warning=True)
            ready_processes.sort(key=lambda p: (-p['priority'], p['arrival_time']))
            return ready_processes[0]

        X_ready_features = np.array([[p['priority'], p['burst']] for p in ready_processes])
        try:
            predictions = self.model.predict(X_ready_features)
            for i, p in enumerate(ready_processes):
                if predictions[i] == 1:
                    return p
            self.log_message("ML model did not select any process as '1', selecting highest priority (then FIFO).", is_warning=True)
            ready_processes.sort(key=lambda p: (-p['priority'], p['arrival_time']))
            return ready_processes[0]
        except Exception as e:
            self.log_message(f"ML prediction error: {e}. Fallback used.", is_warning=True)
            ready_processes.sort(key=lambda p: (-p['priority'], p['arrival_time']))
            return ready_processes[0]

    def step(self):
        step_log_messages = []
        executed_pid_this_step = None

        running_process = next((p for p in self.processes if p['state'] == 'Running'), None)
        if running_process:
            running_process['burst'] -= 1
            step_log_messages.append(f"PID {running_process['pid']} (Priority:{running_process['priority']}) continues. Remaining burst: {running_process['burst']}.")
            executed_pid_this_step = running_process['pid']
            if running_process['burst'] <= 0:
                running_process['state'] = 'Finished'
                running_process['completion_time'] = self.time + 1
                step_log_messages.append(f"PID {running_process['pid']} finished (CT: {running_process['completion_time']}).")
                self.completed_processes_stats.append(running_process.copy())
        else:
            selected_proc_for_new_run = self.ml_select()
            if selected_proc_for_new_run:
                selected_proc_for_new_run['state'] = 'Running'
                selected_proc_for_new_run['burst'] -= 1
                step_log_messages.append(f"PID {selected_proc_for_new_run['pid']} (Priority:{selected_proc_for_new_run['priority']}) started. Remaining burst: {selected_proc_for_new_run['burst']}.")
                executed_pid_this_step = selected_proc_for_new_run['pid']
                if selected_proc_for_new_run['burst'] <= 0:
                    selected_proc_for_new_run['state'] = 'Finished'
                    selected_proc_for_new_run['completion_time'] = self.time + 1
                    step_log_messages.append(f"PID {selected_proc_for_new_run['pid']} finished (CT: {selected_proc_for_new_run['completion_time']}).")
                    self.completed_processes_stats.append(selected_proc_for_new_run.copy())
            else:
                active_processes = [p for p in self.processes if p['state'] not in ['Finished']]
                if not self.processes:
                    step_log_messages.append("No processes in the system.")
                elif not active_processes:
                    step_log_messages.append("All processes finished.")
                else:
                    step_log_messages.append("CPU idle. No 'Ready' process to run or select.")

        if executed_pid_this_step is not None:
            self.timeline.append((self.time, executed_pid_this_step))
        elif not step_log_messages:
            step_log_messages.append("CPU idle.")

        log_prefix = f"Time {self.time}:"
        self.log_message(f"{log_prefix} {' '.join(step_log_messages)}")

        self.time += 1
        self.update_table()
        self.draw_timeline()
        self.update_status_bar()

    def update_table(self):
        table_data = [[p['pid'], p['priority'], p['burst'], p['state'], p.get('arrival_time', 'N/A')]
                      for p in self.processes]
        self.window['-TABLE-'].update(values=table_data)

    def update_status_bar(self):
        self.window['-TIME_STATUS-'].update(f'Time: {self.time}')
        model_status_text = 'Model: Trained' if self.trained else 'Model: Not Trained'
        model_color = 'lightgreen' if self.trained else 'pink'
        self.window['-MODEL_STATUS-'].update(model_status_text, text_color=model_color)

    def draw_timeline(self):
        self.ax.clear()
        self.ax.set_facecolor('#23272e')
        self.fig.patch.set_facecolor('#23272e')

        if self.timeline:
            unique_pids = sorted(list(set(pid for _, pid in self.timeline)))
            color_map = {pid: plt.cm.get_cmap('tab20')(i % 20) for i, pid in enumerate(unique_pids)}
            for t_start, pid in self.timeline:
                self.ax.barh(f'P{pid}', 1, left=t_start, color=color_map[pid], edgecolor='white', height=0.7)
            y_labels = sorted(list(set(f'P{pid}' for _, pid in self.timeline)), key=lambda x: int(x[1:]))
            self.ax.set_yticks(range(len(y_labels)))
            self.ax.set_yticklabels(y_labels, color='#80c8ff', fontsize=13, fontweight='bold')
            self.ax.invert_yaxis()
            # Write PID on each bar
            for t_start, pid in self.timeline:
                self.ax.text(t_start + 0.5, y_labels.index(f'P{pid}'), f'P{pid}', va='center', ha='center', fontsize=11, color='white', fontweight='bold')
        else:
            self.ax.set_yticks([])

        self.ax.set_xlabel('Time', color='#80c8ff', fontsize=12, fontweight='bold')
        max_time_on_timeline = 0
        if self.timeline:
            times, _ = zip(*self.timeline)
            if times:
                max_time_on_timeline = max(times)
        current_max_xaxis = max(10, max_time_on_timeline + 2, self.time + 1)
        self.ax.set_xlim(-0.5, current_max_xaxis)
        self.ax.set_title('CPU Timeline', color='#80c8ff', fontsize=14, fontweight='bold')
        self.ax.grid(axis='x', color='#444', linestyle='--', linewidth=0.7)
        self.fig.tight_layout(pad=0.5)
        self.fig_canvas_agg.draw()

    def log_message(self, message, is_warning=False, clear_before=False):
        if self.window and not self.window.is_closed():
            log_text_color = "#ffb347" if is_warning else "#80c8ff"
            if clear_before:
                self.window['-LOG-'].update(message + "\n", text_color_for_value=log_text_color)
            else:
                self.window['-LOG-'].update(message + "\n", append=True, text_color_for_value=log_text_color)

    def reset_simulation(self):
        self.processes = []
        self.completed_processes_stats = []
        self.time = 0
        self.pid_counter = 1
        self.trained = False
        self.timeline = []
        self.log_message("Simulation reset.", clear_before=True)
        self.update_table()
        self.draw_timeline()
        self.update_status_bar()

    # For MainWindow compatibility:
    def handle_event(self, event, values):
        if event in (sg.WIN_CLOSED, 'Close'):
            return 'close'
        elif event == 'Add Process':
            self.add_process()
        elif event == 'Train Model':
            self.train_model()
        elif event == 'Step Simulation':
            self.step()
        elif event == 'Reset':
            self.reset_simulation()
        return None

    def run(self):
        while True:
            event, values = self.window.read()
            result = self.handle_event(event, values)
            if result == 'close':
                break
        plt.close(self.fig)
        self.window.close()

if __name__ == '__main__':
    sim = MLSchedulerSim()
    sim.run()