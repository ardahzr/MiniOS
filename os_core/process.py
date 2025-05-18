import itertools

class PCB:
    _pid_counter = itertools.count(1)

    def __init__(self, name, memory_requirements):
        self.pid = next(PCB._pid_counter)
        self.name = name
        self.state = 'NEW'  # NEW, READY, RUNNING, WAITING, TERMINATED
        self.memory_requirements = memory_requirements
        # Add registers, program counter, etc.