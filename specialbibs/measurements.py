import inspect
from io import TextIOWrapper
import threading
import time
import queue
from typing import Any, Callable, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field


@dataclass
class PlotData:
    plot_id: str
    x_data: List[float] = field(default_factory=list)
    y_data: List[List[float]] = field(default_factory=list)
    x_label: str = "Time (s)"
    y_labels: List[str] = field(default_factory=list)
    num_series: int = 0


class RealTimePlotter:
    def __init__(self):
        self.data_queue: queue.Queue[tuple[str, tuple[str, float], List[tuple[str, float]]]] = queue.Queue()
        self.plots: Dict[str, PlotData] = {}
        self.plot_order: List[str] = []  # Maintains order of plot creation
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.lines: Dict[str, List] = {}
        self.initialized = False
        self._lock = threading.Lock()

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_plot_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def add_data(self, plot_id: str, x: tuple[str, float], y_values: List[tuple[str, float]]):
        self.data_queue.put((plot_id, x, y_values))

    def _run_plot_loop(self):
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation

        plt.ion()  # Enable interactive mode

        def update(_frame):
            while not self.data_queue.empty():
                try:
                    plot_id, x, y_values = self.data_queue.get_nowait()
                    self._process_data(plot_id, x, y_values)
                except queue.Empty:
                    break

            # Update plots if we have data
            if self.plots and self.initialized:
                self._update_plot_lines()

            return []

        # Create initial empty figure
        self.fig, self._axes = plt.subplots(1, 1, figsize=(10, 6))
        self.axes = [self._axes]  

        _anim = animation.FuncAnimation(
            self.fig, update, interval=50, blit=False, cache_frame_data=False
        )

        plt.show(block=True)

    def _process_data(self, plot_id: str, x: tuple[str, float], y_values: List[tuple[str, float]]):
        with self._lock:
            if plot_id not in self.plots:
                self.plots[plot_id] = PlotData(
                    plot_id=plot_id, num_series=len(y_values),
                    x_label=x[0], y_labels=[v[0] for v in y_values]
                )
                self.plot_order.append(plot_id)
                self._reconfigure_subplots()

            plot = self.plots[plot_id]
            plot.x_data.append(x[1])
            plot.y_data.append([v[1] for v in y_values])

    def _reconfigure_subplots(self):
        num_plots = len(self.plot_order)
        if num_plots == 0:
            return

        # Clear and recreate subplots
        self.fig.clear()
        self.axes = self.fig.subplots(num_plots, 1, squeeze=False)
        self.axes = [ax[0] for ax in self.axes]

        # Initialize lines for each plot
        self.lines.clear()
        colors = ["b", "r", "g", "c", "m", "y", "k"]

        for idx, plot_id in enumerate(self.plot_order):
            plot = self.plots[plot_id]
            ax = self.axes[idx]
            ax.set_xlabel(plot.x_label)
            y_labels = [l for l in plot.y_labels if l]
            if len(y_labels) == 1:
                ax.set_ylabel(y_labels[0])
            ax.grid(True, alpha=0.3)

            self.lines[plot_id] = []
            for series_idx in range(plot.num_series):
                color = colors[series_idx % len(colors)]
                if len(y_labels) > 1 and series_idx < len(plot.y_labels):
                    (line,) = ax.plot([], [], f"{color}-", linewidth=1, label=plot.y_labels[series_idx])
                else:
                    (line,) = ax.plot([], [], f"{color}-", linewidth=1)
                self.lines[plot_id].append(line)

        self.fig.tight_layout()
        self.initialized = True

    def _update_plot_lines(self):
        """Update all plot lines with current data"""
        with self._lock:
            for plot_id in self.plot_order:
                if plot_id not in self.lines:
                    continue

                plot = self.plots[plot_id]
                lines = self.lines[plot_id]


                if not plot.x_data:
                    continue

                for series_idx, line in enumerate(lines):
                    y_series = [
                        y[series_idx] for y in plot.y_data if series_idx < len(y)
                    ]
                    line.set_data(plot.x_data[: len(y_series)], y_series)

                # Auto-scale axes
                ax_idx = self.plot_order.index(plot_id)
                ax = self.axes[ax_idx]
                ax.relim()
                ax.autoscale_view()


class MeasurementContext:
    def __init__(
        self,
        duration: float,
        plotter: Optional[RealTimePlotter] = None,
        file: Optional[str] = None,
    ):
        self.time: float = 0.0
        self.duration: float = duration
        self._completed_ops: Set[str] = set()
        self._lock = threading.Lock()
        self._plotter = plotter
        self._file = file
        self._file_handle: Optional[TextIOWrapper] = None

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
                resolved_values.append((str(getattr(callable, '__name__', repr(callable))), v()))
            elif hasattr(v, "get"):
                resolved_values.append(('', v.get()))
            elif isinstance(v, tuple):
                resolved_values.append(v)
            else:
                resolved_values.append(('', float(v)))
        return resolved_values



    def save(self, *values: Any):
        resolved_values = [v[1] for v in self._resolve_values(*values)]

        if self._file_handle:
            line = f"{self.time:.6f}\t" + "\t".join(f"{v:.6f}" for v in resolved_values)
            self._file_handle.write(line + "\n")
            self._file_handle.flush()


    def plot(self, *values: Any):
        """
        Save values to file and plot them in real-time.

        Automatically identifies its position in the loop based on call location.
        Multiple calls in the same loop iteration create separate plots.

        Args:
            *values: Values to save and plot. Can be raw values or
                    instrument channels (will call .get() automatically)
        """
        # Get unique plot ID based on call location
        plot_id = self._get_caller_key(depth=2)
        resolved_values = self._resolve_values(*values)

        if len(resolved_values) < 2:
            x_value = ('Time (s)', self.time)
        else:
            x_value = resolved_values[0]
            resolved_values = resolved_values[1:]


        # Send to plotter
        if self._plotter:
            self._plotter.add_data(plot_id, x_value, resolved_values)

        self.save(*values)

    def reset(self):
        """Reset the once cache (useful for multiple runs)"""
        with self._lock:
            self._completed_ops.clear()


class SpecialBibs:
    def __init__(
        self,
        func: Callable,
        duration: float,
        sample_rate: float,
        file: str,
        plot: bool = True,
    ):
        """
        Args:
            func: Measurement function that takes a MeasurementContext
            duration: Total measurement duration in seconds
            sample_rate: Sample rate in Hz
            file: Output file path for data
            plot: Whether to enable real-time plotting (default: True)
        """
        self.func = func
        self.duration = duration
        self.sample_rate = sample_rate
        self.file = file
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
        # Initialize plotter
        if self._plot_enabled:
            self._plotter = RealTimePlotter()

        # Initialize measurement context
        self._meas_context = MeasurementContext(
            duration=self.duration, plotter=self._plotter, file=self.file
        )

        # Start measurement thread
        self._meas_thread = threading.Thread(target=self._measurement_loop, daemon=True)
        self._meas_thread.start()

        # Start plotter (runs in its own thread with matplotlib event loop)
        if self._plotter:
            self._plotter.start()

    def _measurement_loop(self):
        num_samples = int(self.duration * self.sample_rate)
        interval = 1.0 / self.sample_rate

        try:
            # Open file for writing
            self._meas_context._file_handle = open(self.file, "w")

            start_time = time.perf_counter()

            for i in range(num_samples):
                if self._stop_event.is_set():
                    break

                # Wait if paused
                self._paused_event.wait()

                # Calculate target time and current time
                target_time = i * interval
                t = i / self.sample_rate

                self._meas_context.time = t

                # Execute user function
                self.func(self._meas_context)

                # Sleep to maintain sample rate
                elapsed = time.perf_counter() - start_time
                sleep_time = target_time - elapsed + interval
                if sleep_time > 0:
                    time.sleep(sleep_time)

            self._completed = True

        except Exception as e:
            print(f"Measurement error: {e}")
            raise
        finally:
            if self._meas_context._file_handle:
                self._meas_context._file_handle.close()
            print(f"Measurement completed. Data saved to {self.file}")

    def stop(self):
        """Stop the measurement"""
        self._stop_event.set()
        self._paused_event.set()  # Unpause to allow thread to exit
        if self._meas_thread:
            self._meas_thread.join(timeout=2.0)
        if self._plotter:
            self._plotter.stop()

    def pause(self):
        """Pause the measurement"""
        self._paused_event.clear()
        print("Measurement paused")

    def resume(self):
        """Resume the measurement"""
        self._paused_event.set()
        print("Measurement resumed")

    @property
    def is_running(self) -> bool:
        """Check if measurement is still running"""
        return self._meas_thread is not None and self._meas_thread.is_alive()

    @property
    def is_completed(self) -> bool:
        """Check if measurement completed normally"""
        return self._completed

    @property
    def current_time(self) -> float:
        """Get current measurement time"""
        if self._meas_context:
            return self._meas_context.time
        return 0.0

    def wait(self):
        """Wait for measurement to complete"""
        if self._meas_thread:
            self._meas_thread.join()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
