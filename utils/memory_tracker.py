import psutil
import os
from datetime import datetime
import gc
from functools import wraps

def get_process_memory():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # Convert to MB

def log_memory(message=""):
    gc.collect()  # Force garbage collection
    memory_mb = get_process_memory()
    print(f"[{datetime.now()}] Memory Usage {memory_mb:.2f} MB - {message}")
    return memory_mb

def memory_tracker(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        gc.collect()
        start_mem = get_process_memory()
        print(f"[{datetime.now()}] Starting {func.__name__} - Memory: {start_mem:.2f} MB")
        
        result = func(*args, **kwargs)
        
        gc.collect()
        end_mem = get_process_memory()
        print(f"[{datetime.now()}] Finished {func.__name__} - Memory: {end_mem:.2f} MB (Change: {end_mem - start_mem:.2f} MB)")
        return result
    return wrapper
