import asyncio

import hw_input_driver
from hw_input_driver import INPUT


def test_input_send_event(monkeypatch):
    sent = []

    class FakeEvent:
        def __init__(self, target, payload=None, **kwargs):
            self.target = target
            self.payload = payload or {}
            self.payload.update(kwargs)

        def send(self):
            sent.append((self.target, self.payload))

    monkeypatch.setattr(hw_input_driver, "Event", FakeEvent)

    inp = INPUT()
    inp.send_event(name="TRIG", value="SINGLE")
    assert sent[0][0] == "GAME.INPUT"
    assert sent[1][0] == "HW"


def test_rotate_watcher_emits_change(monkeypatch):
    sent = []

    inp = INPUT()

    def fake_send_event(**kwargs):
        sent.append(kwargs)
        inp.active = False

    inp.send_event = fake_send_event
    inp.last_position = 0
    inp.encoder.position = 1

    asyncio.run(inp.rotate_watcher())
    assert sent[0]["value"] == "INC"


def test_click_watcher_single_iteration(monkeypatch):
    inp = INPUT()

    class _MB:
        async def wait(self, **kwargs):
            return ("TRIG", hw_input_driver.Button.SINGLE)

    sent = []

    def fake_send_event(**kwargs):
        sent.append(kwargs)
        inp.active = False

    inp.send_event = fake_send_event
    inp.active = True

    asyncio.run(inp.click_watcher(_MB()))
    assert sent and sent[0]["name"] == "TRIG"


def test_async_start_invokes_watchers(monkeypatch):
    inp = INPUT()
    called = {"click": 0, "rotate": 0}

    async def fake_click(_mb):
        called["click"] += 1

    async def fake_rotate():
        called["rotate"] += 1

    monkeypatch.setattr(inp, "click_watcher", fake_click)
    monkeypatch.setattr(inp, "rotate_watcher", fake_rotate)

    asyncio.run(inp.async_start())
    assert called["click"] == 1
    assert called["rotate"] == 1
