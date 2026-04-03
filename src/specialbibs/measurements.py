import inspect
from io import TextIOWrapper
import os
import sys
import threading
from datetime import datetime
import time
from typing import Any, Callable, Dict, Optional, Set, Union

from IPython.core.autocall import IPyAutocall
from .plotting import RealTimePlotter

class MeasurementContext:
    def __init__(
        self,
        duration: Optional[float],
        plotter: Optional[RealTimePlotter] = None,
        folder: Optional[str] = None,
        stop: Optional[Callable] = None,
    ):
        self.time: float = 0.0
        self.duration: Optional[float] = duration
        self._completed_ops: Set[str] = set()
        self._lock = threading.Lock()
        self._plotter = plotter
        self._folder = folder
        self._stop = stop if stop is not None else lambda: None
        self._file_handlers: Dict[str, TextIOWrapper] = {}

    def map(
        self,
        start: float,
        end: float,
        since: float = 0.0,
        until: Optional[float] = None,
    ) -> float:
        """
        Map time to a value range with linear interpolation.

        Args:
            start: Starting value
            end: Ending value
            since: Start time for mapping (default: 0)
            until: End time for mapping (default: measurement duration)

        Returns:
            Interpolated value based on current time
        """
        if until is None:
            if self.duration is None:
                raise ValueError("Until must be specified if measurement duration is not set")
            until = self.duration

        if self.time < since:
            return start
        if self.time > until:
            return end

        # Linear interpolation
        t_normalized = (self.time - since) / (until - since)
        return start + (end - start) * t_normalized

    def once(
        self,
        operation: Union[Callable, Any],
        *args,
        key: Optional[str] = None,
        **kwargs,
    ) -> bool:
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

    def plot(self, *values: Any):
        # Get unique plot ID based on call location
        plot_id = self._get_caller_key(depth=2)
        resolved_values = self._resolve_values(*values)

        if len(resolved_values) < 2:
            x_value = ('Time (s)', self.time)
        else:
            x_value = resolved_values[0]
            resolved_values = resolved_values[1:]


        if self._plotter:
            self._plotter.add_data(plot_id, x_value, resolved_values)

        self._save(plot_id, *values)

    def reset(self):
        """Reset the once cache (useful for multiple runs)"""
        with self._lock:
            self._completed_ops.clear()


    def _get_caller_key(self, depth: int = 3) -> str:
        frame = inspect.currentframe()
        for _ in range(depth):
            if frame:
                frame = frame.f_back
            else:
                break

        if frame is None:
            return "unknown:0:0"

        filename = frame.f_code.co_filename
        lineno = frame.f_lineno

        try:
            col_offset = frame.f_lasti
        except AttributeError:
            col_offset = 0

        return f"{filename}:{lineno}:{col_offset}"

    def _execute(self, operation: Any, *args, **kwargs):
        if callable(operation):
            operation(*args, **kwargs)
        elif hasattr(operation, "set"):
            operation.set(*args, **kwargs)
        else:
            raise TypeError(
                f"Operation {operation} is not callable and has no .set() method"
            )

    def _resolve_values(self, *values: Any) -> list[tuple[str, float]]:
        # Resolve values (call .get() on instrument channels)
        from specialbibs.instruments import _InstrumentChannel
        resolved_values: list[tuple[str, Any]] = []
        for v in values:
            if isinstance(v, _InstrumentChannel):
                resolved_values.append((f"{v.channel.name} ({v.channel.unit})", v.get()))
            elif callable(v):
                resolved_values.append((str(getattr(v, '__name__', repr(v))), v()))
            elif hasattr(v, "get"):
                resolved_values.append(('', v.get()))
            elif isinstance(v, tuple):
                resolved_values.append(v)
            else:
                resolved_values.append(('', float(v)))
        return resolved_values


    def _save(self, id: str, *values: Any):
        resolved_values = [v[1] for v in self._resolve_values(*values)]

        if id not in self._file_handlers:
            self._file_handlers[id] = open(f"{self._folder}/measurement{len(self._file_handlers) + 1}.txt", "w")
            line = "Time (s)\t" + "\t".join(f"{v[0]}" for v in self._resolve_values(*values)) + "\n"
        else:
            line = ""
        line += f"{self.time:.6f}\t" + "\t".join(f"{v:.6f}" for v in resolved_values)
        self._file_handlers[id].write(line + "\n")
        self._file_handlers[id].flush()

class SpecialBibs:
    current: 'Optional[SpecialBibs]' = None
    def __init__(
        self,
        func: Optional[Callable] = None,
        duration: Optional[float] = None,
        sample_rate: float = 1,
        folder: str = "output",
        plot: bool = True,
        on_stop: Optional[Callable] = None,
    ):
        """
        Args:
            func: Measurement function that takes a MeasurementContext
            duration: Total measurement duration in seconds
            sample_rate: Sample rate in Hz
            file: Output file path for data
            plot: Whether to enable real-time plotting (default: True)
        """
        global current
        SpecialBibs.current = self
        self.func = func
        self.on_stop = on_stop
        self.duration = duration
        self.sample_rate = sample_rate
        self._folder = folder
        self.folder = self._folder + '/' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self._plot_enabled = plot

        self._meas_thread: Optional[threading.Thread] = None
        self._plotter: Optional[RealTimePlotter] = None
        #self._meas_context: Optional[MeasurementContext] = None
        self._stop_event = threading.Event()
        self._paused_event = threading.Event()
        self._paused_event.set()  # Not paused initially
        self._completed = False


        # Auto-start
        self._start()

    def _start(self):
        if self._plot_enabled and self.func is not None:
            self._plotter = RealTimePlotter()
            self._plotter.key_press_event = _on_mplt_keypress
            self._plotter.close_event = _on_mplt_close

        self._start_measuremt_thread()

        shell = _create_shell()

        if self._plotter:
            self._plotter.start()
        
        shell()
        self.stop()  # Ensure measurement stops when shell exits



    def _start_measuremt_thread(self):
        self._meas_context = MeasurementContext(duration=self.duration, plotter=self._plotter, folder=self.folder, stop=self._soft_stop)

        # Start measurement thread
        self._meas_thread = threading.Thread(target=self._measurement_loop, daemon=True)
        self._meas_thread.start()


    def _measurement_loop(self):
        if self.func is None:
            return
        num_samples = int(self.duration * self.sample_rate) if self.duration else None
        interval = 1.0 / self.sample_rate

        try:
            os.makedirs(self.folder, exist_ok=True)

            start_time = time.perf_counter()

            i = 0
            while True:
                if (self.duration is not None) and (i >= (num_samples or 0)):
                    break
                # Wait if paused
                self._paused_event.wait()
                if self._stop_event.is_set():
                    break

                # Calculate target time and current time
                target_time = i * interval
                t = i / self.sample_rate

                self._meas_context.time = t

                try:
                    # Execute user function
                    self.func(self._meas_context)
                except Exception as e:
                    print(f"Error during measurement: {e}")
                    self.pause()
                    continue

                # Sleep to maintain sample rate
                elapsed = time.perf_counter() - start_time
                sleep_time = target_time - elapsed + interval
                if sleep_time > 0:
                    time.sleep(sleep_time)

                i += 1

            if not self._stop_event.is_set():
                self._completed = True

        except Exception as e:
            print(f"Measurement error: {e}")
            raise
        finally:
            for file in self._meas_context._file_handlers.values():
                file.close()
            if self._completed:
                print(f"Measurement completed. Data saved to folder {self.folder}/")
            else:
                print(f"Measurement aborted at time {self.current_time:.2f}s.\nPartial data may be saved on {self.folder}/")

    def _soft_stop(self):
        self._completed = True
        self.stop()

    def stop(self):
        self._stop_event.set()
        self._paused_event.set()  # Unpause to allow thread to exit
        if self._meas_thread:
            self._meas_thread.join(timeout=2.0)
        if self.on_stop:
            self.on_stop()

    def pause(self):
        if not self.is_running:
            return
        self._paused_event.clear()
        print("Measurement paused at time {:.2f}s".format(self.current_time))

    def resume(self):
        if not self.is_running:
            return
        self._paused_event.set()
        print("Measurement resumed")

    def toggle_pause(self):
        if self._paused_event.is_set():
            self.pause()
        else:
            self.resume()

    def restart(self):
        self.stop()
        self._completed = False
        self._paused_event.set()  # Ensure it's not paused
        self._stop_event.clear()  # Clear stop event for new run
        self.folder = self._folder + '/' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self._start_measuremt_thread()
        if self._plotter:
            self._plotter.restart()
        print("Restarting measurement...")

    @property
    def is_running(self) -> bool:
        return self._meas_thread is not None and self._meas_thread.is_alive()

    @property
    def is_completed(self) -> bool:
        return self._completed

    @property
    def current_time(self) -> float:
        if self._meas_context:
            return self._meas_context.time
        return 0.0



def _create_shell() -> Callable:
    from IPython.terminal.embed import InteractiveShellEmbed
    from IPython.terminal.prompts import Prompts
    from pygments.token import Token
    from traitlets.config import Config
    class ClassicPrompt(Prompts):
        def in_prompt_tokens(self):
            return [(Token.Prompt, '>>> ')]
        def continuation_prompt_tokens(self, width=None,*, lineno=None, wrap_count=None):
            return [(Token.Prompt, '... ')]

    c = Config()
    c.TerminalInteractiveShell.prompts_class = ClassicPrompt
    c.TerminalInteractiveShell.separate_in = ''
    c.TerminalInteractiveShell.banner1 = (
        '------------ SpecialBibs ------------\n'
        'Diga não ao MatLab. Viva a revolução!\n\n'
    )
    c.TerminalInteractiveShell.enable_tip = False
    c.InteractiveShellApp.exec_lines.append('%load_ext autoreload')
    c.InteractiveShellApp.exec_lines.append('%autoreload 2')

    shell = InteractiveShellEmbed(config=c)
    #shell.enable_matplotlib()

    kb = shell.pt_app.key_bindings
    @kb.add('escape', eager=True)  
    @kb.add('c-c')  
    def _(_):
        if SpecialBibs.current:
            SpecialBibs.current.stop()

    @kb.add('space')  
    def _(_):
        if SpecialBibs.current:
            SpecialBibs.current.toggle_pause()



    if SpecialBibs.current is not None:
        call_stack = sys._getframe(2).f_back
        assert call_stack is not None
        locals = call_stack.f_locals
        locals['meas'] = SpecialBibs.current._meas_context
        locals['stop'] = _MeasurementAutocall(SpecialBibs.current.stop)
        locals['pause'] = _MeasurementAutocall(SpecialBibs.current.pause)
        locals['resume'] = _MeasurementAutocall(SpecialBibs.current.resume)
        locals['restart'] = _MeasurementAutocall(SpecialBibs.current.restart)
    else:
        locals = None

    def _run_shell():
        shell(local_ns=locals)

    return _run_shell

def _on_mplt_keypress(event):
    if event.key == 'ctrl+c' or event.key == 'escape':
        if SpecialBibs.current:
            SpecialBibs.current.stop()
    elif event.key == ' ':
        if SpecialBibs.current:
            SpecialBibs.current.toggle_pause()

def _on_mplt_close(event):
    if SpecialBibs.current:
        SpecialBibs.current.stop()


class _MeasurementAutocall(IPyAutocall):
    rewrite = False
    def __init__(self, command: Callable):
        self._command = command

    def __call__(self):
        self._command()

