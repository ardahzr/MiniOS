import threading
import queue

class ProducerConsumerSimulation:
    def __init__(self, buffer_size=10):
        self.buffer = queue.Queue(maxsize=buffer_size)

    def producer(self, items):
        for item in items:
            self.buffer.put(item)
            print(f"Produced {item}")

    def consumer(self, count):
        for _ in range(count):
            item = self.buffer.get()
            print(f"Consumed {item}")