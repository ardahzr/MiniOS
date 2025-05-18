PAGE_SIZE = 4096  # 4 KB pages

class PageTableEntry:
    def __init__(self):
        self.frame_number = None
        self.valid = False
        self.dirty = False
        self.referenced = False

class MemoryManager:
    def __init__(self, num_frames):
        self.num_frames = num_frames
        self.frame_table = [None] * num_frames  # track which page is loaded
        # Optionally implement replacement policy data structures

    def translate(self, page_number, offset):
        # check page table entry, simulate page fault if needed
        # return physical_address = frame_number * PAGE_SIZE + offset
        pass