#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Header simple
"""
# import
import math
import tkinter as tk

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["Header"]
# classe
class Header(tk.Canvas):
    """
    Entête du jeu
    """

    def __init__(self, parent, skin):
        """
        Constructeur
        """
        # Initialisation générique :
        tk.Canvas.__init__(
            self, parent, {"bg": "#FFFFFF", "borderwidth": 0, "highlightthickness": 0}
        )
        self.skin = skin
        # Graphisme :
        self._bg_graph = self.create_image(0, 0, anchor="nw", state="hidden")
        # resize :
        self.width = self.height = None
        self._is_resized = False
        self.bind("<Configure>", self.on_resize)

    def on_resize(self, event):
        """
        Gestion de l'image de fond
        """
        if (event.width, event.height) != (self.width, self.height):
            self.width = self.winfo_width()
            self.height = self.winfo_height()
            # dim graph :
            wg, hg = self.skin.get_source_size("screens", "entete")
            ratio = self.width / wg
            wr, hr, = math.ceil(self.width), math.ceil(hg * ratio)
            imgscreen = self.skin.get_image("screens", "entete_light", size=(wr, hr))
            self.itemconfig(self._bg_graph, image=imgscreen)
            self.itemconfig(self._bg_graph, state="disabled")
            self._is_resized = True
            self["height"] = hr
