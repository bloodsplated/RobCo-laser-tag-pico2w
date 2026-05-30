import logging
import pathlib
import sys
import types


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))


# ---- CircuitPython/Desktop compatibility stubs ----


def _install_stub(name, module):
    sys.modules[name] = module


class _FakeGroup(list):
    def __init__(self):
        super().__init__()
        self.hidden = False


class _FakeLabel:
    def __init__(self, font, text="", **kwargs):
        self.font = font
        self.text = text
        self.color = kwargs.get("color")
        self.background_color = kwargs.get("background_color")


class _FakePixels:
    def __init__(self, pin, n, brightness=1, auto_write=False):
        self.n = n
        self.values = [(0, 0, 0)] * n

    def __setitem__(self, idx, value):
        self.values[idx] = value

    def __getitem__(self, idx):
        return self.values[idx]

    def fill(self, value):
        self.values = [value] * self.n

    def show(self):
        return None


class _FakeVoice:
    def __init__(self):
        self.level = 0.0
        self.playing = False

    def play(self, _snd):
        self.playing = True

    def stop(self):
        self.playing = False


class _FakeAudioOut:
    def __init__(self, *args, **kwargs):
        self.playing = False

    def play(self, _mixer):
        self.playing = True

    def stop(self):
        self.playing = False


class _FakePulseOut:
    def __init__(self, *args, **kwargs):
        self.last = None


class _FakePulseIn:
    def __init__(self, *args, **kwargs):
        self.cleared = False

    def clear(self):
        self.cleared = True

    def resume(self):
        return None


class _FakeIRMessage:
    def __init__(self, code, pulses=None):
        self.code = tuple(code)
        self.pulses = pulses if pulses is not None else []


class _FakeGenericTransmit:
    def __init__(self, **kwargs):
        self.sent = []

    def transmit(self, pulseout, value, repeat=0):
        pulseout.last = (list(value), repeat)
        self.sent.append((pulseout, list(value), repeat))


class _FakeDecoder:
    def __init__(self, pulsein):
        self._queue = []

    def read(self):
        return list(self._queue)

    def clear(self):
        self._queue = []


class _FakeDRV:
    def __init__(self, i2c):
        self.sequence = [None] * 8
        self.play_called = 0
        self.stop_called = 0

    def play(self):
        self.play_called += 1

    def stop(self):
        self.stop_called += 1


class _FakeEffect:
    def __init__(self, idx):
        self.idx = idx


class _FakePause:
    def __init__(self, length):
        self.length = length


class _FakeEncoder:
    def __init__(self, *args, **kwargs):
        self.position = 0


class _FakeButton:
    SINGLE = 1
    DOUBLE = 2
    TRIPLE = 3
    LONG = 4
    ANY_CLICK = 99

    def __init__(self, *args, **kwargs):
        pass


class _FakeMultiButton:
    def __init__(self, **kwargs):
        self.calls = 0

    async def wait(self, **kwargs):
        self.calls += 1
        return ("TRIG", _FakeButton.SINGLE)


class _FakeDisplay:
    def __init__(self, *args, **kwargs):
        self.root_group = None


class _FakeWaveFile:
    def __init__(self, file_obj):
        self.channel_count = 1
        self.sample_rate = 22050
        self.bits_per_sample = 16


class _FakeUART:
    def __init__(self, *args, **kwargs):
        self.writes = []

    def write(self, payload):
        self.writes.append(payload)

    def readline(self):
        return None


class _FakeDirection:
    INPUT = 0
    OUTPUT = 1


class _FakePull:
    UP = 1
    DOWN = 2


class _FakeDigitalInOut:
    def __init__(self, pin):
        self.pin = pin
        self.direction = None
        self.pull = None
        self.value = True


def pytest_configure(config):
    tick_state = {"value": 0}

    def _ticks_ms():
        # Step by >1s so cooldown checks in game logic are deterministic in tests.
        tick_state["value"] += 1100
        return tick_state["value"]

    supervisor = types.SimpleNamespace(
        runtime=types.SimpleNamespace(autoreload=True),
        ticks_ms=_ticks_ms,
    )
    _install_stub("supervisor", supervisor)

    adalog = types.ModuleType("adafruit_logging")
    adalog.DEBUG = logging.DEBUG
    adalog.ERROR = logging.ERROR
    adalog.getLogger = logging.getLogger
    adalog.StreamHandler = logging.StreamHandler
    adalog.Formatter = logging.Formatter
    _install_stub("adafruit_logging", adalog)

    board = types.ModuleType("board")
    for pin in ["GP0", "GP6", "GP7", "GP8", "GP9", "GP10", "GP11", "GP12", "GP18", "GP20", "GP21", "GP22"]:
        setattr(board, pin, pin)
    board.STEMMA_I2C = lambda: object()
    _install_stub("board", board)

    busio = types.ModuleType("busio")
    busio.UART = _FakeUART
    _install_stub("busio", busio)

    digitalio = types.ModuleType("digitalio")
    digitalio.DigitalInOut = _FakeDigitalInOut
    digitalio.Direction = _FakeDirection
    digitalio.Pull = _FakePull
    _install_stub("digitalio", digitalio)

    microcontroller = types.ModuleType("microcontroller")
    microcontroller.cpu = types.SimpleNamespace(uid=b"\x10\x20\x30\x40")
    _install_stub("microcontroller", microcontroller)

    storage = types.ModuleType("storage")
    storage.erase_filesystem = lambda: None
    _install_stub("storage", storage)

    displayio = types.ModuleType("displayio")
    displayio.Group = _FakeGroup
    displayio.release_displays = lambda: None
    _install_stub("displayio", displayio)

    terminalio = types.ModuleType("terminalio")
    terminalio.FONT = object()
    _install_stub("terminalio", terminalio)

    adafruit_displayio_ssd1306 = types.ModuleType("adafruit_displayio_ssd1306")
    adafruit_displayio_ssd1306.SSD1306 = _FakeDisplay
    _install_stub("adafruit_displayio_ssd1306", adafruit_displayio_ssd1306)

    label_mod = types.ModuleType("adafruit_display_text.label")
    label_mod.Label = _FakeLabel
    adafruit_display_text = types.ModuleType("adafruit_display_text")
    adafruit_display_text.label = label_mod
    _install_stub("adafruit_display_text", adafruit_display_text)
    _install_stub("adafruit_display_text.label", label_mod)

    i2cdisplaybus = types.ModuleType("i2cdisplaybus")
    i2cdisplaybus.I2CDisplayBus = lambda *args, **kwargs: object()
    _install_stub("i2cdisplaybus", i2cdisplaybus)

    neopixel = types.ModuleType("neopixel")
    neopixel.NeoPixel = _FakePixels
    _install_stub("neopixel", neopixel)

    audiobusio = types.ModuleType("audiobusio")
    audiobusio.I2SOut = _FakeAudioOut
    _install_stub("audiobusio", audiobusio)

    audiomixer = types.ModuleType("audiomixer")

    class _FakeMixer:
        def __init__(self, **kwargs):
            self.voice = [_FakeVoice()]

    audiomixer.Mixer = _FakeMixer
    _install_stub("audiomixer", audiomixer)

    audiocore = types.ModuleType("audiocore")
    audiocore.WaveFile = _FakeWaveFile
    _install_stub("audiocore", audiocore)

    pulseio = types.ModuleType("pulseio")
    pulseio.PulseOut = _FakePulseOut
    pulseio.PulseIn = _FakePulseIn
    _install_stub("pulseio", pulseio)

    adafruit_irremote = types.ModuleType("adafruit_irremote")
    adafruit_irremote.IRMessage = _FakeIRMessage
    adafruit_irremote.GenericTransmit = _FakeGenericTransmit
    adafruit_irremote.NonblockingGenericDecode = _FakeDecoder
    _install_stub("adafruit_irremote", adafruit_irremote)

    adafruit_drv2605 = types.ModuleType("adafruit_drv2605")
    adafruit_drv2605.DRV2605 = _FakeDRV
    adafruit_drv2605.Effect = _FakeEffect
    adafruit_drv2605.Pause = _FakePause
    _install_stub("adafruit_drv2605", adafruit_drv2605)

    rotaryio = types.ModuleType("rotaryio")
    rotaryio.IncrementalEncoder = _FakeEncoder
    _install_stub("rotaryio", rotaryio)

    async_button = types.ModuleType("async_button")
    async_button.Button = _FakeButton
    async_button.MultiButton = _FakeMultiButton
    _install_stub("async_button", async_button)


import pytest


@pytest.fixture(autouse=True)
def _reset_shared_globals(monkeypatch):
    import shared_utils

    monkeypatch.setattr(shared_utils, "THE_ONLY_HARDWARE", None, raising=False)
    monkeypatch.setattr(shared_utils, "THE_ONLY_GAMELOADER", None, raising=False)
    monkeypatch.setattr(shared_utils, "THE_ONLY_DATA", None, raising=False)
    yield
