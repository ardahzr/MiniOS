from abc import ABC, abstractmethod
from collections import deque # Add deque for other schedulers

class Scheduler(ABC):
    @abstractmethod
    def add_process(self, pcb):
        pass

    @abstractmethod
    def get_next(self):
        pass

# MLFQ Scheduler Example
class MLFQScheduler(Scheduler):
    def __init__(self, levels=3, time_quanta=None):
        self.levels = levels
        self.queues = [deque() for _ in range(levels)] # Use deque for queues
        self.time_quanta = time_quanta or [5, 10, 15] # Adjusted default quanta

    def add_process(self, pcb, level=0): # Allow specifying level, default to highest
        if 0 <= level < self.levels:
            pcb.state = 'READY'
            self.queues[level].append(pcb)
        else:
            # Add to highest priority queue if level is invalid
            self.queues[0].append(pcb)


    def get_next(self):
        for lvl, queue in enumerate(self.queues):
            if queue:
                pcb = queue.popleft()
                pcb.state = 'RUNNING'
                return pcb, self.time_quanta[lvl]
        return None, None

    def get_all_queues_str_list(self):
        return [f"Q{i} (TQ:{self.time_quanta[i]}): " + (" -> ".join([f"{p.name}({p.remaining_time})" for p in self.queues[i]]) if self.queues[i] else "Empty") for i in range(self.levels)]

# FIFO Scheduler
class FIFOScheduler(Scheduler):
    def __init__(self):
        self.ready_queue = deque()

    def add_process(self, pcb):
        pcb.state = 'READY'
        self.ready_queue.append(pcb)

    def get_next(self):
        if self.ready_queue:
            pcb = self.ready_queue.popleft()
            pcb.state = 'RUNNING'
            # FIFO runs until completion or I/O block, for simulation, TQ is effectively infinite
            return pcb, float('inf')
        return None, None

    def get_all_queues_str_list(self): # For consistent interface
        return ["FIFO: " + (" -> ".join([f"{p.name}({p.remaining_time})" for p in self.ready_queue]) if self.ready_queue else "Empty")]

# Round Robin Scheduler
class RoundRobinScheduler(Scheduler):
    def __init__(self, time_quantum=5):
        self.ready_queue = deque()
        self.time_quantum = time_quantum

    def add_process(self, pcb):
        pcb.state = 'READY'
        self.ready_queue.append(pcb)

    def get_next(self):
        if self.ready_queue:
            pcb = self.ready_queue.popleft()
            pcb.state = 'RUNNING'
            return pcb, self.time_quantum
        return None, None

    def get_all_queues_str_list(self): # For consistent interface
        return ["RR: " + (" -> ".join([f"{p.name}({p.remaining_time})" for p in self.ready_queue]) if self.ready_queue else "Empty")]