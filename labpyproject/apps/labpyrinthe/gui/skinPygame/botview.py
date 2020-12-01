#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vue d'un robot utilisée dans la zone_bots et la carte
"""
# imports
import labpyproject.apps.labpyrinthe.gui.skinPygame.uitools as uit
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractSwitch
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseRobot

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["BotView"]
# classe
class BotView(uit.WButton):
    """
    Vue de la case robot
    """

    def __init__(self, mngr, skin, case, size=(80, 80), **kwargs):
        """
        Constructeur
        """
        # Manager : ZoneCarte ou ZoneBots
        self.mngr = mngr
        # ref au skin :
        self.skin = skin
        # case robot associée :
        self.case = case
        # taille de l'image :
        self.size = size
        # état par défaut :
        self.default_state = AbstractSwitch.UNSELECTED
        # case actuellement highlightée (/ affichage danger)
        self.current_highbotcase = None
        # sources :
        self.sources_dict = None
        # générique :
        name = None
        if "name" in kwargs.keys():
            name = kwargs["name"]
            del kwargs["name"]
        uit.WButton.__init__(self, mngr, skin, name, switch=True, fixed=False, **kwargs)

    def _init_images(self):
        """
        Crée le dict statesdict attendu par le constructeur de WButton
        """
        statesdict = dict()
        statesdict[AbstractSwitch.UNSELECTED] = None
        statesdict[AbstractSwitch.OVER] = None
        statesdict[AbstractSwitch.PRESSED] = None
        statesdict[AbstractSwitch.SELECTED] = None
        statesdict[AbstractSwitch.DISABLED] = None
        if self.case != None:
            states_surf = self.skin.get_image_for_BotItem(self.case, self.size)
            self.sources_dict = dict()
            self.sources_dict["normal"] = states_surf[0]
            self.sources_dict["over"] = states_surf[1]
            self.sources_dict["select"] = states_surf[2]
            self.sources_dict["dead"] = states_surf[3]
            if self.case.behavior == CaseRobot.BEHAVIOR_HUMAN:
                self.sources_dict["disconnected"] = states_surf[4]
            else:
                self.sources_dict["disconnected"] = None
            statesdict[AbstractSwitch.UNSELECTED] = self.sources_dict["normal"]
            statesdict[AbstractSwitch.OVER] = self.sources_dict["over"]
            statesdict[AbstractSwitch.PRESSED] = self.sources_dict["select"]
            statesdict[AbstractSwitch.SELECTED] = self.sources_dict["select"]
            statesdict[AbstractSwitch.DISABLED] = self.sources_dict["dead"]
        return statesdict

    def change_case(self, case):
        """
        Ré initialise la case associée.
        """
        if case != self.case:
            self.case = case
            # debug
            if case != None:
                self.name = case.uid
            self._init_images()
            self.set_state(AbstractSwitch.UNSELECTED)

    def highlight(self, dohigh):
        """
        Marque le switch comme sélectionné ou non
        
        Args:
            dohigh : bool
        """
        state = None
        if self.case.alive:
            current_state = self.get_state()
            if dohigh:
                state = AbstractSwitch.SELECTED
            else:
                if current_state == AbstractSwitch.SELECTED:
                    state = AbstractSwitch.UNSELECTED
                else:
                    state = current_state
        else:
            state = AbstractSwitch.DISABLED
        self.set_state(state)

    def set_current_highbotcase(self, case):
        """
        Met à jour la ref au joueur dont c'est le tour.
        """
        self.current_highbotcase = case

    def get_current_highbotcase(self):
        """
        Met à jour la ref au joueur dont c'est le tour.
        """
        return self.current_highbotcase
