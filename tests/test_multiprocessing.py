import unittest
from concurrent.futures import ProcessPoolExecutor, as_completed
import random
import time
import random
import math
import os


def is_prime(n, c) -> tuple:
    print('counter before wait: ', c)
    t = random.randint(2, 10)
    print('time to wait: ', t, ' sec')
    time.sleep(t)
    print('counter after wait: ', c)
    if n < 2:
        return False, n
    if n == 2:
        return True, n
    if n % 2 == 0:
        return False, n
    sqrt_n = int(math.floor(math.sqrt(n)))
    for i in range(3, sqrt_n + 1, 2):
        if n % i == 0:
            return False, n
    return True, n


class MultiProcessingTest(unittest.TestCase):
    """Test multiprocessing"""
    def setUp(self):
        return super().setUp()
    
    def test_intensive_process(self):
        PRIMES = [
            112272535095293,
            112582705942171,
            112272535095293,
            115280095190773,
            115797848077099,
            1099726899285419]
        with ProcessPoolExecutor(os.process_cpu_count()) as executor:
            c = 1
            futures = []
            for p in PRIMES:
                print(p)
                ex = executor.submit(is_prime, p, c)
                futures.append(ex)
                c += 1
            for future in as_completed(futures):
                result, p = future.result()
                if result:
                    print(p, ' is prime')
                else:
                    print(p, ' is not prime')
            
    
    def test_pool(self):
        """Test multiprocessor using pool"""
        
    
    def tearDown(self):
        return super().tearDown()