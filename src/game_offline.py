""" offline game with FFA rules """
from shared_classes import BaseGameRules

INFO = {
    "module_name": __name__,
    "version": 1.0,
    "game_name": "offline",
    "description": """ offline game with FFA rules """
}


class Rules(BaseGameRules):
    """ offline game with FFA rules """
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **INFO)


    def game_loaded(self,**lastgamedata):
        """caled by gameloader will provide info from last name used for lobby score board info"""
        super().game_loaded(**lastgamedata)
        #copy lobby team and shot for debug
        self.game_team_id = lastgamedata.get("game_team_id",self.game_team_id)
        self.game_shot_type = lastgamedata.get("game_shot_type",self.game_shot_type)
        self.game_start()
