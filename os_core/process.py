import itertools

class PCB:
    _pid_counter = itertools.count(1)

    def __init__(self, name, memory_requirements_bytes, priority=0, burst_time=10): # Added burst_time
        self.pid = next(PCB._pid_counter)
        self.name = name
        self.state = 'NEW'  # NEW, READY, RUNNING, WAITING, TERMINATED
        self.memory_requirements_bytes = memory_requirements_bytes
        self.num_pages_required = (memory_requirements_bytes + page_size - 1) // page_size # Calculate pages
        self.page_table = {}  # Virtual Page Num -> PageTableEntry object
        self.program_counter = 0
        self.registers = {}
        self.priority = priority
        self.open_files = []
        self.burst_time = burst_time  # Total time needed
        self.remaining_time = burst_time # Time left to execute
        self.time_in_current_quantum = 0 # For RR and MLFQ

    @staticmethod
    def reset_pid_counter():
        """Resets the class-level PID counter to start from 1 again."""
        PCB._pid_counter = itertools.count(1)