#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
**GUI du jeu : implémentation Tkinter**
"""
# imports :
import tkinter as tk
from labpyproject.apps.labpyrinthe.bus.game_manager import GameManager
from labpyproject.apps.labpyrinthe.gui.skinBase.GUIBase import GUIBase
from labpyproject.apps.labpyrinthe.gui.skinBase.GUIBase import GUIBaseNoThread
from labpyproject.apps.labpyrinthe.gui.skinBase.zone_command_base import ZoneCommandBase
from labpyproject.apps.labpyrinthe.gui.skinTkinter.skinTkinter import SkinTkinter
from labpyproject.apps.labpyrinthe.gui.skinTkinter.zone_partie import ZonePartie
from labpyproject.apps.labpyrinthe.gui.skinTkinter.zone_command import ZoneCommand
from labpyproject.apps.labpyrinthe.gui.skinTkinter.zone_menu import ZoneMenu
from labpyproject.apps.labpyrinthe.gui.skinTkinter.screen_wait import ScreenWait
from labpyproject.apps.labpyrinthe.gui.skinTkinter.header import Header

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["GUITk"]
# classe
class GUITk(tk.Tk, GUIBaseNoThread):
    """
    Interface Tk
    """

    # méthodes
    def __init__(self, master=None, frozen=False):
        """
        Constructeur
        """
        # initialisation Tk :
        tk.Tk.__init__(self, master)
        self.grid()
        self.minsize(width=900, height=670)
        self.resizable(width=True, height=True)
        # skin :
        self.skin = SkinTkinter(frozen=frozen)
        # initialisation GUIBase :
        GUIBaseNoThread.__init__(self)
        # Gestion du resize :
        self._init_resize()
        # tempo de traitement des tâches :
        self.task_tempo = 1  # ms
        # lancement process task :
        self.process_task()

    #-----> Surcharge de GUIBase
    def refresh_view(self):
        """
        Réalise un update de l'affichage
        """
        self.update_idletasks()

    def process_task(self):
        """
        Pseudo boucle de traitement de la pile d'échange
        """
        # traitement générique :
        GUIBase.process_task(self)
        # relance du process :
        self.after(self.task_tempo, self.process_task)

    def shutdown(self):
        """
        Fermeture de l'interface
        """
        # générique :
        GUIBaseNoThread.shutdown(self)
        # spécifique :
        self.destroy()

    def set_config_wait(self, show):
        """
        Configuration écran d'attente
        
        Args:
            show (Bool)
        """
        if show:
            if not self.screen_wait.winfo_ismapped():
                self.screen_wait.place(x=0, y=0, relwidth=1, relheight=1)
        else:
            if self.screen_wait.winfo_ismapped():
                self.screen_wait.place_forget()
            self.screen_wait.set_state(None)

    def set_config_content(self, show):
        """
        Configuration écran de contenu (menu, partie)
        
        Args:
            show (Bool)
        """
        if show:
            if not self.screen_content.winfo_ismapped():
                self.screen_content.place(x=0, y=0, relwidth=1, relheight=1)
        else:
            if self.screen_content.winfo_ismapped():
                self.screen_content.place_forget()

    def set_config_menu(self, show):
        """
        Configuration écran menu principal
        
        Args:
            show (Bool)
        """
        if show:
            self.zone_cmd.set_state(ZoneCommandBase.STATE_MENU)
            if not self.zone_menu.winfo_ismapped():
                self.zone_menu.grid()
        else:
            if self.zone_menu.winfo_ismapped():
                self.zone_menu.grid_remove()

    def set_config_game(self, show):
        """
        Configuration écran partie
        
        Args:
            show (Bool)
        """
        if show:
            self.zone_cmd.set_state(ZoneCommandBase.STATE_GAME)
            if not self.zone_partie.winfo_ismapped():
                self.zone_partie.grid()
        else:
            if self.zone_partie.winfo_ismapped():
                self.zone_partie.grid_remove()

    def post_set_configuration(self):
        """
        Finalisation du process de configuration de l'interface
        """
        # update :
        self.update_idletasks()

    #-----> resize
    def _init_resize(self):
        """
        Initialise la gestion du resize
        """
        self.width = self.winfo_reqwidth()
        self.height = self.winfo_reqheight()
        self.screen_content.bind("<Configure>", self.on_resize)

    def on_resize(self, event):
        """
        Evénement de resize
        """
        if (event.width, event.height) != (self.width, self.height):
            self._manage_partie_resize_start()
            # suite du process
            self.after_idle(self._delayed_resize, event)

    def _delayed_resize(self, event):
        """
        Fin du process de resize
        """
        self.width = self.winfo_width()
        self.height = self.winfo_height()

    def _manage_partie_resize_start(self):
        """
        Anticipe l'affichage de l'écran de resize (la carte prendra en charge la fin du process)
        """
        if self.partie_state in [
            GameManager.PARTIE_CREATED,
            GameManager.PARTIE_STARTED,
        ]:
            self.zone_partie.on_resize_start()

    #-----> création de l'interface
    def create_interface(self):
        """
        Initialise la création de l'interface
        """
        # Frame principale :
        self._create_mainframe()
        # Ecran d'attente :
        self._create_waitingScreen()
        # Cadre global :
        self._create_globalcadre()
        # Contenu menu :
        self._create_menu()
        # Contenu partie :
        self._create_game_content()
        # Synchro app :
        self.on_interface_created()

    def _create_waitingScreen(self):
        """
        Crée l'écran principal d'attente
        """
        self.screen_wait = ScreenWait(self, self.skin, ScreenWait.STATE_LOADING)
        self.screen_wait.place(x=0, y=0, relwidth=1, relheight=1)

    def _create_mainframe(self):
        """
        Création du conteneur principal de l'interface
        """
        # Frame principale :
        self.screen_content = tk.Frame(
            self, {"bg": "#FFFFFF", "borderwidth": 0, "highlightthickness": 0}
        )
        self.screen_content.place(x=0, y=0, relwidth=1, relheight=1)
        self.screen_content.rowconfigure(0, weight=1)
        self.screen_content.columnconfigure(0, weight=1)

    def _create_globalcadre(self):
        """
        Création des éléments permanents de l'interface
        """
        self.screen_content_content = tk.Frame(
            self.screen_content,
            {"bg": "#FFFFFF", "borderwidth": 0, "highlightthickness": 0},
        )
        self.screen_content_content.grid(column=0, row=0, padx=0, pady=0, sticky="nesw")
        self.screen_content_content.rowconfigure(0, minsize=100)
        self.screen_content_content.rowconfigure(1, minsize=400, weight=1)
        self.screen_content_content.rowconfigure(2, minsize=170)
        self.screen_content_content.columnconfigure(0, minsize=900, weight=1)
        # Entête :
        self.canvas_entete = Header(self.screen_content_content, self.skin)
        self.canvas_entete.grid(column=0, row=0, padx=0, pady=0, sticky="nesw")
        # Frame contenu :
        self.frame_content = tk.Frame(
            self.screen_content_content,
            {"bg": "#FFFFFF", "borderwidth": 0, "highlightthickness": 0},
        )
        self.frame_content.grid(column=0, row=1, padx=0, pady=0, sticky="nesw")
        self.frame_content.columnconfigure(0, minsize=900, weight=1)
        self.frame_content.rowconfigure(0, minsize=400, weight=1)
        # Pied de page / commandes :
        self.zone_cmd = ZoneCommand(self.screen_content_content, self, self.skin)
        self.zone_cmd.grid(column=0, row=2, padx=0, pady=0, sticky="nesw")

    def _create_menu(self):
        """
        Menu principal
        """
        self.zone_menu = ZoneMenu(self.frame_content, self, self.skin)
        self.zone_menu.grid(column=0, row=0, padx=0, pady=0, sticky="nesw")
        self.zone_menu.grid_remove()

    def _create_game_content(self):
        """
        Crée les éléments utilisés dans une partie
        """
        self.zone_partie = ZonePartie(self.frame_content, self, self.skin)
        self.zone_partie.grid(
            column=0, row=0, padx=0, pady=0, ipadx=5, ipady=5, sticky="nesw"
        )
        self.zone_partie.grid_remove()
        # refs internes :
        self.zone_carte = self.zone_partie.zone_carte
        self.zone_bots = self.zone_partie.zone_bots
