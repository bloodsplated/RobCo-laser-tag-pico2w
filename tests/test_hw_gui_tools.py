import hw_gui_tools
import pytest

from hw_gui_tools import GUI


class _Row:
    def __init__(self):
        self.text = ""


class _LCD:
    def __init__(self):
        self.menu_group = type("Group", (), {"hidden": False})()
        self.rows = [_Row() for _ in range(5)]
        self.menu_group = self.rows
        self.menu_group.hidden = False
        self.events = []
        self.active = True

    def is_active(self):
        return self.active

    def update_bar(self, value):
        self.events.append(("bar", value))

    def on_event(self, **payload):
        self.events.append(("lcd", payload))

    def show_menu(self, show):
        self.menu_group.hidden = not show


class _ListWithHidden(list):
    def __init__(self, rows):
        super().__init__(rows)
        self.hidden = False


class _LCD2:
    def __init__(self):
        self.menu_group = _ListWithHidden([_Row() for _ in range(5)])
        self.events = []

    def is_active(self):
        return True

    def update_bar(self, value):
        self.events.append(("bar", value))

    def on_event(self, **payload):
        self.events.append(("lcd", payload))

    def show_menu(self, show):
        self.menu_group.hidden = not show


def _build_gui():
    lcd = _LCD2()
    gui = GUI(LCD=lcd)
    return gui, lcd


def test_gui_set_menu_and_navigation():
    gui, lcd = _build_gui()

    menu = [
        ("Start", "ACTION", lambda **k: "ok", {"view": "x"}),
        ("Sub", "SUB", [("Go", "LABEL")]),
        ("Toggle []", "SET_LIST", lambda **k: "next", {"view": "v"}),
    ]

    gui.set_menu(menu)
    assert isinstance(gui.menu_object, list)

    gui.menu_input(value="INC")
    gui.menu_input(value="SINGLE")


def test_gui_stringme_and_data():
    gui, lcd = _build_gui()
    s = gui.stringme(("Value []", "SET_LIST", lambda **k: "abc", {"view": "v"}), True)
    assert s.startswith(">")

    assert isinstance(gui.data_callback(name="gun_id"), str)


def test_gui_on_event_heartbeat_and_menu():
    gui, lcd = _build_gui()
    gui.on_event(HEARTBEAT={"menubar": "status"})

    gui.on_event(MENU={"long_hide": False, "setMenu": [("Quit", "QUIT", None, {})]})
    assert gui.long_hide is False


def test_gui_init_requires_lcd():
    with pytest.raises(ValueError):
        GUI()


def test_gui_more_branches(monkeypatch):
    gui, lcd = _build_gui()

    sent = []

    class FakeEvent:
        def __init__(self, target, payload=None, **kwargs):
            self.target = target
            self.payload = payload or {}
            self.payload.update(kwargs)

        def send(self):
            sent.append((self.target, self.payload))
            return None

    monkeypatch.setattr(hw_gui_tools, "Event", FakeEvent)

    class HW:
        def __init__(self):
            self.cleaned = 0

        def cleanup(self):
            self.cleaned += 1

    hw = HW()
    monkeypatch.setattr(hw_gui_tools, "get_hw", lambda: hw)

    gui.switch_game(game_name="game_offline")
    gui.exit_system(reset=True)
    assert hw.cleaned == 1
    assert sent and sent[0][0] == "GAME.START"

    gui.idle_menu = 1
    gui.unlocked = True
    gui.on_event(HEARTBEAT={"menubar": "tick"})
    assert gui.idle_menu == 0

    assert gui.set_menu(None) == "No menu provided."

    gui.set_menu([("bad", "SET_BOOL", lambda **k: None, {"view": "x"})])
    gui.set_menu([("bad", "WHAT", None, {})])
    gui.set_menu([(123, "LABEL")])
    gui.set_menu([("[]", "SET_LIST", lambda **k: None, {})])


def test_gui_button_and_menu_input_paths(monkeypatch):
    gui, lcd = _build_gui()

    gui.menu_object = [("Top", "SUB", [("Action", "ACTION", lambda **k: "v", {"view": "old"})])]
    gui.pos = 0

    gui.button_action(("X", 1), "SINGLE")
    gui.button_action(("X", "SUB", []), "SINGLE")
    gui.button_action(("Back", "BACK"), "SINGLE")

    d = {"value": False, "view": "f"}
    gui.button_action(("B", "SET_BOOL", lambda **k: "x", d), "SINGLE")
    assert d["value"] is True

    gui.button_action(("A", "ACTION", lambda **k: "new", {"view": "v"}), "SINGLE")

    gui.long_hide = False
    gui.lcd_menu_group.hidden = True
    assert gui.menu_input(value="SINGLE") is None

    gui.lcd_menu_group.hidden = False
    gui.unlocked = True
    gui.menu_input(value="INC")
    gui.menu_input(value="DNC")

    gui.menu_object = {}
    gui.menu_input(value="SINGLE")


def test_gui_data_exception_branch(monkeypatch):
    gui, lcd = _build_gui()
    monkeypatch.setattr(hw_gui_tools, "data", lambda: (_ for _ in ()).throw(RuntimeError("x")))
    assert gui.data_callback(name="gun_id") == "gun_id"
