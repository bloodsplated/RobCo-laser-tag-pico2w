import asyncio
import types

import game_lobby
import hw_gui_tools
import hw_light_driver
import shared_hardware
import shared_utils


class _Pixels:
    def __init__(self):
        self.buf = [(0, 0, 0)] * 16
        self.show_count = 0

    def fill(self, value):
        self.buf = [value] * 16

    def __setitem__(self, idx, value):
        self.buf[idx] = value

    def show(self):
        self.show_count += 1


class _SoundUnit:
    def __init__(self):
        self.running = False

    def is_running(self):
        return self.running

    def is_active(self):
        return True

    def on_event(self, **kwargs):
        return "ok"

    def stop(self):
        return None


class _HapticUnit(_SoundUnit):
    pass


class _LCDRow:
    def __init__(self):
        self.text = ""


class _LCDMenu(list):
    def __init__(self):
        super().__init__([_LCDRow() for _ in range(5)])
        self.hidden = False


class _LCD:
    def __init__(self):
        self.menu_group = _LCDMenu()
        self.idle_menu = 0

    def is_active(self):
        return True

    def on_event(self, **kwargs):
        return None

    def show_menu(self, show):
        self.menu_group.hidden = not show

    def update_bar(self, value):
        return None

    def get_start_screen(self):
        return ["a", "b", "c", "d", "e"]


class _DummyDriver(shared_hardware.DriverModule):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active = True

    async def async_start(self):
        return None

    def cleanup(self):
        self.active = False


class _DummyLight(_DummyDriver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pixels = _Pixels()


class _DummyGui(_DummyDriver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unlocked = False
        self.events = []

    def menu_input(self, **payload):
        self.events.append(payload)


class _DummyLCD(_DummyDriver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.idle_menu = 0

    def get_start_screen(self):
        return ["a", "b", "c", "d", "e"]

    def show_menu(self, show):
        return None


class _DummyFX(_DummyDriver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.LIGHT = kwargs["LIGHT"]

    def stop(self):
        return None

    def on_event(self, **kwargs):
        return "fx"


def test_light_async_paths(monkeypatch):
    light = hw_light_driver.LIGHT()
    light.playlist = [("PIXELS", [0, 1], (255, 0, 0)), ("SHOW", 0, 0), ("STOP", 0, 0)]

    async def fast_sleep(_):
        light.active = False

    monkeypatch.setattr(hw_light_driver.asyncio, "sleep", fast_sleep)
    asyncio.run(light.async_start())

    light.running = False

    def show_once():
        light.running = False

    light.pixels.show = show_once
    asyncio.run(light.play_rainbow())


def test_gui_extra_branches(monkeypatch):
    gui = hw_gui_tools.GUI(LCD=_LCD())

    menu = [
        ("Toggle []", "SET_LIST", lambda **k: "val", {"view": "v"}),
        ("Flag", "SET_BOOL", lambda **k: "x", {"value": False, "view": "x"}),
        ("Data []", "DATA", None, {"name": "gun_id", "view": "0"}),
        ("Game", "SET_GAME", None, {"game_name": "game_offline", "view": "g"}),
        ("Quit", "QUIT", None, {"reset": False, "view": "q"}),
        ("Sub", "SUB", [("Child", "ACTION", lambda **k: "ok", {"view": "y"})]),
    ]
    gui.set_menu(menu)

    gui.unlocked = True
    gui.menu_input(value="INC")
    gui.menu_input(value="DNC")
    gui.menu_input(value="SINGLE")
    gui.menu_input(value="LONG")

    gui.button_action(("Back", "BACK"), "SINGLE")
    gui.button_action(("L", "LABEL"), "SINGLE")


def test_game_lobby_async_callbacks(monkeypatch):
    class _Light:
        def is_active(self):
            return True

        def update(self, **kwargs):
            return None

        pixels = _Pixels()

    class _Haptic:
        def on_event(self, **kwargs):
            return None

        def stop(self):
            return None

    class _FX:
        def __init__(self):
            self.LIGHT = _Light()
            self.HAPTIC = _Haptic()
            self.calls = 0

        def is_fx_running(self):
            self.calls += 1
            return False

        def on_event(self, **kwargs):
            return None

    class _HW:
        def __init__(self):
            self.fx_driver = _FX()
            self.gui_driver = types.SimpleNamespace(unlocked=True, on_event=lambda **k: None)
            self.lcd_driver = types.SimpleNamespace(show_menu=lambda *_: None)
            self.LCD = types.SimpleNamespace(get_start_screen=lambda: ["1", "2", "3", "4", "5"], menu_group=[types.SimpleNamespace(text="") for _ in range(5)])
            self.next_callback = None

        async def Bootup_show(self):
            return None

    shared_utils.data().gun_id = 7
    shared_utils.setglobals(_HW(), object())

    class FakeEvent:
        def __init__(self, target, payload=None, **kwargs):
            self.target = target
            self.payload = payload or {}
            self.payload.update(kwargs)

        def send(self):
            return [False, False, False, False]

    monkeypatch.setattr(game_lobby, "Event", FakeEvent)

    async def fast_sleep(_):
        return None

    monkeypatch.setattr(game_lobby.asyncio, "sleep", fast_sleep)

    rules = game_lobby.Rules(None, 10)
    rules.testlock = True
    asyncio.run(rules.fxcycle_callback())

    rules.testlock = True

    async def stop_after_first(_):
        rules.testlock = False

    monkeypatch.setattr(game_lobby.asyncio, "sleep", stop_after_first)
    asyncio.run(rules.fx_haptic_callback())


def test_shared_hardware_async_paths(monkeypatch):
    monkeypatch.setattr(shared_hardware.os, "uname", lambda: types.SimpleNamespace(machine="Test Device Name X"), raising=False)
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

    events = []

    class FakeEvent:
        def __init__(self, target, payload=None, **kwargs):
            self.target = target
            self.payload = payload or {}
            self.payload.update(kwargs)

        def send(self):
            events.append((self.target, self.payload))
            if self.target == "GAME.HEARTBEAT":
                hw.active = False
            return None

    monkeypatch.setattr(shared_hardware, "Event", FakeEvent)

    async def quick_sleep(_):
        return None

    monkeypatch.setattr(shared_hardware.asyncio, "sleep", quick_sleep)

    monkeypatch.setenv("SKIP_SHOW", "1")
    asyncio.run(hw.ready_check())

    hw.active = True

    async def one_tick(_):
        hw.active = False

    monkeypatch.setattr(shared_hardware.asyncio, "sleep", one_tick)
    asyncio.run(hw.async_callback())

    hw.active = True
    asyncio.run(hw.bootup_show())

    async def fake_ready():
        return None

    async def fake_callback():
        return None

    hw.ready_check = fake_ready
    hw.async_callback = fake_callback
    asyncio.run(hw.async_start_all())
