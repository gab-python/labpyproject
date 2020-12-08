#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Panneau d'information sur les robots : implémentation Tkinter
"""
# imports
import tkinter as tk
from labpyproject.apps.labpyrinthe.gui.skinBase.zone_bots_base import ZoneBotsBase

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ZoneBots"]
# classe
class ZoneBots(tk.Frame, ZoneBotsBase):
    """
    Zone d'information sur les robots
    """

    # paramètres statiques
    CASE_SIZE = (20, 20) #: taille de l'image du joueur
    # méthodes
    def __init__(self, parent, mngr, skin):
        """
        Constructeur
        """
        # générique :
        tk.Frame.__init__(
            self,
            parent,
            {
                "padx": 10,
                "pady": 10,
                "bg": "#FFFFFF",
                "borderwidth": 0,
                "highlightthickness": 0,
            },
        )
        ZoneBotsBase.__init__(self, mngr, skin)

    #-----> Surcharge de ZoneBotsBase
    def draw_interface(self, robotlist):
        """
        Crée l'interface au premier affichage
        """
        col_txt = self.color_txt
        # params :
        self._botlabeldict = dict()
        commonargs = {
            "bg": "#FFFFFF",
            "foreground": col_txt,
            "highlightbackground": "#FFFFFF",
            "highlightthickness": 1,
            "compound": "left",
        }
        # titre image :
        titre_img = self.skin.get_image("nav", "titre_joueurs")
        self._titre = tk.Label(
            self,
            {"bg": "#FFFFFF", "borderwidth": 0, "highlightthickness": 0},
            image=titre_img,
        )
        self._titre.grid(row=0, column=0, sticky="we")
        # Frame tableau bot :
        self._frame_bots = tk.Frame(
            self,
            {
                "padx": 5,
                "pady": 5,
                "bg": "#FFFFFF",
                "borderwidth": 0,
                "highlightthickness": 0,
            },
        )
        self._frame_bots.grid(row=1, column=0, sticky="we")
        # entete :
        img_ent = self.get_robot_image(None)
        txt_ent = self.get_robot_text(None)
        self._botlabeldict["entete"] = tk.Label(
            self._frame_bots, commonargs, image=img_ent, text=txt_ent
        )
        self._botlabeldict["entete"].grid(row=0, column=0)
        # robots :
        i = 1
        for case in robotlist:
            # bot
            img = self.get_robot_image(case)
            txt = self.get_robot_text(case)
            self._botlabeldict[case.uid] = tk.Label(
                self._frame_bots, commonargs, image=img, text=txt
            )
            self._botlabeldict[case.uid].grid(row=i, column=0)
            i += 1
        # légende :
        self._frame_leg = tk.Frame(
            self,
            {
                "padx": 5,
                "pady": 5,
                "bg": "#FFFFFF",
                "borderwidth": 0,
                "highlightthickness": 0,
            },
        )
        self._frame_leg.grid(row=2, column=0, sticky="we")
        txt_leg = self.get_txt_legende()
        self._legende = tk.Message(
            self._frame_leg,
            text=txt_leg,
            width=380,
            justify="left",
            anchor="nw",
            fg=col_txt,
            bg="#FFFFFF",
            bd=0,
            highlightthickness=0,
        )
        self._legende.grid(row=0, column=0)

    def update_bot_item(self, case, txt, img, bgcolor, fgcolor, hcolor):
        """
        Met à jour un item de la liste d'infos robots
        """
        label = self._botlabeldict[case.uid]
        label.configure(image=img)
        label.configure(text=txt)
        if bgcolor != None:
            label.configure(background=bgcolor)
        if fgcolor != None:
            label.configure(foreground=fgcolor)
        if hcolor != None:
            label.configure(highlightbackground=hcolor)

    def clear_bots_list(self):
        """
        Efface la liste des bots publiée
        """
        listchilds = self.winfo_children()
        for child in listchilds:
            child.destroy()
        self._botlabeldict = dict()

    def get_robot_image(self, case):
        """
        Retourne l'image associée au robot
        """
        if case == None:
            imgtk = self.skin.get_image("common", "transp", size=self.get_case_size())
        elif case == "sep":
            size = (self.get_case_size()[0], 1)
            imgtk = self.skin.get_image("common", "transp", size=size)
        else:
            imgtk = ZoneBotsBase.get_robot_image(self, case)
        return imgtk

    def get_case_size(self):
        """
        Retourne la taille de l'image du robot
        """
        return ZoneBots.CASE_SIZE
