#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ecran d'attente
"""
# import
import tkinter as tk
from labpyproject.apps.labpyrinthe.gui.skinBase.screen_wait_base import ScreenWaitBase

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ScreenWait"]
# classes
class ScreenWait(tk.Frame, ScreenWaitBase):
    """
    Ecran d'attente : implémentation Tkinter
    """

    # méthodes
    def __init__(self, parent, skin, initialstate):
        """
        Constructeur
        """
        # surcharge de ScreenWaitBase :
        ScreenWaitBase.STATE_LOADING_RSC = "visuel_loading"
        ScreenWaitBase.STATE_CREATING_RSC = "visuel_partie"
        ScreenWaitBase.STATE_RESIZE_RSC = "visuel_resize"
        # générique :
        tk.Frame.__init__(
            self, parent, {"bg": "#FFFFFF", "borderwidth": 0, "highlightthickness": 0}
        )
        self._image = None
        ScreenWaitBase.__init__(self, skin, initialstate)

    def draw_interface(self):
        """
        Création de l'interface
        """
        self._image = tk.Label(bg="#FFFFFF", bd=0, highlightthickness=0)

    def show_image(self, img):
        """
        Affiche l'image img
        """
        if self._image != None:
            if img != None:
                self._image.configure(image=img)
                self._image.place(relx=0.5, rely=0.5, anchor="center")
            else:
                self._image.place_forget()
