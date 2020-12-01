#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Implémentation Tkinter de SkinBase
"""
# imports :
import PIL.ImageTk
from labpyproject.apps.labpyrinthe.gui.skinBase.skin_base import SkinBase

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["SkinTkinter"]
# classe :
class SkinTkinter(SkinBase):
    """
    Implémentation Tkinter de SkinBase
    """

    def __init__(self, optmode=True, frozen=False):
        """
        Constructeur
        """
        # générique :
        SkinBase.__init__(self, optmode=optmode, frozen=frozen)

    #-----> Conversion à subclasser
    def export_image_from_PIL(self, src):
        """
        Convertit une source PIL.Image dans le format attendu par
        le moteur graphique.
        """
        # spécifique
        return PIL.ImageTk.PhotoImage(src)
