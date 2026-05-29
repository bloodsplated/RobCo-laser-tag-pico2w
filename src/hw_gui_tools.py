"""" interface tools driver """
from shared_classes import DriverModule
from shared_utils import get_hw,get_gl,Event,MyLogger,data

log = MyLogger(__name__)

INFO = {
    "module_name": __name__,
    "version": 1.0,
    "Driver": "GUI_Tools",
    "description": """ GUI_Tools """
}


class GUI(DriverModule):
    """" interface tools driver """
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **INFO)

        self.active = True
        self.long_hide = True
        self.unlocked = False

        self.idle_menu = 0 # auto hide after inactivity
        self.menu_object = {} #stores the menu
        self.menu_path = [] #used for submenu tracking
        self.pos = 0 #used for menu position tracking

        self.hw_lcd = kwargs.get('LCD',None)
        if self.hw_lcd is None:
            raise ValueError("LCD must not be None")


        self.lcd_menu_group = self.hw_lcd.menu_group
        self.max_rows = len(self.lcd_menu_group)



    def on_event(self, **payload):
        """" handles incoming events for the GUI, such as display updates or menu changes """
        if not self.hw_lcd.is_active():
            return

        heart_data = payload.get("HEARTBEAT", None)
        if heart_data is not None:
            self.hw_lcd.update_bar(heart_data.get("menubar",None))
            if self.idle_menu > 0 and self.unlocked:
                self.idle_menu -= 1
                if self.idle_menu < 1:
                    self.hw_lcd.show_menu(False)


        menu_data = payload.get("MENU",None)
        if menu_data is not None:
            self.long_hide = menu_data.get('long_hide',True)
            self.set_menu(menu_data.get('setMenu',None))
            self.idle_menu = 0


        self.hw_lcd.on_event(**payload.get("LCD",{}))


    def switch_game(self,**kwargs):
        """ switch game function """
        gametojoin = kwargs.get("game_name", None)
        if gametojoin:
            Event("GAME.START",{"GAME_TYPE":gametojoin}).send()

    def exit_system(self,**kwargs):
        """ starts the exit sytem """
        if kwargs.get("erase_filesystem", False):
            print("Performing filesystem erase!")
            get_hw().exit_command = "erase_filesystem"


        if kwargs.get("hardware_reboot", False):
            print("Performing hardware reboot!")
            get_hw().exit_command = "hardware_reboot"


        get_hw().cleanup()





    def set_menu(self, menu_object):
        """ error checking for setmenu"""
        def check_callable(item):
            t_name = item[0]
            t_type = item[1]
            t_func = item[2] if len(item) > 2 else None
            t_vars = item[3] if len(item) > 3 else None


            if t_type in ["SET_LIST", "SET_BOOL", "DATA", "ACTION","SET_GAME","QUIT"]:
                if t_vars is None:
                    raise ValueError(f"{t_type} must have dict in [3]")


            if t_type in ["SET_BOOL"]:
                if t_vars.get("value", None) is None:
                    raise ValueError(f"{t_type} [3] must have value key")

            if t_type == "SET_GAME":
                t_func = self.switch_game

            if t_type == "QUIT":
                t_func = self.exit_system

            if t_type == "DATA":
                if t_vars.get("name", None) is None:
                    raise ValueError(f"{t_type} [3] must have 'name' key")
                t_func = self.data_callback


            return (t_name,t_type,t_func,t_vars)

        def process_menu(menu, is_root=False):
            processed = []

            for item in menu:
                if not (isinstance(item, tuple) and len(item) > 0):
                    raise ValueError(f"rejected not tuple item: {item}")

                t_name = item[0]
                t_type = item[1] if len(item) > 1 else "LABEL"
                t_func = item[2] if len(item) > 2 else None
                t_vars = item[3] if len(item) > 3 else None

                if t_type not in [
                    "SUB","LABEL",
                    "SET_LIST",
                    "SET_BOOL",
                    "DATA",
                    "ACTION",
                    "SET_GAME",
                    "QUIT"]:
                    raise ValueError(f"unknow menu type {t_type}")


                if (not is_root and t_name == 'Back'):
                    continue # Remove any existing 'Back'

                if not isinstance(t_name, str) or not isinstance(t_type, str):
                    raise ValueError(f"rejected not str[0,1] item: {t_name}")


                if t_type == "LABEL":
                    processed.append((t_name, "LABEL"))
                    continue

                if "[]" in t_name:
                    if t_vars is None or t_vars.get("view", None) is None:
                        raise ValueError(f"rejected [] view key missing item: {t_name}")


                if isinstance(t_func, list):
                    submenu = process_menu(t_func, is_root=False)
                    processed.append((t_name, "SUB" ,submenu))
                    continue


                call_item = check_callable(item)
                if call_item is not None:
                    processed.append(call_item)




            if not is_root:
                processed = [i for i in processed if not (isinstance(i, tuple) and i[0] == 'Back')]
                processed.append(('Back', 'BACK')) #add back to end of submenu
            return processed


        #end of process_menu
        try:
            self.hw_lcd.show_menu(False)
            if menu_object is None:
                return "No menu provided."
            self.menu_object.clear()
            self.menu_object = process_menu(menu_object, is_root=True)
            self.pos = 0
            self.menu_path = []
            self.update_view()

        except ValueError as e:
            log.error("setMenu Exception:", e)




    def get_menu_item_at_path(self, menu_path: list, add_index=None):
        """gets a menu at a path list """
        current = self.menu_object
        try:
            path = list(menu_path)
            if add_index is not None:
                path.append(add_index)
            if not path:
                return ("","", current) #root level
            for depth, idx in enumerate(path):
                if not isinstance(current, list) or idx < 0 or idx >= len(current):
                    return None
                item = current[idx]
                # If this is the last index in the path, return the tuple
                if depth == len(path) - 1:
                    return item
                # Otherwise, descend into submenu (now at index 2)
                if len(item) > 2 and isinstance(item[2], list):
                    current = item[2]
                else:
                    return None
            return None
        except Exception:
            return None


    def update_view(self):
        """draws menu"""

        try:
            menu_pair = self.get_menu_item_at_path(self.menu_path)

            if not isinstance(menu_pair[2], list):
                log.error(f"updateView  menu_path: {self.menu_path} not list!")
                return

            offset = self.pos -1
            offset = max(offset, 0)
            start = 0 + offset
            end = self.max_rows + offset

            if end > len(menu_pair[2]):
                end = len(menu_pair[2])
                start = end - self.max_rows

            start = max(start, 0)

            lcdrow = 0
            for x1 in range(start, end):
                string_me_text = self.stringme( menu_pair[2][x1], (x1 == self.pos))
                self.lcd_menu_group[lcdrow].text = string_me_text
                lcdrow += 1

            for x2 in range(lcdrow , self.max_rows):
                self.lcd_menu_group[x2].text = ""

        except Exception as e:
            log.error("updateView Exception:", e)


    def stringme(self,line_tuple,highlighted):
        """this populates the [] in the menu"""
        try:
            line_x = line_tuple[0]

            if len(line_tuple) >=4:
                view =  line_tuple[3].get("view","[]")
                if line_tuple[1] == "DATA":
                    view = line_tuple[2](**line_tuple[3])

                line_x = line_x.replace("[]", f"{view}")

            trimmed_strings =line_x

            if highlighted:
                return ">"+trimmed_strings

            return " "+trimmed_strings
        except Exception as e:
            log.error("stringme Exception:", e)
        return None

    def data_callback(self,**kwargs):
        """used for menu DATA type callback"""
        try:
            key = kwargs.get("name", "")

            if key.startswith("game."):
                gamekey = key[5:]
                cur_game = get_gl().get_current_game()
                if cur_game is None:
                    return key
                game_value = cur_game.__dict__.get(gamekey, None)
                return str(game_value)

            else:
                value = data().__dict__.get(key, None)
                return str(value)

        except Exception as e:
            log.error("setMenu Exception:", e)

        return key






    def  button_action (self, clicked_tuple,butt_value):
        """ handles input clicks"""
        try:

            if not isinstance(clicked_tuple[1], str):
                return
            action = clicked_tuple[1]

            if action == "SUB" and isinstance(clicked_tuple[2], list):
                self.menu_path.append(self.pos)
                self.pos = 0
                return

            if action == "BACK":
                self.pos = self.menu_path.pop()
                return

            if action == "LABEL":
                return


            if len(clicked_tuple) > 3 and isinstance(clicked_tuple[3], dict):

                if action == "SET_LIST":
                    if butt_value == "SINGLE":
                        self.unlocked = not self.unlocked
                    new_dict = clicked_tuple[3]
                    new_dict["INPUT"] = butt_value

                    clicked_tuple[3]["view"] = clicked_tuple[2](**new_dict)


                if action == "SET_BOOL" and butt_value == "SINGLE":
                    clicked_tuple[3]["value"] = not clicked_tuple[3]["value"]

                if callable(clicked_tuple[2]) and butt_value == "SINGLE":
                    clicked_tuple[3]["view"] = clicked_tuple[2](**clicked_tuple[3])
                    if action == "ACTION":
                        self.hw_lcd.show_menu(False)



        except Exception as e:
            log.error("button_action Exception:", e)






    def menu_input(self, **kwargs):
        """input form system encoder clicks"""
        input_value = kwargs.get("value",None)

        if input_value == "LONG":
            self.hw_lcd.show_menu(self.lcd_menu_group.hidden)

        try:
            if self.lcd_menu_group.hidden:
                if self.long_hide:
                    return None
                #self.lcdGroup.hidden = False
                self.hw_lcd.show_menu(True)
                self.idle_menu = 10
                self.update_view()
                return None

            cur_menu = self.get_menu_item_at_path(self.menu_path)
            max_items = len(cur_menu[2]) -1
            do_clicks = True
            self.idle_menu = 10


            if ( self.unlocked and input_value == "INC"):
                self.pos += 1
                do_clicks = False

            if ( self.unlocked and input_value == "DNC"):
                self.pos -= 1
                do_clicks = False

            self.pos = max(self.pos, 0)
            self.pos = min(self.pos, max_items)

            cur_sel = self.get_menu_item_at_path(self.menu_path, self.pos)

            if do_clicks:
                self.button_action(cur_sel,input_value)

            self.update_view()
            return cur_sel[0]
        except Exception as e:
            log.error("button_action Exception:", e)
