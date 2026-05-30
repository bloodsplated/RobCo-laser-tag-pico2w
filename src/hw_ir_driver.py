"""IR driver"""
import asyncio,time,board,pulseio,adafruit_irremote

from shared_classes import DriverModule
from shared_utils import Event,data,MyLogger

log = MyLogger(__name__)

INFO = {
    "module_name": __name__,
    "version": 1.0,
    "Driver": "IR",
    "description": """ IR Driver"""
}




# pylint: disable=broad-exception-caught disable=no-member
class IR(DriverModule):
    """IR driver"""
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **INFO)

        ir_out0 = board.GP10 #beam
        ri_out1 = board.GP11 #blast

        ir_in0 = board.GP12 #gun front
        #ir_in1 = board.GP13 #vest not used yet

        self.lastvalid = (0, 0, 0, '', 0)

        # Create a 'PulseOut' to send infrared signals on the IR transmitter @ 38KHz
        self.pulseout0 = pulseio.PulseOut(ir_out0, frequency=38000, duty_cycle=2**15)
        self.pulseout1 = pulseio.PulseOut(ri_out1, frequency=38000, duty_cycle=2**15)


        # Create an encoder that will take numbers and turn them into NEC IR pulses
        self.encoder = adafruit_irremote.GenericTransmit(header=[9000, 4500],
                                            one=[560, 1700],
                                            zero=[560, 560],
                                            trail=0)

        self.pulsein0 = pulseio.PulseIn(ir_in0, maxlen=120, idle_state=True)
        self.decoder0 = adafruit_irremote.NonblockingGenericDecode(self.pulsein0)


        #vest not used yet
       # pulsein1 = pulseio.PulseIn(ir_in1, maxlen=120, idle_state=True)
       # self.decoder1 = adafruit_irremote.NonblockingGenericDecode(pulsein1)
        self.active = True


    async def async_start(self):
        """ start up acync loop"""
        try:

            while self.active:
                data().async_watcher["IR_async_decoderWatch"] = time.monotonic()
                for message in self.decoder0.read():
                    gun_front = await self.ir_decode(message,"gun")
                    if gun_front is  None:
                        #clear out bad data
                        self.pulsein0.clear()
                        self.pulsein0.resume()
                    else:
                        payload = {
                            "PlayerID" : gun_front[0],
                            "game_team_id" : gun_front[1],
                            "ShotID" : gun_front[2],
                            "Receiver" : gun_front[3]
                        }
                        log.debug(f"front = {payload}")
                        Event("GAME.IRTAG",payload).send()
                    await asyncio.sleep(0)
                await asyncio.sleep(.005)

        except asyncio.CancelledError:
            log.debug("async_decoderWatch task cancelled.")
        except Exception as e:
            log.error("async_decoderWatchtask Exception:", e)
        finally:
            log.debug("async_start task end")


    async def ir_decode(self,message,location):
        """decode tags from ir throws TypeError if invalid """
        try:
            if not isinstance(message, adafruit_irremote.IRMessage):
                return None

            received_code = message.code
            log.debug(f"----- received_code:{received_code} ----- ")


            if len(received_code) < 5:
                raise ValueError(f"received_code tooshort :{len(message.pulses)} ")

            first3b = received_code[1:4]
            check = sum(first3b)

            if check != received_code[4]:
                raise ValueError(f"Checksum failed {check} != {received_code[4]}")

            conveted_format = received_code[1:4] + (location,time.monotonic())
            timediff = conveted_format[4] - self.lastvalid[4]
            self.lastvalid = conveted_format

            if timediff < .5 and conveted_format[0] == self.lastvalid[0]:
                raise ValueError(f"validCode: {conveted_format} but Repeat timediff = { timediff }")

            return conveted_format
        except ValueError as e:
            log.debug(f"invalid IR code ValueError: {e}")
        return None



    def shoot_lasers(self, **Shotinfo):
        """ to be retired  """
        return self.on_event(**Shotinfo)

    def on_event(self, **payload):
        """REQUIRED and must be implemented for all drivers to handle events """

        player_id = payload.get("player_id",None)
        team_id = payload.get("team_id",None)
        shot_id = payload.get("shot_id",None)
        emitter_id = payload.get("emitter_id",0)
        pulse_out_x = self.pulseout0
        if emitter_id == 1:
            pulse_out_x = self.pulseout1

        try:

            if not (isinstance(player_id, int) and 0 < player_id <= 145) :
                return f"player_id:{player_id} out of range  "

            if not (isinstance(team_id, int) and 0 <= team_id <= 10) :
                return f"team_id:{team_id} out of range  "

            if not (isinstance(shot_id, int) and 0 <= shot_id <= 100 ):
                return f"shot_id:{shot_id} out of range  "

            byte1 = player_id
            byte2 = team_id
            byte3 = shot_id
            checksum = byte1 + byte2 + byte3

            if checksum > 255 :
                return f"checksum:{checksum} out of range  "

            value = [255, byte1, byte2, byte3, checksum, 0]
            self.encoder.transmit(pulse_out_x, value, repeat =0)

            return f"Ima firin' mah lazar! {value})"
        except Exception as e:
            log.error("Exception:", e)
            return f"error {e}"
