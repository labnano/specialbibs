"""G50 mass flow controller, over its built-in web interface.

The device is an embedded HTTP server, not a VISA instrument. There are two
ways in, and which one to use depends entirely on the rate you need.

Occasional reads come from ``iobuf.js``, which the web UI loads as plain
JavaScript assignments (``iobuf.flow_sensor = 0.235282;``). One fetch carries
every field, but costs a ~0.5 s round trip, so this tops out near 2 Hz.

Fast flow reading uses the trace stream the plot applet uses -- ask once, then
the device pushes samples down one long-lived response. Measured 19.7 / 49.0 /
98.1 Hz for 20 / 50 / 100 Hz requested, with ~2 % of samples dropped at every
rate (visible as gaps in the returned device timestamp)::

    POST /ToolWeb/Con
      <TraceDefine><Trace Name="PY" Enable="True" Period="50" GroupSize="1">
        <EVIDS><V Name="EVID_0"/></EVIDS></Trace></TraceDefine>
    GET  /ToolWeb/Trace?Name=PY&Seq=0&Cont=1
      -> <Data><BulkTrace Time="0.43" Seq="28350" ...>
           <V><V>0x3E7C7A3F</V></V></BulkTrace></Data>   (one per sample)

``Period`` is milliseconds, so 50 gives 20 Hz and 10 gives the 100 Hz ceiling.
Values are hex IEEE-754 float32. EVID_0 is the flow signal, confirmed against
``iobuf.flow_sensor``. Only one trace exists at a time, so streaming here and
plotting in the web UI are mutually exclusive.

Writing the setpoint posts the same two forms the UI posts:

    POST /digital_analog_mode   mfc.sp_adc_enable=0
    POST /flow_setpoint_html    iobuf.setpoint_unit=<value>&SUBMIT=Submit
"""

from __future__ import annotations

import atexit
import http.client
import re
import struct
import threading
import time
import urllib.parse
import urllib.request
from typing import Iterator, Tuple

from specialbibs.instruments import Channel, Instrument

# iobuf.js and friends are flat lists of "<object>.<field> = <value>;" lines.
_ASSIGNMENT = re.compile(r"^\s*(\w+)\.(\w+)\s*=\s*([^;]+);", re.MULTILINE)

# One streamed sample: <BulkTrace ... Time="0.43" Seq="28350" ...><V><V>0x3E7C7A3F</V></V>
_SAMPLE_TIME = re.compile(r'Time="([\d.]+)"')
_SAMPLE_HEX = re.compile(r">(0x[0-9A-Fa-f]{8})<")


class G50(Instrument):
    """G50 mass flow controller.

        mfc = G50("10.0.0.251")
        print(mfc.flow, mfc.temperature)
        mfc.setpoint = 25.0

    ``.flow`` is served from a background stream: the first read starts it and
    every later read returns the newest sample, so polling it costs nothing.
    The stream stops on ``close()``, on leaving a ``with`` block, at process
    exit, or after ``idle_timeout`` seconds without a read -- whichever comes
    first -- so the device's single trace slot is never held by a caller that
    has moved on. The next read starts it again.
    """

    flow = Channel("Flow", unit="sccm")
    setpoint = Channel("Setpoint", unit="sccm")
    temperature = Channel("Temperature", unit="℃")
    valve_command = Channel("Valve command", unit="mA")

    def __init__(
        self,
        host: str,
        port: int = 80,
        timeout: float = 5.0,
        rate_hz: float = 20.0,
        idle_timeout: float = 10.0,
    ):
        super().__init__()
        self._host = host
        self._port = port
        self._base = f"http://{host}:{port}"
        self._timeout = timeout
        self._cache: dict[str, tuple[float, dict[str, float]]] = {}

        # Background flow stream, started on the first read of .flow.
        self._rate_hz = rate_hz
        self._idle_timeout = idle_timeout
        self._flow_value: float | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._first = threading.Event()
        self._last_read = 0.0

        # Backstop: never leave the device's single trace slot held.
        atexit.register(self.close)

    # ------------------------------------------------------------------ io

    def _read_vars(self, namespace: str, max_age: float = 0.2) -> dict[str, float]:
        """Numeric fields of ``<namespace>.js``.

        One fetch carries every field, and the device takes ~0.5 s to answer,
        so a short cache keeps a four-channel read to a single request -- and
        returns four values from the same instant rather than four spread over
        two seconds.
        """
        cached = self._cache.get(namespace)
        if cached and time.monotonic() - cached[0] < max_age:
            return cached[1]

        url = f"{self._base}/{namespace}.js"
        with urllib.request.urlopen(url, timeout=self._timeout) as response:
            text = response.read().decode("latin-1")

        values = {}
        for obj, field, raw in _ASSIGNMENT.findall(text):
            if obj == namespace:
                try:
                    values[field] = float(raw)
                except ValueError:
                    pass  # strings and arrays are not useful here

        if not values:
            raise RuntimeError(f"{url} contained no numeric fields")

        self._cache[namespace] = (time.monotonic(), values)
        return values

    def _var(self, namespace: str, field: str, max_age: float = 0.2) -> float:
        return self._read_vars(namespace, max_age)[field]

    def _post(self, path: str, fields: dict[str, str] | None, xml: str | None = None) -> str:
        if xml is None:
            data = urllib.parse.urlencode(fields or {}).encode("latin-1")
            content_type = "application/x-www-form-urlencoded"
        else:
            data = xml.encode("ascii")
            content_type = "text/xml"

        request = urllib.request.Request(
            self._base + path, data=data, headers={"Content-Type": content_type}
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            body = response.read().decode("latin-1")

        self._cache.clear()
        return body

    # --------------------------------------------------------------- reads

    @flow.read
    def _read_flow(self) -> float:
        """Latest value from the background stream.

        The first read starts the stream and waits for a sample; later reads
        just hand back whatever arrived most recently, so this stays cheap at
        any call rate.
        """
        self._last_read = time.monotonic()
        self._ensure_stream()

        if self._first.wait(timeout=self._timeout) and self._flow_value is not None:
            return self._flow_value

        # The stream could not start -- most likely the web plot page holds the
        # device's only trace slot. Fall back to the slower polled read.
        return self._var("iobuf", "flow_sensor")

    @setpoint.read
    def _read_setpoint(self) -> float:
        # setpoint_unit is what the UI shows and writes, in the configured unit.
        return self._var("iobuf", "setpoint_unit")

    @temperature.read
    def _read_temperature(self) -> float:
        return self._var("iobuf", "temp_sensor")

    @valve_command.read
    def _read_valve_command(self) -> float:
        return self._var("iobuf", "valve_command")

    # --------------------------------------------------------------- write

    @setpoint.write
    def _set_setpoint(self, value: float) -> None:
        limit = self._var("iobuf", "max_setpoint_unit")
        if not 0.0 <= value <= limit:
            raise ValueError(f"setpoint {value} outside 0..{limit}")

        # While the setpoint follows the analog input, a written one is ignored.
        if self._var("mfc", "sp_adc_enable"):
            self._post("/digital_analog_mode", {"mfc.sp_adc_enable": "0"})

        self._post(
            "/flow_setpoint_html",
            {"iobuf.setpoint_unit": f"{value:g}", "SUBMIT": "Submit"},
        )

        # The form answers with a page, not a status, so confirm by reading back.
        written = self._var("iobuf", "setpoint_unit", max_age=0)
        if abs(written - value) > max(1e-3, abs(value) * 1e-4):
            raise RuntimeError(f"setpoint read back as {written}, expected {value}")

    # ------------------------------------------------------- flow streaming

    def _ensure_stream(self) -> None:
        """Start the reader thread, or restart it if it stopped."""
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop.clear()
        self._first.clear()
        self._flow_value = None
        self._thread = threading.Thread(target=self._stream_worker, daemon=True)
        self._thread.start()

    def _stream_worker(self) -> None:
        stream = self.stream_flow(rate_hz=self._rate_hz)
        try:
            for _, value in stream:
                self._flow_value = value
                self._first.set()

                # Stop once nobody is reading, so the device's single trace slot
                # is not held by a caller that has moved on. The next read of
                # .flow starts it again.
                if self._stop.is_set():
                    break
                if time.monotonic() - self._last_read > self._idle_timeout:
                    break
        except Exception:
            self._flow_value = None
        finally:
            self._first.set()  # never leave a reader waiting
            stream.close()     # closes the connection and disables the trace

    def close(self) -> None:
        """Stop streaming and release the device's trace slot."""
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=self._timeout)
            self._thread = None

    def __enter__(self) -> "G50":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -------------------------------------------------------------- stream

    def stream_flow(self, rate_hz: float = 20.0, name: str = "PY") -> Iterator[Tuple[float, float]]:
        """Yield ``(device_time, flow)`` samples at up to 100 Hz.

        Reading ``iobuf.js`` costs a ~0.5 s round trip, so it tops out near
        2 Hz. This uses the same trace stream the plot applet uses: the device
        is asked once for a periodic trace, then pushes each sample down a
        single long-lived response.

        The device allows one trace at a time, so this cannot run while the
        plot page is tracing. The trace is disabled again when the generator is
        closed.

            for t, flow in mfc.stream_flow(rate_hz=20):
                ...
        """
        period_ms = max(10, round(1000.0 / rate_hz))  # 10 ms floor == 100 Hz

        self._post(
            "/ToolWeb/Con",
            None,
            f'<TraceDefine><Trace Name="{name}" Enable="True" Period="{period_ms}"'
            f' GroupSize="1"><EVIDS><V Name="EVID_0"/></EVIDS></Trace></TraceDefine>',
        )

        connection = http.client.HTTPConnection(self._host, self._port, timeout=self._timeout)
        try:
            connection.request("GET", f"/ToolWeb/Trace?Name={name}&Seq=0&Cont=1")
            response = connection.getresponse()

            block = ""
            while True:
                line = response.readline()
                if not line:
                    return

                block += line.decode("latin-1")
                if "</Data>" not in block:
                    continue

                stamp = _SAMPLE_TIME.search(block)
                values = _SAMPLE_HEX.findall(block)
                block = ""

                if stamp and values:
                    raw = struct.unpack(">f", bytes.fromhex(values[0][2:]))[0]
                    yield float(stamp.group(1)), raw
        finally:
            connection.close()
            # Free the device's single trace slot.
            try:
                self._post(
                    "/ToolWeb/Con",
                    None,
                    f'<TraceDefine><Trace Name="{name}" Enable="False"/></TraceDefine>',
                )
            except OSError:
                pass

    # ---------------------------------------------------------- properties

    @property
    def max_setpoint(self) -> float:
        return self._var("iobuf", "max_setpoint_unit")

    @property
    def full_scale(self) -> float:
        return self._var("iobuf", "full_scale")
