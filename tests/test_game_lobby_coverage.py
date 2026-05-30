import asyncio

import game_lobby
import pytest
import shared_classes
import shared_utils


class _TextCell:
    def __init__(self):
        self.text = ""


class _Light:
    def __init__(self):
        self.updated = []

    def update(self, **kwargs):
        self.updated.append(kwargs)


class _Haptic:
    def __init__(self):
        self.events = []
        self.stop_calls = 0

    def on_event(self, **kwargs):
        self.events.append(kwargs)

    def stop(self):
        self.stop_calls += 1


class _FX:
    def __init__(self):
        self.LIGHT = _Light()
        self.HAPTIC = _Haptic()
        self._running_steps = []

    def is_fx_running(self):
        if self._running_steps:
            return self._running_steps.pop(0)
        return False


class _Sound:
    def __init__(self):
        self.active = True
        self.running_steps = []
        self.vol_ops = []
        self.sound_list = [("A", "alpha", 0.1), ("B", "beta", 0.2)]

    def is_active(self):
        return self.active

    def is_running(self):
        if self.running_steps:
            return self.running_steps.pop(0)
        return False

    def change_vol(self, op):
        self.vol_ops.append(op)
        return "UP" if op == "+" else "DOWN"


class _LCDDriver:
    def __init__(self):
        self.show_calls = []

    def show_menu(self, value):
        self.show_calls.append(value)


class _LCDModule:
    def __init__(self):
        self.menu_group = [_TextCell() for _ in range(5)]

    def get_start_screen(self):
        return ["s0", "s1", "s2", "s3", "s4"]


class _GUI:
    def __init__(self):
        self.unlocked = True


class _HW:
    def __init__(self):
        self.fx_driver = _FX()
        self.sound_driver = _Sound()
        self.gui_driver = _GUI()
        self.lcd_driver = _LCDDriver()
        self.LCD = _LCDModule()
        self.next_callback = None
        self.boot_calls = 0

    async def Bootup_show(self):
        self.boot_calls += 1


@pytest.fixture
def lobby_ctx(monkeypatch):
    hw = _HW()
    shared_utils.data().debug = False
    shared_utils.data().gun_id = 9
    shared_utils.setglobals(hw, object())

    sent = []
    holder = {"rules": None, "echo_ir": False}

    class FakeEvent:
        def __init__(self, target, payload=None, **kwargs):
            self.target = target
            self.payload = payload or {}
            self.payload.update(kwargs)

        def send(self):
            sent.append((self.target, self.payload))
            if self.target == "IR" and holder["echo_ir"] and holder["rules"] is not None:
                holder["rules"].ir_hits.add(self.payload.get("player_id", 0))
            return [False, False, False, False]

    monkeypatch.setattr(game_lobby, "Event", FakeEvent)
    rules = game_lobby.Rules(None, 11)
    holder["rules"] = rules
    return rules, hw, sent, holder


def test_game_loaded_menu_includes_debug_when_enabled(lobby_ctx):
    rules, _hw, sent, _holder = lobby_ctx
    shared_utils.data().debug = True
    rules.game_loaded()

    gui_events = [payload for target, payload in sent if target == "GUI"]
    menu = gui_events[0]["MENU"]["setMenu"]
    labels = [item[0] for item in menu]
    assert "DEBUG Tools" in labels
    assert "Quit" in labels


def test_gunchange_and_teamchange_branches(lobby_ctx):
    rules, hw, _sent, _holder = lobby_ctx

    rules.game_shot_type = 1
    assert rules.gunchange(INPUT="INC") == "Wep:2 Basic"
    assert rules.gunchange(INPUT="DNC") == "Wep:1 Basic"
    assert rules.gunchange(INPUT="DNC") == "Wep:1 Basic"

    rules.game_team_id = 0
    assert "Team" in rules.teamchange(INPUT="INC")
    assert "ID:0" in rules.teamchange(INPUT="DNC")
    assert hw.fx_driver.LIGHT.updated


def test_volchange_all_paths(lobby_ctx):
    rules, hw, _sent, _holder = lobby_ctx

    hw.sound_driver.active = False
    assert rules.volchange(INPUT="INC") == "Vol: offline"

    hw.sound_driver.active = True
    assert rules.volchange(INPUT="INC") == "Vol: UP"
    assert rules.volchange(INPUT="DNC") == "Vol: DOWN"
    assert rules.volchange(INPUT="OTHER") == "Vol: X"


def test_run_test_assigns_callbacks_and_honors_lock(lobby_ctx):
    rules, hw, _sent, _holder = lobby_ctx

    rules.run_test(run_test="IR_100")
    assert hw.next_callback == rules.ir100_callback

    rules.testlock = False
    rules.run_test(run_test="FX_Tests")
    assert hw.next_callback == rules.fxcycle_callback

    rules.testlock = False
    rules.run_test(run_test="FX_HAPTIC")
    assert hw.next_callback == rules.fx_haptic_callback

    rules.testlock = False
    rules.run_test(run_test="BootUp")
    assert hw.next_callback == rules.boot_up_callback

    rules.testlock = False
    rules.run_test(run_test="SOUND_LIST")
    assert hw.next_callback == rules.sound_list_callback

    locked_callback = hw.next_callback
    rules.run_test(run_test="IR_100")
    assert hw.next_callback == locked_callback


def test_callback_cleanup_sets_state_and_sends_stop(monkeypatch, lobby_ctx):
    rules, hw, sent, _holder = lobby_ctx
    calls = {"lcd": 0}

    def _fake_update_lcd():
        calls["lcd"] += 1

    monkeypatch.setattr(rules, "update_gamelcd", _fake_update_lcd)
    rules.testlock = True
    hw.gui_driver.unlocked = False

    rules.callback_cleanup()

    assert rules.testlock is False
    assert hw.gui_driver.unlocked is True
    assert hw.lcd_driver.show_calls[-1] is True
    assert calls["lcd"] == 1
    assert any(target == "FX" and payload.get("STOP") is True for target, payload in sent)


def test_sound_list_callback_inactive_path(lobby_ctx):
    rules, hw, _sent, _holder = lobby_ctx
    hw.sound_driver.active = False
    called = {"cleanup": 0}

    def _cleanup():
        called["cleanup"] += 1

    rules.callback_cleanup = _cleanup
    asyncio.run(rules.sound_list_callback())
    assert called["cleanup"] == 1


def test_sound_list_callback_active_path(monkeypatch, lobby_ctx):
    rules, hw, sent, _holder = lobby_ctx
    hw.sound_driver.active = True
    hw.sound_driver.running_steps = [True, False, False]
    rules.testlock = True
    called = {"cleanup": 0}

    async def _fast_sleep(_delay):
        rules.testlock = False

    monkeypatch.setattr(game_lobby.asyncio, "sleep", _fast_sleep)

    def _cleanup():
        called["cleanup"] += 1

    rules.callback_cleanup = _cleanup
    asyncio.run(rules.sound_list_callback())

    assert called["cleanup"] == 1
    assert any(target == "FX" and "SOUND" in payload for target, payload in sent)


def test_boot_up_callback(monkeypatch, lobby_ctx):
    rules, hw, _sent, _holder = lobby_ctx
    called = {"cleanup": 0}

    async def _fast_sleep(_delay):
        return None

    monkeypatch.setattr(game_lobby.asyncio, "sleep", _fast_sleep)

    def _cleanup():
        called["cleanup"] += 1

    rules.callback_cleanup = _cleanup
    asyncio.run(rules.boot_up_callback())

    assert hw.lcd_driver.show_calls[-1] is True
    assert hw.gui_driver.unlocked is False
    assert hw.boot_calls == 1
    assert hw.LCD.menu_group[0].text == "s0"
    assert called["cleanup"] == 1


def test_fx_haptic_callback_loop_and_cleanup(monkeypatch, lobby_ctx):
    rules, hw, _sent, _holder = lobby_ctx
    rules.testlock = True
    called = {"cleanup": 0, "sleeps": 0}

    async def _fast_sleep(_delay):
        called["sleeps"] += 1
        if called["sleeps"] >= 1:
            rules.testlock = False

    monkeypatch.setattr(game_lobby.asyncio, "sleep", _fast_sleep)

    def _cleanup():
        called["cleanup"] += 1

    rules.callback_cleanup = _cleanup
    asyncio.run(rules.fx_haptic_callback())

    assert hw.fx_driver.HAPTIC.events
    assert hw.fx_driver.HAPTIC.stop_calls == 1
    assert called["cleanup"] == 1


def test_fxcycle_callback_paths(monkeypatch, lobby_ctx):
    rules, hw, _sent, _holder = lobby_ctx
    rules.testlock = True
    hw.fx_driver._running_steps = [False] * 20
    triggered = []
    called = {"cleanup": 0}

    async def _fast_sleep(_delay):
        return None

    monkeypatch.setattr(game_lobby.asyncio, "sleep", _fast_sleep)
    monkeypatch.setattr(game_lobby.time, "monotonic", lambda: 100.0)

    def _trigger_fx(name, payload):
        triggered.append((name, payload["status"], payload["is_winning"]))

    rules.trigger_fx = _trigger_fx

    def _cleanup():
        called["cleanup"] += 1

    rules.callback_cleanup = _cleanup
    asyncio.run(rules.fxcycle_callback())

    assert ("GAMEOVER", "ALIVE", True) in triggered
    assert ("DEAD", "DEAD", False) in triggered
    assert called["cleanup"] == 1


def test_ir100_callback_early_exit(monkeypatch, lobby_ctx):
    rules, _hw, _sent, _holder = lobby_ctx
    rules.testlock = False
    called = {"cleanup": 0}

    async def _fast_sleep(_delay):
        return None

    monkeypatch.setattr(game_lobby.asyncio, "sleep", _fast_sleep)

    def _cleanup():
        called["cleanup"] += 1

    rules.callback_cleanup = _cleanup
    asyncio.run(rules.ir100_callback())
    assert called["cleanup"] == 1


def test_ir100_callback_full_path(monkeypatch, lobby_ctx):
    rules, _hw, sent, holder = lobby_ctx
    rules.testlock = True
    holder["echo_ir"] = True
    called = {"cleanup": 0}

    async def _fast_sleep(delay):
        if delay == 0.5:
            rules.testlock = False

    monkeypatch.setattr(game_lobby.asyncio, "sleep", _fast_sleep)

    def _cleanup():
        called["cleanup"] += 1

    rules.callback_cleanup = _cleanup
    asyncio.run(rules.ir100_callback())

    assert 1 in rules.ir_hits
    assert 98 in rules.ir_hits
    assert called["cleanup"] == 1
    assert any(target == "GUI" and "LCD" in payload for target, payload in sent)


def test_game_input_and_update_gamelcd_overrides(monkeypatch, lobby_ctx):
    rules, _hw, _sent, _holder = lobby_ctx
    calls = {"on_event": 0, "update": 0}

    def _base_on_event(self, **kwargs):
        calls["on_event"] += 1

    def _base_update(self):
        calls["update"] += 1

    monkeypatch.setattr(shared_classes.BaseGameRules, "on_event", _base_on_event)
    monkeypatch.setattr(shared_classes.BaseGameRules, "update_gamelcd", _base_update)

    rules.testlock = True
    rules.game_input(name="TRIG", value="SINGLE")
    assert rules.testlock is False
    assert calls["on_event"] == 1

    rules.testlock = False
    rules.game_input(name="TRIG", value="SINGLE")
    assert calls["on_event"] == 2

    rules.testlock = True
    rules.update_gamelcd()
    assert calls["update"] == 0

    rules.testlock = False
    rules.update_gamelcd()
    assert calls["update"] == 1


def test_game_irtag_adds_default_and_playerid(lobby_ctx):
    rules, _hw, _sent, _holder = lobby_ctx
    rules.game_irtag(PlayerID=42)
    rules.game_irtag()
    assert 42 in rules.ir_hits
    assert 0 in rules.ir_hits


def test_sound_list_callback_final_wait_loop_line(monkeypatch, lobby_ctx):
    rules, hw, _sent, _holder = lobby_ctx
    hw.sound_driver.active = True
    hw.sound_driver.sound_list = []
    rules.testlock = True
    called = {"cleanup": 0}

    async def _sleep_once(_delay):
        rules.testlock = False

    monkeypatch.setattr(game_lobby.asyncio, "sleep", _sleep_once)

    def _cleanup():
        called["cleanup"] += 1

    rules.callback_cleanup = _cleanup
    asyncio.run(rules.sound_list_callback())
    assert called["cleanup"] == 1


def test_fx_haptic_callback_inner_wait_line(monkeypatch, lobby_ctx):
    rules, hw, _sent, _holder = lobby_ctx
    rules.testlock = True
    hw.fx_driver._running_steps = [True, False]
    called = {"cleanup": 0, "sleeps": 0}

    async def _sleep_then_unlock(_delay):
        called["sleeps"] += 1
        if called["sleeps"] > 1:
            rules.testlock = False

    monkeypatch.setattr(game_lobby.asyncio, "sleep", _sleep_then_unlock)

    def _cleanup():
        called["cleanup"] += 1

    rules.callback_cleanup = _cleanup
    asyncio.run(rules.fx_haptic_callback())
    assert called["cleanup"] == 1


def test_fxcycle_callback_inner_wait_line(monkeypatch, lobby_ctx):
    rules, hw, _sent, _holder = lobby_ctx
    rules.testlock = True
    hw.fx_driver._running_steps = [True, False] + ([False] * 20)
    called = {"cleanup": 0}

    async def _sleep_noop(_delay):
        return None

    monkeypatch.setattr(game_lobby.asyncio, "sleep", _sleep_noop)
    monkeypatch.setattr(game_lobby.time, "monotonic", lambda: 100.0)

    def _cleanup():
        called["cleanup"] += 1

    rules.callback_cleanup = _cleanup
    asyncio.run(rules.fxcycle_callback())
    assert called["cleanup"] == 1
