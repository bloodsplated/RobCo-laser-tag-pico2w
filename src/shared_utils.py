"""Shared tools used by all"""
import os,traceback

#this is the only way to prevent circular imports
THE_ONLY_HARDWARE = None
THE_ONLY_GAMELOADER = None
THE_ONLY_DATA = None


def get_gl():
    """gets the shared Game loader"""
    return THE_ONLY_GAMELOADER

def get_hw():
    """gets the shared hardware"""
    return THE_ONLY_HARDWARE

def setglobals(hw, gl):
    """sets the global game loader and hardware"""
    global THE_ONLY_HARDWARE ,THE_ONLY_GAMELOADER# pylint: disable=global-statement
    if THE_ONLY_HARDWARE is None:
        THE_ONLY_HARDWARE = hw
    if THE_ONLY_GAMELOADER is None:
        THE_ONLY_GAMELOADER = gl




def data(key=None,def_value=None):
    """inits the global data and handles config"""
    global THE_ONLY_DATA # pylint: disable=global-statement
    if  THE_ONLY_DATA is None :
        THE_ONLY_DATA = SharedData()

    if isinstance(key,str):
        return os.getenv(key, default=def_value)
    return THE_ONLY_DATA


class MyLogger:
    """simple logger"""
    def __init__(self, name):
        self.name = name
        self.is_debug = data().debug

    def debug(self, *parts):
        """print debug message"""
        if not self.is_debug:
            return
        print("[DEBUG]", self.name + ":", *parts)

    def error(self, *parts):
        """print error message with traceback"""
        print("[ERROR]", self.name + ":", *parts)
        for part in parts:
            if isinstance(part, Exception):
                traceback.print_exception(part)


# pylint: disable=too-many-instance-attributes, too-few-public-methods
class SharedData:
    """ data object shared between all """
    def __init__(self):
        self.debug = False
        self.vol_muted = False
        self.gun_sn = ""
        self.gun_id = 0
        self.gun_model ="UNKNOWN"
        self.gun_model2 ="UNKNOWN"
        self.hw_ver = 0.0
        self.ip_address = "UNKNOWN"

        self.sound_names = []

        #may not be needed
        self.gun_sname = "" #from the server?
        self.async_watcher ={} # keep an eye on all the async










def pp(pp_data, indent_level=0):
    """for printing json nice"""

    indent_spaces = 4
    indent = " " * (indent_level * indent_spaces)
    next_indent = " " * ((indent_level + 1) * indent_spaces)
    result = []

    if isinstance(pp_data, dict):
        result.append("{\n")
        items = list(pp_data.items())
        for i, (key, value) in enumerate(items):
            # Keys in JSON must be double-quoted strings
            json_key = f'"{key}"'
            # Recursively format the value
            json_value = pp(value, indent_level + 1)
            # Add comma for all but the last item
            comma = "," if i < len(items) - 1 else ""
            result.append(f"{next_indent}{json_key}: {json_value}{comma}\n")
        result.append(f"{indent}}}")
    elif isinstance(pp_data, list):
        result.append("[\n")
        for i, value in enumerate(pp_data):
            # Recursively format list items
            json_value = pp(value, indent_level + 1)
            # Add comma for all but the last item
            comma = "," if i < len(pp_data) - 1 else ""
            result.append(f"{next_indent}{json_value}{comma}\n")
        result.append(f"{indent}]")
    elif isinstance(pp_data, str):
        # Enclose strings in double quotes, escaping existing ones
        xdata = pp_data.replace("\"", "\\\"")
        result.append(f'"{xdata}"')
    elif isinstance(pp_data, bool):
        result.append(str(pp_data).lower()) # JSON uses 'true' and 'false'
    elif callable(pp_data):
        # Safely get the function/class name if available
        name = getattr(pp_data, "__name__", pp_data.__class__.__name__)
        result.append(f"Function: {name}")
    elif pp_data is None:
        result.append("null") # JSON uses 'null'
    else:
        # Handle numbers and other basic types
        result.append(str(pp_data))

    return "".join(result)




class Event:
    """event messageing object"""
    def __init__(self, target, payload = None, **kwargs):
        if not (isinstance(target, (str, int)) and target != "" and target is not None):
            raise ValueError("target must be a non-empty string or int")
        self.target = target

        # Merge payload dict and kwargs into self.payload
        self.payload = {}
        if payload is not None:
            if not isinstance(payload, dict):
                raise ValueError("payload must be a dict if provided")
            self.payload.update(payload)
        self.payload.update(kwargs)


    def send(self):
        """sends message"""
        try:
            if isinstance(self.target, str):

                if self.target.startswith("GAME."):
                    return get_gl().pass_event(self.target,self.payload)

                if self.target  in ["GUI","HW.GUI"]:
                    return get_hw().gui_driver.on_event(**self.payload)

                if self.target  in ["FX","HW.FX"]:
                    return get_hw().fx_driver.on_event(**self.payload)

                if self.target  in ["IR","HW.IR"]:
                    return get_hw().ir_driver.on_event(**self.payload)

                if self.target  == "HW":
                    return get_hw().on_event(**self.payload)

                raise ValueError(f"un known target got:{self.target}")

            elif isinstance(self.target, int):
                if self.target < 0 or self.target > 100:
                    raise ValueError(f"target int must be between 0 and 100, got {self.target}")
                return get_hw().mqtt_message(**self.payload)
            else:
                raise ValueError(f"target must be a string or int, got {type(self.target)}")
        except Exception as e:
            logger = MyLogger("Event")
            logger.error("Failed to send event", e)
            return None


def color_helper(color, p:int = 255):
    """helper function for colors
    color can be name  or int
    p is the brightness default is full
    """
    color_list = [
        (p, p, p,"WHITE"),
        (p, 0, 0,"RED"),
        (0, p, 0,"GREEN"),
        (0, 0, p,"BLUE"),
        (p, p, 0,"YELLOW"),
        (p, p//2, 0,"ORANGE"),
        (p//2,p, 0,"LIME"),
        (0, p, p//2, "TEAL"),
        (p, 0, p//2, "PINK"),
        (p//2, 0, p, "PURPLE")
        #(p, 0, p, "PINK2"),
        #(0, p, p, "CYAN"),
        #(0, p//2, p, "CYAN2"),
        #(p//2, p, p,"WHITE1"),
        #(p, p//2, p,"WHITE2"),
        #(p, p, p//2,"WHITE3")
    ]
    if isinstance(color,int):
        return color_list[color] if color < len(color_list) else (0, 0, 0,"ERROR")


    if isinstance(color,str):
        up_color = color.upper()
        if up_color == "ON":
            return (255, 255, 255)
        if up_color == "OFF":
            return (0, 0, 0)
        matches = [cl for cl in color_list if cl[3] == up_color.upper()]
        return matches[0][:3] if matches else None

    return color_list
