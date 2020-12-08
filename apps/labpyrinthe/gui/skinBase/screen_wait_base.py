#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ecran d'attente (minimaliste) : logique applicative.
Implémentation générique de AbstractScreenWait.
"""
# imports :
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractScreenWait

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ScreenWaitBase"]
# classe :
class ScreenWaitBase(AbstractScreenWait):
    """
    Ecran d'attente minimaliste
    """

    # états:
    STATE_NEUTRAL = "STATE_NEUTRAL" #: marqueur d'état
    STATE_LOADING = "STATE_LOADING" #: marqueur d'état
    STATE_CREATING = "STATE_CREATING" #: marqueur d'état
    STATE_RESIZE = "STATE_RESIZE" #: marqueur d'état
    # ressources associées
    STATE_NEUTRAL_RSC = "neutre" #: ressource associée à un état
    STATE_LOADING_RSC = "txt_loading" #: ressource associée à un état
    STATE_CREATING_RSC = "txt_partie" #: ressource associée à un état
    STATE_RESIZE_RSC = "txt_resize" #: ressource associée à un état
    # méthodes
    def __init__(self, skin, initialstate):
        """
        Constructeur
        """
        # ref au skin :
        self.skin = skin
        # identification de l'image associée :
        self.cat_img = "screens"
        self.name_img = None
        # état initial :
        self._initialstate = initialstate
        # graphisme :
        self.draw_interface()
        self.set_state(self._initialstate)

    def get_initial_state(self):
        """
        Retourne l'état initial : permet de distinguer l'écran de chargement 
        initial de l'écran de chargement de partie.
        """
        return self._initialstate

    def draw_interface(self):
        """
        Création de l'interface
        """
        # à subclasser

    def set_state(self, statename):
        """
        Modification du visuel
        """
        if statename == ScreenWaitBase.STATE_LOADING:
            self.name_img = ScreenWaitBase.STATE_LOADING_RSC
        elif statename == ScreenWaitBase.STATE_RESIZE:
            self.name_img = ScreenWaitBase.STATE_RESIZE_RSC
        elif statename == ScreenWaitBase.STATE_CREATING:
            self.name_img = ScreenWaitBase.STATE_CREATING_RSC
        elif statename == ScreenWaitBase.STATE_NEUTRAL:
            self.name_img = ScreenWaitBase.STATE_NEUTRAL_RSC
        else:
            self.name_img = None
        img = self.skin.get_image(self.cat_img, self.name_img)
        self.show_image(img)

    def show_image(self, img):
        """
        Affiche l'image img
        """
        # à subclasser
