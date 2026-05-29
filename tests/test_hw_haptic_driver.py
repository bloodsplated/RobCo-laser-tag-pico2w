from hw_haptic_driver import HAPTIC


def test_haptic_on_event_and_stop():
    h = HAPTIC()
    reply = h.on_event(List=[12, 0.1], runtime=0.2)
    assert "playing" in reply
    assert h.is_running() in [True, False]

    h.stop()
    h.cleanup()


def test_haptic_rejects_invalid_payloads():
    h = HAPTIC()
    assert "Error" in h.on_event(List="bad")
    assert "Error" in h.on_event(List=[1] * 9)
    assert "No haptic effect" in h.on_event(List=[])
