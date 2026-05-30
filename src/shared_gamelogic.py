"""loads games"""
import json,gc
from shared_utils import Event,MyLogger


log = MyLogger(__name__)


from shared_classes import BaseGameRules

class GameLoader:
    """loads games"""
    def __init__(self):
        self.loadedgames = 0
        self.curentgamerules = None


    def pass_event(self,fun_target: str, payload: dict):
        """passes events to the current running game"""
        if not isinstance(fun_target, (str)):
            raise TypeError(f"ext_target must be str or None, not {type(fun_target).__name__}")
        if not isinstance(payload, dict):
            raise TypeError(f"payload must be a dict, not {type(payload).__name__}")
        action = fun_target.lower()

        if action == "game.start":
            self.switch_game(**payload)
            return
        if action == "game.gameover":
            self.switch_game(GAME_TYPE="game_lobby")
            return

        if self.curentgamerules is None:
            return

        wild_card = action.replace(".","_")

        method_to_call = getattr(self.curentgamerules, wild_card, None)
        if callable(method_to_call):
            reply = method_to_call(**payload)
            return reply

        raise TypeError(f"game loader event:{fun_target}  not callable: as:{wild_card} ")

    def get_current_game(self):
        """returns the current game rules object"""
        if self.curentgamerules is None:
            return None
        return self.curentgamerules


    def game_msg_event(self,**msg_payload):
        """"passes messages to the current running game"""
        mtype = msg_payload.get("TYPE", "NONE")

        def call_method(obj, method_name, **msg_payload):
            if not method_name in ["EVENT_HEARTBEAT"]:
                log.debug(f" game_msg_event calling {type(obj)}.{method_name}")

            if obj is None:
                return
            method_to_call = getattr(obj, method_name, None)
            if callable(method_to_call):
                method_to_call(**msg_payload)
            else:
                log.error(f" game_msg_event not callable{method_name}")



        if mtype == "GAME_NEW":
            error = self.switch_game(**msg_payload)
            log.error(error)
            return
        if mtype == "GAME_GAMEOVER":
            error = self.switch_game(GAME_TYPE="game_lobby")
            log.error(error)
            return


        if self.curentgamerules: #if game it loaded pass to it
            msg_route = mtype.split("_")
            call_method(self.curentgamerules, f"EVENT_{msg_route[1]}", **msg_payload)




    def switch_game(self,**kwargs):
        """switches the current game"""
        self.loadedgames += 1
        Event("FX",STOP=True).send()
        last_game_data = {}
        rules_name = kwargs.get("GAME_TYPE", "None")
        try:
            if not rules_name.startswith("game_"):
                raise TypeError(f"Invalid Game Type '{rules_name}'")

            if self.curentgamerules:
                make_a_copy = self.curentgamerules.game_exit()
                last_game_data = json.loads(json.dumps(make_a_copy))


            imported_rules = __import__(rules_name)
            if not hasattr(imported_rules, "Rules") or not callable(getattr(imported_rules, "Rules")):
                raise TypeError(f"Rules() invalid '{rules_name}'")

            mod = getattr(imported_rules, "Rules")(self.loadedgames)
            if not isinstance(mod, BaseGameRules):
                del mod
                raise TypeError(f"Rules() invalid '{rules_name}'")

            log.debug(f"Success  {rules_name} loaded!")
            self.curentgamerules = mod

            mod.game_loaded(**kwargs.get("lastgame", last_game_data))

        except Exception as e:
            log.error(f"'{rules_name}' Module Exception:", e)
            return f"'{rules_name}' Module Exception: {e}"
        gc.collect()
