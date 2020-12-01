#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sous écran partie : implémentation pygame
"""
# imports
import labpyproject.core.pygame.widgets as wgt
import labpyproject.apps.labpyrinthe.gui.skinPygame.uitools as uit
from labpyproject.apps.labpyrinthe.gui.skinBase.zone_partie_base import ZonePartieBase
from labpyproject.apps.labpyrinthe.gui.skinPygame.zone_bots import ZoneBots
from labpyproject.apps.labpyrinthe.gui.skinPygame.zone_carte import ZoneCarte
from labpyproject.apps.labpyrinthe.gui.skinPygame.screen_wait import ScreenWait
from labpyproject.apps.labpyrinthe.gui.skinBase.screen_wait_base import ScreenWaitBase

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ZonePartie"]
# classes :
class ZonePartie(wgt.HStack, ZonePartieBase):
    """
    Ecran partie (carte + infos robots)
    """

    # méthodes
    def __init__(self, Mngr, skin, **kwargs):
        """
        Constructeur
        """
        # spécifique :
        wgt.HStack.__init__(self, width="100%", height="100%", **kwargs)
        # générique :
        ZonePartieBase.__init__(self, Mngr, skin)

    def draw_interface(self):
        """
        Création de l'interface
        """
        # Zone carte :
        self.zone_carte = ZoneCarte(
            self, self.skin, flex=1, height="100%", name="zonecarte",
        )
        self.add_item(self.zone_carte)
        # colonne droite :
        self.right_column = wgt.VStack(
            width="35%", minwidth=355, height="100%", name="partie_right"
        )
        self.add_item(self.right_column)
        # Infos bots :
        self.zone_bots = ZoneBots(
            self, self.skin, width="100%", height="100%", flex=1, name="zonebots"
        )
        self.right_column.add_item(self.zone_bots)
        # spacers :
        self.spacer_1 = uit.Spacer(width="100%", height=115)  # zone commande
        self.right_column.add_item(self.spacer_1)
        self.spacer_2 = uit.Spacer(
            width="100%", height="20%", minheight=150
        )  # zone info
        self.right_column.add_item(self.spacer_2)
        # Ecran d'attente
        self.waiting_screen = ScreenWait(
            self,
            self.skin,
            ScreenWaitBase.STATE_CREATING,
            position="absolute",
            local_layer=1,
            name="partie",
            show_carte=True,
        )
        self.add_item(self.waiting_screen)

    def show_carte_txt_in_preload(self, txt):
        """
        Affichage de la carte txt dans l'écran de preload de partie
        """
        self.waiting_screen.show_txt_carte(txt)

    def apply_current_state(self):
        """
        Applique l'état courant
        """
        state = None
        # écran de chatgement :
        if self.current_state == ZonePartieBase.STATE_CREATING:
            state = ScreenWaitBase.STATE_CREATING
        elif self.current_state == ZonePartieBase.STATE_RESIZE:
            state = ScreenWaitBase.STATE_RESIZE
        self.waiting_screen.set_state(state)
        if state != None:
            self.waiting_screen.left = 0
            self.waiting_screen.show_preload(True)
        else:
            self.waiting_screen.left = "100%"
            self.waiting_screen.show_preload(False)

    def on_view_changed(self, visible):
        """
        Appelée par la GUI avant un changement d'affichage
        
        Args:
            visible : boolean indiquant l'état prochain d'affichage
        """
        if not visible:
            self.visible = False
        else:
            self.visible = True
            if self.current_state in [
                ZonePartieBase.STATE_CREATING,
                ZonePartieBase.STATE_RESIZE,
            ]:
                self.waiting_screen.visible = True

    #-----> Interface entre ZoneCarte et ZoneBots
    def set_bot_state(self, case, state, caller):
        """
        Synchro des roll over/out sur les bots entre les deux zone
        
        Args:
            * case : case robot
            * state : AbstractSwitch.OVER ou AbstractSwitch.UNSELECTED
            * caller : self.zone_carte ou self.zone_bots
        
        """
        # synchro :
        self.zone_bots.handle_bot_state(case, state, caller)
        self.zone_carte.handle_bot_state(case, state, caller)
