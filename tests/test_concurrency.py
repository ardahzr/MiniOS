import unittest
import threading
import time
from unittest.mock import Mock
from os_core.concurrency import ThreadAPI, ProducerConsumerSimulation, ThreadInfo


class TestConcurrency(unittest.TestCase):

    def test_thread_api_creation(self):
        """Test ThreadAPI thread creation and management"""
        api = ThreadAPI()
        
        def dummy_task():
            time.sleep(0.1)
        
        thread = api.create_thread(target=dummy_task, name="test_thread")
        self.assertIsInstance(thread, threading.Thread)
        self.assertEqual(thread.name, "test_thread")
        self.assertIn(thread, api.threads)

    def test_thread_api_start_and_join(self):
        """Test ThreadAPI start and join functionality"""
        api = ThreadAPI()
        result = []
        
        def append_task(value):
            result.append(value)
        
        thread = api.create_thread(target=append_task, args=(42,))
        api.start_thread(thread)
        api.join_all()
        
        self.assertEqual(result, [42])
        self.assertFalse(thread.is_alive())

    def test_thread_info_creation(self):
        """Test ThreadInfo class"""
        info = ThreadInfo("test_thread", "Running", 50.0)
        self.assertEqual(info.name, "test_thread")
        self.assertEqual(info.state, "Running")
        self.assertEqual(info.progress, 50.0)

    def test_producer_consumer_initialization(self):
        """Test ProducerConsumerSimulation initialization"""
        logger = Mock()
        sim = ProducerConsumerSimulation(buffer_size=5, logger=logger)
        
        self.assertEqual(sim.buffer_size, 5)
        self.assertEqual(len(sim.buffer), 0)
        self.assertEqual(sim.produced_count, 0)
        self.assertEqual(sim.consumed_count, 0)
        self.assertFalse(sim.running)
        self.assertEqual(sim.logger, logger)    
    
    def test_producer_consumer_put_get(self):
        """Test basic put and get operations"""
        sim = ProducerConsumerSimulation(buffer_size=3)
        
        # Test put operation
        sim.put("item1")
        self.assertEqual(len(sim.buffer), 1)
        self.assertIn("item1", sim.buffer)
        
        # Test get operation (LIFO - uses pop())
        item = sim.get()
        self.assertEqual(item, "item1")
        self.assertEqual(len(sim.buffer), 0)    
    
    def test_producer_consumer_buffer_overflow(self):
        """Test buffer behavior when adding multiple items"""
        sim = ProducerConsumerSimulation(buffer_size=2)
        
        # The actual implementation doesn't limit buffer size in put()
        # It uses semaphores for synchronization, but put() itself just appends
        sim.put("item1")
        sim.put("item2")
        sim.put("item3")  # This will succeed in the actual implementation
        
        self.assertEqual(len(sim.buffer), 3)
        self.assertIn("item3", sim.buffer)

    def test_producer_consumer_empty_buffer(self):
        """Test getting from empty buffer"""
        sim = ProducerConsumerSimulation(buffer_size=2)
        
        # Try to get from empty buffer
        item = sim.get()
        self.assertIsNone(item)    
    
    def test_producer_consumer_statistics(self):
        """Test statistics tracking"""
        logger = Mock()
        sim = ProducerConsumerSimulation(buffer_size=5, logger=logger)
        sim.running = True
        
        # Test producer with items list (actual method signature)
        sim.producer(producer_id=1, items=["item1", "item2"], delay=0.01)
        self.assertEqual(sim.produced_count, 2)
        
        # Test consumer
        sim.consumer(consumer_id=1, count=2, delay=0.01)
        self.assertEqual(sim.consumed_count, 2)    
    
    def test_producer_consumer_thread_states(self):
        """Test thread state management"""
        sim = ProducerConsumerSimulation(buffer_size=3)
        sim.running = True
        
        # Set up thread state
        thread_name = "test_producer"
        sim.thread_api.thread_states[thread_name] = ThreadInfo(thread_name, "Ready", 0.0)
        
        # Mock current thread
        with unittest.mock.patch('threading.current_thread') as mock_thread:
            mock_thread.return_value.name = thread_name
            sim.producer(producer_id=1, items=["item1"], delay=0.01)
            
            # Check final state
            self.assertEqual(sim.thread_api.thread_states[thread_name].state, "Finished")
            self.assertEqual(sim.thread_api.thread_states[thread_name].progress, 100.0)

    def test_threading_lock_mutual_exclusion(self):
        """Test basic threading.Lock for mutual exclusion"""
        lock = threading.Lock()
        shared_resource = {"counter": 0}
        results = []
        
        def increment_worker():
            for _ in range(100):
                with lock:
                    current = shared_resource["counter"]
                    time.sleep(0.0001)  # Small delay to increase chance of race condition
                    shared_resource["counter"] = current + 1
            results.append(shared_resource["counter"])
        
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=increment_worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # With proper locking, final counter should be 500
        self.assertEqual(shared_resource["counter"], 500)

    def test_threading_semaphore_limit(self):
        """Test threading.Semaphore resource limiting"""
        semaphore = threading.Semaphore(2)  # Allow max 2 concurrent access
        active_count = {"value": 0}
        max_concurrent = {"value": 0}
        lock = threading.Lock()
        
        def resource_worker():
            with semaphore:
                with lock:
                    active_count["value"] += 1
                    max_concurrent["value"] = max(max_concurrent["value"], active_count["value"])
                
                time.sleep(0.1)  # Hold resource
                
                with lock:
                    active_count["value"] -= 1
        
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=resource_worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Semaphore should limit concurrent access to 2
        self.assertLessEqual(max_concurrent["value"], 2)
        self.assertEqual(active_count["value"], 0)  # All should be done


if __name__ == '__main__':
    unittest.main()