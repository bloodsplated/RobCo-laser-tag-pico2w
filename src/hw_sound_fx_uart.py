"""handles direct IO sound out """
import board,time
import busio
import digitalio
from shared_utils import data,MyLogger
from shared_classes import DriverModule

from time import sleep

log = MyLogger(__name__)

INFO = {
    "module_name": __name__,
    "version": 1.0,
    "Driver": "SOUND",
    "description": """ Adafruit Audio FX Sound Board
    PRODUCT ID: 2133 this sends commands over Uart
    https://learn.adafruit.com/adafruit-audio-fx-sound-board/serial-audio-control
    """
}

# pylint: disable=broad-exception-caught disable=no-member
class SOUND(DriverModule):
    """ handles fx board contoll"""
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **INFO)
        self.module_name = __name__

        self._cur_vol = 204


        #list of all sounds (name , fx name, runtime)
        # install script will generate this list for you
        self.sound_list = [ #sh generated data
        ("BOOT_00","BOOT_00 WAV",2.000635),
        ("BOOT_01","BOOT_01 WAV",0.899864),
        ("EMPTY_00","EMPTY_00WAV",0.257687),
        ("END_00","END_00  WAV",4.903991),
        ("END_01","END_01  WAV",3.136871),
        ("FIRE_00","FIRE_00 WAV",1.253878),
        ("HIT_00","HIT_00  WAV",2.113016),
        ("LOAD_00","LOAD_00 WAV",0.876961),
        ("SPAWN_00","SPAWN_00WAV",1.360862)
        ] #remove last comma

        data().sound_names.clear()
        first_values = [item[0] for item in self.sound_list]
        data().sound_names.extend(first_values)

        #for is_running
        self.done_at = time.monotonic()

        # 1. Initialize UART
        self.uart = busio.UART(tx=board.GP20, rx=board.GP21, baudrate=9600)

        #Set up the pin as an input not reliable for is playing but can show if the board is online
        self.playing_pin = digitalio.DigitalInOut(board.GP22)
        self.playing_pin.direction = digitalio.Direction.INPUT
        self.playing_pin.pull = digitalio.Pull.UP

        if self.playing_pin.value:
            self.active = True
            log.debug(f"Audio FX Sound Board pin.value:{self.playing_pin.value}")




    def cleanup(self):
        """cleanup is called when the driver is stopped or restarted"""
        super().cleanup()
        self.stop()


    def stop(self):
        """ stop sounds send q """
        self.uart.write(bytes("q\n", "utf-8"))

    def is_running(self):
        """ is sounds playing """
        now = time.monotonic()
        return self.done_at > now


    def on_event(self, **payload):
        """just send play hope the files there
        payload:
            "STOP":True to stop curently playing sound
            "SoundName":"FIRE_00" name of sound
        """
        try:
            log.debug(f"on_event: {payload}")
            if payload.get("STOP",False):
                self.stop()

            lookup = payload.get("SoundName",None)
            if lookup is not None:
                if self.is_running():
                    log.debug("cant play next sound yet use STOP=true")
                    return

                matches = [sl for sl in self.sound_list if sl[0] == lookup.upper()]
                sound_trip = matches[0] if matches else None
                if sound_trip is None:
                    log.error(f"Cant find sound: {lookup}")
                    return

                toplay = sound_trip[1]
                duration = sound_trip[2]

                now = time.monotonic()
                self.done_at = now + duration
                log.debug(f"""playing sound:{toplay}:
                vol_muted:{ data().vol_muted}
                now:{now}
                duration:{duration}
                done_at:{self.done_at}""")

                #fire and forget mode if muted we still start the timer.
                if not  data().vol_muted:
                    self.uart.write(bytes(f"P{toplay}\n", "utf-8"))

        except Exception as e:
            log.error("on_event Exception",e)


    def change_vol(self,cmd,mult=6):
        """change volume on the FX board Very SLOW!"""
        for _ in range(0, mult):
            self._send_simple(cmd)
        self._cur_vol = int(self._send_simple(cmd,True))
        return self._cur_vol




    def _send_simple(self, cmd,reply=False):
        """Send uart command and get reply if needed mostly for volume"""

        if reply:
            m = self.uart.read()
            while m is not None:
                m = self.uart.read()


        self.uart.write(bytes(f"{cmd}\n", "utf-8"))
        if reply:
            sleep(0.010)
            try:
                msg = self.uart.readline()
                if not isinstance(msg, bytes):
                    return None
                message = msg.decode("utf-8").strip()
                return message

            except (AttributeError, AssertionError, UnicodeError) as e:
                log.error("_send_simple Exception:", e)


        return None
