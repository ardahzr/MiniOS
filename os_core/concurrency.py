import threading
import time
import random
from typing import List, Callable, Any

class ThreadAPI:
    """Basic thread API with enhanced functionality"""
    
    def __init__(self):
        self.threads: List[threading.Thread] = []
        self.thread_states = {}
        self.lock = threading.Lock()
    
    def create_thread(self, target: Callable, args: tuple = (), name: str = None) -> threading.Thread:
        """Create a new thread"""
        thread = threading.Thread(target=target, args=args, name=name)
        with self.lock:
            self.threads.append(thread)
        return thread
    
    def start_thread(self, thread: threading.Thread):
        """Start a thread"""
        thread.start()
    
    def join_all(self):
        """Join all threads"""
        for thread in self.threads:
            if thread.is_alive():
                thread.join()

# class ReadersWritersLock:
#     """Readers-Writers lock implementation"""
    
#     def __init__(self):
#         self._readers = 0
#         self._writers = 0
#         self._read_ready = threading.Condition(threading.RLock())
#         self._write_ready = threading.Condition(threading.RLock())
    
#     def acquire_read(self):
#         """Acquire read lock"""
#         with self._read_ready:
#             while self._writers > 0:
#                 self._read_ready.wait()
#             self._readers += 1
    
#     def release_read(self):
#         """Release read lock"""
#         with self._read_ready:
#             self._readers -= 1
#             if self._readers == 0:
#                 self._read_ready.notifyAll()
    
#     def acquire_write(self):
#         """Acquire write lock"""
#         with self._write_ready:
#             while self._writers > 0 or self._readers > 0:
#                 self._write_ready.wait()
#             self._writers += 1
    
#     def release_write(self):
#         """Release write lock"""
#         with self._write_ready:
#             self._writers -= 1
#             self._write_ready.notifyAll()
#             with self._read_ready:
#                 self._read_ready.notifyAll()

class ProducerConsumerSimulation:

    """Enhanced Producer-Consumer simulation with real-time monitoring"""
    def __init__(self, buffer_size=10, logger: Callable[[str], None] = None): # Added logger parameter
        self.buffer_size = buffer_size
        self.buffer = []
        
        # Synchronization primitives
        self.mutex = threading.Lock()
        
        # Semaphores for demonstration
        self.empty = threading.Semaphore(buffer_size)
        self.full = threading.Semaphore(0)
        
        # Statistics
        self.produced_count = 0
        self.consumed_count = 0
        self.stats_lock = threading.Lock()
        
        # Real-time monitoring
        self.running = False

        self.thread_api = ThreadAPI()
        self.logger = logger if logger else print # Use provided logger or default to print

    def _log(self, message: str):
        """Internal log method to use the provided logger."""
        if self.logger:
            self.logger(message)

    def put(self, item):
        """Add item to buffer"""
        self.buffer.append(item)

    def get(self):
        """Remove and return item from buffer"""
        if self.buffer:
            return self.buffer.pop()
        return None

    def producer(self, producer_id: int, items: List[Any], delay: float = 0.1):
        """Enhanced producer with real-time monitoring"""
        for item in items:
            if not self.running:
                break
                
            # Acquire semaphore (wait for empty slot)
            self.empty.acquire()
            
            # Critical section
            with self.mutex:
                self.put(f"P{producer_id}-{item}")
                with self.stats_lock:
                    self.produced_count += 1
                
                buffer_state = list(self.buffer)
                self._log(f"Producer {producer_id} produced: P{producer_id}-{item}") # Changed print to self._log
                self._log(f"Buffer state: {buffer_state} (size: {len(self.buffer)})") # Changed print to self._log
                
            
            # Release semaphore (signal filled slot)
            self.full.release()
            
            # Simulate production time
            time.sleep(delay + random.uniform(0, 0.05))

    def consumer(self, consumer_id: int, count: int, delay: float = 0.15):
        """Enhanced consumer with real-time monitoring"""
        consumed = 0
        while consumed < count and self.running:
            # Acquire semaphore (wait for filled slot)
            self.full.acquire()
            
            # Critical section
            with self.mutex:
                item = self.get()
                if item is not None:
                    with self.stats_lock:
                        self.consumed_count += 1
                    consumed += 1
                    
                    buffer_state = list(self.buffer)
                    self._log(f"Consumer {consumer_id} consumed: {item}") # Changed print to self._log
                    self._log(f"Buffer state: {buffer_state} (size: {len(self.buffer)})") # Changed print to self._log
                else:
                    self._log(f"Consumer {consumer_id}: Buffer empty!") # Changed print to self._log

            # Release semaphore (signal empty slot)
            self.empty.release()
            
            # Simulate consumption time
            time.sleep(delay + random.uniform(0, 0.05))

    def start_simulation(self, num_producers: int = 2, num_consumers: int = 2, 
                        items_per_producer: int = 5, items_per_consumer: int = 5,
                        producer_delay: float = 1, consumer_delay: float = 1.5):
        """Start multi-threaded producer-consumer simulation"""
        self.running = True
        
        self._log(f"Starting simulation with {num_producers} producers and {num_consumers} consumers") # Changed print to self._log
        self._log(f"Buffer size: {self.buffer_size}") # Changed print to self._log
        self._log("-" * 60) # Changed print to self._log
        
        # Create producer threads
        for i in range(num_producers):
            items = list(range(1, items_per_producer + 1))
            thread = self.thread_api.create_thread(
                target=self.producer, 
                args=(i + 1, items, producer_delay + i * 0.05),
                name=f"Producer-{i+1}"
            )
        
        # Create consumer threads
        for i in range(num_consumers):
            thread = self.thread_api.create_thread(
                target=self.consumer, 
                args=(i + 1, items_per_consumer, consumer_delay + i * 0.05),
                name=f"Consumer-{i+1}"
            )
        
        # Start all threads
        for thread in self.thread_api.threads:
            self.thread_api.start_thread(thread)

        # Wait for all threads to complete
        self.thread_api.join_all()
        
        self.running = False
        
        self._log("-" * 60) # Changed print to self._log
        self._log("Simulation complete!") # Changed print to self._log
        self._log(f"Total produced: {self.produced_count}") # Changed print to self._log
        self._log(f"Total consumed: {self.consumed_count}") # Changed print to self._log
        self._log(f"Final buffer size: {len(self.buffer)}") # Changed print to self._log
        self._log(f"Remaining items: {list(self.buffer)}") # Changed print to self._log

    def get_stats(self) -> dict:
        """Get current simulation statistics"""
        with self.stats_lock:
            return {
                "produced": self.produced_count,
                "consumed": self.consumed_count,
                "buffer_size": len(self.buffer),
                "buffer_capacity": self.buffer_size,
                "buffer_contents": list(self.buffer)
            }
    
    def stop_simulation(self):
        """Stop the simulation gracefully"""
        self.running = False
        self._log("Simulation stopped.") # Changed print to self._log

# class DiningPhilosophers:
#     """Classical Dining Philosophers problem implementation"""
    
#     def __init__(self, num_philosophers: int = 5):
#         self.num_philosophers = num_philosophers
#         self.forks = [threading.Lock() for _ in range(num_philosophers)]
#         self.eating_count = [0] * num_philosophers
#         self.state = ["THINKING"] * num_philosophers
#         self.observers = []
#         self.running = False
    
#     def add_observer(self, callback: Callable):
#         """Add observer for real-time updates"""
#         self.observers.append(callback)
    
#     def notify_observers(self, philosopher_id: int, state: str):
#         """Notify observers of philosopher state change"""
#         self.state[philosopher_id] = state
#         for observer in self.observers:
#             try:
#                 observer("philosopher_state", {
#                     "philosopher_id": philosopher_id,
#                     "state": state,
#                     "eating_count": self.eating_count[philosopher_id],
#                     "all_states": self.state.copy()
#                 })
#             except Exception as e:
#                 print(f"Observer error: {e}")
    
#     def philosopher(self, philosopher_id: int):
#         """Philosopher thread function"""
#         left_fork = philosopher_id
#         right_fork = (philosopher_id + 1) % self.num_philosophers
        
#         while self.running:
#             # Think
#             self.notify_observers(philosopher_id, "THINKING")
#             print(f"Philosopher {philosopher_id} is thinking...")
#             time.sleep(random.uniform(1, 3))
            
#             # Try to eat
#             self.notify_observers(philosopher_id, "HUNGRY")
#             print(f"Philosopher {philosopher_id} is hungry...")
            
#             # Acquire forks (avoid deadlock by ordering)
#             first_fork = min(left_fork, right_fork)
#             second_fork = max(left_fork, right_fork)
            
#             with self.forks[first_fork]:
#                 print(f"Philosopher {philosopher_id} picked up fork {first_fork}")
#                 with self.forks[second_fork]:
#                     print(f"Philosopher {philosopher_id} picked up fork {second_fork}")
                    
#                     # Eat
#                     self.notify_observers(philosopher_id, "EATING")
#                     self.eating_count[philosopher_id] += 1
#                     print(f"Philosopher {philosopher_id} is eating (meal #{self.eating_count[philosopher_id]})")
#                     time.sleep(random.uniform(1, 2))
                    
#                     print(f"Philosopher {philosopher_id} put down fork {second_fork}")
#                 print(f"Philosopher {philosopher_id} put down fork {first_fork}")
    
#     def start_simulation(self, duration: int = 30):
#         """Start the dining philosophers simulation"""
#         self.running = True
#         threads = []
        
#         print(f"Starting Dining Philosophers with {self.num_philosophers} philosophers")
#         print(f"Simulation will run for {duration} seconds")
#         print("-" * 60)
        
#         # Create philosopher threads
#         for i in range(self.num_philosophers):
#             thread = threading.Thread(
#                 target=self.philosopher,
#                 args=(i,),
#                 name=f"Philosopher-{i}"
#             )
#             threads.append(thread)
#             thread.start()
        
#         # Let simulation run
#         time.sleep(duration)
        
#         # Stop simulation
#         self.running = False
        
#         # Wait for threads to finish
#         for thread in threads:
#             thread.join(timeout=2)
        
#         print("-" * 60)
#         print("Dining Philosophers simulation complete!")
#         for i, count in enumerate(self.eating_count):
#             print(f"Philosopher {i}: ate {count} times")

# class FileIOSimulation:
#     """Simulate concurrent file I/O operations"""

#     def __init__(self):
#         self.file_locks = {}
#         self.operations_count = 0
#         self.ops_lock = threading.Lock()
#         self.observers = []
#         self.running = False
    
#     def add_observer(self, callback: Callable):
#         """Add observer for real-time updates"""
#         self.observers.append(callback)
    
#     def notify_observers(self, operation: str, data: dict):
#         """Notify observers of file operations"""
#         for observer in self.observers:
#             try:
#                 observer("file_operation", {
#                     "operation": operation,
#                     "data": data,
#                     "total_operations": self.operations_count
#                 })
#             except Exception as e:
#                 print(f"Observer error: {e}")
    
#     def get_file_lock(self, filename: str) -> threading.Lock:
#         """Get or create a lock for a specific file"""
#         if filename not in self.file_locks:
#             self.file_locks[filename] = threading.Lock()
#         return self.file_locks[filename]
    
#     def read_file(self, thread_id: int, filename: str):
#         """Simulate reading a file"""
#         file_lock = self.get_file_lock(filename)
        
#         print(f"Thread {thread_id}: Attempting to read {filename}")
#         with file_lock:
#             with self.ops_lock:
#                 self.operations_count += 1
            
#             self.notify_observers("READ_START", {
#                 "thread_id": thread_id,
#                 "filename": filename
#             })
            
#             print(f"Thread {thread_id}: Reading {filename}...")
#             time.sleep(random.uniform(0.5, 1.5))  # Simulate I/O time
            
#             self.notify_observers("READ_COMPLETE", {
#                 "thread_id": thread_id,
#                 "filename": filename
#             })
            
#             print(f"Thread {thread_id}: Finished reading {filename}")
    
#     def write_file(self, thread_id: int, filename: str, data: str):
#         """Simulate writing to a file"""
#         file_lock = self.get_file_lock(filename)
        
#         print(f"Thread {thread_id}: Attempting to write to {filename}")
#         with file_lock:
#             with self.ops_lock:
#                 self.operations_count += 1
            
#             self.notify_observers("WRITE_START", {
#                 "thread_id": thread_id,
#                 "filename": filename,
#                 "data": data
#             })
            
#             print(f"Thread {thread_id}: Writing to {filename}...")
#             time.sleep(random.uniform(1, 2))  # Simulate I/O time
            
#             self.notify_observers("WRITE_COMPLETE", {
#                 "thread_id": thread_id,
#                 "filename": filename,
#                 "data": data
#             })
            
#             print(f"Thread {thread_id}: Finished writing to {filename}")
    
#     def file_worker(self, worker_id: int, operations: List[dict]):
#         """Worker thread that performs file operations"""
#         for op in operations:
#             if not self.running:
#                 break
                
#             if op["type"] == "read":
#                 self.read_file(worker_id, op["filename"])
#             elif op["type"] == "write":
#                 self.write_file(worker_id, op["filename"], op.get("data", f"Data from worker {worker_id}"))
            
#             # Small delay between operations
#             time.sleep(random.uniform(0.1, 0.3))
    
#     def start_simulation(self, num_workers: int = 3, ops_per_worker: int = 5):
#         """Start concurrent file I/O simulation"""
#         self.running = True
#         threads = []
        
#         print(f"Starting File I/O simulation with {num_workers} workers")
#         print("-" * 60)
        
#         files = ["file1.txt", "file2.txt", "file3.txt", "shared.txt"]
        
#         # Create worker threads
#         for worker_id in range(num_workers):
#             operations = []
#             for _ in range(ops_per_worker):
#                 op_type = random.choice(["read", "write"])
#                 filename = random.choice(files)
#                 operations.append({
#                     "type": op_type,
#                     "filename": filename,
#                     "data": f"Data from worker {worker_id}" if op_type == "write" else None
#                 })
            
#             thread = threading.Thread(
#                 target=self.file_worker,
#                 args=(worker_id, operations),
#                 name=f"FileWorker-{worker_id}"
#             )
#             threads.append(thread)
#             thread.start()
        
#         # Wait for all workers to complete
#         for thread in threads:
#             thread.join()
        
#         self.running = False
        
#         print("-" * 60)
#         print("File I/O simulation complete!")
#         print(f"Total operations performed: {self.operations_count}")

def demo_concurrency():
    """Demonstrate all concurrency primitives"""
    print("=" * 80)
    print("CONCURRENCY & SYNCHRONIZATION DEMONSTRATION")
    print("=" * 80)
    
    # Demo 1: Enhanced Producer-Consumer
    print("\n1. PRODUCER-CONSUMER SIMULATION")
    print("=" * 50)
    # For demo purposes, we'll use the default print logger here
    pc_sim = ProducerConsumerSimulation(buffer_size=5) 
    pc_sim.start_simulation(num_producers=2, num_consumers=2, 
                           items_per_producer=3, items_per_consumer=3)
    
    time.sleep(2)
    
    # # Demo 2: Dining Philosophers
    # print("\n2. DINING PHILOSOPHERS PROBLEM")
    # print("=" * 50)
    # philosophers = DiningPhilosophers(num_philosophers=5)
    # philosophers.start_simulation(duration=10)
    
    # time.sleep(2)
    
    # # Demo 3: File I/O Simulation
    # print("\n3. CONCURRENT FILE I/O SIMULATION")
    # print("=" * 50)
    # file_sim = FileIOSimulation()
    # file_sim.start_simulation(num_workers=3, ops_per_worker=3)
    
    print("\n" + "=" * 80)
    print("ALL CONCURRENCY DEMONSTRATIONS COMPLETE!")
    print("=" * 80)
    

if __name__ == "__main__":
    demo_concurrency()