"""LCD screen driver"""
import board
from shared_utils import data,MyLogger
from shared_classes import DriverModule

import terminalio
import displayio
import adafruit_displayio_ssd1306
from adafruit_display_text import label
from i2cdisplaybus import I2CDisplayBus

log = MyLogger(__name__)

INFO = {
    "module_name": __name__,
    "version": 1.0,
    "Driver": "LCD",
    "description": """ LCD Driver"""
}


I2C = board.STEMMA_I2C() # pylint: disable=no-member
WIDTH = 128
HEIGHT = 64
displayio.release_displays()

class LCD(DriverModule):
    """LCD screen driver"""
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **INFO)

        self.module_name = __name__

        self.max_length = 21
        self.max_rows = 5

        self.highlight_line = 0

        self.text_fields = []
        self.menu = {}
        self.pos = 0
        self.error =""


        self.game_group = displayio.Group()
        self.menu_group = displayio.Group()
        self.active_layer = 1

        try:
            display_bus = I2CDisplayBus(I2C, device_address=0x3d)
            self.disp = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)
            root_group = displayio.Group()

            self.disp.root_group = root_group
            root_group.append(self.game_group)
            root_group.append(self.menu_group)


            offset = 0
            info = self.get_start_screen()


            for i in range(self.max_rows):
                self.game_group.append(
                    label.Label(
                        terminalio.FONT,
                        text="",
                        color=0xFFFFFF,
                        background_color=0x000000,
                        background_tight=False,
                        padding_right=128,
                        padding_left=5,
                        x = 3,
                        y = 10 + offset
                    )
                )
                self.menu_group.append(
                    label.Label(
                        terminalio.FONT,
                        text=f"{info[i]}",
                        color=0xFFFFFF,
                        background_color=0x000000,
                        background_tight=False,
                        padding_right=128,
                        padding_left=5,
                        x = 3,
                        y = 10 + offset
                    )
                )
                offset += 12

            self.game_group[0].color =0x000000
            self.game_group[0].background_color =0xFFFFFF
            self.game_group[0].text = info[0]

            self.show_menu(True)
            self.active = True
        except Exception as e:
            log.error("display Init Exception:", e)

    def get_start_screen(self):
        """default screen info """
        info = ["1","2","3","4","5"]
        info[0] = f"-= RobCo OS v{data().hw_ver} =-"
        info[1] = f"{data().gun_id}"
        info[2] = f"{data().gun_sn}"
        info[3] = f"{data().gun_model}"
        info[4] = f"{data().gun_model2}"
        return info




    def on_event(self, **payload):
        """handles incoming events for the GUI, such as display updates or menu changes
        LCD={"show_menu":True,"menu_display":[5],"game_display":[4]}
        """
        show_menu = payload.get("show_menu",None)
        if show_menu is not None:
            self.show_menu(show_menu)


        menu_display = payload.get("menu_display",None)
        if menu_display is not None:
            if isinstance(menu_display, list) and len(menu_display) == 5:
                for i in range(4, -1, -1):
                    self.menu_group[i].text = menu_display[i]
            else:
                raise ValueError(f"menu_display:{menu_display} invalid")

        game_display = payload.get("game_display",None)
        if game_display is not None:
            if isinstance(game_display, list) and len(game_display) == 4:
                for j in range(0,4):
                    self.game_group[j+1].text = game_display[j]
            else:
                raise ValueError(f"menu_display:{game_display} invalid")


    def update_bar(self,barvalue:str):
        """updates bar on game group"""
        if  barvalue is not None:
            self.game_group[0].text = barvalue



    def show_menu(self, showit):
        """switches between groups"""
        if showit:
            self.menu_group.hidden = False
            self.game_group.hidden = True
        else:
            self.menu_group.hidden = True
            self.game_group.hidden = False
