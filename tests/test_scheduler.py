import unittest
from os_core.scheduler import Scheduler, FIFOScheduler, RoundRobinScheduler, MLFQScheduler
from os_core.process import PCB


class TestScheduler(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Reset PCB counter for consistent testing
        PCB.reset_pid_counter()

    def create_test_pcb(self, name, burst_time=10, priority=0):
        """Helper method to create test PCB"""
        return PCB(name=name, memory_requirements_bytes=4, page_size=4, 
                  priority=priority, burst_time=burst_time)

    def test_scheduler_abstract_class(self):
        """Test that Scheduler is properly abstract"""
        with self.assertRaises(TypeError):
            Scheduler()  # Should not be able to instantiate abstract class

    def test_fifo_scheduler_initialization(self):
        """Test FIFO scheduler initialization"""
        scheduler = FIFOScheduler()
        self.assertEqual(len(scheduler.ready_queue), 0)

    def test_fifo_scheduler_add_process(self):
        """Test adding processes to FIFO scheduler"""
        scheduler = FIFOScheduler()
        pcb1 = self.create_test_pcb("Process1")
        pcb2 = self.create_test_pcb("Process2")
        
        scheduler.add_process(pcb1)
        scheduler.add_process(pcb2)
        
        self.assertEqual(len(scheduler.ready_queue), 2)
        self.assertEqual(pcb1.state, 'READY')
        self.assertEqual(pcb2.state, 'READY')

    def test_fifo_scheduler_get_next_order(self):
        """Test FIFO scheduling order (first in, first out)"""
        scheduler = FIFOScheduler()
        pcb1 = self.create_test_pcb("Process1")
        pcb2 = self.create_test_pcb("Process2")
        pcb3 = self.create_test_pcb("Process3")
        
        scheduler.add_process(pcb1)
        scheduler.add_process(pcb2)
        scheduler.add_process(pcb3)
        
        # Should get processes in FIFO order
        next_pcb, time_quantum = scheduler.get_next()
        self.assertEqual(next_pcb.name, "Process1")
        self.assertEqual(time_quantum, float('inf'))
        self.assertEqual(next_pcb.state, 'RUNNING')
        
        next_pcb, time_quantum = scheduler.get_next()
        self.assertEqual(next_pcb.name, "Process2")
        
        next_pcb, time_quantum = scheduler.get_next()
        self.assertEqual(next_pcb.name, "Process3")
        
        # Should return None when queue is empty
        next_pcb, time_quantum = scheduler.get_next()
        self.assertIsNone(next_pcb)
        self.assertIsNone(time_quantum)

    def test_fifo_scheduler_queue_string(self):
        """Test FIFO scheduler queue string representation"""
        scheduler = FIFOScheduler()
        
        # Empty queue
        queue_strings = scheduler.get_all_queues_str_list()
        self.assertEqual(len(queue_strings), 1)
        self.assertIn("Empty", queue_strings[0])
        
        # Non-empty queue
        pcb1 = self.create_test_pcb("P1", burst_time=5)
        pcb2 = self.create_test_pcb("P2", burst_time=8)
        scheduler.add_process(pcb1)
        scheduler.add_process(pcb2)
        
        queue_strings = scheduler.get_all_queues_str_list()
        self.assertIn("P1(5)", queue_strings[0])
        self.assertIn("P2(8)", queue_strings[0])

    def test_round_robin_scheduler_initialization(self):
        """Test Round Robin scheduler initialization"""
        scheduler = RoundRobinScheduler(time_quantum=10)
        self.assertEqual(scheduler.time_quantum, 10)
        self.assertEqual(len(scheduler.ready_queue), 0)
        
        # Test default time quantum
        scheduler_default = RoundRobinScheduler()
        self.assertEqual(scheduler_default.time_quantum, 5)

    def test_round_robin_scheduler_add_process(self):
        """Test adding processes to Round Robin scheduler"""
        scheduler = RoundRobinScheduler(time_quantum=3)
        pcb1 = self.create_test_pcb("Process1")
        pcb2 = self.create_test_pcb("Process2")
        
        scheduler.add_process(pcb1)
        scheduler.add_process(pcb2)
        
        self.assertEqual(len(scheduler.ready_queue), 2)
        self.assertEqual(pcb1.state, 'READY')
        self.assertEqual(pcb2.state, 'READY')

    def test_round_robin_scheduler_get_next(self):
        """Test Round Robin scheduling with time quantum"""
        scheduler = RoundRobinScheduler(time_quantum=3)
        pcb1 = self.create_test_pcb("Process1")
        pcb2 = self.create_test_pcb("Process2")
        
        scheduler.add_process(pcb1)
        scheduler.add_process(pcb2)
        
        # First process
        next_pcb, time_quantum = scheduler.get_next()
        self.assertEqual(next_pcb.name, "Process1")
        self.assertEqual(time_quantum, 3)
        self.assertEqual(next_pcb.state, 'RUNNING')
        
        # Second process
        next_pcb, time_quantum = scheduler.get_next()
        self.assertEqual(next_pcb.name, "Process2")
        self.assertEqual(time_quantum, 3)
        
        # Empty queue
        next_pcb, time_quantum = scheduler.get_next()
        self.assertIsNone(next_pcb)
        self.assertIsNone(time_quantum)

    def test_round_robin_scheduler_queue_string(self):
        """Test Round Robin scheduler queue string representation"""
        scheduler = RoundRobinScheduler(time_quantum=5)
        
        # Empty queue
        queue_strings = scheduler.get_all_queues_str_list()
        self.assertEqual(len(queue_strings), 1)
        self.assertIn("Empty", queue_strings[0])
        
        # Non-empty queue
        pcb1 = self.create_test_pcb("P1", burst_time=3)
        scheduler.add_process(pcb1)
        
        queue_strings = scheduler.get_all_queues_str_list()
        self.assertIn("P1(3)", queue_strings[0])

    def test_mlfq_scheduler_initialization(self):
        """Test MLFQ scheduler initialization"""
        scheduler = MLFQScheduler(levels=3, time_quanta=[2, 4, 6])
        
        self.assertEqual(scheduler.levels, 3)
        self.assertEqual(len(scheduler.queues), 3)
        self.assertEqual(scheduler.time_quanta, [2, 4, 6])
        
        # Test default initialization
        scheduler_default = MLFQScheduler()
        self.assertEqual(scheduler_default.levels, 3)
        self.assertEqual(scheduler_default.time_quanta, [5, 10, 15])

    def test_mlfq_scheduler_add_process(self):
        """Test adding processes to MLFQ scheduler"""
        scheduler = MLFQScheduler(levels=3)
        pcb1 = self.create_test_pcb("Process1")
        pcb2 = self.create_test_pcb("Process2")
        pcb3 = self.create_test_pcb("Process3")
        
        # Add to different levels
        scheduler.add_process(pcb1, level=0)  # Highest priority
        scheduler.add_process(pcb2, level=1)  # Medium priority
        scheduler.add_process(pcb3, level=2)  # Lowest priority
        
        self.assertEqual(len(scheduler.queues[0]), 1)
        self.assertEqual(len(scheduler.queues[1]), 1)
        self.assertEqual(len(scheduler.queues[2]), 1)
        
        # Test default level (should go to level 0)
        pcb4 = self.create_test_pcb("Process4")
        scheduler.add_process(pcb4)
        self.assertEqual(len(scheduler.queues[0]), 2)

    def test_mlfq_scheduler_add_process_invalid_level(self):
        """Test adding process to invalid level in MLFQ"""
        scheduler = MLFQScheduler(levels=3)
        pcb = self.create_test_pcb("Process1")
        
        # Invalid level should default to level 0
        scheduler.add_process(pcb, level=5)
        self.assertEqual(len(scheduler.queues[0]), 1)
        self.assertEqual(len(scheduler.queues[1]), 0)
        self.assertEqual(len(scheduler.queues[2]), 0)

    def test_mlfq_scheduler_priority_order(self):
        """Test MLFQ scheduler priority ordering"""
        scheduler = MLFQScheduler(levels=3, time_quanta=[2, 4, 6])
        pcb1 = self.create_test_pcb("Low", burst_time=10)
        pcb2 = self.create_test_pcb("High", burst_time=5)
        pcb3 = self.create_test_pcb("Medium", burst_time=8)
        
        # Add processes to different priority levels
        scheduler.add_process(pcb1, level=2)  # Lowest priority
        scheduler.add_process(pcb2, level=0)  # Highest priority
        scheduler.add_process(pcb3, level=1)  # Medium priority
        
        # Should get highest priority first
        next_pcb, time_quantum = scheduler.get_next()
        self.assertEqual(next_pcb.name, "High")
        self.assertEqual(time_quantum, 2)  # Time quantum for level 0
        
        # Then medium priority
        next_pcb, time_quantum = scheduler.get_next()
        self.assertEqual(next_pcb.name, "Medium")
        self.assertEqual(time_quantum, 4)  # Time quantum for level 1
        
        # Finally lowest priority
        next_pcb, time_quantum = scheduler.get_next()
        self.assertEqual(next_pcb.name, "Low")
        self.assertEqual(time_quantum, 6)  # Time quantum for level 2

    def test_mlfq_scheduler_empty_queues(self):
        """Test MLFQ scheduler with empty queues"""
        scheduler = MLFQScheduler(levels=3)
        
        next_pcb, time_quantum = scheduler.get_next()
        self.assertIsNone(next_pcb)
        self.assertIsNone(time_quantum)

    def test_mlfq_scheduler_queue_strings(self):
        """Test MLFQ scheduler queue string representation"""
        scheduler = MLFQScheduler(levels=2, time_quanta=[3, 6])
        
        # Empty queues
        queue_strings = scheduler.get_all_queues_str_list()
        self.assertEqual(len(queue_strings), 2)
        self.assertIn("Q0 (TQ:3)", queue_strings[0])
        self.assertIn("Empty", queue_strings[0])
        self.assertIn("Q1 (TQ:6)", queue_strings[1])
        self.assertIn("Empty", queue_strings[1])
        
        # Add processes
        pcb1 = self.create_test_pcb("P1", burst_time=5)
        pcb2 = self.create_test_pcb("P2", burst_time=8)
        scheduler.add_process(pcb1, level=0)
        scheduler.add_process(pcb2, level=1)
        
        queue_strings = scheduler.get_all_queues_str_list()
        self.assertIn("P1(5)", queue_strings[0])
        self.assertIn("P2(8)", queue_strings[1])

    def test_process_state_transitions(self):
        """Test that process states are properly updated by schedulers"""
        schedulers = [
            FIFOScheduler(),
            RoundRobinScheduler(time_quantum=5),
            MLFQScheduler(levels=2)
        ]
        
        for scheduler in schedulers:
            pcb = self.create_test_pcb("TestProcess")
            initial_state = pcb.state
            
            # Add process should set state to READY
            scheduler.add_process(pcb)
            self.assertEqual(pcb.state, 'READY')
            
            # Get next should set state to RUNNING
            next_pcb, _ = scheduler.get_next()
            if next_pcb:  # MLFQ might have different interface
                self.assertEqual(next_pcb.state, 'RUNNING')


if __name__ == '__main__':
    unittest.main()