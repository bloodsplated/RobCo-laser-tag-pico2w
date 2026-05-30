import hw_sound_fx_uart as sound_mod
from hw_sound_fx_uart import SOUND
from shared_utils import data


class _TestUART:
    def __init__(self, read_values=None, readline_values=None):
        self.writes = []
        self._read_values = list(read_values or [])
        self._readline_values = list(readline_values or [])

    def write(self, payload):
        self.writes.append(payload)

    def read(self):
        if not self._read_values:
            return None
        return self._read_values.pop(0)

    def readline(self):
        if not self._readline_values:
            return None
        return self._readline_values.pop(0)


class _LogSpy:
    def __init__(self):
        self.debug_calls = []
        self.error_calls = []

    def debug(self, *parts):
        self.debug_calls.append(parts)

    def error(self, *parts):
        self.error_calls.append(parts)


def test_sound_init_populates_names_and_sets_active():
    s = SOUND()

    assert s.is_active() is True
    assert s.module_name == "hw_sound_fx_uart"
    assert len(data().sound_names) == len(s.sound_list)
    assert "BOOT_00" in data().sound_names


def test_stop_cleanup_and_is_running(monkeypatch):
    s = SOUND()
    s.uart = _TestUART()

    monkeypatch.setattr(sound_mod.time, "monotonic", lambda: 50.0)
    s.done_at = 60.0
    assert s.is_running() is True

    s.done_at = 40.0
    assert s.is_running() is False

    s.stop()
    assert s.uart.writes[-1] == b"q\n"

    s.active = True
    s.cleanup()
    assert s.active is False
    assert s.uart.writes[-1] == b"q\n"


def test_on_event_stop_mute_and_play(monkeypatch):
    s = SOUND()
    s.uart = _TestUART()
    s.done_at = 0.0

    calls = iter([100.0, 100.0])
    monkeypatch.setattr(sound_mod.time, "monotonic", lambda: next(calls))

    s.on_event(STOP=True, MUTE=False, SoundName="FIRE_00")

    assert b"q\n" in s.uart.writes
    assert b"PFIRE_00 WAV\n" in s.uart.writes
    assert s.done_at > 100.0


def test_on_event_skip_when_running_and_missing_sound(monkeypatch):
    s = SOUND()
    s.uart = _TestUART()

    s.done_at = 200.0
    monkeypatch.setattr(sound_mod.time, "monotonic", lambda: 100.0)
    s.on_event(SoundName="FIRE_00")
    assert s.uart.writes == []

    s.done_at = 0.0
    s.on_event(SoundName="NOT_A_SOUND")
    assert s.uart.writes == []


def test_on_event_muted_does_not_write_play_command(monkeypatch):
    s = SOUND()
    s.uart = _TestUART()
    calls = iter([10.0, 10.0])
    monkeypatch.setattr(sound_mod.time, "monotonic", lambda: next(calls))

    s.on_event(MUTE=True, SoundName="FIRE_00")
    assert s.uart.writes == []


def test_on_event_exception_path_is_caught(monkeypatch):
    s = SOUND()
    spy = _LogSpy()

    monkeypatch.setattr(sound_mod, "log", spy)
    monkeypatch.setattr(s, "is_running", lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    s.on_event(SoundName="FIRE_00")
    assert len(spy.error_calls) == 1
    assert spy.error_calls[0][0] == "on_event Exception"




def test_change_vol_calls_send_simple_and_updates_current_volume(monkeypatch):
    s = SOUND()
    calls = []

    def _fake_send(cmd, reply=False):
        calls.append((cmd, reply))
        return "198" if reply else None

    monkeypatch.setattr(s, "_send_simple", _fake_send)

    out = s.change_vol("+", mult=3)

    assert out == 198
    assert s._cur_vol == 198
    assert calls == [("+", False), ("+", False), ("+", False), ("+", True)]


def test_send_simple_paths(monkeypatch):
    s = SOUND()

    # reply=False branch
    s.uart = _TestUART()
    assert s._send_simple("v") is None
    assert s.uart.writes[-1] == b"v\n"

    # reply=True with buffer drain and decode
    s.uart = _TestUART(read_values=[b"x", b"y", None], readline_values=[b"210\n"])
    monkeypatch.setattr(sound_mod, "sleep", lambda _secs: None)
    assert s._send_simple("v", True) == "210"
    assert s.uart.writes[-1] == b"v\n"

    # reply=True with non-bytes readline
    s.uart = _TestUART(read_values=[None], readline_values=["not-bytes"])
    assert s._send_simple("v", True) is None


def test_send_simple_reply_exception_logs_error(monkeypatch):
    s = SOUND()
    spy = _LogSpy()

    monkeypatch.setattr(sound_mod, "log", spy)
    monkeypatch.setattr(sound_mod, "sleep", lambda _secs: None)
    s.uart = _TestUART(read_values=[None], readline_values=[b"\xff"])

    assert s._send_simple("v", True) is None
    assert len(spy.error_calls) == 1
    assert spy.error_calls[0][0] == "_send_simple Exception:"
