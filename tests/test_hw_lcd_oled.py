import pytest

from hw_lcd_oled import LCD
import shared_utils


def test_lcd_start_screen_and_menu_toggle():
    shared_utils.data().hw_ver = "1.0"
    shared_utils.data().gun_id = 9
    shared_utils.data().gun_sn = "SN"
    shared_utils.data().gun_model = "MODEL"
    shared_utils.data().gun_model2 = "MODEL2"

    lcd = LCD()
    start = lcd.get_start_screen()
    assert len(start) == 5

    lcd.show_menu(True)
    assert lcd.menu_group.hidden is False
    lcd.show_menu(False)
    assert lcd.menu_group.hidden is True


def test_lcd_on_event_updates_and_validation():
    lcd = LCD()
    lcd.on_event(show_menu=True)
    lcd.on_event(menu_display=["a", "b", "c", "d", "e"])
    lcd.on_event(game_display=["1", "2", "3", "4"])

    with pytest.raises(ValueError):
        lcd.on_event(menu_display=["x"])
    with pytest.raises(ValueError):
        lcd.on_event(game_display=["x"])

    lcd.update_bar("hello")
    assert lcd.game_group[0].text == "hello"


def test_lcd_init_exception_path(monkeypatch):
    def _raise_display_bus(*args, **kwargs):
        raise RuntimeError("display bus unavailable")

    monkeypatch.setattr("hw_lcd_oled.I2CDisplayBus", _raise_display_bus)
    lcd = LCD()
    assert lcd.active is False


def test_lcd_update_bar_none_noop():
    lcd = LCD()
    before = lcd.game_group[0].text
    lcd.update_bar(None)
    assert lcd.game_group[0].text == before
