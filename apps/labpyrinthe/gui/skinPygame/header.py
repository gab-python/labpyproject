#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Header simple.
"""
# import
import labpyproject.core.pygame.widgets as wgt
import labpyproject.apps.labpyrinthe.gui.skinPygame.uitools as uit

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["Header"]
# classe
class Header(wgt.Stack):
    """
    Header graphique
    """

    def __init__(self, skin, **kwargs):
        """
        Constructeur
        """
        # ref au skin :
        self.skin = skin
        # générique :
        wgt.Stack.__init__(
            self, width="100%", snapH=True, height="100%", name="Header", **kwargs
        )
        # création de l'image :
        self.widget_image = uit.WImage("screens", "entete", self.skin, fixed=False)
        self.add_item(self.widget_image)
