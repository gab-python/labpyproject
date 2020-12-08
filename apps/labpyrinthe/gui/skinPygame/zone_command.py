#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Commandes du jeu : implémentation Pygame
"""
# import
import pygame.locals
import labpyproject.core.pygame.widgets as wgt
import labpyproject.core.pygame.events as evt
from labpyproject.apps.labpyrinthe.bus.game_manager import GameManager
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import LabHelper
import labpyproject.apps.labpyrinthe.gui.skinPygame.uitools as uit
from labpyproject.apps.labpyrinthe.gui.skinBase.zone_command_base import ZoneCommandBase
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractSwitch
from labpyproject.apps.labpyrinthe.app.app_types import AppTypes

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ZoneCommand"]
# classes
class ZoneCommand(wgt.HStack, ZoneCommandBase, evt.CustomBaseControl):
    """
    Conteneur principal des outils de navigation
    """

    # méthodes
    def __init__(self, Mngr, skin, **kwargs):
        """
        Constructeur
        """
        self.visuel_inact = None
        self.img_bot = None
        # ref au skin :
        self.skin = skin
        # générique :
        wgt.HStack.__init__(self, width="100%", height="100%", **kwargs)
        ZoneCommandBase.__init__(self, Mngr, skin)
        # permet d'abonner la zone aux événements clavier (move via flèches)
        evt.CustomBaseControl.__init__(
            self, {"evttypes": [evt.CustomEventManager.KEY_PRESSED]}
        )

    #----->  Surcharge de ZoneCommandBase
    def register_APPType(self, app_type):
        """
        Défini le type d'appli associé.
        """
        # générique
        ZoneCommandBase.register_APPType(self, app_type)
        # spécifique
        if self.type_app == AppTypes.APP_CLIENT:
            # on désactive le retour au menu :
            self.btnsdict["menu"].enabled = False

    def _init_colors(self):
        """
        Couleurs portées par le skin :
        """
        # textes
        self.color_texte = self.skin.get_color("nav", "texte")
        self.color_texte_dis = self.skin.get_color("nav", "texte_dis")
        self.color_texte_info = self.skin.get_color("nav", "texte_info")
        # fonds
        self.color_bg_command = self.skin.get_color("nav", "bg_command")
        self.color_bg_info = self.skin.get_color("nav", "bg_info")
        self.color_bg_input = self.skin.get_color("nav", "bg_input")

    def toggle_help(self):
        """
        Affiche / masque l'aide
        """
        self.img_help.visible = not self.img_help.visible

    def draw_interface(self):
        """
        Création de l'interface
        """
        self.btnsdict = dict()
        self.imgdict = dict()
        # 1- colonne gaucje :
        self.left_column = wgt.Stack(height="100%", padding="2%", flex=1)
        self.add_item(self.left_column)
        # image aide :
        self.img_help = uit.WImage(
            "screens",
            "aide",
            self.skin,
            fixed=False,
            height="85%",
            valign="bottom",
            visible=False,
            align="center",
        )
        self.left_column.add_item(self.img_help)
        # 2- colonne droite :
        self.right_column = wgt.VStack(
            width="35%", minwidth=355, height="100%", name="colright"
        )
        self.add_item(self.right_column)
        # Conteneur des commandes de jeu :
        self.spacer = uit.Spacer(width="100%", height="100%", flex=1)
        self.right_column.add_item(self.spacer)
        # commandes de jeu :
        self.block_game = wgt.Canvas(
            bgcolor=self.color_bg_command, width="100%", height=115, name="block-game"
        )
        self.right_column.add_item(self.block_game)
        self._draw_game_block()
        # Conteneur infos et input :
        self.block_info = wgt.VStack(
            bgcolor=self.color_bg_info,
            width="100%",
            height="20%",
            minheight=150,
            name="block-info",
        )
        self.right_column.add_item(self.block_info)
        self._draw_infos_block()

    def _draw_infos_block(self):
        """
        Bloc info et input
        """
        # Input et boutons :
        self.line_input = wgt.Stack(width="100%", height=30)
        self.block_info.add_item(self.line_input)
        # entry
        self.choiceentry = uit.WEntry(
            "PoppinsMedium",
            18,
            self.skin,
            align="center",
            top=3,
            name="input",
            height="27",
            width=150,
            fgcolor=self.color_texte,
            bgcolor=self.color_bg_input,
        )
        self.line_input.add_item(self.choiceentry)
        # menu
        self.btnsdict["menu"] = uit.WButton(
            self, self.skin, "menu_2", left=0, top=0, fixed=True
        )
        self.line_input.add_item(self.btnsdict["menu"])
        # aide
        self.btnsdict["aide"] = uit.WButton(
            self, self.skin, "aide", left=30, top=0, fixed=True
        )
        self.line_input.add_item(self.btnsdict["aide"])
        # plein écran
        self.btnsdict["fullscreen"] = uit.WButton(
            self, self.skin, "fullscreen", right=30, top=0, fixed=True
        )
        self.line_input.add_item(self.btnsdict["fullscreen"])
        if not self.Mngr.support_fullscreen():
            self.btnsdict["fullscreen"].enabled = False
        # quitter
        self.btnsdict["quitter"] = uit.WButton(
            self, self.skin, "quitter_2", right=0, top=0, fixed=True
        )
        self.line_input.add_item(self.btnsdict["quitter"])
        # Décor
        self.img_bot = uit.WImage(
            "screens",
            "decor_hunter",
            self.skin,
            right=0,
            bottom=0,
            position="absolute",
            height="45%",
        )
        self.block_info.add_item(self.img_bot)
        # texte config partie
        self.partietext = uit.WText(
            "PoppinsBlack",
            18,
            self.skin,
            snapH=True,
            left=5,
            bottom=-5,
            position="absolute",
            fgcolor="#8C9557",
        )
        self.block_info.add_item(self.partietext)
        # texte info :
        self.infotext = uit.WText(
            "PoppinsMedium",
            14,
            self.skin,
            width="100%",
            padding="5%",
            flex=1,
            height="100%",
            minheight=120,
            name="infotext",
            fgcolor=self.color_texte_info,
        )
        self.block_info.add_item(self.infotext)

    def _draw_game_block(self):
        """
        Bloc commandes de jeu
        """
        self.sub_block_game = wgt.Stack(width=355, height=115, align="center")
        self.block_game.add_item(self.sub_block_game)
        # boutons :
        bp = dict()
        bp["move"] = (5, 5)
        bp["mur"] = (90, 5)
        bp["porte"] = (175, 5)
        bp["kill"] = (5, 30)
        bp["grenade"] = (90, 30)
        bp["mine"] = (175, 30)
        bp["top"] = (300, 5)
        bp["left"] = (275, 30)
        bp["right"] = (325, 30)
        bp["bottom"] = (300, 55)
        bp["d_1"] = (90, 65)
        bp["d_2"] = (119, 65)
        bp["d_3"] = (148, 65)
        bp["d_4"] = (177, 65)
        bp["d_5"] = (206, 65)
        bp["d_6"] = (235, 65)
        bp["p_1"] = (90, 90)
        bp["p_5"] = (119, 90)
        bp["p_9"] = (148, 90)
        bp["p_13"] = (177, 90)
        bp["p_17"] = (206, 90)
        bp["p_25"] = (235, 90)
        bp["valider"] = (270, 90)
        for name, coords in bp.items():
            if name[1] == "_":
                num = name.split("_")[1]
                btnname = "radio_" + num
            else:
                btnname = name
            self.btnsdict[name] = uit.WButton(
                self, self.skin, btnname, switch=True, x=coords[0], y=coords[1]
            )
            self.sub_block_game.add_item(self.btnsdict[name])
        # textes :
        tp = dict()
        tp["silhouette0001"] = (300, 30)
        tp["distance_2"] = (5, 65)
        tp["puissance_2"] = (5, 90)
        for name, coords in tp.items():
            # version enabled :
            self.imgdict[name] = uit.WImage(
                "nav", name, self.skin, x=coords[0], y=coords[1], visible=False
            )
            self.sub_block_game.add_item(self.imgdict[name])
            # version disabled :
            self.imgdict[name + "_dis"] = uit.WImage(
                "nav", name + "_dis", self.skin, x=coords[0], y=coords[1], visible=False
            )
            self.sub_block_game.add_item(self.imgdict[name + "_dis"])
        # visuel :
        self.visuel_inact = uit.WImage(
            "nav",
            "visuel_elimine",
            self.skin,
            x=0,
            y=0,
            width=355,
            height=115,
            visible=False,
        )
        self.sub_block_game.add_item(self.visuel_inact)

    def apply_current_state(self):
        """
        Applique l'état courant
        """
        if self.current_state == ZoneCommandBase.STATE_MENU:
            # affichages :
            self.block_game.visible = False
            # bot :
            surf_bot = self.skin.get_image("screens", "decor_hunter")
            self.img_bot.load_surface(surf_bot)
        if self.current_state == ZoneCommandBase.STATE_GAME:
            # affichages :
            self.block_game.visible = True

    def handle_change_states(self, changelist, newstate):
        """
        Applique le changement d'état à la liste
        """
        # générique :
        ZoneCommandBase.handle_change_states(self, changelist, newstate)
        # textes :
        is_dir = False
        is_dist = False
        is_puis = False
        txt_vis = not newstate == AbstractSwitch.DISABLED
        for elt in changelist:
            if isinstance(elt, str):
                if elt == "directions":
                    is_dir = True
                elif elt == "distances":
                    is_dist = True
                elif elt == "puissances":
                    is_puis = True
            else:
                if not is_dir and elt in self.ctrlsdict["directions"].keys():
                    is_dir = True
                if not is_dist and elt in self.ctrlsdict["distances"].keys():
                    is_dist = True
                if not is_puis and elt in self.ctrlsdict["puissances"].keys():
                    is_puis = True
        names = []
        if is_dir:
            names.append("silhouette0001")
        if is_dist:
            names.append("distance_2")
        if is_puis:
            names.append("puissance_2")
        for name in names:
            txtimg = self.imgdict[name]
            txtimg_dis = self.imgdict[name + "_dis"]
            # visibilité
            txtimg.visible = txt_vis
            txtimg_dis.visible = not txt_vis

    def publish_message(self, msg):
        """
        Affichage d'un message dans la zone info
        """
        self.infotext.text = msg

    def affiche_type_partie(self, txt):
        """
        Affichage du type de partie
        """
        self.partietext.text = txt

    def show_player_status(self, dictargs):
        """
        Affichage des infos de statut du joueur.
        """
        # données d'état
        client = dictargs["client"] in [True, "True"]
        connected = dictargs["connected"] in [True, "True"]
        type_partie = dictargs["type_partie"]
        viewer = dictargs["viewer"] in [True, "True"]
        robot = dictargs["robot"]
        killed = dictargs["killed"] in [True, "True"]
        # visuels à modifier (par défaut)
        surf_bot = self.skin.get_image("screens", "decor_hunter")
        surf_vis = None
        #  particularisation :
        if client and not connected:
            surf_vis = self.skin.get_image("nav", "visuel_deconnecte")
        elif killed:
            surf_vis = self.skin.get_image("nav", "visuel_elimine")
        elif viewer or type_partie == GameManager.GAME_MODE_DEMO:
            surf_vis = self.skin.get_image("nav", "visuel_spectateur")
        elif robot != None:
            states_surf = self.skin.get_image_for_BotItem(robot, (60, 60))
            surf_bot = states_surf[0]
        # application :
        self.img_bot.load_surface(surf_bot)
        if surf_vis:
            self.visuel_inact.load_surface(surf_vis)
            self.visuel_inact.visible = True
        else:
            self.visuel_inact.visible = False

    def global_control_callback(self, ctrl, state):
        """
        Prend en charge les contrôles globaux, retourne un boolean
        indiquant si ctrl est un contrôle global.
        """
        isglobal = False
        # contrôles globaux (avec roll over)
        if ctrl in [
            self.btnsdict["menu"],
            self.btnsdict["quitter"],
            self.btnsdict["aide"],
            self.btnsdict["fullscreen"],
        ]:
            isglobal = True
            # txt d'info en rollover :
            txtover = None
            if state == AbstractSwitch.OVER:
                if ctrl == self.btnsdict["menu"]:
                    txtover = "Retour au menu (en quitant la partie en cours)."
                elif ctrl == self.btnsdict["quitter"]:
                    txtover = "Quitter le jeu."
                elif ctrl == self.btnsdict["aide"]:
                    txtover = "Afficher les raccourcis clavier."
                elif ctrl == self.btnsdict["fullscreen"]:
                    txtover = "Entrer/sortir du mode plein écran (Ne pas utiliser avec plusieurs moniteurs!)."
            self._handle_txt_rollover(txtover)
            # action transmise à la GUI :
            if state == AbstractSwitch.PRESSED:
                if ctrl == self.btnsdict["menu"]:
                    self.Mngr.ask_goto_menu()
                elif ctrl == self.btnsdict["quitter"]:
                    self.Mngr.ask_quit_game()
                elif ctrl == self.btnsdict["aide"]:
                    self.toggle_help()
                elif ctrl == self.btnsdict["fullscreen"]:
                    self.Mngr.ask_fullscreen()
        return isglobal

    #-----> Déplacement avec les flèches clavier :
    def on_item_added_to_displaylist(self):
        """
        Appelée lorsque l'item (via sa hiérarchie parente) est publié par
        le root dans la displaylist finale
        """
        # générique :
        wgt.Stack.on_item_added_to_displaylist(self)
        # events :
        self.register()

    def on_item_removed_from_displaylist(self):
        """
        Appelée lorsque l'item (via sa hiérarchie parente) est dé-publié par
        le root de la displaylist finale
        """
        # générique :
        wgt.Stack.on_item_removed_from_displaylist(self)
        # events :
        self.unregister()

    def handle_key_event(self, customeventtype, event):
        """
        Appelée par le manager d'événements
        
        Args:
            * customeventtype : CustomEventManager.KEY_PRESSED ou 
                    CustomEventManager.KEY_RELEASED
            * event : pygame.KEYDOWN ou pygame.KEYUP
        
        """
        if customeventtype == evt.CustomEventManager.KEY_PRESSED:
            if event.key in evt.CustomEventManager.ARROW_KEYS:
                # code de direction :
                codedirect = None
                if event.key == pygame.locals.K_LEFT:
                    codedirect = LabHelper.CHAR_LEFT
                elif event.key == pygame.locals.K_RIGHT:
                    codedirect = LabHelper.CHAR_RIGHT
                elif event.key == pygame.locals.K_UP:
                    codedirect = LabHelper.CHAR_TOP
                elif event.key == pygame.locals.K_DOWN:
                    codedirect = LabHelper.CHAR_BOTTOM
                # commande :
                self.current_cmd["cmd"] = LabHelper.ACTION_MOVE
                self.current_cmd["action"] = ""
                self.current_cmd["distance"] = "1"
                self.current_cmd["direction"] = codedirect
                self.current_cmd["puissance"] = None
                self.current_cmd["cmd2send"] = (
                    self.current_cmd["action"]
                    + self.current_cmd["direction"]
                    + self.current_cmd["distance"]
                )
                # envoi et post traitements
                self._send_command()
                self.post_control_callback()
            elif event.key == pygame.locals.K_ESCAPE:
                self.Mngr.ask_escape()
