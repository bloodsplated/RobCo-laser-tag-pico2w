import asyncio
import types

import shared_hardware
import shared_utils


class _DummyDriver:
    def __init__(self, *args, **kwargs):
        self._active = True
        self.cleaned = False
        self.module_name = self.__class__.__name__

    async def async_start(self):
        return "ok"

    def is_active(self):
        return self._active

    def cleanup(self):
        self.cleaned = True

    def stop(self):
        self.cleaned = True


class _DummyGui(_DummyDriver):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.unlocked = False
        self.calls = []

    def menu_input(self, **payload):
        self.calls.append(payload)


class _DummyLCD(_DummyDriver):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.idle_menu = 0

    def get_start_screen(self):
        return ["a", "b", "c", "d", "e"]

    def show_menu(self, show):
        return None


class _DummyLight(_DummyDriver):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.pixels = types.SimpleNamespace(fill=lambda *_: None, show=lambda: None, __setitem__=lambda *a: None)


class _DummyFX(_DummyDriver):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.LIGHT = kwargs["LIGHT"]

    def on_event(self, **kwargs):
        return "fx"

    def stop(self):
        return None


def test_hardware_init_and_cleanup(monkeypatch):
    monkeypatch.setattr(shared_hardware.os, "uname", lambda: types.SimpleNamespace(machine="Test Machine Name 123"), raising=False)
    monkeypatch.setattr(shared_hardware, "INPUT_DRIVER", _DummyDriver)
    monkeypatch.setattr(shared_hardware, "IR_DRIVER", _DummyDriver)
    monkeypatch.setattr(shared_hardware, "LCD_DRIVER", _DummyLCD)
    monkeypatch.setattr(shared_hardware, "GUI_DRIVER", _DummyGui)
    monkeypatch.setattr(shared_hardware, "SOUND_DRIVER", _DummyDriver)
    monkeypatch.setattr(shared_hardware, "HAPTIC_DRIVER", _DummyDriver)
    monkeypatch.setattr(shared_hardware, "LIGHT_DRIVER", _DummyLight)
    monkeypatch.setattr(shared_hardware, "FX_DRIVER", _DummyFX)

    hw = shared_hardware.Hardware()
    shared_utils.setglobals(hw, object())

    hw.on_event(name="ROTARY", value="INC")
    assert hw.gui_driver.calls

    hw.msg_youare(gun_sn=shared_utils.data().gun_sn, gun_id=77, gun_sname="TEST")
    assert shared_utils.data().gun_id == 77

    hw.cleanup()
    assert hw.active is False


def test_hardware_do_callback(monkeypatch):
    monkeypatch.setattr(shared_hardware.os, "uname", lambda: types.SimpleNamespace(machine="Test Machine Name 123"), raising=False)
    monkeypatch.setattr(shared_hardware, "INPUT_DRIVER", _DummyDriver)
    monkeypatch.setattr(shared_hardware, "IR_DRIVER", _DummyDriver)
    monkeypatch.setattr(shared_hardware, "LCD_DRIVER", _DummyLCD)
    monkeypatch.setattr(shared_hardware, "GUI_DRIVER", _DummyGui)
    monkeypatch.setattr(shared_hardware, "SOUND_DRIVER", _DummyDriver)
    monkeypatch.setattr(shared_hardware, "HAPTIC_DRIVER", _DummyDriver)
    monkeypatch.setattr(shared_hardware, "LIGHT_DRIVER", _DummyLight)
    monkeypatch.setattr(shared_hardware, "FX_DRIVER", _DummyFX)

    hw = shared_hardware.Hardware()

    called = {"ok": False}

    async def cb():
        called["ok"] = True

    asyncio.run(hw.do_callback(cb))
    assert called["ok"] is True
