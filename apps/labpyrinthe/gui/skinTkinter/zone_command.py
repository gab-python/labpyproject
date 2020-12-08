#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Commandes du jeu : implémentation Tkinter
"""
# import
import math
import tkinter as tk
import labpyproject.apps.labpyrinthe.gui.skinTkinter.uitools as uit
from labpyproject.apps.labpyrinthe.gui.skinBase.zone_command_base import ZoneCommandBase

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ZoneCommand"]
# classes
class ZoneCommand(tk.Canvas, ZoneCommandBase):
    """
    Conteneur principal des outils de navigation
    """

    def __init__(self, parent, Mngr, skin):
        """
        Constructeur
        """
        # générique :
        tk.Canvas.__init__(
            self, parent, {"bg": "#FFFFFF", "borderwidth": 0, "highlightthickness": 0}
        )

        # Variable associée au texte d'info :
        self.infovar = tk.StringVar()
        # Variable associée au champ de saisie
        self.choicevar = tk.StringVar()
        # Mesures
        self.width = self.height = None
        self._cmd_width = None
        self._cmd_height = None
        # générique :
        ZoneCommandBase.__init__(self, Mngr, skin)
        # resize :
        self._is_resized = False
        self.bind("<Configure>", self.on_resize)

    #-----> Resize
    def on_resize(self, event):
        """
        Gestion du resize
        """
        if (event.width, event.height) != (self.width, self.height):
            self.width = self.winfo_width()
            self.height = self.winfo_height()
            # Fond graphique :
            wg, hg = 2760, 100
            ratio = self.width / wg
            wr, hr = math.ceil(self.width), math.ceil(hg * ratio)
            imgscreen = self.skin.get_image("screens", "footer_tk", size=(wr, hr))
            self.itemconfig(self._bg_graph, image=imgscreen)
            self.itemconfig(self._bg_graph, state="disabled")
            hC = max(hr, 140) + 30
            self["height"] = hC
            self.coords(self._bg_graph, 0, hC - hr)
            # commandes :
            xC = (self.width - self._cmd_width) / 2
            self.coords(self._cmd_window, xC, 0)
            # menu et quitter :
            xMQ = xC + self._cmd_width
            self.coords(self._mq_window, xMQ, 0)
            # fin
            self._is_resized = True

    #----->  Surcharge de ZoneCommandBase
    def draw_interface(self):
        """
        Création de l'interface
        """
        self._static_imgtk = dict()
        self.btnsdict = dict()
        # 1- fond image :
        self._bg_graph = self.create_image(0, 0, anchor="nw", state="hidden")
        # Params :
        px = py = 0
        h_act = h_dir = h_para = 100
        h_val = 20
        h_info = h_act + h_val
        hW = h_info + 2 * 10
        w_act = 160
        w_dir = 110
        w_para = 46 + 6 * 20
        w_val = w_act + w_dir + w_para
        w_info = math.ceil(w_val / 2)
        wW = w_val + w_info
        self._cmd_width = wW
        self._cmd_height = hW
        # mémorisation (changements d'états)
        self._sizes_dict = dict()
        self._sizes_dict["w_info"] = w_info
        self._sizes_dict["h_info"] = h_info
        self._sizes_dict["w_info_full"] = wW
        self._sizes_dict["h_info_full"] = h_info
        # 2- Conteneur des commandes de jeu :
        self._frame_content = tk.Frame(
            self,
            {"height": hW, "bg": "#FFFFFF", "borderwidth": 0, "highlightthickness": 0},
        )
        # association window / frame :
        self._cmd_window = self.create_window(
            0, 0, anchor="nw", window=self._frame_content
        )
        # Ligne blanche
        self._frame_space = tk.Frame(
            self._frame_content,
            {
                "width": wW,
                "height": 10,
                "bg": "#FFFFFF",
                "borderwidth": 0,
                "highlightthickness": 0,
            },
        )
        self._frame_space.grid(row=0, column=0, columnspan=4)
        self._frame_space.grid_propagate(0)
        # Actions
        col_action = self.color_bg_action
        self._frame_action = tk.Frame(
            self._frame_content,
            {
                "width": w_act,
                "height": h_act,
                "bg": col_action,
                "borderwidth": 0,
                "highlightthickness": 0,
            },
        )
        self._frame_action.grid(row=1, column=0)
        self._frame_action.grid_propagate(0)
        self._static_imgtk["titre_action"] = uit.CanvasImage(
            self._frame_action, self.skin, "titre_action", col_action
        )
        self._static_imgtk["titre_action"].grid(
            row=0, column=0, columnspan=2, padx=px, pady=py
        )
        self._static_imgtk["spacer_1"] = uit.CanvasSpacer(
            self._frame_action, self.skin, (10, 10), col_action
        )
        self._static_imgtk["spacer_1"].grid(row=1, column=0, columnspan=2)
        self.btnsdict["move"] = uit.CanvasSwitch(
            self._frame_action, self, self.skin, "move", True, col_action
        )
        self.btnsdict["move"].grid(row=2, column=0, padx=px, pady=py)
        self.btnsdict["porte"] = uit.CanvasSwitch(
            self._frame_action, self, self.skin, "porte", True, col_action
        )
        self.btnsdict["porte"].grid(row=3, column=0, padx=px, pady=py)
        self.btnsdict["mur"] = uit.CanvasSwitch(
            self._frame_action, self, self.skin, "mur", True, col_action
        )
        self.btnsdict["mur"].grid(row=4, column=0, padx=px, pady=py)
        self.btnsdict["kill"] = uit.CanvasSwitch(
            self._frame_action, self, self.skin, "kill", True, col_action
        )
        self.btnsdict["kill"].grid(row=2, column=1, padx=px, pady=py)
        self.btnsdict["grenade"] = uit.CanvasSwitch(
            self._frame_action, self, self.skin, "grenade", True, col_action
        )
        self.btnsdict["grenade"].grid(row=3, column=1, padx=px, pady=py)
        self.btnsdict["mine"] = uit.CanvasSwitch(
            self._frame_action, self, self.skin, "mine", True, col_action
        )
        self.btnsdict["mine"].grid(row=4, column=1, padx=px, pady=py)
        # Directions :
        col_direct = self.color_bg_direct
        self._frame_direct = tk.Frame(
            self._frame_content,
            {
                "width": w_dir,
                "height": h_dir,
                "bg": col_direct,
                "borderwidth": 0,
                "highlightthickness": 0,
            },
        )
        self._frame_direct.grid(row=1, column=1)
        self._frame_direct.grid_propagate(0)
        self._static_imgtk["titre_direction"] = uit.CanvasImage(
            self._frame_direct, self.skin, "titre_direction", col_direct
        )
        self._static_imgtk["titre_direction"].grid(
            row=0, column=0, columnspan=5, padx=px, pady=py
        )
        self._static_imgtk["spacer_2"] = uit.CanvasSpacer(
            self._frame_direct, self.skin, (10, 10), col_direct
        )
        self._static_imgtk["spacer_2"].grid(row=1, column=0, columnspan=5)
        self._static_imgtk["spacer_dir_1"] = uit.CanvasSpacer(
            self._frame_direct, self.skin, (20, 20), col_direct
        )
        self._static_imgtk["spacer_dir_1"].grid(row=2, column=0)
        self.btnsdict["top"] = uit.CanvasSwitch(
            self._frame_direct, self, self.skin, "top", True, col_direct
        )
        self.btnsdict["top"].grid(row=2, column=2, padx=px, pady=py)
        self.btnsdict["left"] = uit.CanvasSwitch(
            self._frame_direct, self, self.skin, "left", True, col_direct
        )
        self.btnsdict["left"].grid(row=3, column=1, padx=px, pady=py)
        self._static_imgtk["silhouette"] = uit.CanvasImage(
            self._frame_direct, self.skin, "silhouette0001", col_direct
        )
        self._static_imgtk["silhouette"].grid(row=3, column=2, padx=px, pady=py)
        self.btnsdict["right"] = uit.CanvasSwitch(
            self._frame_direct, self, self.skin, "right", True, col_direct
        )
        self.btnsdict["right"].grid(row=3, column=3, padx=px, pady=py)
        self.btnsdict["bottom"] = uit.CanvasSwitch(
            self._frame_direct, self, self.skin, "bottom", True, col_direct
        )
        self.btnsdict["bottom"].grid(row=4, column=2, padx=px, pady=py)
        self._static_imgtk["spacer_dir_2"] = uit.CanvasSpacer(
            self._frame_direct, self.skin, (20, 20), col_direct
        )
        self._static_imgtk["spacer_dir_2"].grid(row=2, column=4)
        # Paramètres :
        col_param = self.color_bg_param
        self._frame_param = tk.Frame(
            self._frame_content,
            {
                "width": w_para,
                "height": h_para,
                "bg": col_param,
                "borderwidth": 0,
                "highlightthickness": 0,
            },
        )
        self._frame_param.grid(row=1, column=2)
        self._frame_param.grid_propagate(0)
        self._static_imgtk["titre_parametres"] = uit.CanvasImage(
            self._frame_param, self.skin, "titre_parametres", col_param
        )
        self._static_imgtk["titre_parametres"].grid(row=0, column=0, padx=px, pady=py)
        self._static_imgtk["spacer_3"] = uit.CanvasSpacer(
            self._frame_param, self.skin, (10, 10), col_param
        )
        self._static_imgtk["spacer_3"].grid(row=1, column=0)
        # distance / portée
        self._frame_distance = tk.Frame(
            self._frame_param,
            {"bg": col_param, "borderwidth": 0, "highlightthickness": 0},
        )
        self._frame_distance.grid(row=2, column=0, padx=0, pady=0)
        self._static_imgtk["distance"] = uit.CanvasImage(
            self._frame_distance, self.skin, "distance", col_param
        )
        self._static_imgtk["distance"].grid(row=0, column=0, padx=px, pady=py)
        self.btnsdict["d_1"] = uit.CanvasSwitch(
            self._frame_distance, self, self.skin, "radio_1", True, col_param
        )
        self.btnsdict["d_1"].grid(row=0, column=1, padx=px, pady=py)
        self.btnsdict["d_2"] = uit.CanvasSwitch(
            self._frame_distance, self, self.skin, "radio_2", True, col_param
        )
        self.btnsdict["d_2"].grid(row=0, column=2, padx=px, pady=py)
        self.btnsdict["d_3"] = uit.CanvasSwitch(
            self._frame_distance, self, self.skin, "radio_3", True, col_param
        )
        self.btnsdict["d_3"].grid(row=0, column=3, padx=px, pady=py)
        self.btnsdict["d_4"] = uit.CanvasSwitch(
            self._frame_distance, self, self.skin, "radio_4", True, col_param
        )
        self.btnsdict["d_4"].grid(row=0, column=4, padx=px, pady=py)
        self.btnsdict["d_5"] = uit.CanvasSwitch(
            self._frame_distance, self, self.skin, "radio_5", True, col_param
        )
        self.btnsdict["d_5"].grid(row=0, column=5, padx=px, pady=py)
        self.btnsdict["d_6"] = uit.CanvasSwitch(
            self._frame_distance, self, self.skin, "radio_6", True, col_param
        )
        self.btnsdict["d_6"].grid(row=0, column=6, padx=px, pady=py)
        # puissance :
        self._frame_puissance = tk.Frame(
            self._frame_param,
            {"bg": col_param, "borderwidth": 0, "highlightthickness": 0},
        )
        self._frame_puissance.grid(row=3, column=0, padx=0, pady=0)
        self._static_imgtk["puissance"] = uit.CanvasImage(
            self._frame_puissance, self.skin, "puissance", col_param
        )
        self._static_imgtk["puissance"].grid(row=0, column=0, padx=px, pady=py)
        self.btnsdict["p_1"] = uit.CanvasSwitch(
            self._frame_puissance, self, self.skin, "radio_1", True, col_param
        )
        self.btnsdict["p_1"].grid(row=0, column=1, padx=px, pady=py)
        self.btnsdict["p_5"] = uit.CanvasSwitch(
            self._frame_puissance, self, self.skin, "radio_5", True, col_param
        )
        self.btnsdict["p_5"].grid(row=0, column=2, padx=px, pady=py)
        self.btnsdict["p_9"] = uit.CanvasSwitch(
            self._frame_puissance, self, self.skin, "radio_9", True, col_param
        )
        self.btnsdict["p_9"].grid(row=0, column=3, padx=px, pady=py)
        self.btnsdict["p_13"] = uit.CanvasSwitch(
            self._frame_puissance, self, self.skin, "radio_13", True, col_param
        )
        self.btnsdict["p_13"].grid(row=0, column=4, padx=px, pady=py)
        self.btnsdict["p_17"] = uit.CanvasSwitch(
            self._frame_puissance, self, self.skin, "radio_17", True, col_param
        )
        self.btnsdict["p_17"].grid(row=0, column=5, padx=px, pady=py)
        self.btnsdict["p_25"] = uit.CanvasSwitch(
            self._frame_puissance, self, self.skin, "radio_25", True, col_param
        )
        self.btnsdict["p_25"].grid(row=0, column=6, padx=px, pady=py)
        # Btn valider :
        col_valid = self.color_bg_valid
        self._frame_valid = tk.Frame(
            self._frame_content,
            {
                "width": w_val,
                "height": h_val,
                "bg": col_valid,
                "borderwidth": 0,
                "highlightthickness": 0,
            },
        )
        self._frame_valid.grid(row=2, column=0, columnspan=3)
        self._frame_valid.grid_propagate(0)
        self._static_imgtk["spacer_4"] = uit.CanvasSpacer(
            self._frame_valid, self.skin, (w_val - 80, 10), col_valid
        )
        self._static_imgtk["spacer_4"].grid(row=0, column=0)
        self.btnsdict["valider"] = uit.CanvasSwitch(
            self._frame_valid, self, self.skin, "valider", False, col_valid
        )
        self.btnsdict["valider"].grid(row=0, column=1, sticky="e")
        # Texte infos et Input commande
        col_input = self.color_bg_input
        col_txt = self.color_info
        self._frame_input = tk.Frame(
            self._frame_content,
            {
                "width": w_info,
                "height": h_info,
                "bg": col_input,
                "borderwidth": 0,
                "highlightthickness": 0,
            },
        )
        self._frame_input.grid(row=1, column=3, rowspan=2)
        self._frame_input.grid_propagate(0)
        # infos
        self._static_imgtk["titre_infos"] = uit.CanvasImage(
            self._frame_input, self.skin, "titre_infos", col_input
        )
        self._static_imgtk["titre_infos"].grid(
            row=0, column=0, columnspan=2, padx=px, pady=py
        )
        self._frame_infos = tk.Frame(
            self._frame_input,
            {
                "width": w_info,
                "height": 80,
                "bg": col_input,
                "borderwidth": 0,
                "highlightthickness": 0,
            },
        )
        self._frame_infos.grid(row=1, column=0, columnspan=2)
        self._frame_infos.grid_propagate(0)
        self.infotext = tk.Message(
            self._frame_infos,
            textvariable=self.infovar,
            font=None,
            width=w_info - 10,
            justify="left",
            anchor="nw",
            fg=col_txt,
            bg=col_input,
            bd=0,
            highlightthickness=0,
        )
        self.infotext.grid(row=0, column=0, padx=5, pady=5, sticky="sew")
        # input
        self._static_imgtk["symb_cmd"] = uit.CanvasImage(
            self._frame_input, self.skin, "symbole_commande", col_input
        )
        self._static_imgtk["symb_cmd"].grid(row=2, column=0, sticky="e")
        self.choiceentry = uit.CustomEntry(
            self._frame_input,
            textvariable=self.choicevar,
            font=None,
            fg=col_input,
            bg=col_txt,
            bd=0,
            highlightthickness=0,
            width=15,
        )
        self.choiceentry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        # Ligne sombre
        self._frame_space_2 = tk.Frame(
            self._frame_content,
            {
                "width": wW,
                "height": 10,
                "bg": "#330000",
                "borderwidth": 0,
                "highlightthickness": 0,
            },
        )
        self._frame_space_2.grid(row=3, column=0, columnspan=4)
        self._frame_space_2.grid_propagate(0)
        # 3- Menu et quitter
        self._frame_mq = tk.Frame(
            self,
            {
                "height": 40,
                "width": 60,
                "bg": "#FFFFFF",
                "borderwidth": 0,
                "highlightthickness": 0,
            },
        )
        # association window / frame
        self._mq_window = self.create_window(0, 0, anchor="nw", window=self._frame_mq)
        # ligne blanche :
        self._frame_space_mq = tk.Frame(
            self._frame_mq,
            {
                "width": 10,
                "height": 10,
                "bg": "#FFFFFF",
                "borderwidth": 0,
                "highlightthickness": 0,
            },
        )
        self._frame_space_mq.grid(row=0, column=0, columnspan=2)
        self._frame_space_mq.grid_propagate(0)
        # menu :
        self.btnsdict["menu"] = uit.CanvasSwitch(
            self._frame_mq, self, self.skin, "menu", False, "#FFFFFF"
        )
        self.btnsdict["menu"].grid(row=1, column=0)
        # quitter :
        self.btnsdict["quitter"] = uit.CanvasSwitch(
            self._frame_mq, self, self.skin, "quitter", False, "#FFFFFF"
        )
        self.btnsdict["quitter"].grid(row=1, column=1)

    def apply_current_state(self):
        """
        Applique l'état courant
        """
        gameFrames = [
            self._frame_action,
            self._frame_direct,
            self._frame_param,
            self._frame_valid,
        ]
        if self.current_state == ZoneCommandBase.STATE_MENU:
            for w in gameFrames:
                w.grid_remove()
            wFI = self._sizes_dict["w_info_full"]
            hFI = self._sizes_dict["h_info_full"]
        if self.current_state == ZoneCommandBase.STATE_GAME:
            for w in gameFrames:
                w.grid()
            wFI = self._sizes_dict["w_info"]
            hFI = self._sizes_dict["h_info"]
        self._frame_input.configure(width=wFI)
        self._frame_input.configure(height=hFI)
        self._frame_infos.configure(width=wFI)
        self.infotext.configure(width=wFI - 10)

    def publish_message(self, msg):
        """
        Affichage d'un message dans la zone info
        """
        self.infovar.set(msg)
        # Rafraichissement :
        self.update_idletasks()

    def post_control_callback(self):
        """
        Post traitement éventuel après gestion des callbacks de boutons
        """
        # Rafraichissement :
        self.update_idletasks()
