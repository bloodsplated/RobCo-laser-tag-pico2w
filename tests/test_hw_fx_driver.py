import pytest

from hw_fx_driver import FX


class _Unit:
    def __init__(self):
        self._running = False
        self._active = True
        self.events = []
        self.stop_calls = 0

    def is_running(self):
        return self._running

    def is_active(self):
        return self._active

    def on_event(self, **kwargs):
        self.events.append(kwargs)
        return "ok"

    def stop(self):
        self.stop_calls += 1


def test_fx_requires_all_modules():
    with pytest.raises(ValueError):
        FX("x", LIGHT=None, SOUND=_Unit(), HAPTIC=_Unit())


def test_fx_stop_and_status():
    light, sound, haptic = _Unit(), _Unit(), _Unit()
    fx = FX("x", LIGHT=light, SOUND=sound, HAPTIC=haptic)

    assert fx.is_fx_running() is False
    light._running = True
    assert fx.is_fx_running() is True

    reply = fx.on_event(STOP=True)
    assert reply[0] == "STOPPED ALL FX"
    assert light.stop_calls == 1


def test_fx_dispatches_to_subdrivers():
    light, sound, haptic = _Unit(), _Unit(), _Unit()
    fx = FX("x", LIGHT=light, SOUND=sound, HAPTIC=haptic)

    out = fx.on_event(SOUND={"SoundName": "X"}, LIGHT={"playlist": []}, HAPTIC={"List": [1]})
    assert out[1] == "ok"
    assert out[2] == "ok"
    assert out[3] == "ok"

    status = fx.on_event(is_fx_running=True)
    assert isinstance(status, list) and len(status) == 4
