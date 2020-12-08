#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Composants graphiques simples dédiés à un usage avec le skinPygame.
"""
# imports:
import labpyproject.core.pygame.widgets as wgt
import labpyproject.core.pygame.core as co
from labpyproject.apps.labpyrinthe.gui.skinPygame.skinPygame import SkinPygame
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractSwitch
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractInput

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["WImage", "WText", "WEntry", "WButton", "Spacer"]
# classes :
class WImage(wgt.Image):
    """
    Widget image custom
    """

    def __init__(
        self,
        cat,
        name,
        skin,
        surface=None,
        fixed=True,
        resizemode=SkinPygame.DEFAULT_RESIZEMODE,
        **kwargs
    ):
        """
        Constructeur:
        
        * kwargs : voir wgt.Image
        * resizemode : SkinPygame.SCALE_RESIZEMODE (scaling surface) ou 
            SkinPygame.SKIN_RESIZEMODE (resize PIL)
        
        """
        # ref au skin :
        self.skin = skin
        # identification de l'image associée :
        self.cat_img = cat
        self.name_img = name
        # mode de resize :
        self.resizemode = resizemode
        # générique :
        wgt.Image.__init__(self, surface=surface, fixed=fixed, name=name, **kwargs)
        # initialisation de la source :
        if surface == None and (cat != None and name != None and skin != None):
            surf = self.skin.get_image(self.cat_img, self.name_img)
            self.load_surface(surf)

    #-----> Surcharge de WImage :
    def get_surface_for_size(self, newsize):
        """
        Retourne une nouvelle surface à la taille newsize
        """
        newsurf = None
        if self.resizemode == SkinPygame.SKIN_RESIZEMODE:
            # spécifique : génération de l'image resizée via PIL
            if self.cat_img != None and self.name_img != None:
                newsurf = self.skin.get_image(self.cat_img, self.name_img, size=newsize)
        elif self.resizemode == SkinPygame.SCALE_RESIZEMODE:
            # générique : via rescale de la surface source
            newsurf = wgt.Image.get_surface_for_size(self, newsize)
        return newsurf

    def get_source_size(self):
        """
        Retourne les dimensions de la source
        """
        ws, hs = None, None
        if self.resizemode == SkinPygame.SKIN_RESIZEMODE:
            # spécifique : via le skin
            if self.cat_img != None and self.name_img != None:
                ws, hs = self.skin.get_source_size(self.cat_img, self.name_img)
        elif self.resizemode == SkinPygame.SCALE_RESIZEMODE:
            # générique : surface source
            ws, hs = wgt.Image.get_source_size(self)
        return ws, hs


class WText(wgt.Text):
    """
    Widget text custom
    """

    def __init__(self, fontname, size, skin, text="", extendchars=False, **kwargs):
        """
        Constructeur
            * kwargs : voir wgt.Text
        """
        # ref au skin :
        self.skin = skin
        # font object :
        self.fontobj = self.skin.get_FontObject(
            fontname, size, freetypefont=extendchars
        )
        # générique :
        wgt.Text.__init__(self, self.fontobj, text=text, **kwargs)


class WEntry(wgt.Entry, AbstractInput):
    """
    Widget Entry custom supportant l'interface AbstractInput
    """

    def __init__(self, fontname, size, skin, text="", extendchars=False, **kwargs):
        """
        Constructeur
        kwargs : voir wgt.WEntry
        """
        # ref au skin :
        self.skin = skin
        # callback :
        self._callback = None
        # font object :
        self.fontobj = self.skin.get_FontObject(
            fontname, size, freetypefont=extendchars
        )
        # générique :
        wgt.Entry.__init__(self, self.fontobj, text=text, **kwargs)

    #-----> Implémentation AbstractInput
    def register_callback(self, clb):
        """
        Enregistre le callback à appeler après validation (appui touche entrée)
        """
        if callable(clb):
            self._callback = clb

    def take_focus(self):
        """
        Méthode d'acquisition du focus input
        """
        self.ask_input_focus()

    def get_input_value(self):
        """
        Getter du texte input
        """
        return wgt.Entry._get_inputext(self)

    def set_input_value(self, val):
        """
        Setter du texte input
        """
        wgt.Entry._set_inputext(self, val)

    def on_entry_validated(self, event):
        """
        Appelée par handle_key_event lorsqu'une touche entrée a été pressée
        """
        if self._callback != None:
            self._callback(event)


class WButton(wgt.Button, AbstractSwitch):
    """
    Widget bouton image custom
    kwargs : voir wgt.Button
    
    Rq : AbstractSwitch implémentée dans la superclasse CustomBaseButton
    """

    def __init__(self, Mngr, skin, name, **kwargs):
        """
        Constructeur
        kwargs : voir wgt.WImageButton
        """
        # Manager :
        self.Mngr = Mngr
        # Skin :
        self.skin = skin
        # spécifique :
        self.name = name
        kwargs["name"] = name
        if "statesdict" in kwargs.keys():
            statesdict = kwargs["statesdict"]
        else:
            statesdict = self._init_images()
        # générique :
        wgt.Button.__init__(self, statesdict, **kwargs)

    def _init_images(self):
        """
        Crée le dict statesdict attendu par le constructeur de Button
        """
        statesdict = dict()
        statesdict[AbstractSwitch.UNSELECTED] = self.skin.get_image(
            "nav", self.name, state=1
        )
        statesdict[AbstractSwitch.OVER] = self.skin.get_image("nav", self.name, state=2)
        statesdict[AbstractSwitch.PRESSED] = self.skin.get_image(
            "nav", self.name, state=3
        )
        statesdict[AbstractSwitch.SELECTED] = self.skin.get_image(
            "nav", self.name, state=4
        )
        statesdict[AbstractSwitch.DISABLED] = self.skin.get_image(
            "nav", self.name, state=5
        )
        return statesdict

    def send_callback(self, state):
        """
        Méthode destinée à transmettre l'état au manager de ce contrôle
        """
        self.Mngr.control_callback(self, state)


class Spacer(co.CustomSprite):
    """
    Sprite image destiné à des fonds monochromes de conteneurs virtuels.
    """

    def __init__(self, **kwargs):
        """
        DirtySprite transparent utilisé dans des layouts flexibles.
        """
        # générique :
        co.CustomSprite.__init__(self, **kwargs)
