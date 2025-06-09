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

class ThreadInfo:
    def __init__(self, name, state='Ready', progress=0.0):
        self.name = name
        self.state = state
        self.progress = progress

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
        thread_name = threading.current_thread().name
        # Set state to Running
        with self.thread_api.lock:
            if thread_name in self.thread_api.thread_states:
                self.thread_api.thread_states[thread_name].state = 'Running'
        total = len(items)
        for idx, item in enumerate(items):
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
            
            # Update progress
            with self.thread_api.lock:
                if thread_name in self.thread_api.thread_states:
                    self.thread_api.thread_states[thread_name].progress = ((idx+1)/total)*100
            # Simulate production time
            time.sleep(delay + random.uniform(0, 0.05))
        # Set state to Finished
        with self.thread_api.lock:
            if thread_name in self.thread_api.thread_states:
                self.thread_api.thread_states[thread_name].state = 'Finished'
                self.thread_api.thread_states[thread_name].progress = 100.0

    def consumer(self, consumer_id: int, count: int, delay: float = 0.15):
        thread_name = threading.current_thread().name
        # Set state to Running
        with self.thread_api.lock:
            if thread_name in self.thread_api.thread_states:
                self.thread_api.thread_states[thread_name].state = 'Running'
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
            
            # Update progress
            with self.thread_api.lock:
                if thread_name in self.thread_api.thread_states:
                    self.thread_api.thread_states[thread_name].progress = ((consumed)/count)*100
            # Simulate consumption time
            time.sleep(delay + random.uniform(0, 0.05))        # Set state to Finished
        with self.thread_api.lock:
            if thread_name in self.thread_api.thread_states:
                self.thread_api.thread_states[thread_name].state = 'Finished'
                self.thread_api.thread_states[thread_name].progress = 100.0
    
    def start_simulation(self, num_producers: int = 2, num_consumers: int = 2, 
                        items_per_producer: int = 5, items_per_consumer: int = 5,
                        producer_delay: float = 1, consumer_delay: float = 1.5):
        """Start multi-threaded producer-consumer simulation"""
        self.running = True
        self._log(f"Starting simulation with {num_producers} producers and {num_consumers} consumers")
        self._log(f"Buffer size: {self.buffer_size}")
        self._log("-" * 60)
        
        # Clear any existing thread states
        with self.thread_api.lock:
            self.thread_api.thread_states.clear()
            self.thread_api.threads.clear()
        
        # Create producer threads
        for i in range(num_producers):
            items = list(range(1, items_per_producer + 1))
            thread_name = f"Producer-{i+1}"
            thread = self.thread_api.create_thread(
                target=self.producer, 
                args=(i + 1, items, producer_delay + i * 0.05),
                name=thread_name
            )
            # Add ThreadInfo for visualization
            with self.thread_api.lock:
                self.thread_api.thread_states[thread_name] = ThreadInfo(name=thread_name, state='Ready', progress=0.0)
        
        # Create consumer threads
        for i in range(num_consumers):
            thread_name = f"Consumer-{i+1}"
            thread = self.thread_api.create_thread(
                target=self.consumer, 
                args=(i + 1, items_per_consumer, consumer_delay + i * 0.05),
                name=thread_name
            )
            # Add ThreadInfo for visualization
            with self.thread_api.lock:
                self.thread_api.thread_states[thread_name] = ThreadInfo(name=thread_name, state='Ready', progress=0.0)
        
        # Start all threads
        for thread in self.thread_api.threads:
            self.thread_api.start_thread(thread)
    
    def wait_for_completion(self):
        """Wait for all simulation threads to complete"""
        self.thread_api.join_all()
        self.running = False
        self._log("-" * 60)
        self._log("Simulation complete!")
        self._log(f"Total produced: {self.produced_count}")
        self._log(f"Total consumed: {self.consumed_count}")
        self._log(f"Final buffer size: {len(self.buffer)}")
        self._log(f"Remaining items: {list(self.buffer)}")
    
    def is_simulation_complete(self) -> bool:
        """Check if all simulation threads have completed"""
        if not self.thread_api.threads:
            return False
        return all(not thread.is_alive() for thread in self.thread_api.threads)

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
    
    print("\n" + "=" * 80)
    print("ALL CONCURRENCY DEMONSTRATIONS COMPLETE!")
    print("=" * 80)
    

if __name__ == "__main__":
    demo_concurrency()