"""This is run first by the Pico """
import sys,asyncio
import microcontroller,storage,supervisor
from shared_utils import get_hw,data,setglobals,MyLogger

supervisor.runtime.autoreload = False



data().hw_ver = "1.0"

if data("DEBUG",0) != 0:
    data().debug = True
    print("DEBUG on")

if data("MUTE",0) != 0:
    data().vol_muted = True
    print("Sound system Muted")

log = MyLogger(__name__)
log.debug("debug logging test hw_ver:", data().hw_ver)
log.error("error logging test", Exception("test exception"))

print(f"""
_ ________,
>`(==(----' -= RobCo Pico tag v:{data().hw_ver} =-
(__/~~`
""")


import shared_hardware
import shared_gamelogic

setglobals(shared_hardware.Hardware(),shared_gamelogic.GameLoader())

exit_command = ""
try:
    if len(data().gun_sn) < 3:
        raise ValueError(f"must have a valid Serial Number SN:'{data().gun_sn}'")
    exit_command = asyncio.run(get_hw().async_start_all())
except KeyboardInterrupt:
    log.debug("KeyboardInterrupt Exiting gracefully.")
except Exception as e: # pylint: disable=broad-except
    log.error("[ERROR] in code.py", e)


finally:
    log.debug("cleaning up all hardware and exiting")
    get_hw().cleanup()

log.debug(f"exit_command = {exit_command}")

#only used for debug
if exit_command == "erase_filesystem":
    storage.erase_filesystem()
    microcontroller.reset()

if exit_command == "hardware_reboot":
    microcontroller.reset()

sys.exit(0)
