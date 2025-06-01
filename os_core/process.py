import itertools

class PCB:
    _pid_counter = itertools.count(1)

    def __init__(self, name, memory_requirements_bytes, page_size):
        self.pid = next(PCB._pid_counter)
        self.name = name
        self.state = 'NEW'  # NEW, READY, RUNNING, WAITING, TERMINATED
        self.memory_requirements_bytes = memory_requirements_bytes
        self.num_pages_required = (memory_requirements_bytes + page_size - 1) // page_size # Calculate pages
        self.page_table = {}  # Virtual Page Num -> PageTableEntry object
        # Add registers, program counter, etc.

    @staticmethod
    def reset_pid_counter():
        """Resets the class-level PID counter to start from 1 again."""
        PCB._pid_counter = itertools.count(1)