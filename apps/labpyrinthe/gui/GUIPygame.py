#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
**GUI du jeu : implémentation Pygame**
"""
# imports :
import os
import pygame
import labpyproject.core.pygame.widgets as wgt
import labpyproject.apps.labpyrinthe.gui.skinPygame.uitools as uit
from labpyproject.apps.labpyrinthe.bus.game_manager import GameManager
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import LabHelper
from labpyproject.apps.labpyrinthe.gui.skinBase.GUIBase import GUIBaseNoThread
from labpyproject.apps.labpyrinthe.gui.skinPygame.skinPygame import SkinPygame
from labpyproject.apps.labpyrinthe.gui.skinPygame.zone_partie import ZonePartie
from labpyproject.apps.labpyrinthe.gui.skinPygame.zone_command import ZoneCommand
from labpyproject.apps.labpyrinthe.gui.skinPygame.zone_menu import ZoneMenu
from labpyproject.apps.labpyrinthe.gui.skinPygame.screen_wait import ScreenWait
from labpyproject.apps.labpyrinthe.gui.skinBase.screen_wait_base import ScreenWaitBase
from labpyproject.apps.labpyrinthe.gui.skinPygame.header import Header
from labpyproject.apps.labpyrinthe.gui.skinPygame.footer import Footer

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["GUIPygame"]
# classe
class GUIPygame(wgt.Root, GUIBaseNoThread):
    """
    Interface Pygame
    """

    # méthodes
    def __init__(self, frozen=False):
        """
        Constructeur
        """
        # initialisation pygame :
        os.environ["PYGAME_FREETYPE"] = "1"
        pygame.init()
        # skin :
        self.skin = SkinPygame(frozen=frozen)
        # ico :
        ico = self.skin.get_image("carte", "winner", size=(32, 32))
        # titre :
        title = "LabPyrinthe"
        # root pygame
        wgt.Root.__init__(self, icon=ico, caption=title, width=1000, height=700)
        # objets graphiques supplémentaires :
        self.main_screen = None
        self.header = None
        self.footer = None
        self.bg_graph = None
        self._surface_menu = self.skin.get_image("screens", "bg_menu")
        self._surface_partie = self.skin.get_image("screens", "bg_partie")
        # initialisation GUIBase :
        GUIBaseNoThread.__init__(self)
        # démarrage méthode run : dans le script de lancement
        # après création de l'AppManager.

    #-----> thread d'interface
    def before_frame_processed(self):
        """
        Appelée à chaque frame d'exécution avant les traitements génériques de
        Root (événements puis update graphique)
        """
        # Traitement de la pile d'échanges :
        self.process_task()

    def shutdown(self):
        """
        Fermeture de l'interface
        """
        # générique :
        GUIBaseNoThread.shutdown(self)
        # pygame :
        self.close_Root()

    def on_quit_event(self, event):
        """
        Méthode appelée par CustomEventManager lorsque survient l'événement pygame.QUIT. 
        Rq : l'événement n'a aucun attribut particulier
        """
        # générique :
        # wgt.Root.on_quit_event(self, event)
        # fermeture globale de l'appli :
        self.shutdown()

    #-----> actions globales
    def ask_fullscreen(self):
        """
        Entrer/sortir du mode plein écran
        """
        self.toggle_fullscreen()

    def ask_escape(self):
        """
        Touche echap
        """
        if self.is_fullscreen():
            self.toggle_fullscreen()

    #-----> informations et affichages
    def refresh_view(self):
        """
        Réalise un update de l'affichage
        """
        self.update()

    def show_message(self, msg, is_input):
        """
        Affichage de message ou consigne
        """
        if self.config_screen == GUIBaseNoThread.CONFIG_LOADING:
            self.screen_wait.show_message(msg, is_input)
        else:
            self.zone_cmd.show_message(msg, is_input)

    def dispatch_type_partie(self, dictargs):
        """
        Affichage du type de partie.
        """
        # générique :
        GUIBaseNoThread.dispatch_type_partie(self, dictargs)
        # config zone bots
        if self.zone_bots != None:
            self.zone_bots.register_type_partie(self.current_game_mode)
        # affichage :
        if self.current_game_mode == None:
            txt = ""
        else:
            if self.current_game_mode == GameManager.GAME_MODE_PARTIE:
                txt = "PARTIE N."
            else:
                txt = "DEMO N."
            txt += str(self.current_game_level)
        self.zone_cmd.affiche_type_partie(txt)

    def show_NETInfos(self, dictargs):
        """
        Affichage des infos réseau.
        
        Args:
            dictargs : dict généré par la méthode get_network_infos du composant réseau associé
        """
        # délégué au footer :
        if self.footer:
            self.footer.show_NETInfos(dictargs)

    def on_app_type_defined(self):
        """
        Appelée lorsque la GUI connait le type d'application associée (client, serveur, standalone)
        """
        # générique :
        GUIBaseNoThread.on_app_type_defined(self)
        # footer :
        if self.footer != None:
            self.footer.set_app_type(self.type_app)
        # l'ensemble de l'appli est crée, on peut surcharger des propriétés
        # "business" :
        LabHelper.ANIMATION_RESOLUTION = LabHelper.ANIMATION_RESOLUTION_PIXEL

    def show_player_status(self, dictargs):
        """
        Affichage des infos de statut du joueur.
        """
        if self.zone_cmd:
            self.zone_cmd.show_player_status(dictargs)

    #-----> Configurations :
    def set_config_wait(self, show):
        """
        Configuration écran d'attente
        
        Args:
            show (Bool)
        """
        if self.screen_wait != None:
            self.screen_wait.show_preload(show)
        if show:
            self.screen_wait.left = 0
        else:
            # une fois l'application chargée, l'écran est inutile
            if self.screen_wait != None:
                self.remove_item(self.screen_wait)
                self.screen_wait = None

    def set_config_content(self, show):
        """
        Configuration écran de contenu (menu, partie)
        
        Args:
            show (Bool)
        """
        pass

    def set_config_menu(self, show):
        """
        Configuration écran menu principal
        
        Args:
            show (Bool)
        """
        if show:
            self.zone_menu.left = 0
            self.bg_graph.load_surface(self._surface_menu)
        else:
            self.zone_menu.left = "100%"

    def set_config_game(self, show):
        """
        Configuration écran partie
        
        Args:
            show (Bool)
        """
        if show:
            self.zone_partie.left = 0
            self.bg_graph.load_surface(self._surface_partie)
        else:
            self.zone_partie.left = "100%"

    def toggle_help(self):
        """
        Affichage / masquage aide
        """
        self.zone_cmd.toggle_help()

    #-----> création de l'interface
    def create_interface(self):
        """
        Initialise la création de l'interface
        """
        # Ecran d'attente :
        self._create_waitingScreen()
        self.screen_wait.show_preload(True)
        self.update()
        # Cadre global :
        self._create_globalcadre()
        # Contenu menu :
        self._create_menu()
        # Contenu partie :
        self._create_game_content()
        # type APP :
        if self.type_app != None:
            self.footer.set_app_type(self.type_app)
        # Synchro app :
        self.on_interface_created()

    def _create_waitingScreen(self):
        """
        Crée l'écran principal d'attente
        """
        self.screen_wait = ScreenWait(
            self,
            self.skin,
            # ScreenWait.STATE_LOADING,
            ScreenWaitBase.STATE_LOADING,
            show_infos=True,
            position="absolute",
            local_layer=2,
            name="main",
        )
        self.add_item(self.screen_wait)

    def _create_globalcadre(self):
        """
        Création des éléments permanents de l'interface
        """
        # conteneur global :
        self.main_screen = wgt.VStack(
            width="100%", height="100%", name="main", position="absolute", local_layer=0
        )
        self.add_item(self.main_screen)
        # header :
        self.header = Header(self.skin, position="static", local_layer=1)
        self.main_screen.add_item(self.header)
        # conteneur secondaire (menu / partie)
        self.screen_content = wgt.Stack(
            width="100%", height="100%", flex=1, position="static", name="content"
        )
        self.main_screen.add_item(self.screen_content)
        # fonds imgs
        self.bg_graph = uit.WImage(
            "screens",
            "bg_menu",
            self.skin,
            fixed=False,
            valign="top",
            width="100%",
            position="absolute",
            local_layer=0,
            fillmode="cover",
        )
        self.screen_content.add_item(self.bg_graph)
        # footer :
        self.footer = Footer(self.skin, position="static", local_layer=1)
        self.main_screen.add_item(self.footer)
        # zone commande :
        self.zone_cmd = ZoneCommand(
            self,
            self.skin,
            position="absolute",
            top=0,
            bottom=50,
            local_layer=2,
            name="command",
        )
        self.main_screen.add_item(self.zone_cmd)

    def _create_menu(self):
        """
        Menu principal
        """
        self.zone_menu = ZoneMenu(
            self,
            self.skin,
            position="absolute",
            left="100%",
            local_layer=2,
            name="zone_menu",
        )
        self.screen_content.add_item(self.zone_menu)

    def _create_game_content(self):
        """
        Crée les éléments utilisés dans une partie
        """
        self.zone_partie = ZonePartie(
            self,
            self.skin,
            position="absolute",
            left="100%",
            local_layer=1,
            name="zone_partie",
        )
        self.screen_content.add_item(self.zone_partie)
        # refs internes :
        self.zone_carte = self.zone_partie.zone_carte
        self.zone_bots = self.zone_partie.zone_bots
