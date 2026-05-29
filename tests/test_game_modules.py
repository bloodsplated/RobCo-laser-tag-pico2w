import asyncio

import game_lobby
import game_offline
import shared_utils


class _Light:
    def __init__(self):
        self.updated = []

    def update(self, **kwargs):
        self.updated.append(kwargs)


class _FX:
    def __init__(self):
        self.LIGHT = _Light()

    def is_fx_running(self):
        return False

    def on_event(self, **kwargs):
        return "ok"


class _LCD:
    def __init__(self):
        self.menu_visible = None

    def show_menu(self, value):
        self.menu_visible = value


class _GUI:
    def __init__(self):
        self.unlocked = True

    def on_event(self, **kwargs):
        return None


class _HW:
    def __init__(self):
        self.fx_driver = _FX()
        self.gui_driver = _GUI()
        self.lcd_driver = _LCD()
        self.next_callback = None

    def mqtt_message(self, **payload):
        pass

def _stub_event_send(monkeypatch):
    sent = []

    class FakeEvent:
        def __init__(self, target, payload=None, **kwargs):
            self.target = target
            self.payload = payload or {}
            self.payload.update(kwargs)

        def send(self):
            sent.append((self.target, self.payload))
            return [False, False, False, False]

    monkeypatch.setattr(game_lobby, "Event", FakeEvent)
    return sent


def test_offline_game_loaded_starts_game(monkeypatch):
    hw = _HW()
    shared_utils.data().gun_id = 9
    shared_utils.setglobals(hw, object())
    _stub_event_send(monkeypatch)

    rules = game_offline.Rules(None, 1)
    rules.game_loaded()
    assert rules.status == "ALIVE"


def test_lobby_menu_and_actions(monkeypatch):
    hw = _HW()
    shared_utils.data().gun_id = 9
    shared_utils.setglobals(hw, object())
    _stub_event_send(monkeypatch)

    rules = game_lobby.Rules(None, 2)
    rules.game_loaded()

    assert "Wep:" in rules.gunchange(INPUT="INC")
    assert "Team" in rules.teamchange(INPUT="INC")

    rules.run_test(run_test="FX_Tests")
    assert hw.next_callback == rules.fxcycle_callback

    rules.testlock = True
    rules.game_input(name="TRIG", value="SINGLE")
    assert rules.testlock is False


def test_lobby_update_gamelcd_lock(monkeypatch):
    hw = _HW()
    shared_utils.data().gun_id = 9
    shared_utils.setglobals(hw, object())
    sent = _stub_event_send(monkeypatch)

    rules = game_lobby.Rules(None, 3)
    rules.testlock = True
    rules.update_gamelcd()
    assert sent == []


def test_lobby_irtag_capture(monkeypatch):
    hw = _HW()
    shared_utils.data().gun_id = 9
    shared_utils.setglobals(hw, object())
    _stub_event_send(monkeypatch)

    rules = game_lobby.Rules(None, 4)
    rules.game_irtag(PlayerID=42)
    assert 42 in rules.ir_hits
