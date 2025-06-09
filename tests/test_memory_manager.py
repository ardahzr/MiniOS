import unittest
from os_core.memory_manager import MemoryManager, PageTableEntry
from os_core.process import PCB


class TestMemoryManager(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Reset PCB counter for consistent testing
        PCB.reset_pid_counter()

    def test_memory_manager_initialization(self):
        """Test MemoryManager initialization"""
        mm = MemoryManager(page_size=4, num_frames=8, num_disk_frames=4)
        
        self.assertEqual(mm.page_size, 4)
        self.assertEqual(mm.num_frames, 8)
        self.assertEqual(mm.num_disk_frames, 4)
        self.assertEqual(len(mm.frame_table), 8)
        self.assertEqual(len(mm.disk_blocks), 4)
        self.assertEqual(mm.free_frames, list(range(8)))
        self.assertEqual(mm.free_disk_blocks, list(range(4)))
        self.assertEqual(mm.swapping_algorithm, 'clockhand')

    def test_page_table_entry_initialization(self):
        """Test PageTableEntry initialization"""
        pte = PageTableEntry()
        
        self.assertIsNone(pte.frame_number)
        self.assertFalse(pte.valid)
        self.assertFalse(pte.on_disk)
        self.assertIsNone(pte.disk_block_number)
        self.assertFalse(pte.use_bit)

    def test_memory_allocation_success(self):
        """Test successful memory allocation"""
        mm = MemoryManager(page_size=4, num_frames=8, num_disk_frames=4)
        pcb = PCB(name="Process1", memory_requirements_bytes=8, page_size=4)
        
        # Process needs 2 pages (8 bytes / 4 bytes per page)
        self.assertEqual(pcb.num_pages_required, 2)
        
        result = mm.allocate_memory(pcb)
        self.assertTrue(result)
        
        # Check memory manager state
        self.assertEqual(mm.get_free_frames_count(), 6)  # 8 - 2 = 6
        self.assertIn(pcb.pid, mm.pid_to_pcb_map)
        
        # Check PCB page table
        self.assertEqual(len(pcb.page_table), 2)
        for i in range(2):
            self.assertIn(i, pcb.page_table)
            pte = pcb.page_table[i]
            self.assertTrue(pte.valid)
            self.assertIsNotNone(pte.frame_number)
            self.assertTrue(pte.use_bit)

    def test_memory_allocation_too_large(self):
        """Test allocation failure when process is too large"""
        mm = MemoryManager(page_size=4, num_frames=4, num_disk_frames=2)
        # Process needs 8 pages but only 4 frames available
        pcb = PCB(name="LargeProcess", memory_requirements_bytes=32, page_size=4)
        
        result = mm.allocate_memory(pcb)
        self.assertFalse(result)
        self.assertEqual(mm.get_free_frames_count(), 4)  # Should remain unchanged
        self.assertNotIn(pcb.pid, mm.pid_to_pcb_map)

    def test_memory_allocation_duplicate_pid(self):
        """Test allocation failure when PID already allocated"""
        mm = MemoryManager(page_size=4, num_frames=8, num_disk_frames=4)
        pcb = PCB(name="Process1", memory_requirements_bytes=4, page_size=4)
        
        # First allocation should succeed
        result1 = mm.allocate_memory(pcb)
        self.assertTrue(result1)
        
        # Second allocation with same PCB should fail
        result2 = mm.allocate_memory(pcb)
        self.assertFalse(result2)

    def test_memory_deallocation(self):
        """Test memory deallocation"""
        mm = MemoryManager(page_size=4, num_frames=8, num_disk_frames=4)
        pcb = PCB(name="Process1", memory_requirements_bytes=8, page_size=4)
        
        # Allocate memory
        mm.allocate_memory(pcb)
        initial_free_frames = mm.get_free_frames_count()
        
        # Deallocate memory
        result = mm.deallocate_memory(pcb.pid)
        self.assertTrue(result)
        
        # Check memory manager state
        self.assertEqual(mm.get_free_frames_count(), 8)  # All frames should be free
        self.assertNotIn(pcb.pid, mm.pid_to_pcb_map)
        self.assertEqual(pcb.state, 'TERMINATED')

    def test_memory_deallocation_invalid_pid(self):
        """Test deallocation failure with invalid PID"""
        mm = MemoryManager(page_size=4, num_frames=8, num_disk_frames=4)
        
        result = mm.deallocate_memory(999)  # Non-existent PID
        self.assertFalse(result)

    def test_memory_maps(self):
        """Test memory map retrieval functions"""
        mm = MemoryManager(page_size=4, num_frames=4, num_disk_frames=2)
        
        # Test empty state
        self.assertEqual(mm.get_memory_map(), [None, None, None, None])
        self.assertEqual(mm.get_disk_map(), [None, None])
        self.assertEqual(mm.get_free_frames_count(), 4)
        self.assertEqual(mm.get_free_disk_blocks_count(), 2)
        
        # Allocate memory and check maps
        pcb = PCB(name="Process1", memory_requirements_bytes=8, page_size=4)
        mm.allocate_memory(pcb)
        
        memory_map = mm.get_memory_map()
        self.assertEqual(len(memory_map), 4)
        # Two frames should be occupied
        occupied_frames = [frame for frame in memory_map if frame is not None]
        self.assertEqual(len(occupied_frames), 2)

    def test_virtual_address_translation_success(self):
        """Test successful virtual address translation"""
        mm = MemoryManager(page_size=4, num_frames=8, num_disk_frames=4)
        pcb = PCB(name="Process1", memory_requirements_bytes=8, page_size=4)
        
        # Allocate memory
        mm.allocate_memory(pcb)
        
        # Test translation for valid address
        result = mm.translate(pcb.pid, 5)  # Page 1, offset 1
        self.assertIsInstance(result, str)
        self.assertIn("PA", result)  # Should contain physical address
        self.assertIn("Frame", result)

    def test_virtual_address_translation_segmentation_fault(self):
        """Test segmentation fault detection"""
        mm = MemoryManager(page_size=4, num_frames=8, num_disk_frames=4)
        pcb = PCB(name="Process1", memory_requirements_bytes=8, page_size=4)  # 2 pages
        
        mm.allocate_memory(pcb)
        
        # Test translation for address outside process space
        result = mm.translate(pcb.pid, 12)  # Page 3, but process only has 0-1
        self.assertIn("Segmentation Fault", result)

    def test_virtual_address_translation_invalid_pid(self):
        """Test translation with invalid PID"""
        mm = MemoryManager(page_size=4, num_frames=8, num_disk_frames=4)
        
        result = mm.translate(999, 0)  # Non-existent PID
        self.assertIn("Process PID 999 not found", result)

    def test_swapping_algorithm_setting(self):
        """Test different swapping algorithms"""
        mm1 = MemoryManager(page_size=4, num_frames=4, num_disk_frames=2, swapping_algorithm='clockhand')
        self.assertEqual(mm1.swapping_algorithm, 'clockhand')
        
        mm2 = MemoryManager(page_size=4, num_frames=4, num_disk_frames=2, swapping_algorithm='clockhand+')
        self.assertEqual(mm2.swapping_algorithm, 'clockhand+')

    def test_multiple_process_allocation(self):
        """Test allocating memory for multiple processes"""
        mm = MemoryManager(page_size=4, num_frames=8, num_disk_frames=4)
        
        # Create multiple processes
        pcb1 = PCB(name="Process1", memory_requirements_bytes=4, page_size=4)  # 1 page
        pcb2 = PCB(name="Process2", memory_requirements_bytes=8, page_size=4)  # 2 pages
        pcb3 = PCB(name="Process3", memory_requirements_bytes=4, page_size=4)  # 1 page
        
        # Allocate memory for all processes
        self.assertTrue(mm.allocate_memory(pcb1))
        self.assertTrue(mm.allocate_memory(pcb2))
        self.assertTrue(mm.allocate_memory(pcb3))
        
        # Check remaining free frames
        self.assertEqual(mm.get_free_frames_count(), 4)  # 8 - 1 - 2 - 1 = 4
        
        # All processes should be in the map
        self.assertIn(pcb1.pid, mm.pid_to_pcb_map)
        self.assertIn(pcb2.pid, mm.pid_to_pcb_map)
        self.assertIn(pcb3.pid, mm.pid_to_pcb_map)


if __name__ == '__main__':
    unittest.main()