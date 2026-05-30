"""" specal effects driver """
from shared_utils import MyLogger
from shared_classes import DriverModule

log = MyLogger(__name__)
INFO = {
    "module_name": __name__,
    "version": 1.0,
    "Driver": "FX",
    "description": """ FX Driver"""
}

# pylint: disable=too-many-instance-attributes disable=invalid-name
class FX(DriverModule):
    """" specal effects driver """
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **INFO)

        self.active = True
        self.fx_is_done = True
        self.playlist =[] #this is {} of effect data
        self.LIGHT = kwargs.get('LIGHT',None)
        self.HAPTIC = kwargs.get('HAPTIC',None)
        self.SOUND = kwargs.get('SOUND',None)

        if None in [self.LIGHT,self.HAPTIC,self.SOUND]:
            raise ValueError("lights,sound,haptic  must not be None")

    def stop(self):
        """stops all active effects immediately"""
        log.debug("stop called")
        self.LIGHT.stop()
        self.SOUND.stop()
        self.HAPTIC.stop()

    def is_fx_running(self):
        """checks FX modules for if they are currently running an effect"""
        return self.LIGHT.is_running() or self.SOUND.is_running() or self.HAPTIC.is_running()


    def on_event(self,**effect):
        """ event handler expected format SOUND={},LIGHT={},HAPTIC={} """
        fxreply = None
        sreply = None
        lreply = None
        hreply = None

        if effect.get("is_fx_running",False):
            return [self.is_fx_running(),
                    self.SOUND.is_running(),
                    self.LIGHT.is_running(),
                    self.HAPTIC.is_running()
                    ]

        if effect.get("STOP",False):
            self.stop()
            fxreply = "STOPPED ALL FX"
            return [fxreply,sreply,lreply,hreply]


        sound = effect.get("SOUND",{})
        if sound is not None and self.SOUND.is_active():
            sreply = self.SOUND.on_event(**sound)

        light = effect.get("LIGHT",{})
        if light is not None and self.LIGHT.is_active():
            lreply = self.LIGHT.on_event(**light)

        haptic = effect.get("HAPTIC",{})
        if haptic is not None and self.HAPTIC.is_active():
            hreply = self.HAPTIC.on_event(**haptic)

        return [fxreply,sreply,lreply,hreply]
