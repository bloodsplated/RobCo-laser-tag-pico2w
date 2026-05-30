import sys
import types

import pytest

import shared_classes
import shared_gamelogic
import shared_utils


class _Rule(shared_classes.BaseGameRules):
    def __init__(self, gid):
        super().__init__(None, gid)
        self.called = []

    def game_loaded(self, **kwargs):
        self.called.append(("loaded", kwargs))

    def game_input(self, **kwargs):
        self.called.append(("input", kwargs))
        return "ok"


class _FX:
    def on_event(self, **kwargs):
        return "fx"


class _HW:
    def __init__(self):
        self.fx_driver = _FX()


def test_pass_event_type_validation():
    gl = shared_gamelogic.GameLoader()
    with pytest.raises(TypeError):
        gl.pass_event(1, {})
    with pytest.raises(TypeError):
        gl.pass_event("GAME.INPUT", [])


def test_pass_event_to_active_rules(monkeypatch):
    shared_utils.setglobals(_HW(), object())
    gl = shared_gamelogic.GameLoader()
    gl.curentgamerules = _Rule(1)

    reply = gl.pass_event("GAME.INPUT", {"name": "TRIG", "value": "SINGLE"})
    assert reply == "ok"


def test_switch_game_invalid_name(monkeypatch):
    shared_utils.setglobals(_HW(), object())
    gl = shared_gamelogic.GameLoader()
    out = gl.switch_game(GAME_TYPE="bad_name")
    assert "Invalid Game Type" in out


def test_switch_game_success(monkeypatch):
    shared_utils.data().gun_id = 8
    shared_utils.setglobals(_HW(), object())

    mod = types.ModuleType("game_fake")

    class Rules(_Rule):
        pass

    mod.Rules = Rules
    monkeypatch.setitem(sys.modules, "game_fake", mod)

    gl = shared_gamelogic.GameLoader()
    out = gl.switch_game(GAME_TYPE="game_fake", lastgame={"score": 1})
    assert out is None
    assert isinstance(gl.curentgamerules, shared_classes.BaseGameRules)


def test_game_msg_event_routes(monkeypatch):
    shared_utils.setglobals(_HW(), object())
    gl = shared_gamelogic.GameLoader()

    class _Receiver:
        def __init__(self):
            self.events = []

        def EVENT_TAG(self, **kwargs):
            self.events.append(kwargs)

    r = _Receiver()
    gl.curentgamerules = r
    gl.game_msg_event(TYPE="GAME_TAG", value=1)
    assert r.events and r.events[0]["value"] == 1


def test_pass_event_switch_routes_and_none_current(monkeypatch):
    gl = shared_gamelogic.GameLoader()
    seen = []

    def _fake_switch_game(**kwargs):
        seen.append(kwargs)
        return None

    monkeypatch.setattr(gl, "switch_game", _fake_switch_game)

    assert gl.pass_event("GAME.START", {"GAME_TYPE": "game_fake"}) is None
    assert gl.pass_event("GAME.GAMEOVER", {}) is None
    assert gl.pass_event("GAME.INPUT", {"name": "TRIG"}) is None

    assert seen[0] == {"GAME_TYPE": "game_fake"}
    assert seen[1] == {"GAME_TYPE": "game_lobby"}


def test_pass_event_non_callable_raises_typeerror():
    gl = shared_gamelogic.GameLoader()
    gl.curentgamerules = object()
    with pytest.raises(TypeError):
        gl.pass_event("GAME.INPUT", {})


def test_get_current_game_branches():
    gl = shared_gamelogic.GameLoader()
    assert gl.get_current_game() is None

    sentinel = object()
    gl.curentgamerules = sentinel
    assert gl.get_current_game() is sentinel


def test_game_msg_event_new_and_gameover(monkeypatch):
    gl = shared_gamelogic.GameLoader()
    calls = []
    errors = []

    def _fake_switch(**kwargs):
        calls.append(kwargs)
        return "boom"

    monkeypatch.setattr(gl, "switch_game", _fake_switch)
    monkeypatch.setattr(shared_gamelogic.log, "error", lambda *parts: errors.append(parts), raising=False)

    gl.game_msg_event(TYPE="GAME_NEW", GAME_TYPE="game_fake")
    gl.game_msg_event(TYPE="GAME_GAMEOVER")

    assert calls[0] == {"TYPE": "GAME_NEW", "GAME_TYPE": "game_fake"}
    assert calls[1] == {"GAME_TYPE": "game_lobby"}
    assert any(parts and parts[0] == "boom" for parts in errors)


def test_game_msg_event_missing_handler_logs_error(monkeypatch):
    gl = shared_gamelogic.GameLoader()
    gl.curentgamerules = object()
    errors = []
    monkeypatch.setattr(shared_gamelogic.log, "error", lambda *parts: errors.append(parts), raising=False)

    gl.game_msg_event(TYPE="GAME_UNKNOWN", sample=1)

    assert any("not callable" in str(parts[0]) for parts in errors)


def test_game_msg_event_heartbeat_route(monkeypatch):
    gl = shared_gamelogic.GameLoader()

    class _HeartbeatReceiver:
        def __init__(self):
            self.called = False

        def EVENT_HEARTBEAT(self, **kwargs):
            self.called = kwargs.get("tick") == 7

    receiver = _HeartbeatReceiver()
    gl.curentgamerules = receiver
    gl.game_msg_event(TYPE="GAME_HEARTBEAT", tick=7)
    assert receiver.called is True


def test_switch_game_rules_symbol_validation(monkeypatch):
    shared_utils.setglobals(_HW(), object())
    gl = shared_gamelogic.GameLoader()

    missing_rules_mod = types.ModuleType("game_missing_rules")
    monkeypatch.setitem(sys.modules, "game_missing_rules", missing_rules_mod)
    out = gl.switch_game(GAME_TYPE="game_missing_rules")
    assert "Rules() invalid" in out

    noncallable_rules_mod = types.ModuleType("game_noncallable_rules")
    noncallable_rules_mod.Rules = 3
    monkeypatch.setitem(sys.modules, "game_noncallable_rules", noncallable_rules_mod)
    out = gl.switch_game(GAME_TYPE="game_noncallable_rules")
    assert "Rules() invalid" in out


def test_switch_game_rules_instance_validation(monkeypatch):
    shared_utils.setglobals(_HW(), object())
    gl = shared_gamelogic.GameLoader()

    bad_mod = types.ModuleType("game_bad_instance")

    class NotRules:
        pass

    bad_mod.Rules = lambda *_args, **_kwargs: NotRules()
    monkeypatch.setitem(sys.modules, "game_bad_instance", bad_mod)

    out = gl.switch_game(GAME_TYPE="game_bad_instance")
    assert "Rules() invalid" in out


def test_switch_game_uses_previous_game_exit_data(monkeypatch):
    shared_utils.setglobals(_HW(), object())
    gl = shared_gamelogic.GameLoader()

    class _PrevRules:
        def game_exit(self):
            return {"copied": {"score": 4}}

    class _NewRules(shared_classes.BaseGameRules):
        def __init__(self, gid):
            super().__init__(None, gid)
            self.loaded_kwargs = None

        def game_loaded(self, **kwargs):
            self.loaded_kwargs = kwargs

    mod = types.ModuleType("game_copy_data")
    mod.Rules = _NewRules
    monkeypatch.setitem(sys.modules, "game_copy_data", mod)

    gl.curentgamerules = _PrevRules()
    out = gl.switch_game(GAME_TYPE="game_copy_data")
    assert out is None
    assert isinstance(gl.curentgamerules, _NewRules)
    assert gl.curentgamerules.loaded_kwargs == {"copied": {"score": 4}}


def test_game_msg_event_inner_none_guard_path():
    gl = shared_gamelogic.GameLoader()

    class _TruthyThenNone:
        def __init__(self, owner):
            self.owner = owner

        def __bool__(self):
            self.owner.curentgamerules = None
            return True

    gl.curentgamerules = _TruthyThenNone(gl)
    gl.game_msg_event(TYPE="GAME_TAG", value=1)


def test_game_msg_event_no_current_rules_noop():
    gl = shared_gamelogic.GameLoader()
    gl.curentgamerules = None
    gl.game_msg_event(TYPE="GAME_TAG", value=99)
