#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sous écran Menu : logique applicative.
Implémentation générique de AbstractZoneMenu.
"""
# imports
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractZoneMenu
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractSwitch

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ZoneMenuBase"]
# classe :
class ZoneMenuBase(AbstractZoneMenu):
    """
    Sous écran menu
    """

    def __init__(self, Mngr, skin):
        """
        Constructeur
        """
        # Manager : GUI
        self.Mngr = Mngr
        # ref au skin :
        self.skin = skin
        # choix :
        self._selected_level = None
        self._selected_mode = None
        # création de l'interface :
        self.btn_niveaux = dict()  # crls niveaux (clef = n° niveau)
        self.btn_modes = dict()  # (clefs partie, demo)
        self.draw_interface()

    def re_initialise(self):
        """
        Ré initialise l'objet
        """
        # choix :
        self._selected_level = None
        self._selected_mode = None
        # désélections :
        listniv = [
            self.btn_niveaux["1"],
            self.btn_niveaux["2"],
            self.btn_niveaux["3"],
        ]
        self.handle_change_states(listniv, AbstractSwitch.UNSELECTED)
        list_modes = [self.btn_modes["partie"], self.btn_modes["demo"]]
        self.handle_change_states(list_modes, AbstractSwitch.UNSELECTED)

    #-----> Publication
    def draw_interface(self):
        """
        Création de l'interface
        Prend en charge l'enregistrement des ctrl niveau, mode et des items de description
        """
        # à subclasser

    #-----> Etats
    def handle_change_states(self, changelist, newstate):
        """
        Applique le changement d'état à la liste
        """
        for elt in changelist:
            if isinstance(elt, AbstractSwitch):
                elt.set_state(newstate)
            elif isinstance(elt, str):
                d = self._ctrls[elt]
                for c in d.keys():
                    c.set_state(newstate)

    #-----> Commandes
    def control_callback(self, ctrl, state):
        """
        Méthode appelée lorsqu'un contrôle est cliqué
        
        state :
        
        * AbstractSwitch.OVER
        * AbstractSwitch.PRESSED
        * AbstractSwitch.SELECTED
        * AbstractSwitch.UNSELECTED
        
        """
        if not isinstance(ctrl, AbstractSwitch):
            return
        prevstate = ctrl.get_state()
        # vars :
        deslectlist = list()
        selectlist = list()
        desactivelist = list()
        activelist = list()
        # niveau :
        listniv = [
            self.btn_niveaux["1"],
            self.btn_niveaux["2"],
            self.btn_niveaux["3"],
        ]
        if ctrl in listniv:
            indice = None
            for k, v in self.btn_niveaux.items():
                if ctrl == v:
                    indice = k
                    break
            # sélection / désélection :
            if state == AbstractSwitch.PRESSED:
                deslectlist = listniv
                if prevstate == AbstractSwitch.UNSELECTED:
                    self._selected_level = indice
                    selectlist.append(ctrl)
                elif prevstate == AbstractSwitch.SELECTED:
                    self._selected_level = None
        # Partie / démo :
        list_modes = [self.btn_modes["partie"], self.btn_modes["demo"]]
        if ctrl in list_modes:
            mode = None
            for k, v in self.btn_modes.items():
                if ctrl == v:
                    mode = k[0]
                    break
            # sélection / désélection :
            if state == AbstractSwitch.PRESSED:
                deslectlist = list_modes
                if prevstate == AbstractSwitch.UNSELECTED:
                    self._selected_mode = mode
                    selectlist.append(ctrl)
                elif prevstate == AbstractSwitch.SELECTED:
                    self._selected_mode = None
        # Gestion des états :
        self.handle_change_states(deslectlist, AbstractSwitch.UNSELECTED)
        self.handle_change_states(desactivelist, AbstractSwitch.DISABLED)
        self.handle_change_states(activelist, AbstractSwitch.ENABLED)
        self.handle_change_states(selectlist, AbstractSwitch.SELECTED)
        # Validation :
        if state == AbstractSwitch.PRESSED:
            if self._selected_level != None and self._selected_mode != None:
                # passage de la cmd à la GUI
                cmd = str(self._selected_level) + str(self._selected_mode)
                self.Mngr.on_choice_made(cmd)
        # post traitement :
        self.post_control_callback()

    def post_control_callback(self):
        """
        Post traitement éventuel après gestion des callbacks de boutons
        """
        # à subclasser
