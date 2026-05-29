import asyncio
import types

import pytest

from hw_light_driver import LIGHT


def test_light_build_playlist_and_update():
    light = LIGHT()
    assert light.build_playlist(("PIXELS", [0, 1], "RED")) is None
    assert len(light.playlist) == 1

    assert "Exception" in light.build_playlist(("BLAH", 1, 2))

    light.update(status="ALIVE", game_team_id=2)
    light.update(status="DEAD", game_team_id=2)
    light.cleanup()


def test_light_on_event_states():
    light = LIGHT()

    light.running = True
    assert light.on_event(playlist=[]) == "effect is running"

    light.running = False
    assert light.on_event(STOP=True) == "LIGHT STOPPED"

    light.playlist = [1]
    assert "playlist is full" in light.on_event(playlist=[])


def test_light_funk_task_and_rainbow_stop():
    light = LIGHT()

    async def run_once():
        await light.funk_task("does_not_exist", {})

    asyncio.run(run_once())


def test_light_init_exception(monkeypatch):
    def _raise_neopixel(*args, **kwargs):
        raise RuntimeError("no neopixel")

    monkeypatch.setattr("hw_light_driver.neopixel.NeoPixel", _raise_neopixel)
    light = LIGHT()
    assert light.pixels is None


def test_light_on_event_update_and_build(monkeypatch):
    light = LIGHT()

    called = {"update": False, "build": False}

    def _fake_update(**payload):
        called["update"] = payload == {"status": "ALIVE", "game_team_id": 1}
        return "updated"

    def _fake_build(*tasks):
        called["build"] = tasks == (("SHOW", 0.0, 0),)
        return "built"

    monkeypatch.setattr(light, "update", _fake_update)
    monkeypatch.setattr(light, "build_playlist", _fake_build)

    assert light.on_event(UPDATE={"status": "ALIVE", "game_team_id": 1}) == "updated"
    assert called["update"] is True

    assert light.on_event(playlist=[("SHOW", 0.0, 0)]) == "built"
    assert called["build"] is True


def test_light_update_limbo_branch():
    light = LIGHT()
    light.update(status="LIMBO", game_team_id=3)
    assert light.pixels.values[0] == (0, 0, 0)


def test_light_build_playlist_valid_variants_and_errors():
    light = LIGHT()

    assert light.build_playlist(("SHOW", 0.1, 0), ("STOP", 0, 0)) is None
    assert light.playlist[0][0] == "SHOW"
    assert light.playlist[1][0] == "STOP"

    light.playlist = []
    assert "Invalid SHOW payload" in light.build_playlist(("SHOW", "bad", 0))
    assert light.playlist == []

    assert "Invalid PIXELS payload" in light.build_playlist(("PIXELS", "bad", "RED"))
    assert "Invalid PIXELS color name" in light.build_playlist(("PIXELS", [0], "NOPE"))

    assert "Invalid FUNK payload" in light.build_playlist(("FUNK", 123, {}))
    assert "no callable function" in light.build_playlist(("FUNK", "no_such", {}))

    assert "Invalid task expected" in light.build_playlist(("SHOW", 1))


def test_light_funk_task_callable_and_exception(monkeypatch):
    light = LIGHT()

    async def _ok_func(**payload):
        light.testlock = payload.get("ok", False)

    async def _bad_func(**payload):
        raise RuntimeError("funk fail")

    monkeypatch.setattr(light, "custom_ok", _ok_func, raising=False)
    monkeypatch.setattr(light, "custom_bad", _bad_func, raising=False)

    async def run_paths():
        await light.funk_task("custom_ok", {"ok": True})
        await light.funk_task("custom_bad", {})

    asyncio.run(run_paths())
    assert light.testlock is True


def test_light_funk_task_attributeerror_branch(monkeypatch):
    light = LIGHT()

    state = {"calls": 0}

    def _attr_then_success(**payload):
        state["calls"] += 1
        if state["calls"] == 1:
            raise AttributeError("forced")
        light.testlock = payload.get("armed", False)

    monkeypatch.setattr(light, "target_func", _attr_then_success, raising=False)

    async def run_attrerror():
        await light.funk_task("target_func", {"armed": True})

    asyncio.run(run_attrerror())
    assert light.testlock is True


def test_light_async_start_processes_show_pixels_and_stop(monkeypatch):
    light = LIGHT()
    light.playlist = [
        ("PIXELS", [0, 1], (1, 2, 3)),
        ("PIXELS", [], (4, 5, 6)),
        ("SHOW", 0.0, 0),
        ("STOP", 0, 0),
    ]

    sleep_calls = {"n": 0}
    real_sleep = asyncio.sleep

    async def _fake_sleep(delay):
        sleep_calls["n"] += 1
        if sleep_calls["n"] > 2:
            light.active = False
        await real_sleep(0)

    monkeypatch.setattr("hw_light_driver.asyncio.sleep", _fake_sleep)
    asyncio.run(light.async_start())
    assert light.running is False


def test_light_async_start_processes_funk_and_running_reset(monkeypatch):
    light = LIGHT()
    light.running = True
    light.playlist = [("FUNK", "play_rainbow", {"x": 1})]

    called = {"funk": False}

    async def _fake_funk(function, payload):
        called["funk"] = function == "play_rainbow" and payload == {"x": 1}
        light.playlist = []
        light.active = False

    monkeypatch.setattr(light, "funk_task", _fake_funk)
    asyncio.run(light.async_start())
    assert called["funk"] is True
    assert light.running is False


def test_light_async_start_handles_nextcommand_and_outer_exceptions(monkeypatch):
    light = LIGHT()
    light.playlist = ["bad command"]

    async def _fake_sleep(_delay):
        light.active = False

    monkeypatch.setattr("hw_light_driver.asyncio.sleep", _fake_sleep)
    asyncio.run(light.async_start())

    light2 = LIGHT()

    def _boom_pop(_idx):
        raise RuntimeError("pop fail")

    light2.playlist = types.SimpleNamespace(__len__=lambda self: 1, pop=_boom_pop)
    light2.active = True

    async def _sleep_once(_delay):
        light2.active = False

    monkeypatch.setattr("hw_light_driver.asyncio.sleep", _sleep_once)
    asyncio.run(light2.async_start())


def test_light_async_start_cancelled_error(monkeypatch):
    light = LIGHT()
    light.active = True

    class _RaisingPlaylist(list):
        def __len__(self):
            raise asyncio.CancelledError()

    light.playlist = _RaisingPlaylist()

    async def _noop_sleep(_delay):
        return None

    monkeypatch.setattr("hw_light_driver.asyncio.sleep", _noop_sleep)
    asyncio.run(light.async_start())


def test_light_play_rainbow_early_return_when_running():
    light = LIGHT()
    light.running = True
    with pytest.raises(TypeError):
        asyncio.run(light.play_rainbow(flag=1))


def test_light_play_rainbow_full_cycle_and_cleanup(monkeypatch):
    light = LIGHT()
    light.running = False
    light.num_pixels = 3

    call_count = {"sleep": 0}
    real_sleep = asyncio.sleep

    async def _fake_sleep(_delay):
        call_count["sleep"] += 1
        if call_count["sleep"] > 1:
            light.running = False
        await real_sleep(0)

    monkeypatch.setattr("hw_light_driver.asyncio.sleep", _fake_sleep)
    asyncio.run(light.play_rainbow())

    assert light.pixels.values[0] == (0, 0, 0)
    assert light.testlock is False
