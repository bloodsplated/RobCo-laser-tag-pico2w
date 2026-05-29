import shared_classes
import shared_utils


class _IR:
    def __init__(self):
        self.calls = []

    def shoot_lasers(self, **kwargs):
        self.calls.append(kwargs)
        return "pew"


class _HW:
    def __init__(self):
        self.ir_driver = _IR()


def _make_rules(monkeypatch):
    shared_utils.data().gun_id = 7
    shared_utils.setglobals(_HW(), object())
    sent = []

    class FakeEvent:
        def __init__(self, target, payload=None, **kwargs):
            self.target = target
            self.payload = payload or {}
            self.payload.update(kwargs)

        def send(self):
            sent.append((self.target, self.payload))
            if self.target == "FX" and self.payload.get("is_fx_running"):
                return [False, False, False, False]
            return [False]

    monkeypatch.setattr(shared_classes, "Event", FakeEvent)
    return shared_classes.BaseGameRules(None, 1), sent


def test_driver_module_basics():
    mod = shared_classes.DriverModule("x", extra=1)
    assert mod.is_active() is False
    assert mod.args == ("x",)
    mod.cleanup()
    assert mod.active is False


def test_base_rules_state_transitions(monkeypatch):
    rules, sent = _make_rules(monkeypatch)

    rules.player_respawn()
    assert rules.status == "ALIVE"
    assert rules.curent_hp == rules.max_hp

    rules.player_hit(1)
    assert rules.curent_hp == rules.max_hp - 1

    rules.curent_hp = 1
    rules.player_hit(1)
    assert rules.status == "DEAD"
    assert rules.death_count == 1




def test_base_rules_game_events_and_points(monkeypatch):
    rules, sent = _make_rules(monkeypatch)
    rules.player_respawn()

    rules.game_input(name="TRIG", value="SINGLE")
    rules.game_input(name="TRIG", value="LONG")

    rules.on_event(msg_type="TAG", VictimHP=0)
    assert rules.hits_count == 1
    assert rules.body_count == 1
    assert rules.game_points == 6

    out = rules.game_irtag(PlayerID=9, game_team_id=2, ShotID=3, Receiver="gun")
    assert out == "-------------I was Shot --------------"


def test_trigger_fx_special_cases(monkeypatch):
    rules, sent = _make_rules(monkeypatch)

    rules.trigger_fx("EMPTY")
    rules.trigger_fx("SHOOT")
    rules.trigger_fx("HIT")
    rules.trigger_fx("GAMEOVER", {"game_team_id": 1, "status": "ALIVE", "game_shot_type": 1, "is_winning": True})

    targets = [t for t, _ in sent]
    assert "FX" in targets
