import threading
import queue
from typing import Callable, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from specialbibs.measurements import SpecialBibs


PLOT_COLORS = ["b", "r", "g", "c", "m", "y", "k"]
ANIMATION_INTERVAL_MS = 50

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
        self.lines: Dict[str, List] = {}
        self.initialized = False
        self._lock = threading.Lock()
        self.key_press_event: Optional[Callable] = None

    def start(self):
        self._run_plot_loop()


    def add_data(self, plot_id: str, x: tuple[str, float], y_values: List[tuple[str, float]]):
        self.data_queue.put((plot_id, x, y_values))

    def clear(self):
        with self._lock:
            self.plots.clear()
            self.plot_order.clear()
            self.lines.clear()
            self.initialized = False
            if hasattr(self, 'fig'):
                self.fig.clf()
                self.axes = []

    def _run_plot_loop(self):
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation

        #plt.ion()  # Enable interactive mode

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

        if self.key_press_event:
            self.fig.canvas.mpl_connect('key_press_event', self.key_press_event)

        anim = animation.FuncAnimation(
            self.fig, update, interval=ANIMATION_INTERVAL_MS, blit=False, cache_frame_data=False
        )
        plt.pause(0.1)
        #plt.show(block=False)

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
                color = PLOT_COLORS[series_idx % len(PLOT_COLORS)]
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


