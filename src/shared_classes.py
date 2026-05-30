"""super classes"""
import supervisor





from shared_utils import data, Event, MyLogger

log = MyLogger(__name__)

class DriverModule:
    """super for all hardware drivers"""

    def __init__(self, *args, **kwargs):
        self.module_name = self.__class__.__name__
        self.active = False
        self.running = False
        self.args = args
        # Dynamically set attributes based on kwargs helps with unit tests
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def async_start(self):
        """part of init kicks off any async loops and sets logger name"""

    def is_active(self):
        """detect if loading was successful"""
        return self.active

    def on_event(self, **payload):
        """and must be implemented for all drivers to handle events"""

    def cleanup(self):
        """used at shutdown to cleanup any active effects or threads"""
        self.active = False
        log.debug(f" cleanup: {self.module_name}")

    def stop(self):
        """used for FX to stop running effects """

    def is_running(self):
        """used for FX to check for running effects """
        return self.running

    # def __getattr__(self, name):
    #    def default_method(*args, **kwargs):
    #        if name in ["display","update_menu"]: return #skip LCD display calls for now
    #        log.error(f"non-existent method '{name}' with arguments: {args},
    # keyword arguments: {kwargs}")
    #        return False
    #    return default_method
FX_LIGHTS = [2, 5, 10, 13]
class Weapon:
    """holds Weapon details"""

    def __init__(self,**kwargs):

        self.wep_name = "basic"
        self.wep_mag_size = 10
        self.wep_cooldown = 1000  #ms time delay between shots
        self.wep_damage = 1
        self.reload_sound =""
        self.empty_sound =""
        self.fire_sound =""

        # Dynamically set attributes based on kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


    def fx_empty(self):
        """fx for empty"""
        payload = {}
        payload["SOUND"] = {"SoundName": "EMPTY_00","STOP": True}
        payload["HAPTIC"] = {"List": [12]}
        return payload

    def fx_load(self):
        """fx for reload"""
        payload = {}
        payload["SOUND"] = {"SoundName": "LOAD_00","STOP": True}
        payload["HAPTIC"] = {"List": [12]}
        return payload

    def fx_fire(self):
        """fx for fireing this gun"""
        payload = {}
        payload["SOUND"] = {"SoundName": "FIRE_00","STOP": True}
        payload["HAPTIC"] = {"List": [58],"runtime":.1}
        playlist = []
        playlist.append(('PIXELS', FX_LIGHTS, 'YELLOW'))
        playlist.append(('SHOW', .2, 0))
        playlist.append(('PIXELS', FX_LIGHTS, 'OFF'))
        playlist.append(('SHOW', 0, 0))
        payload["LIGHT"] = {"playlist": playlist}
        return payload

    def fx_hit(self):
        """fx for a hit from this gun"""
        payload = {}
        payload["SOUND"] = {"SoundName": "HIT_00","STOP": True}
        playlist = []
        playlist.append(('PIXELS', [5, 13], 'RED'))
        playlist.append(('PIXELS', [2, 10], 'ORANGE'))
        playlist.append(('SHOW', .2, 0))
        playlist.append(('PIXELS', FX_LIGHTS, 'OFF'))
        playlist.append(('SHOW', 0, 0))
        payload["LIGHT"] = {"playlist": playlist}
        payload["HAPTIC"] = {"List": [70],"runtime":.1} #"Transition Ramp Down Long Smooth 1"

        return payload




class BaseGameRules:
    """ super class for all games
    full of helper functions that can be overwritten
    """

    def __init__(self, *args, **kwargs):
        self.module_name = __name__
        self.ginstance_id = args[1]
        self.game_name = "template"
        self.status = "LIMBO"  # ALIVE DEAD
        self.is_winning = False  # used for end of game

        self.curent_hp = 0
        self.max_hp = 5

        self.curent_spawn = 0

        self.cooldown_spawn = 10  # 10sec
        self.last_fire = supervisor.ticks_ms()

        self.cooldown_hit = 1000 #ms delay between damage
        self.last_hit = supervisor.ticks_ms()

        self.curent_amo = 0

        # Stats stats at end
        self.shot_count = 0
        self.death_count = 0
        self.body_count = 0  # killed players
        self.hits_count = 0  # wounds on players
        self.game_points = 0 # used to find winner at end of game

        self.game_gun_id  = data().gun_id  # default is gun ID but can be replaced
        self.callsign = "NONE"  # gun hostname unless overwritten
        self.game_team_id = 0  # zero is no team
        self.game_shot_type = 1  # basic gun

        self.cur_weapon = Weapon()

        self.shot_name = "basic"
        self.shot_damage = 1
        self.shot_at_spawn = 1 #for gamemodes

        for key, value in kwargs.items():
            # Dynamically set attributes based on kwargs
            setattr(self, key, value)

        self.name = f"{self.module_name}_{self.ginstance_id}"

# ------------------- external game_ events  -------------------

    def game_loaded(self, **kwargs):  # pylint: disable=unused-argument
        """caled by gameloader will provide info from last name used for lobby score board info"""
        menu = [("Exit to Lobby", "SET_GAME", None,
                 {"game_name": "game_lobby"})]
        Event("GUI", MENU={"long_hide": True,"setMenu": menu}, LCD={"show_menu":False}).send()

        self.update_gamelcd()
        # send ready to server

    def game_start(self, **kwargs):  # pylint: disable=unused-argument
        """called by server to start game"""
        self.player_respawn()
        gamedata = {"TYPE": "START", "PLAYER": self.server_data()}
        Event(0, gamedata=gamedata).send()

    def game_end(self, **kwargs):  # pylint: disable=unused-argument
        """called when the game is over by the server"""
        self.trigger_fx("GAMEOVER")
        self.status = "LIMBO"
        gamedata = {"TYPE": "FINAL", "PLAYER": self.server_data(True)}
        Event(0, gamedata=gamedata).send()
    def game_exit(self, **kwargs):  # pylint: disable=unused-argument
        """caled by gameloader returns data for carry over to lobby creates lastgamedata"""
        Event("FX",STOP=True).send()
        return self.server_data(True)

    def game_input(self, **kwargs):
        """handles button input from hardware"""
        name = kwargs.get("name", "None")
        value = kwargs.get("value", "None")

        if name == "TRIG" and value == "SINGLE":
            self.player_fire()
        if name == "TRIG" and value == "LONG":
            self.player_reload()

    def game_irtag(self, **kwargs):
        """handles ir tag data from hardware"""
        tag_location = kwargs.get("Receiver", "None")
        player_id = kwargs.get("PlayerID", 0)
        team_id = kwargs.get("game_team_id", 0)
        shot_id = kwargs.get("ShotID", 0)

        if player_id < 1 or player_id == self.game_gun_id :
            return

        if self.status == "ALIVE":

            elapsed = supervisor.ticks_ms() - self.last_hit
            if elapsed < self.cooldown_hit:
                log.debug(f"cooldown_hit cooldown elapsed:{elapsed} ms < {self.cooldown_hit}")
                return
            self.last_hit = supervisor.ticks_ms()

            self.player_hit(1)

            tagdata = {
                "location": tag_location,  # gun vest back
                "Victim": int(self.game_gun_id ),  # me
                "Shooter": int(player_id),
                "game_team_id": int(team_id),
                "game_gun_id ": int(shot_id),  # gun code
                "VictimHP": self.curent_hp
            }

            gamedata = {
                "TYPE": "TAG",
                "PLAYER": self.server_data(),
                "TAG_DATA": tagdata
            }
            Event(0, gamedata=gamedata).send()
            Event(int(player_id), gamedata=gamedata).send()
            return "-------------I was Shot --------------"

    def game_heartbeat(self, **kwargs): # pylint: disable=unused-argument
        """should fire 1 a sec when game is active use for Respawn logic"""
        if self.status == "DEAD":
            self.update_gamelcd()
            if self.curent_spawn > 0:
                self.curent_spawn -= 1
            else:
                self.player_respawn()

# ------------------- overwritable player_ actions -------------------
    def get_weapon(self,shot_id): # pylint: disable=unused-argument
        """ only 1 weapon at the moment """
        return self.cur_weapon

    def swap_gun(self, new_shot_type):
        """helper function to swap gun type"""
        self.game_shot_type  = new_shot_type
        self.cur_weapon = self.get_weapon(new_shot_type)
        self.update_gamelcd()

    def swap_team(self,new_team_id):
        """helper function to swap team"""

    def player_respawn(self):
        """the player_respawn action"""
        self.swap_gun(self.shot_at_spawn)
        self.status = "ALIVE"
        self.curent_hp = self.max_hp
        self.curent_amo = self.cur_weapon.wep_mag_size
        self.trigger_fx("RESPAWN")
        self.update_gamelcd()

    def player_hit(self, damage):
        """the player_hit action"""
        if self.status == "ALIVE":
            self.curent_hp -= damage
            if self.curent_hp < 1:
                self.player_death()
            else:
                self.trigger_fx("HIT")
        self.update_gamelcd()

    def player_death(self):
        """the player_death action"""
        self.curent_hp = 0
        self.death_count += 1
        self.status = "DEAD"
        self.curent_spawn = self.cooldown_spawn
        self.trigger_fx("DEAD")

    def player_fire(self):
        """the player_fire action"""
        this_wep = self.get_weapon(self.game_shot_type)
        elapsed = supervisor.ticks_ms() - self.last_fire
        if elapsed < this_wep.wep_cooldown:
            log.debug(f"weapon cooldown elapsed:{elapsed} ms < {this_wep.wep_cooldown}")
            return
        self.last_fire = supervisor.ticks_ms()

        if self.status == "ALIVE":

            if self.curent_amo > 0:
                self.curent_amo -= 1
                self.shot_count += 1

                self.trigger_fx("FIRE")
                log.debug(Event("IR",
                player_id=self.game_gun_id ,
                team_id=self.game_team_id,
                shot_id=self.game_shot_type,
                emitter_id=0
                ).send()
                )

            else:
                self.trigger_fx("EMPTY")
        self.update_gamelcd()

    def player_reload(self):
        """the player_reload action"""
        if self.status == "ALIVE":
            self.curent_amo = self.cur_weapon.wep_mag_size
            self.trigger_fx("RELOAD")
        self.update_gamelcd()

# ------------------- helper functions  -------------------

    def on_event(self, **payload):
        """ not used yet but should be for mqtt events """

        if payload.get("msg_type", None) is not None:
            # def MSG_TAGGED(self,payload={}):
            log.debug(
                f"-------------I Shot someone -------------- \n {payload}")
            self.hits_count += 1
            self.game_points += 1
            if "VictimHP" in payload:
                if payload["VictimHP"] == 0:
                    self.body_count += 1
                    self.game_points += 5

    def are_fx_running(self):
        """helper functon to check if Fx are running """
        reply = Event("FX", {"is_fx_running": True}).send()
        log.debug(f"is_fx_running: {reply}")
        return reply[0]

    def server_data(self, final=False):
        """data sent to server"""
        accuracy = 0
        data2send = {
            "callsign": self.callsign,
            "status": self.status,
            # "curent_hp":self.curent_hp, #needed for kils to work
            "shot_count": self.shot_count,
            "death_count": self.death_count,
            "body_count": self.body_count,
            "hits_count": self.hits_count,
            "accuracy": accuracy,
            "game_points": self.game_points,
            "game_gun_id ": self.game_gun_id ,
            "game_team_id": self.game_team_id
        }
        if final:
            data2send["Events"] = []  # event list
        return data2send

    def trigger_fx(self, fxname, fx_data=None):
        """helper function to send FX"""

        if fx_data is None:
            fx_data = {
                "game_team_id": self.game_team_id,
                "status": self.status,
                "game_shot_type": self.game_shot_type,
                "is_winning": self.is_winning
            }

        fx_data["fxname"] = fxname
        shot_type = fx_data.get("game_shot_type",0)

        payload = {}

        the_weapon = self.get_weapon(shot_type)

        if fxname == "EMPTY":
            payload = the_weapon.fx_empty()

        if fxname == "RELOAD":
            payload = the_weapon.fx_load()

        if fxname == "FIRE":
            payload = the_weapon.fx_fire()

        if fxname == "HIT":
            payload = the_weapon.fx_hit()

        if fxname == "RESPAWN":
            payload["SOUND"] = {"SoundName": "SPAWN_00","STOP": True}

        if fxname == "GAMEOVER":
            if fx_data.get("is_winning", False):
                payload["SOUND"] = {"SoundName": "END_00","STOP": True} # winner sound
                payload["LIGHT"] = {"playlist": [('FUNK', "play_rainbow", {})]}
            else:
                payload["SOUND"] = {"SoundName": "END_01","STOP": True}

        if payload.get("LIGHT",None) is None:
            payload["LIGHT"] = {"playlist": [
                ('FUNK', "update", {"game_team_id": fx_data["game_team_id"], "status": fx_data["status"]})
                ]}

        Event("FX", payload).send()

    def update_gamelcd(self):
        """called when drawing the screen"""
        game_screen = [""] * 4

        if self.status == "DEAD":
            game_screen[1] = "------DEAD------"
            game_screen[2] = f"RESPAWN {self.curent_spawn}"

        if self.status == "LIMBO":
            game_screen[1] = f"{self.game_name}"
            game_screen[2] = f"gun_id: {data().gun_id:02d}"

        if self.status == "ALIVE":

            game_screen[0] = f"ID:{data().gun_id:02d} HP:{self.curent_hp:02d} AMO:{self.curent_amo:02d}"

            game_screen[1] = "   O   [" + \
                ('#' * self.curent_amo) + (' ' * (10 - self.curent_amo)) + "]+"
            game_screen[2] = " - Y - "
            game_screen[3] = "  / \\  "
            if self.curent_hp == 4:
                game_screen[2] = "   Y - "
                game_screen[3] = "  / \\  "
            if self.curent_hp == 3:
                game_screen[2] = "   Y - "
                game_screen[3] = "  /    "
            if self.curent_hp == 2:
                game_screen[2] = "   Y - "
                game_screen[3] = "       "
            if self.curent_hp == 1:
                game_screen[2] = "   Y   "
                game_screen[3] = "       "

        Event("GUI",LCD={"game_display":game_screen}).send()
