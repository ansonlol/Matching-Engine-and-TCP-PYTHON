import threading
class SpscRing:
    def __init__(self, capacity:int):
        self.capacity = capacity
        self.buffer = [None] * capacity
        self.head = 0
        self.tail = 0

    def push(self, item) -> bool:
        if self.tail - self.head == self.capacity:
            return False 

        self.buffer[self.tail % self.capacity] = item
        self.tail += 1
        return True 

    def get(self):
        if self.head == self.tail:
            return None 
        item = self.buffer[self.head % self.capacity]
        self.buffer[self.head % self.capacity] = None 
        self.head += 1
        return item



# tests/test_spsc_ring.py  or bottom of spsc_ring.py

def test_basic():
    r = SpscRing(4)
    assert r.push(10) is True
    assert r.push(20) is True
    assert r.get() == 10
    assert r.get() == 20
    assert r.get() is None
    print("test_basic OK")

def test_full():
    r = SpscRing(2)
    assert r.push(1) is True
    assert r.push(2) is True
    assert r.push(3) is False
    assert r.get() == 1
    assert r.push(3) is True
    assert r.get() == 2
    assert r.get() == 3
    print("test_full OK")

def test_wrap():
    r = SpscRing(3)
    for i in range(3):
        assert r.push(i)
    assert r.get() == 0
    assert r.push(3) is True
    assert r.get() == 1
    assert r.get() == 2
    assert r.get() == 3
    print("test_wrap OK")

def test_threading():
    r = SpscRing(64)
    n = 10000
    errors = []

    def producer():
        for i in range(n):
            while not r.push(i):
                pass 

    def consumer():
        got = []
        while len(got) < n:
            item = r.get()
            if item is not None:
                got.append(item)

        if got != list(range(n)):
            errors.append(got[:10])

    t1 = threading.Thread(target=producer)
    t2 = threading.Thread(target=consumer)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    assert not errors, errors
    print("tests thread ok ")

if __name__ == "__main__":
    test_basic()
    test_full()
    test_wrap()
    test_threading()
    print("all passed")