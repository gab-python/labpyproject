#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sous écran partie : logique applicative.
Implémentation générique de AbstractZonePartie.
"""
# imports
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractZonePartie
from labpyproject.apps.labpyrinthe.bus.game_manager import GameManager

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ZonePartieBase"]
# classes
class ZonePartieBase(AbstractZonePartie):
    """
    Ecran partie (carte + infos robots)
    """

    # états
    STATE_CREATING = "STATE_CREATING"  #: marqueur d'état
    STATE_RESIZE = "STATE_RESIZE" #: marqueur d'état
    STATE_GAME = "STATE_GAME" #: marqueur d'état
    # méthodes
    def __init__(self, Mngr, skin):
        """
        Constructeur
        """
        # Manager : GUI
        self.Mngr = Mngr
        # type d'app :
        self.type_app = None
        # ref au skin :
        self.skin = skin
        # création de l'interface :
        self.zone_carte = None  # AbstractZoneCarte
        self.zone_bots = None  # AbstractZoneBots
        self.partie_state = None
        self.current_state = None
        self.draw_interface()

    def re_initialise(self):
        """
        Ré initialise l'objet
        """
        # carte :
        self.zone_carte.re_initialise()
        # infos bots :
        self.zone_bots.re_initialise()

    def register_APPType(self, app_type):
        """
        Défini le type d'appli associé.
        """
        self.type_app = app_type
        if self.zone_bots:
            self.zone_bots.register_APPType(app_type)

    def draw_interface(self):
        """
        Création de l'interface
        """
        # à subclasser

    def show_carte_txt_in_preload(self, txt):
        """
        Affichage de la carte txt dans l'écran de preload de partie
        """
        # à subclasser
        pass

    def register_partie_state(self, state):
        """
        Enregistre l'état actuel de la partie
        """
        self.partie_state = state
        if self.zone_bots != None:
            self.zone_bots.register_partie_state(state)

    def set_state(self, state):
        """
        Changement d'état : resize, création partie, jeu
        """
        self.current_state = state
        self.apply_current_state()

    def apply_current_state(self):
        """
        Applique l'état courant
        """
        # à subclasser

    def on_view_changed(self, visible):
        """
        Appelée par la GUI avant un changement d'affichage
        visible : boolean indiquant l'état prochain d'affichage
        """
        # à subclasser

    def on_carte_published(self):
        """
        Callback de fin de publication de la carte
        """
        # Configuration :
        self.set_state(ZonePartieBase.STATE_GAME)

    def on_resize_start(self):
        """
        Appelée par la carte au début de son processus de resize. Permet d'afficher 
        un écran d'attente.
        """
        self.set_state(ZonePartieBase.STATE_RESIZE)

    def on_resize_end(self):
        """
        Appelée par la carte à la fin du processus de resize. Masquage de l'éventuel 
        écran d'attente.
        """
        oldstate = None
        if self.partie_state == GameManager.PARTIE_CHOSEN:
            oldstate = ZonePartieBase.STATE_CREATING
        elif self.partie_state == GameManager.PARTIE_CREATED:
            oldstate = ZonePartieBase.STATE_GAME
        elif self.partie_state == GameManager.PARTIE_STARTED:
            oldstate = ZonePartieBase.STATE_GAME
        self.set_state(oldstate)
