from abc import ABC, abstractmethod

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
        self.queues = [[] for _ in range(levels)]
        self.time_quanta = time_quanta or [5, 10, 20]

    def add_process(self, pcb):
        self.queues[0].append(pcb)

    def get_next(self):
        for lvl, queue in enumerate(self.queues):
            if queue:
                pcb = queue.pop(0)
                return pcb, self.time_quanta[lvl]
        return None, None