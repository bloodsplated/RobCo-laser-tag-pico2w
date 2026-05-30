"""input handler """
import asyncio,time,board

from shared_classes import DriverModule
from shared_utils import Event,data,MyLogger


from async_button import Button, MultiButton # type: ignore[import-untyped]
import rotaryio

log = MyLogger(__name__)
INFO = {
    "module_name": __name__,
    "version": 1.0,
    "Driver": "INPUT",
    "description": """ INPUT Driver"""
}

# pylint: disable=no-member
class INPUT(DriverModule):
    """input handler """
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **INFO)
        self.module_name = __name__
        self.active = True

        self.encoder = rotaryio.IncrementalEncoder(board.GP8,board.GP7 )
        self.last_position = 0

    def on_event(self, **payload):
        """REQUIRED and must be implemented for all drivers to handle events """


    def send_event(self, **kwargs):
        """sends buttton events"""
        Event("GAME.INPUT",kwargs).send()
        Event("HW",kwargs).send()


    async def click_watcher(self,multibutton: MultiButton):
        """watches for button clicks"""
        click_names = {
            Button.SINGLE: "SINGLE",
            Button.DOUBLE: "DOUBLE",
            Button.TRIPLE: "TRIPLE",
            Button.LONG: "LONG",
        }

        try:
            while self.active: #waits for event
                data().async_watcher["IN_click_watcher"] = time.monotonic()
                button_name, click = await multibutton.wait(
                    TRIG=Button.ANY_CLICK,
                    ROTARY=Button.ANY_CLICK,
                    )
                self.send_event(name=button_name, value=f"{click_names[click]}")
                await asyncio.sleep(0)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error("async Worker task Exception:", e)
        finally:
            log.debug("async Worker task end")


    async def rotate_watcher(self):
        """watches for encoder changes """
        try:
            while self.active:
                data().async_watcher["IN_rotate_watcher"] = time.monotonic()
                position = self.encoder.position
                if position != self.last_position:
                    if position > self.last_position:
                        change = "INC"
                    else:
                        change = "DNC"

                    self.send_event(name="ROTARY", position=position,value=change)
                self.last_position = position
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error("async Worker task Exception:", e)
        finally:
            log.debug("async Worker task end")




    async def async_start(self):
        await super().async_start() #sets logger name
        try:
            trigger = Button(
            board.GP6,
            value_when_pressed=False,
            double_click_enable=False,
            triple_click_enable=False,
            long_click_enable=True,   )

            menu_b = Button(
            board.GP9,
            value_when_pressed=False,
            double_click_enable=False,
            triple_click_enable=False,
            long_click_enable=True,   )


            multibutton = MultiButton(TRIG=trigger,ROTARY=menu_b)
            await asyncio.gather(self.click_watcher(multibutton), self.rotate_watcher())


        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error("async Worker task Exception:", e)
        finally:
            log.debug("async Worker task end")
