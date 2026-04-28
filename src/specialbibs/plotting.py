import threading
import queue
from typing import Callable, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
import numpy as np

if TYPE_CHECKING:
    from matplotlib.animation import FuncAnimation

from matplotlib.backend_bases import NavigationToolbar2
NavigationToolbar2.toolitems = [
    item for item in NavigationToolbar2.toolitems 
    if item[0] != 'Save' # Save button is bugged so we removed it :)
]


PLOT_COLORS = ["b", "r", "g", "c", "m", "y", "k"]
ANIMATION_INTERVAL_MS = 50

#TOOK FROM https://stackoverflow.com/questions/17446956/matplotlib-exit-after-animation
from matplotlib import animation as ani
class FuncAnimationDisposable(ani.FuncAnimation):
    def __init__(self, fig, func, **kwargs):
        super().__init__(fig, func, **kwargs)
        
    def _step(self, *args):
        from matplotlib import pyplot as plt
        still_going = super()._step(*args)
        if not still_going:
            if self._repeat:
                self._init_draw()
                self.frame_seq = self.new_frame_seq()
                self.event_source.interval = self._repeat_delay
                return True
            else:
                plt.close()
                if self._blit:
                    self._fig.canvas.mpl_disconnect(self._resize_id)
                self._fig.canvas.mpl_disconnect(self._close_id)
                self.event_source = None
                return False

        self.event_source.interval = self._interval
        return True

@dataclass
class PlotData:
    plot_id: str
    x_data: np.ndarray = field(default_factory=lambda: np.array([]))
    y_data: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    x_label: str = "Time (s)"
    y_labels: List[str] = field(default_factory=list)
    num_series: int = 0


class RealTimePlotter:
    def __init__(self, blocking: bool = False):
        self.data_queue: queue.Queue[
            tuple[str, tuple[str, float], List[tuple[str, float]]]
        ] = queue.Queue()
        self.plots: Dict[str, PlotData] = {}
        self.plot_order: List[str] = []
        self.plot_id_to_index: Dict[str, int] = {}
        self.lines: Dict[str, List] = {}
        self.initialized = False
        self.key_press_event: Optional[Callable] = None
        self._anim: Optional["FuncAnimation"] = None
        self.close_event: Optional[Callable] = None
        self._stop_event = threading.Event()
        self._close_cid: Optional[int] = None
        self._blocking: bool = blocking

    def start(self):
        self._run_plot_loop()

    def add_data(
        self, plot_id: str, x: tuple[str, float], y_values: List[tuple[str, float]]
    ):
        self.data_queue.put((plot_id, x, y_values))

    def save_data(self, plot_id: str, path: str):
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
        from matplotlib.figure import Figure
        fig = Figure()
        canvas = FigureCanvas(fig)
        p = self.plots[plot_id]
        ax = fig.add_subplot(111)

        ax.set_xlabel(p.x_label)
        y_labels = [l for l in p.y_labels if l]
        if len(y_labels) == 1:
            ax.set_ylabel(y_labels[0])
        ax.grid(True, alpha=0.3)

        self.lines[plot_id] = []
        for series_idx in range(p.num_series):
            color = PLOT_COLORS[series_idx % len(PLOT_COLORS)]
            if len(y_labels) > 1 and series_idx < len(p.y_labels):
                ax.plot(
                    p.x_data,
                    p.y_data[:, series_idx],
                    f"{color}-",
                    linewidth=1,
                    label=p.y_labels[series_idx],
                )
            else:
                ax.plot(p.x_data, p.y_data[:, series_idx], f"{color}-", linewidth=1)
        canvas.print_figure(path + f'/measurement{list(self.plots).index(plot_id) + 1}.png')
        canvas.print_figure(path + f'/measurement{list(self.plots).index(plot_id) + 1}.svg')
        plt.close(fig)

    def save_agg(self, path):
        # self.fig.tight_layout()
        self.fig.savefig(path + '/measurement_all.png', backend='QtAgg')
        self.fig.savefig(path + '/measurement_all.svg', backend='Cairo')


    def restart(self):
        import matplotlib.pyplot as plt

        self.data_queue.queue.clear()
        self.initialized = False
        self.plot_order.clear()
        self.plots.clear()
        self.lines.clear()
        if self.fig and self._close_cid:
            self.fig.canvas.mpl_disconnect(self._close_cid)
        try:
            if self._anim:
                self._anim.pause()
                del self._anim
        except:
            pass
            

        if hasattr(self, "fig") and self.fig is not None:
            plt.close(self.fig)

        self._run_plot_loop()

    def _run_plot_loop(self):
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation

        plt.ion()  # Enable interactive mode

        def update(_frame):
            while True:
                try:
                    if self._stop_event.is_set():
                        raise StopIteration
                        # self._anim.event_source.stop()
                        # plt.close(self.fig)
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
            self.fig.canvas.mpl_connect("key_press_event", self.key_press_event)

        if self.close_event:
            self._close_cid = self.fig.canvas.mpl_connect(
                "close_event", self.close_event
            )

        self._anim = FuncAnimationDisposable(
            self.fig,
            update,
            interval=ANIMATION_INTERVAL_MS,
            blit=False,
            cache_frame_data=False,
            repeat=False
            # save_count=10
        )
        if self._blocking:
            plt.show(block=True)
            plt.close()
        else:
            plt.pause(0.1)

    
    def _process_data(
        self, plot_id: str, x: tuple[str, float], y_values: List[tuple[str, float]]
    ):
        if plot_id not in self.plots:
            self.plots[plot_id] = PlotData(
                plot_id=plot_id,
                num_series=len(y_values),
                x_label=x[0],
                y_labels=[v[0] for v in y_values],
            )
            self.plot_order.append(plot_id)
            self._reconfigure_subplots()

        plot = self.plots[plot_id]
        plot.x_data = np.append(plot.x_data, x[1])
        y_values_array = np.array([v[1] for v in y_values])
        if plot.y_data.size == 0:
            plot.y_data = y_values_array.reshape(1, -1)
        else:
            plot.y_data = np.vstack([plot.y_data, y_values_array])

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
                    (line,) = ax.plot(
                        [],
                        [],
                        f"{color}-",
                        linewidth=1,
                        label=plot.y_labels[series_idx],
                    )
                else:
                    (line,) = ax.plot([], [], f"{color}-", linewidth=1)
                self.lines[plot_id].append(line)

        self.fig.tight_layout()
        self.initialized = True
        self.plot_id_to_index = {pid: idx for idx, pid in enumerate(self.plot_order)}

    def _update_plot_lines(self):
        """Update all plot lines with current data"""
        for plot_id in self.plot_order:
            if plot_id not in self.lines:
                continue

            plot = self.plots[plot_id]
            lines = self.lines[plot_id]

            if plot.x_data.size == 0:
                continue

            for series_idx, line in enumerate(lines):
                y_series = plot.y_data[:, series_idx]
                line.set_data(plot.x_data, y_series)

            # Auto-scale axes
            ax_idx = self.plot_id_to_index[plot_id]
            ax = self.axes[ax_idx]
            ax.relim()
            ax.autoscale_view()
