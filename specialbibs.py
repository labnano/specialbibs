
import inspect
import threading
from typing import Any, Callable, Optional, Set, Union
from functools import wraps

class MeasurementContext:
    def __init__(self, debug: bool = False):
        self.time: float = 0
        self._completed_ops: Set[str] = set()
        self._lock = threading.Lock()
    
    def set_once(self, operation: Union[Callable, Any], *args, 
                 key: Optional[str] = None, **kwargs) -> bool:
        """
        Execute operation only once per measurement.
        
        Args:
            operation: The operation to execute (callable or object with .set())
            *args, **kwargs: Arguments to pass to the operation
            key: Optional custom key for deduplication. If not provided,
                 uses file:line:column as the key.
        
        Returns:
            bool: True if operation was executed, False if skipped
        """
        if key is None:
            key = self._get_caller_key()
        
        with self._lock:
            if key in self._completed_ops:
                return False
            self._completed_ops.add(key)
        
        
        self._execute(operation, *args, **kwargs)
        return True
    
    def _get_caller_key(self) -> str:
        """Get a unique key from the caller's location"""
        # Get the caller's frame (skip this method and set_once)
        frame = inspect.currentframe()
        for _ in range(3): 
            if frame:
                frame = frame.f_back
            else:
                break
        
        if frame is None:
            return "unknown:0:0"
        
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        
        # Try to get column offset for more precision
        try:
            # For Python 3.8+
            col_offset = frame.f_lasti
        except AttributeError:
            col_offset = 0
        
        return f"{filename}:{lineno}:{col_offset}"
    
    def _execute(self, operation: Any, *args, **kwargs):
        if callable(operation):
            operation(*args, **kwargs)
        elif hasattr(operation, 'set'):
            operation.set(*args, **kwargs)
        else:
            raise TypeError(f"Operation {operation} is not callable and has no .set() method")
    
    def reset(self):
        """Reset the once cache (useful for multiple runs)"""
        with self._lock:
            self._completed_ops.clear()
    

class SpecialBibs:
    def __init__(self, func: Callable, duration: float, sample_rate: float, 
                 file: str, debug: bool = False):
        self.func = func
        self.duration = duration
        self.sample_rate = sample_rate
        self.file = file
        self.debug = debug
        self._meas_context = None
    
    def run(self):
        """Run the measurement loop"""
        self._meas_context = MeasurementContext(debug=self.debug)
        
        num_samples = int(self.duration * self.sample_rate)
        
        try:
            for i in range(num_samples):
                t = i / self.sample_rate
                self._meas_context.time = t
                self.func(self._meas_context)
        finally:
            print(f"Measurement completed. Data saved to {self.file}")
    
    def __enter__(self):
        self.run()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


