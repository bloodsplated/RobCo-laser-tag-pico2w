""" lobby and system tests """
import asyncio,time
from shared_utils import get_hw,Event,MyLogger,color_helper,data
from shared_classes import BaseGameRules

log = MyLogger(__name__)

INFO = {
    "module_name":"lobby",
    "version":1.0,
    "game_name":"the Lobby",
    "description":""" lobby and system tests """
}


class Rules(BaseGameRules):
    """ lobby and system tests """
    def __init__(self,*args,**kwargs):
        super().__init__(self, *args, **INFO)
        self.testlock = False
        self.ir_hits = set()




    def game_loaded(self,**kwargs):
        """caled by gameloader will provide info from last name used for lobby score board info"""
        menu = [
            ("Start Offline Game", "SET_GAME",None,{"game_name":"game_offline"} ),
            ("", "LABEL"),

            ("SYSTEM Tests","SUB", [
                ("Play all FXs", "ACTION", self.run_test, {"run_test":"FX_Tests"}),
                ("Play all sounds", "ACTION", self.run_test, {"run_test":"SOUND_LIST"}),
                ("Play all Haptic", "ACTION", self.run_test, {"run_test":"FX_HAPTIC"}),
                ("IR Bounce Test", "ACTION", self.run_test, {"run_test":"IR_100"})
            ])]


        ismute = data().vol_muted
        menu.append(
            ("Settings","SUB", [
                ("Mute: []", "SET_BOOL", self.mute_sound, {"view": "ON" if ismute else "OFF", "value": ismute}),
                ("[]", "SET_LIST", self.gunchange, {"view":"Wep:0 Basic","action":"none"}),
                ("[]", "SET_LIST", self.teamchange, {"view":"Team 'FFA ID:0","action":"none"})
            ]))

        if data().debug:
            menu.append(
                ("DEBUG Tools","SUB", [
                    ("Play BootUp", "ACTION", self.run_test, {"run_test":"BootUp"}),
                    ("Vol:[]", "SET_LIST", self.volchange, {"view":"Vol: SLOW!","action":"none"}),
                    (" -- use with care --", "LABEL"),
                    ("Exit Reboot", "QUIT", None, {"hardware_reboot":True}),
                    ("Erase Reset", "QUIT", None, {"erase_filesystem":True})
                ]))

        menu.append(("Quit", "QUIT",None,{} ))

        Event("GUI",MENU={"long_hide":False,"setMenu":menu},LCD={"show_menu":False}).send()

        self.update_gamelcd()


    def mute_sound(self,**kwargs):
        """switch shot type """
        print(data().vol_muted ," mute kwargs ",kwargs) #TODO BUG mute value is fliped for not reason
        data().vol_muted = kwargs.get("value",False)

        return "ON" if data().vol_muted else "OFF"



    def gunchange(self,**kwargs):
        """switch shot type """
        invalue = kwargs.get("INPUT","")

        if invalue == "INC":
            self.game_shot_type += 1

        if invalue == "DNC":
            self.game_shot_type -= 1

        self.game_shot_type = max(self.game_shot_type, 1)

        return f"Wep:{self.game_shot_type} Basic"

    def volchange(self,**kwargs):
        """switch shot type """
        invalue = kwargs.get("INPUT","")
        if not get_hw().sound_driver.is_active():
            return "Vol: offline"

        if invalue == "INC":
            output = get_hw().sound_driver.change_vol("+")
            return f"Vol: {output}"

        if invalue == "DNC":
            output = get_hw().sound_driver.change_vol("-")
            return f"Vol: {output}"

        return "Vol: X"




    def teamchange(self,**kwargs):
        """ test team colors """
        invalue = kwargs.get("INPUT","")

        if invalue == "INC":
            self.game_team_id += 1

        if invalue == "DNC":
            self.game_team_id -= 1

        self.game_team_id = max(self.game_team_id, 0)

        name = color_helper(self.game_team_id)[3]
        get_hw().fx_driver.LIGHT.update(game_team_id=self.game_team_id,status="ALIVE" )

        return f"Team '{name}' ID:{self.game_team_id}"


    def run_test(self,**kwargs):
        """ test launcher """
        test = kwargs.get("run_test",None)
        if self.testlock:
            return
        self.testlock = True
        if test == "IR_100":
            get_hw().next_callback = self.ir100_callback
        if test == "FX_Tests":
            get_hw().next_callback = self.fxcycle_callback
        if test == "FX_HAPTIC":
            get_hw().next_callback = self.fx_haptic_callback
        if test == "BootUp":
            get_hw().next_callback = self.boot_up_callback
        if test == "SOUND_LIST":
            get_hw().next_callback = self.sound_list_callback


    def callback_cleanup(self):
        """ cleans up after a test """
        log.debug("callback_cleanup called")
        self.testlock = False
        get_hw().gui_driver.unlocked = True
        get_hw().lcd_driver.show_menu(True)
        Event("FX",STOP=True).send()
        self.update_gamelcd()


    async def sound_list_callback(self):
        """ play each sound """
        if not get_hw().sound_driver.is_active():
            self.callback_cleanup()
            return
        game_screen = [""] *4

        for sound_trip in get_hw().sound_driver.sound_list:
            key = sound_trip[0]
            value = sound_trip[1]
            runtime = sound_trip[2]
            game_screen[0] = f"key: {key}"
            game_screen[1] = f"value: {value}"
            game_screen[2] = f"runtime: {runtime}"
            game_screen[3] =""
            Event("FX",SOUND={"SoundName":key} ).send()
            Event("GUI",LCD={"game_display":game_screen}).send()

            while get_hw().sound_driver.is_running() and self.testlock:
                await asyncio.sleep(.1)

            await asyncio.sleep(.5)


        while self.testlock:
            await asyncio.sleep(.5)
        self.callback_cleanup()



    async def boot_up_callback(self):
        """ tests Bootup show """
        #duplcate the Start up ENV

        get_hw().lcd_driver.show_menu(True)

        startlist = get_hw().LCD.get_start_screen()

        get_hw().gui_driver.unlocked = False

        for i in range(4, -1, -1):
            get_hw().LCD.menu_group[i].text = startlist[i]

        await asyncio.sleep(.5)


        await get_hw().Bootup_show()
        await asyncio.sleep(1)
        self.callback_cleanup()


    async def fx_haptic_callback(self):
        """haptic tests"""
        fx_list = [
            # (effect_id, "Effect Name", runtime)
           # (1, "Strong Click", 0.5),
            #(4, "Sharp Click", 0.5),
            #(7, "Soft Bump", 0.5),
            (10, "Double Click", 0.5),
            (12, "Triple Click", 0.5),
            (14, "Strong Buzz", 0.5),
            (15, "750 ms Alert", 0.5),
            (16, "1000 ms Alert", 0.5),
            #(17, "Strong Click 1", 0.5),
            #(21, "Medium Click 1", 0.5),
            #(24, "Sharp Tick 1", 0.5),
            #(27, "Short Double Click Strong 1", 0.5),
            #(31, "Short Double Click Medium 1", 0.5),
            #(34, "Short Double Sharp Tick 1", 0.5),
            #(37, "Long Double Sharp Click Strong 1", 0.5),
            #(41, "Long Double Sharp Click Medium 1", 0.5),
            #(44, "Long Double Sharp Tick 1", 0.5),
            (47, "Buzz 1", 0.5),
            (52, "Pulsing Strong 1", 1.5),
            (54, "Pulsing Medium 1", 1.5),
            (56, "Pulsing Sharp 1", 10.5),
            (58, "Transition Click 1", 0.5),
            (64, "Transition Hum 1", 0.5),
            (118, "Long buzz for programmatic stopping", 1.0),
            (119, "Smooth Hum 1 (No kick or brake pulse)", 1.0),
            (70, "Transition Ramp Down Long Smooth 1", 1.0),
            (82, "Transition Ramp Up Long Smooth 1", 1.0)
        ]

        idx = 0
        n = len(fx_list)

        game_screen = [""] *4
        while self.testlock:

            effect = fx_list[idx]
            #get_hw().fx_driver.HAPTIC.on_event(List=[effect[0]], runtime=effect[2])
            get_hw().fx_driver.HAPTIC.on_event(List=[effect[0]], runtime=1.0)

            game_screen[0] = "HAPTIC test"
            game_screen[1] = f"effect ID:{effect[0]}"
            game_screen[2] =  effect[1]
            game_screen[3] = "click to exit"

            Event("GUI",LCD={"game_display":game_screen}).send()

            while get_hw().fx_driver.is_fx_running() and self.testlock:
                await asyncio.sleep(0)
            idx = (idx + 1) % n
            get_hw().fx_driver.HAPTIC.stop()
            await asyncio.sleep(1)

        self.callback_cleanup()





    async def fxcycle_callback(self):
        """fx demo code """
        fx_list = ["FIRE","EMPTY","RELOAD","HIT","DEAD","RESPAWN","GAMEOVER","WON"]


        team = max(self.game_team_id, 1)
        game_screen = [""] *4
        start_time = time.monotonic()
        for effect in fx_list:

            game_screen[0] = "FX Tests"
            game_screen[1] = "Playing effect:"
            game_screen[2] =  effect
            game_screen[3] = "click to exit"
            Event("GUI",LCD={"game_display":game_screen}).send()

            status = "ALIVE" #"LIMBO" "DEAD"
            is_winning = False
            if effect == "WON":
                effect = "GAMEOVER"
                is_winning = True

            if effect == "DEAD":
                status = "DEAD"


            payload_data = {
            "game_team_id":team,
            "status":status,
            "game_shot_type":self.game_shot_type,
            "is_winning":is_winning
            }

            self.trigger_fx(effect,payload_data)

            while get_hw().fx_driver.is_fx_running() and self.testlock:
                await asyncio.sleep(.1)
            end_time = time.monotonic()
            log.debug(f"{effect} runtime ={end_time-start_time}")

            await asyncio.sleep(1)

        self.callback_cleanup()





    async def ir100_callback(self):
        """bounce back Ir test"""
        self.ir_hits.clear()
        expected_hits = set()

        game_screen = [""] *4

        game_screen[0] = "Fire test: 0 of 100"
        Event("GUI",LCD={"game_display":game_screen}).send()

        for i in range(1, 99 ):
            emitter = 0 if i % 2 == 0 else 1
            Event("IR",
                player_id=i,
                team_id=(i // 10),
                shot_id=(100 - i),
                emitter_id=emitter
                ).send()

            await asyncio.sleep(.7)
            game_screen[0] = f"Fire test: {i} of 99"
            game_screen[1] = f"P:{i} T:{(i // 10)} S:{(100 - i)} E:{emitter}"
            game_screen[2] = f"Hit Count:{len(self.ir_hits)}"
            game_screen[3] = f"Miss Count:{len(expected_hits.difference(self.ir_hits))}"
            Event("GUI",LCD={"game_display":game_screen}).send()

            expected_hits.add(i)
            if not self.testlock :
                return self.callback_cleanup()

        game_screen[1] = "final score ... "
        game_screen[3] = ""
        Event("GUI",LCD={"game_display":game_screen}).send()
        await asyncio.sleep(2)


        missing_hits = expected_hits.difference(self.ir_hits)
        log.debug(f"BounceBack diff_count:{missing_hits}" )

        game_screen[0] = "Fire test: Score"
        game_screen[1] = "Shots fired 100"
        game_screen[2] = f"Hit Count:{len(self.ir_hits)}"
        game_screen[3] = f"Miss Count:{len(missing_hits)}"
        Event("GUI",LCD={"game_display":game_screen}).send()

        while self.testlock:
            await asyncio.sleep(.5)
        self.callback_cleanup()




    def game_irtag(self,**kwargs):
        """@Override EVENT_IR to capture valid tags"""
        log.debug(f"EVENT_IR captured {kwargs}" )
        self.ir_hits.add(kwargs.get("PlayerID",0))



    def game_input(self,**kwargs):
        """@Override game_input to stop running tests"""
        if self.testlock:
            self.testlock = False
        super().on_event(**kwargs)

    def update_gamelcd(self):
        """@Override LCD updates during Tests"""
        log.debug(f"self.testlock {self.testlock}")
        if self.testlock:
            return
        super().update_gamelcd()
