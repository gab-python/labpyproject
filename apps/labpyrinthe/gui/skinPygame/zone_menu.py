#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Menu (choix de partie) : implémentation pygame
"""
# imports
import labpyproject.core.pygame.widgets as wgt
import labpyproject.apps.labpyrinthe.gui.skinPygame.uitools as uit
from labpyproject.apps.labpyrinthe.gui.skinBase.zone_menu_base import ZoneMenuBase
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractSwitch

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ZoneMenu", "MenuButton"]
# classes
class ZoneMenu(wgt.HStack, ZoneMenuBase):
    """
    Accueil du jeu : écran menu
    """

    # méthodes :
    def __init__(self, Mngr, skin, **kwargs):
        """
        Constructeur
        """
        # générique :
        wgt.HStack.__init__(self, width="100%", height="100%", **kwargs)
        ZoneMenuBase.__init__(self, Mngr, skin)

    #-----> Publication
    def draw_interface(self):
        """
        Création de l'interface. 
        """
        # zone visuel
        self.zone_visuel = wgt.Stack(flex=1, height="100%")
        self.add_item(self.zone_visuel)
        self.visuel = uit.WImage(
            "accueil", "visuel", self.skin, fixed=False, align="center", valign="middle"
        )
        self.zone_visuel.add_item(self.visuel)
        # zone menu
        # - colonne droite
        self.right_column = wgt.VStack(width="35%", minwidth="355", height="100%")
        self.add_item(self.right_column)
        # - VStack flexible
        self.stack_menu = wgt.VStack(width="100%", flex=1)
        self.right_column.add_item(self.stack_menu)
        # - sub space
        self.sub_space_1 = uit.Spacer(flex=2)
        self.stack_menu.add_item(self.sub_space_1)
        # - txt de consignes :
        self.txt_menu = uit.WImage(
            "accueil",
            "txt_menu",
            self.skin,
            fixed=False,
            align="center",
            valign="middle",
        )
        self.stack_menu.add_item(self.txt_menu)
        # - sub space
        self.sub_space_2 = uit.Spacer(flex=1)
        self.stack_menu.add_item(self.sub_space_2)
        # - ligne niveaux :
        self.niv_line = wgt.HStack(snapW=True, snapH=True, align="center")
        self.stack_menu.add_item(self.niv_line)
        # - sub space
        self.sub_space_niv_1 = uit.Spacer(flex=2)
        self.niv_line.add_item(self.sub_space_niv_1)
        # - niv 1 :
        self.btn_niveaux["1"] = MenuButton(self, self.skin, "niv1", fixed=False, flex=3)
        self.niv_line.add_item(self.btn_niveaux["1"])
        # - sub space
        self.sub_space_niv_2 = uit.Spacer(flex=1)
        self.niv_line.add_item(self.sub_space_niv_2)
        # - niv 2 :
        self.btn_niveaux["2"] = MenuButton(self, self.skin, "niv2", fixed=False, flex=3)
        self.niv_line.add_item(self.btn_niveaux["2"])
        # - sub space
        self.sub_space_niv_3 = uit.Spacer(flex=1)
        self.niv_line.add_item(self.sub_space_niv_3)
        # - niv 3 :
        self.btn_niveaux["3"] = MenuButton(self, self.skin, "niv3", fixed=False, flex=3)
        self.niv_line.add_item(self.btn_niveaux["3"])
        # - sub space
        self.sub_space_niv_4 = uit.Spacer(flex=2)
        self.niv_line.add_item(self.sub_space_niv_4)
        # - sub space
        self.sub_space_3 = uit.Spacer(flex=1)
        self.stack_menu.add_item(self.sub_space_3)
        # - ligne modes
        self.mode_line = wgt.HStack(snapW=True, snapH=True, align="center")
        self.stack_menu.add_item(self.mode_line)
        # - sub space
        self.sub_space_mod_1 = uit.Spacer(flex=1)
        self.mode_line.add_item(self.sub_space_mod_1)
        # - partie
        self.btn_modes["partie"] = MenuButton(
            self, self.skin, "partie", fixed=False, flex=5
        )
        self.mode_line.add_item(self.btn_modes["partie"])
        # - sub space
        self.sub_space_mod_2 = uit.Spacer(flex=1)
        self.mode_line.add_item(self.sub_space_mod_2)
        # - démo
        self.btn_modes["demo"] = MenuButton(
            self, self.skin, "demo", fixed=False, flex=5
        )
        self.mode_line.add_item(self.btn_modes["demo"])
        # - sub space
        self.sub_space_mod_3 = uit.Spacer(flex=1)
        self.mode_line.add_item(self.sub_space_mod_3)
        # - sub space
        self.sub_space_4 = uit.Spacer(flex=2)
        self.stack_menu.add_item(self.sub_space_4)
        # - spacer colonne droite :
        self.spacer_right = uit.Spacer(height="20%", minheight=150)
        self.right_column.add_item(self.spacer_right)


class MenuButton(uit.WButton):
    """
    Boutons du menu
    """

    def __init__(self, Mngr, skin, name, **kwargs):
        """
        Constructeur
        """
        # Manager : ZoneCarte ou ZoneBots
        self.Mngr = Mngr
        # ref au skin :
        self.skin = skin
        # nom / ref images
        self.name = name
        # état par défaut :
        self.default_state = AbstractSwitch.ENABLED
        # générique :
        uit.WButton.__init__(self, Mngr, skin, name, switch=True, **kwargs)

    def _init_images(self):
        """
        Crée le dict statesdict attendu par le constructeur de WButton
        """
        statesdict = dict()
        statesdict[AbstractSwitch.UNSELECTED] = self.skin.get_button_image(self.name, 1)
        statesdict[AbstractSwitch.OVER] = self.skin.get_button_image(self.name, 2)
        statesdict[AbstractSwitch.PRESSED] = self.skin.get_button_image(self.name, 3)
        statesdict[AbstractSwitch.SELECTED] = self.skin.get_button_image(self.name, 4)
        statesdict[AbstractSwitch.DISABLED] = None
        return statesdict
