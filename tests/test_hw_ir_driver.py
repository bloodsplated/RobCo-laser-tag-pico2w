import asyncio

from hw_ir_driver import IR


def test_ir_on_event_validation_and_send():
    ir = IR()
    assert "player_id" in ir.on_event(player_id=0, team_id=0, shot_id=1)
    assert "team_id" in ir.on_event(player_id=1, team_id=11, shot_id=1)
    assert "shot_id" in ir.on_event(player_id=1, team_id=0, shot_id=101)

    out = ir.on_event(player_id=1, team_id=1, shot_id=1, emitter_id=1)
    assert "lazar" in out


def test_ir_decode_valid_and_invalid():
    ir = IR()
    msg_ok = ir.decoder0.__class__.__mro__[0]
    from adafruit_irremote import IRMessage

    valid = IRMessage([255, 1, 2, 3, 6, 0], pulses=[1, 2])
    decoded = asyncio.run(ir.ir_decode(valid, "gun"))
    assert decoded[0:3] == (1, 2, 3)

    bad = IRMessage([255, 1, 2, 3, 99, 0], pulses=[1, 2])
    assert asyncio.run(ir.ir_decode(bad, "gun")) is None


def test_ir_shoot_lasers_alias():
    ir = IR()
    out = ir.shoot_lasers(player_id=2, team_id=1, shot_id=2, emitter_id=0)
    assert "lazar" in out


def test_ir_decode_rejects_non_ir_message():
    ir = IR()
    assert asyncio.run(ir.ir_decode(object(), "gun")) is None


def test_ir_decode_too_short_and_repeat(monkeypatch):
    from adafruit_irremote import IRMessage

    ir = IR()

    too_short = IRMessage([255, 1, 2, 3], pulses=[1, 2])
    assert asyncio.run(ir.ir_decode(too_short, "gun")) is None

    ir.lastvalid = (1, 2, 3, "gun", 100.0)
    monkeypatch.setattr("hw_ir_driver.time.monotonic", lambda: 100.2)
    repeat = IRMessage([255, 1, 2, 3, 6, 0], pulses=[1, 2])
    assert asyncio.run(ir.ir_decode(repeat, "gun")) is None


def test_ir_on_event_checksum_and_transmit_error(monkeypatch):
    ir = IR()

    class HugeAddInt(int):
        def __add__(self, other):
            return 999

    checksum_out = ir.on_event(player_id=HugeAddInt(1), team_id=1, shot_id=1)
    assert "checksum" in checksum_out

    def boom(_pulseout, _value, repeat=0):
        raise RuntimeError("tx fail")

    monkeypatch.setattr(ir.encoder, "transmit", boom)
    err_out = ir.on_event(player_id=1, team_id=1, shot_id=1)
    assert "error tx fail" in err_out


def test_ir_async_start_handles_none_decode_and_updates_watcher(monkeypatch):
    from adafruit_irremote import IRMessage

    ir = IR()
    ir.decoder0._queue = [IRMessage([255, 1, 2, 3, 6, 0], pulses=[1, 2])]

    async def fake_decode(_message, _location):
        ir.active = False
        return None

    monkeypatch.setattr(ir, "ir_decode", fake_decode)
    asyncio.run(ir.async_start())

    from shared_utils import data

    assert "IR_async_decoderWatch" in data().async_watcher
    assert ir.pulsein0.cleared is True


def test_ir_async_start_handles_valid_decode_and_event_send(monkeypatch):
    from adafruit_irremote import IRMessage

    ir = IR()
    ir.decoder0._queue = [IRMessage([255, 1, 2, 3, 6, 0], pulses=[1, 2])]

    async def fake_decode(_message, _location):
        ir.active = False
        return (1, 2, 3, "gun", 123.4)

    monkeypatch.setattr(ir, "ir_decode", fake_decode)
    asyncio.run(ir.async_start())


def test_ir_async_start_handles_cancelled_error(monkeypatch):
    ir = IR()

    def raise_cancelled():
        raise asyncio.CancelledError()

    monkeypatch.setattr(ir.decoder0, "read", raise_cancelled)
    asyncio.run(ir.async_start())


def test_ir_async_start_handles_generic_error(monkeypatch):
    ir = IR()

    def raise_generic():
        raise RuntimeError("decoder boom")

    monkeypatch.setattr(ir.decoder0, "read", raise_generic)
    asyncio.run(ir.async_start())
