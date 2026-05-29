""" LIGHT Driver """
import traceback,board ,asyncio,time
import neopixel

from shared_classes import DriverModule
from shared_utils import color_helper,data,MyLogger
log = MyLogger(__name__)
INFO = {
    "module_name": __name__,
    "version": 1.0,
    "Driver": "LIGHT",
    "description": """ NeoPixel light Driver"""
}



NON_TEAMLIST = [2,5,10,13]



class LIGHT(DriverModule):
    """ LIGHT Driver """
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **INFO)
        self.module_name = __name__
        self.active = True
        self.running = False
        self.playlist =[] #contains the todolist
        self.num_pixels  = 16
        self.pixels = None
        self.testlock = False

        try:
            pixel_pin = board.GP18 # pylint: disable=no-member
            self.pixels = neopixel.NeoPixel(pixel_pin, self.num_pixels, brightness=1, auto_write=False)
            self.pixels.fill(color_helper("OFF"))
            self.pixels.show()
        except Exception as e:
            log.error("Exception pixels:", e)
            self.pixels = None


    #stops all active effects immediately
    def stop(self):
        log.debug("stop called")
        self.playlist.clear()
        self.running = False


    #turn off lights
    def cleanup(self):
        super().cleanup()
        self.stop()
        if self.pixels is not None:
            self.pixels.fill(color_helper("OFF"))
            self.pixels.show()





    #needed for timeded effects
    async def async_start(self):
        await super().async_start() #sets logger name

        try:
            while self.active:
                data().async_watcher["FX.LIGHT_async_start"] = time.monotonic()

                extra_wait = 0
                while len(self.playlist) > 0:

                    nextcommand = self.playlist.pop(0)
                    try:
                        if isinstance(nextcommand, tuple) and len(nextcommand) > 0:


                            if str(nextcommand[0]) == "PIXELS":
                                pixels = nextcommand[1]
                                color = nextcommand[2]

                                for p in pixels:
                                    if p < self.num_pixels:
                                        self.pixels[p] = color
                                if len(pixels) == 0:
                                    self.pixels.fill(color)



                            if str(nextcommand[0]) == "STOP":
                                self.stop()
                                break

                            if str(nextcommand[0]) == "FUNK":
                                await self.funk_task(nextcommand[1],nextcommand[2])
                                break

                            if str(nextcommand[0]) == "SHOW":
                                self.pixels.show()
                                extra_wait = nextcommand[1]
                                break

                    except Exception as e:
                        log.error("nextcommand got an error:", e)


                await asyncio.sleep(0.1+extra_wait)

                if len(self.playlist) == 0 and self.running:
                    self.running = False

        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error("async Worker task Exception:", e)
        finally:
            log.debug("async Worker task end")


    # payload = contents of LIGHT:{} from FX event
    def on_event(self, **payload):

        if self.running:
            return "effect is running"

        if payload.get("STOP",False):
            self.stop()
            return "LIGHT STOPPED"

        if payload.get("UPDATE",False):
            return self.update(**payload.get("UPDATE"))

        if len(self.playlist) > 0:
            return f"playlist is full {len(self.playlist)}"
        newplaylist = payload.get("playlist",[])
        return self.build_playlist(*newplaylist)

    async def funk_task(self,function,payload):
        """ calls functions """
        try:
            func = getattr(self, function, None)
            if not callable(func):
                return
            await func(**payload)
        except AttributeError:
            func(**payload)

        except Exception as e:
            log.error("funk_task Exception:", e)


    def update(self,**payload):
        """ updates lights after an effect"""
        #log.debug(f"UPDATE payload: {payload}")
        player_status = payload.get("status","LIMBO") #"ALIVE" "LIMBO" "DEAD"
        team_id = payload.get("game_team_id",0)

        if player_status == "DEAD":
            self.pixels.fill(color_helper("OFF"))

        elif player_status == "ALIVE":
            for a in range(self.num_pixels):
                if a in NON_TEAMLIST:
                    self.pixels[a] = color_helper("OFF")
                else:
                    self.pixels[a] = color_helper(team_id,20)[:3]
        else:
            self.pixels.fill(color_helper("OFF"))
        self.pixels.show()




    def build_playlist(self,*tasks):
        """    # tasks will be a list of triples like (command,var,color)"""
        try:
            #log.debug(f"build_playlist called with tasks {tasks}")


            for task in tasks:
                if not isinstance(task, tuple) or not isinstance(task[0], str) or len(task) != 3:
                    raise ValueError(f"Invalid task expected: ('str',x,x) format: {task}.")
                command = task[0].upper()
                var1 = task[1]
                var2 = task[2]

                if command not in ["SHOW","PIXELS","STOP","FUNK"]:
                    raise ValueError(f"Invalid command {command}.")

                if command == "SHOW":
                    if not isinstance(task[1], (int, float)):
                        raise ValueError(f"Invalid SHOW payload expected: number got {task[1]}")

                if command == "PIXELS": #[] = fill
                    if not isinstance(task[1], list) or not isinstance(task[2], str):
                        raise ValueError("Invalid PIXELS payload expected: list ")
                    var2 = color_helper(task[2].upper())
                    if var2 is None or len(var2)!= 3:
                        raise ValueError(f"Invalid PIXELS color name {task[2]} var2:{var2}")

                if command == "FUNK":
                    if not isinstance(task[1], str) or not isinstance(task[2], dict):
                        raise ValueError(f"Invalid FUNK payload expected: (FUNK,str,dict) got {task}")

                    func = getattr(self, task[1], None)
                    if not callable(func):
                        raise ValueError(f"Invalid FUNK: self has no callable function named '{task[1]}'")

                self.playlist.append((command,var1, var2))



        except Exception as e:
            traceback.print_exception(e)
            self.playlist = []
            return f"Exception in build_playlist: {e}"


    async def play_rainbow(self,**nextfx):
        """#used for winner of a game, runs untill stopped"""
        if self.running:
            return "effect is running" + nextfx
        self.running = True
        #run untill stopped! used for winner of a game
        def wheel(pos):
            if pos < 0 or pos > 255:
                r = g = b = 0
            elif pos < 85:
                r = int(pos * 3)
                g = int(255 - pos * 3)
                b = 0
            elif pos < 170:
                pos -= 85
                r = int(255 - pos * 3)
                g = 0
                b = int(pos * 3)
            else:
                pos -= 170
                r = 0
                g = int(pos * 3)
                b = int(255 - pos * 3)
            return (r, g, b) #if ORDER in {neopixel.RGB, neopixel.GRB} else (r, g, b, 0)


        while self.running:

            for j in range(255):
                if not self.running:
                    break
                for i in range(self.num_pixels):
                    if not self.running:
                        break
                    pixel_index = (i * 256 // self.num_pixels) + j
                    self.pixels[i] = wheel(pixel_index & 255)

                self.pixels.show()
                await asyncio.sleep(0)

        self.pixels.fill((0, 0, 0))#off
        self.pixels.show()
        self.testlock = False
