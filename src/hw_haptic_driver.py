""" HAPTIC Driver"""
import traceback,time,board
from shared_utils import MyLogger

import adafruit_drv2605
from shared_classes import DriverModule

I2C = board.STEMMA_I2C() # pylint: disable=no-member

log = MyLogger(__name__)
INFO = {
    "module_name": __name__,
    "version": 1.0,
    "Driver": "HAPTIC",
    "description": """ HAPTIC Driver"""
}


class HAPTIC(DriverModule):
    """ HAPTIC Driver"""
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **INFO)

        self.active = True
        self.haptic = adafruit_drv2605.DRV2605(I2C)
        self.runtime = 0

    def cleanup(self):
        """cleanup is called when the driver is stopped or restarted"""
        super().cleanup()
        self.stop()

    def stop(self):
        """stops all active effects immediately"""
        self.haptic.stop()


    def is_running(self):
        """checks if any haptic FX is currently playing"""
        return time.monotonic() < self.runtime

    def on_event(self, **nextfx):
        """event handler ontents of HAPTIC:{} from FX event"""
        try:
            sequencelist = nextfx.get('List', [])

            if not isinstance(sequencelist, list):
                raise ValueError("fxlist must be a list.")
            if len(sequencelist) > 8:
                raise ValueError("fxlist cannot have more than 8 items.")

            for x, fx in enumerate(sequencelist):
                if isinstance(fx, int):
                    self.haptic.sequence[x] = adafruit_drv2605.Effect(fx)
                elif isinstance(fx, float):
                    self.haptic.sequence[x] = adafruit_drv2605.Pause(fx)
                else:
                    raise ValueError(f"Invalid type {type(fx)} at position {x} in List.")


            if len(sequencelist) == 0:
                return "No haptic effect to play."

            self.runtime = time.monotonic() + nextfx.get('runtime',  0.5)
            self.haptic.play()  # play the effect
            return "Haptic effect is playing."



        except Exception as e:
            traceback.print_exception(e)
            return f"Error processing haptic event: {e}"
