import types

import pytest

import shared_utils


def test_data_singleton_and_env(monkeypatch):
    d1 = shared_utils.data()
    d2 = shared_utils.data()
    assert d1 is d2

    monkeypatch.setenv("SKIP_SHOW", "1")
    assert shared_utils.data("SKIP_SHOW", "0") == "1"


def test_setglobals_only_sets_once():
    hw1 = object()
    gl1 = object()
    shared_utils.setglobals(hw1, gl1)

    hw2 = object()
    gl2 = object()
    shared_utils.setglobals(hw2, gl2)

    assert shared_utils.get_hw() is hw1
    assert shared_utils.get_gl() is gl1


def test_pp_formats_nested_payload():
    result = shared_utils.pp({"a": [1, True, None, "x"]})
    assert '"a"' in result
    assert "true" in result
    assert "null" in result


def test_color_helper_variants():
    assert shared_utils.color_helper("ON") == (255, 255, 255)
    assert shared_utils.color_helper("OFF") == (0, 0, 0)
    assert shared_utils.color_helper(1, 100)[3] == "RED"
    assert shared_utils.color_helper("does-not-exist") is None


class _Collector:
    def __init__(self):
        self.calls = []

    def on_event(self, **payload):
        self.calls.append(payload)
        return "ok"


class _GL:
    def pass_event(self, target, payload):
        return (target, payload)


class _HW:
    def __init__(self):
        self.gui_driver = _Collector()
        self.fx_driver = _Collector()
        self.ir_driver = _Collector()
        self.hw_calls = []
        self.mqtt_calls = []

    def on_event(self, **payload):
        self.hw_calls.append(payload)
        return "hw"

    def mqtt_message(self, **payload):
        self.mqtt_calls.append(payload)
        return "mqtt"


def test_event_send_routes_targets(monkeypatch):
    hw = _HW()
    gl = _GL()
    shared_utils.setglobals(hw, gl)

    assert shared_utils.Event("GAME.START", GAME_TYPE="game_lobby").send()[0] == "GAME.START"
    assert shared_utils.Event("GUI", LCD={"show_menu": True}).send() == "ok"
    assert shared_utils.Event("FX", STOP=True).send() == "ok"
    assert shared_utils.Event("IR", player_id=1, team_id=0, gun_id=1).send() == "ok"
    assert shared_utils.Event("HW", name="ROTARY").send() == "hw"
    assert shared_utils.Event(0, hello="world").send() == "mqtt"


def test_event_rejects_invalid_target_and_payload():
    with pytest.raises(ValueError):
        shared_utils.Event("", {})

    with pytest.raises(ValueError):
        shared_utils.Event("GUI", payload="bad")


def test_event_send_unknown_string_target_returns_none():
    hw = _HW()
    gl = _GL()
    shared_utils.setglobals(hw, gl)

    e = shared_utils.Event("UNKNOWN_TARGET")
    assert e.send() is None


def test_event_send_out_of_range_int_returns_none():
    hw = _HW()
    gl = _GL()
    shared_utils.setglobals(hw, gl)

    assert shared_utils.Event(101).send() is None
    assert shared_utils.Event(-1).send() is None


def test_event_send_non_str_non_int_target_returns_none():
    hw = _HW()
    gl = _GL()
    shared_utils.setglobals(hw, gl)

    e = shared_utils.Event(1)
    e.target = 3.14  # bypass constructor validation
    assert e.send() is None


def test_event_init_with_dict_payload():
    e = shared_utils.Event("GUI", payload={"LCD": {"show_menu": True}})
    assert e.payload == {"LCD": {"show_menu": True}}