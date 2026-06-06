# RobCo-laser-tag-pico2w
Fallout-Themed Laser Tag System (Powered by Raspberry Pi Pico 2W &amp; CircuitPython)




## Links to parts
- [3D printed parts](https://www.printables.com/model/1503654-robco-ae7p-lazer-tag-system)
- [Build instructions and parts](https://docs.google.com/document/d/1JX9dtdxTVsxvUcgsNUCupUGkhv20qMDKx6A4yy7gj8I/edit?usp=sharing)
- [cirkitdesigner Wiring](https://app.cirkitdesigner.com/project/1d3a4b62-3213-40ae-a360-1e849d3ae2aa) `not all parts are correct` 

## Software Installation

1. Follow the CircuitPython setup instructions:
   https://circuitpython.org/board/raspberry_pi_pico2_w/

   This project was built and tested with CircuitPython 10.2.1.

2. Install `circup` and required libraries:
   https://docs.circuitpython.org/projects/circup/en/latest/

   This is the fastest way to install all dependencies:

   ```bash
   circup --verbose install asyncio adafruit_logging async_button adafruit_irremote neopixel adafruit_drv2605 adafruit_display_text adafruit_displayio_ssd1306 adafruit_bitmap_font adafruit_minimqtt
   ```

3. Copy the contents of `sounds` to your FX Sound Board drive.
4. Copy the contents of `src` to the root of your `CIRCUITPY` drive.
5. Reboot the board.

## Project Layout

```text
src/
    code.py                 # CircuitPython entrypoint
    shared_*.py             # Shared helpers
    game_*.py               # Game modes
    hw_*.py                 # Individual hardware drivers
    settings.toml           # CircuitPython environment settings
sounds/                   # Sound files for FX board
tests/                    # Unit tests for shared, game, and hw modules
helper.sh                 # Installer script with helper tools (macOS)
```

## Configuration: settings.toml

Current keys:
- `DEBUG = 1`: Enables debug mode
- `MUTE = 1`: mute sounds
- `SKIP_SHOW = 1`: Skips boot up effects, sould not be skiped if server is used
- `SKIP_LOBBY = "game_offline"`: Bypasses lobby and jumps directly into offline game
- `CIRCUITPY_WIFI_SSID`, `CIRCUITPY_WIFI_PASSWORD`: Wi-Fi credentials (not used in 1.0 yet)

## Roadmap
- `1.0`
   - First public release 
   - basic offline gameplay
- `2.0`
   - MQTT server integration
   - Team game modes
- `3.0`
   - Vest support
   - More game modes
- `Wishlist`
   - Power ups
   - Weapon modes  
   - IR Bases/Flags
   - Lobby game votes
