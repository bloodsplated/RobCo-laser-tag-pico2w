"""
loads all hardware
all subsystems must be child classes of DriverModule



"""


from  hw_input_driver import INPUT as INPUT_DRIVER
from  hw_ir_driver import IR as IR_DRIVER
from  hw_lcd_oled import LCD as LCD_DRIVER
from  hw_gui_tools import GUI as GUI_DRIVER
from  hw_sound_fx_uart import SOUND as SOUND_DRIVER

from  hw_haptic_driver  import HAPTIC as HAPTIC_DRIVER
from  hw_light_driver import LIGHT as LIGHT_DRIVER
from  hw_fx_driver import FX as FX_DRIVER

#from  hw_wifi_driver import WIFI as WIFI_DRIVER
#from  hw_mqtt_driver import MQTT as MQTT_DRIVER

from shared_classes import DriverModule as WIFI_DRIVER
from shared_classes import DriverModule as MQTT_DRIVER

import asyncio,os,re,microcontroller,time

from shared_classes import DriverModule
from shared_utils import data,Event,color_helper,MyLogger




log = MyLogger(__name__)

# pylint: disable=too-many-instance-attributes disable=broad-exception-caught disable=no-member
class Hardware:
    """loads all hardware"""
    def __init__(self):

        uname_info = os.uname()
        machine = uname_info.machine

        data().gun_model = machine
        data().gun_model2 = ""
        splitlen = 22
        if len(machine) >= splitlen:
            split_index = machine.rfind(" ", 0, splitlen)

            if split_index == -1:
                split_index = splitlen
            data().gun_model = machine[:split_index].strip()
            data().gun_model2 = machine[split_index:].strip()


        uid_bytes = microcontroller.cpu.uid
        sn = "".join([f"{x:02x}" for x in uid_bytes])

        data().gun_sn = sn.upper()
        newid = re.sub("[^1-9.]", "", sn.upper())
        data().gun_id = int(newid[-2:])


        self.lcd_driver = LCD_DRIVER()
        self.gui_driver = GUI_DRIVER(LCD = self.lcd_driver)

        self.input_driver = INPUT_DRIVER()
        self.ir_driver = IR_DRIVER()

        self.wifi_driver = WIFI_DRIVER()
        self.mqtt_driver = MQTT_DRIVER(WIFI = self.wifi_driver)

        self.light_driver = LIGHT_DRIVER()
        self.sound_driver = SOUND_DRIVER()
        self.haptic_driver = HAPTIC_DRIVER()

        self.fx_driver = FX_DRIVER("FX_MODULE",
                    LIGHT = self.light_driver,
                    SOUND = self.sound_driver,
                    HAPTIC = self.haptic_driver)


        self.gameclock = 0
        self.spinbit = 0
        self.statusbit = "0"
        self.active = True
        self.next_callback = None
        self.exit_command = ""




    def on_event(self,**payload):
        """routing just HW events."""
        name = payload.get("name",None)
        if name == "ROTARY":
            self.gui_driver.menu_input(**payload)



    async def async_start_all(self):
        """runs async start for all modules should have it works like init"""
        try:
            tasks =[]
            log.debug("-------- HW async start all --------"  )
            for key, obj in self.__dict__.items():
                if isinstance(obj, DriverModule):
                    if  hasattr(obj, "async_start") and callable(getattr(obj, "async_start")):

                        newkey = f"/{key.upper()}".replace("_DRIVER", "")

                        tasks.append(asyncio.create_task(obj.async_start()))
                        l2 = "ONLINE" if obj.is_active() else '______'
                        log.debug(f"{newkey:<7} | {l2} |  module_name: {obj.module_name}")

            tasks.append(asyncio.create_task(self.ready_check()))
            tasks.append(asyncio.create_task(self.async_callback()))

            replays = await asyncio.gather(*tasks, return_exceptions=True)
            log.debug(f"asyncio.gather tasks {replays}")

        except Exception as e:
            log.error("async_start_all Exception:", e)

        return self.exit_command




    async def do_callback(self,acallback):
        """   #part of the async callback system """
        log.debug(f"do_callback {acallback}")
        try:
            if callable(acallback):
                log.debug(f"is callable { acallback}")
                await acallback()

            log.debug("do_callback Done")
        except Exception as e:
            log.error("do_callback task Exception:", e)


    async def async_callback(self):
        """ #part of the async callback system"""
        try:
            log.debug("async_callback task start.")
            while self.active:
                data().async_watcher["async_callback"] = time.monotonic()
                if self.next_callback:
                    await self.do_callback(self.next_callback)

                    self.next_callback = None

                await asyncio.sleep(0)

        except asyncio.CancelledError:
            log.debug("async_debug task cancelled.")
        except Exception as e:
            log.error("async_debug task Exception:", e)
        finally:
            log.debug("async_debug task end")



    async def ready_check(self):
        """# -----------------------------  ready check -----------------------------
        # ready check is the final step of async start up this kicks off everything else
        # ------------------------------------------------------------------------  """
        gametojoin = data("SKIP_LOBBY","game_lobby")

        log.debug(f"Requesting name from Server 'GET_ID' gun_sn:{data().gun_sn}")
        Event(0,{"gun_sn":data().gun_sn}).send() #0 = TOPIC_QUEEN > 99: = all_DRONEs


        if data("SKIP_SHOW", 0 ) == 0 and self.fx_driver.is_active:
            await self.bootup_show()


        self.gui_driver.unlocked = True #relases the lock on the gui
        self.lcd_driver.show_menu(False)


        log.debug(f"Requesting name from Server 'GET_ID' curentID:{data().gun_id}")
        Event("GAME.START",GAME_TYPE=gametojoin).send()


        await asyncio.sleep(.1) #wait for lobby to load

        log.debug(" Start GAME_HEARTBEAT")
        tick_tock = True
        network_status = False
        while self.active:
            tick_tock = not tick_tock
            network_status = self.mqtt_driver.is_running()
            self.spinbit += 1
            onbit = "x" if tick_tock else "+"
            offbit = "0" if tick_tock else "O"

            self.gameclock += 1
            Event("GAME.HEARTBEAT",gameclock=self.gameclock).send()


            if self.gui_driver.is_active():
                menubar1 = f"RobCo OS:{data().hw_ver}"
                menubar2 = f"[{offbit}]" if network_status else f"[{onbit}]"
                padding_needed = 21  - (len(menubar1) + len(menubar2))
                menubar = menubar1 + (" " * padding_needed) + menubar2
                Event("GUI",HEARTBEAT={"gameclock":self.gameclock,"menubar":menubar}).send()

            await asyncio.sleep(1)




    async def bootup_show(self):
        """ bootup up efect  will show system info and buy time for the network to respond """
        codeonscreen = self.lcd_driver.get_start_screen().copy()
        self.lcd_driver.idle_menu = 10



        Event("FX",SOUND={"SoundName":"BOOT_00"} ).send()

        bootshowlist = []


        for key, obj in self.__dict__.items():
            if isinstance(obj, DriverModule):
                newkey = f"/{key.upper()}".replace("_DRIVER", "")
                l2 = "_ONLINE" if obj.is_active() else '____ERR'
                driverstr =f"0x00 {newkey:0>8}:{l2}"
                bootshowlist.append(driverstr)


        bootshowlist.append("")

        menubar1 = f"RobCo OS:{data().hw_ver}"
        menubar2 = "[#]"
        padding_needed = 21  - (len(menubar1) + len(menubar2))
        menubar = menubar1 + (" " * padding_needed) + menubar2

        bootshowlist.append(menubar)
        bootshowlist.append("")
        bootshowlist.append(f"SN:{data().gun_sn}")
        bootshowlist.append(f"Gun_ID:{data().gun_id}")
        bootshowlist.append("")

        pix = 0
        while bootshowlist:
            try:
                codeonscreen.pop(0)
                codeonscreen.append(bootshowlist.pop(0))
                Event("GUI",LCD={"menu_display":codeonscreen,"show_menu":True}).send()


                if pix <= 8 and self.fx_driver.LIGHT.is_active():
                    playlist =[]
                    playlist.append(('PIXELS', [], 'OFF'))
                    playlist.append(('PIXELS', [(15 -pix),pix], 'WHITE'))
                    playlist.append(('SHOW', 0, 0))


                    self.fx_driver.LIGHT.pixels.fill(color_helper("OFF"))
                    self.fx_driver.LIGHT.pixels[15 -pix] = color_helper("WHITE")
                    self.fx_driver.LIGHT.pixels[pix] = color_helper("WHITE")
                    self.fx_driver.LIGHT.pixels.show()
                    pix += 1


                await asyncio.sleep(0.1) #.2 = ~5 seconds
            except Exception as e:
                log.error("Bootup_show Exception:", e)
        Event("FX",SOUND={"SoundName":"BOOT_01"} ).send()



        await asyncio.sleep(0.3) #last chance to get an IP
        codeonscreen[1] =  "Boot up complete"
        Event("GUI",LCD={"show_menu":True,"menu_display":codeonscreen}).send()
        await asyncio.sleep(1)

        codeonscreen[4] =  f"IP:{data().ip_address}"
        Event("GUI",LCD={"show_menu":True,"menu_display":codeonscreen}).send()
        await asyncio.sleep(1)


        self.lcd_driver.idle_menu = 0
        self.fx_driver.LIGHT.pixels.fill(color_helper("OFF"))
        self.fx_driver.LIGHT.pixels.show()
        await asyncio.sleep(0.1)
        self.fx_driver.stop()



    def msg_youare(self,**msg_payload):
        """part of get identiy not yet active"""
        log.debug(f"MSG_YOUARE !! {msg_payload}")
        server_sn = msg_payload.get("gun_sn", "")
        if data().gun_sn == server_sn:
            data().gun_id = int(msg_payload.get("gun_id", 0))
            data().gun_sname = msg_payload.get("gun_sname", data().gun_sname)
            log.debug(f"MSG_YOUARE gun_id:{data().gun_id} gun_sname:{data().gun_sname}")
            #self.MQTT.subscribe()

    def mqtt_message(self,**payload):
        """ placeholder for routing for all mqtt target = (int) events. """
        log.debug(f"mqtt_message not yet active {payload}")


    def cleanup(self):
        """part of shutdown"""
        self.active = False
        for key, obj in self.__dict__.items():
            if  hasattr(obj, "cleanup") and callable(getattr(obj, "cleanup")):
                getattr(obj, "cleanup", None)() # Call the cleanup method
                log.debug(f"{key} cleanup done")
