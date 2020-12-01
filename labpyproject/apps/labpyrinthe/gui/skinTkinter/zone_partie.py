#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sous écran partie : implémentation Tkinter
"""
# imports
import tkinter as tk
from labpyproject.apps.labpyrinthe.gui.skinBase.zone_partie_base import ZonePartieBase
from labpyproject.apps.labpyrinthe.gui.skinTkinter.zone_bots import ZoneBots
from labpyproject.apps.labpyrinthe.gui.skinTkinter.zone_carte import ZoneCarte
from labpyproject.apps.labpyrinthe.gui.skinTkinter.screen_wait import ScreenWait

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ZonePartie"]
# classe
class ZonePartie(tk.Frame, ZonePartieBase):
    """
    Ecran partie (carte + infos robots)
    """

    # méthodes
    def __init__(self, parent, Mngr, skin):
        """
        Constructeur
        """
        # spécifique :
        tk.Frame.__init__(
            self, parent, {"bg": "#FFFFFF", "borderwidth": 0, "highlightthickness": 0}
        )
        # générique :
        ZonePartieBase.__init__(self, Mngr, skin)

    def draw_interface(self):
        """
        Création de l'interface
        """
        # Conteneur :
        self.frame_content = tk.Frame(
            self, {"bg": "#FFFFFF", "borderwidth": 0, "highlightthickness": 0}
        )
        self.frame_content.columnconfigure(0, minsize=479, weight=4)
        self.frame_content.rowconfigure(0, minsize=400, weight=2)
        self.frame_content.columnconfigure(1, minsize=421, weight=1)
        self.frame_content.grid_propagate(0)
        # Carte :
        self.zone_carte = ZoneCarte(self.frame_content, self, self.skin)
        self.zone_carte.grid(column=0, row=0, padx=10, pady=10, sticky="nesw")
        # Infos bots :
        self.zone_bots = ZoneBots(self.frame_content, self, self.skin)
        self.zone_bots.grid(column=1, row=0, padx=0, pady=0, ipadx=5, ipady=5)
        # Ecran d'attente :
        self.waiting_screen = ScreenWait(self, self.skin, None)

    def apply_current_state(self):
        """
        Applique l'état courant
        """
        state = None
        if self.current_state == ZonePartieBase.STATE_CREATING:
            state = ScreenWait.STATE_CREATING
        elif self.current_state == ZonePartieBase.STATE_RESIZE:
            state = ScreenWait.STATE_RESIZE
        self.waiting_screen.set_state(state)
        if state != None:
            self.waiting_screen.place(x=0, y=0, relwidth=1, relheight=1)
        else:
            self.waiting_screen.place_forget()
        # Update affichage :
        self.update_idletasks()

    def on_view_changed(self, visible):
        """
        Appelée par la GUI avant un changement d'affichage. 
        visible : boolean indiquant l'état prochain d'affichage
        """
        if not visible:
            self.frame_content.place_forget()
            self.waiting_screen.place_forget()
        else:
            self.frame_content.place(x=0, y=0, relwidth=1, relheight=1)
            if self.current_state in [
                ZonePartieBase.STATE_CREATING,
                ZonePartieBase.STATE_RESIZE,
            ]:
                self.waiting_screen.place(x=0, y=0, relwidth=1, relheight=1)
