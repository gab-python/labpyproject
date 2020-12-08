#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Menu (choix de partie) : implémentation Tkinter
"""
# imports
import tkinter as tk
import labpyproject.apps.labpyrinthe.gui.skinTkinter.uitools as uit
from labpyproject.apps.labpyrinthe.gui.skinBase.zone_menu_base import ZoneMenuBase

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ZoneMenu"]
# classe
class ZoneMenu(tk.Frame, ZoneMenuBase):
    """
    Accueil du jeu : version simplifiée (sans boutons)
    """

    # statique :
    COLOR_BG = "#FFFFFF" #: couleur du fond
    # méthodes :
    def __init__(self, parent, Mngr, skin):
        """
        Constructeur
        """
        # générique :
        tk.Frame.__init__(
            self,
            parent,
            {
                "bg": "#FFFFFF",
                "borderwidth": 0,
                "highlightthickness": 0,
                "padx": 0,
                "pady": 0,
            },
        )
        self.rowconfigure(0, minsize=400, weight=1)
        self.columnconfigure(0, minsize=900, weight=1)
        ZoneMenuBase.__init__(self, Mngr, skin)

    def re_initialise(self):
        """
        Ré initialise l'objet
        """
        pass

    #-----> Publication
    def draw_interface(self):
        """
        Création de l'interface. 
        """
        # frame contenu
        self._frame_content = tk.Frame(
            self,
            {
                "bg": "#FFFFFF",
                "borderwidth": 0,
                "highlightthickness": 0,
                "width": 900,
                "height": 400,
            },
        )
        self._frame_content.grid(column=0, row=0, padx=0, pady=0)
        self._frame_content.columnconfigure(0, weight=2)
        self._frame_content.columnconfigure(1, weight=1)
        # visuel :
        self._canvas_visuel = tk.Canvas(
            self._frame_content,
            width=600,
            height=400,
            bg="#FFFFFF",
            bd=0,
            highlightthickness=0,
        )
        self._canvas_visuel.grid(column=0, row=0, padx=0, pady=0)
        visuel = self.skin.get_image("accueil", "visuel", size=(600, 374))
        self.visuel = self._canvas_visuel.create_image(
            300, 200, state="disabled", image=visuel
        )
        # consignes :
        self._canvas_consignes = tk.Canvas(
            self._frame_content,
            width=300,
            height=400,
            bg="#FFFFFF",
            bd=0,
            highlightthickness=0,
        )
        self._canvas_consignes.grid(column=1, row=0, padx=0, pady=0)
        consignes = self.skin.get_image("accueil", "consignes", size=(300, 257))
        self.consignes = self._canvas_consignes.create_image(
            150, 200, state="disabled", image=consignes
        )
