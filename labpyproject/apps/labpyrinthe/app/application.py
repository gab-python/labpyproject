#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
**Manager de l'application multi-threads** prenant en charge deux rôles :

    1- Initialiser l'application globale, créer le composant d'interface (si celui-ci
    n'exige pas d'être lancé dans le thread principal) puis les composants réseau
    et métier. Lance et joint l'ensemble des threads initialisés.

    2- Router les tâches entre les différents threads associés aux composants
    (réseau, interface, métier). Rôle générique hérité de labpyproject.core.app.APPComp.
"""
# imports
import os, sys
import labpyproject.core.io.custom_IO as cio
import labpyproject.core.net.custom_TCP as ctcp
from labpyproject.core.app import app_components as appcomp
from labpyproject.apps.labpyrinthe.app.app_types import AppTypes
from labpyproject.apps.labpyrinthe.bus.game_manager import GameManager
import labpyproject.apps.labpyrinthe.gui.GUIConsole as guicons
# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["AppManager"]
# classe :
class AppManager(appcomp.APPComp):
    """
    **Manager de l'application multi-threads**.
    """

    # Variables statiques
    # types d'application :
    APP_SERVER = AppTypes.APP_SERVER  #: = AppTypes.APP_SERVER
    APP_CLIENT = AppTypes.APP_CLIENT  #: = AppTypes.APP_CLIENT
    APP_STANDALONE = AppTypes.APP_STANDALONE  #: = AppTypes.APP_STANDALONE
    # types d'interface : console ou tk
    INTERFACE_CONSOLE = "INTERFACE_CONSOLE"  #: identifie une interface console
    INTERFACE_TK = "INTERFACE_TK"  #: identifie une interface Tkinter
    INTERFACE_PYGAME = "INTERFACE_PYGAME"  #: identifie une interface Pygame
    # adresse par défaut du serveur TCP :
    default_tcp_address = ("", 11001)  #: adresse par défaut du serveur
    # racine du jeu
    GAME_PATH = ""  #: racine du jeu
    # méthodes
    def __init__(
        self,
        typeapp,
        address=None,
        interface=INTERFACE_CONSOLE,
        guiclass=guicons.GUIConsole,
    ):
        """
        Constructeur :
        
        Args:
            typeapp : AppManager.APP_SERVER (serveur) ou AppManager.APP_CLIENT (client) 
                        ou AppManager.APP_STANDALONE (standalone)
            address : adresse de connection du serveur
            interface : AppManager.INTERFACE_CONSOLE (console, défaut), 
                        AppManager.INTERFACE_TK, (standalone uniquement), 
                        AppManager.INTERFACE_PYGAME (standalone et client)
            guiclass : classe à instancier pour la GUI 
                        (GUIConsole par défaut en mode console)     
        """
        # init superclasse appcomp.APPComp:
        appcomp.APPComp.__init__(self)
        # composants applicatifs (net, business, gui):
        self.TCPMngr = None
        self.gameMngr = None
        self.gui = None
        # répertoire racine
        self.game_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        AppManager.GAME_PATH = self.game_path
        # démarrage de l'appli
        self.app_started = False
        # type d'application
        self.type_app = typeapp
        # surcharge éventuelle :
        if self.type_app == AppManager.APP_SERVER:
            self.interface = AppManager.INTERFACE_CONSOLE
        else:
            self.interface = interface
        # réseau :
        self.param_address = address
        # initialisation de l'interface :
        self._init_interface()
        # attente de la GUI :
        self._wait_GUI = True
        self.wait_for_GUI()

    def wait_for_GUI(self):
        """
        Boucle d'attente de la GUI (à ce stade les threads ne sont pas démarrés).
        """
        while self._wait_GUI:
            # Routage des tâches
            self.handleAPPQueues()

    def on_GUI_Ready(self, exobj):
        """
        Méthode appelée lorsque l'application détecte un GUIExchangeObject de type
        GUI_READY signalant que l'interface est prête à réagir.
        """
        # désactive l'attente :
        self._wait_GUI = False
        # finalise l'initialisation
        self.init_others_components()

    def init_others_components(self):
        """
        Achève l'initialisation une fois la GUI prête.
        """
        # réseau :
        self._init_network(self.param_address)
        # jeu :
        self._init_game()
        # gestion des threads :
        dojoin = True
        if self.interface in [AppManager.INTERFACE_TK, AppManager.INTERFACE_PYGAME]:
            dojoin = False
        self.start_and_join_threads(join=dojoin)

    def on_threads_started(self):
        """
        Appelée à la fin du process de démarrage et join des threads.
        """
        # appli démarrée
        self.app_started = True
        # on lance l'initialisation du jeu :
        task = lambda: self.gameMngr.init_game()
        self.sendBusinessTask(task)

    #-----> Initialisation du réseau
    def _init_network(self, appaddress):
        """
        Initialisation du composant réseau.
        
        Args:
            appaddress:  adresse passée en paramètre au constructeur de l'application
        """
        self.TCPMngr = None
        # cas particulier :
        if self.type_app == AppManager.APP_STANDALONE:
            return
        if appaddress != None and appaddress != (None, None):
            address = appaddress
        else:
            # fichier de conf :
            host = None
            port = None
            address = (None, None)
            try:
                # adresse du fichier de config :
                path_file = self.game_path + "/tcp_config.txt"
                net_txt = cio.load_text_file(path_file, splitlines=False)
                # net_txt de la forme host=&port=
                list_var_txt = net_txt.split("&")
                for var_txt in list_var_txt:
                    if var_txt.find("=") != -1:
                        splitted_var = var_txt.split("=")
                        name = splitted_var[0]
                        value = splitted_var[1]
                        if name == "host":
                            host = value
                        elif name == "port":
                            port = int(value)
                address = (host, port)
            except Exception:
                pass
        if address == (None, None):
            # adresse par défaut de la classe :
            address = AppManager.default_tcp_address
        # création du composant TCP
        if self.type_app == AppManager.APP_SERVER:
            # Serveur :
            self.TCPMngr = ctcp.CustomTCPServerContainer(address, auto_connect=True)
            # self.allow_new_connections(False)
        elif self.type_app == AppManager.APP_CLIENT:
            # client :
            self.TCPMngr = ctcp.CustomTCPThreadedClient(address, auto_connect=True)
        self.register_child_component(self.TCPMngr)

    def allow_new_connections(self, allow):
        """
        Appelée par le seveur TCP pour indiquer s'il accepte ou non de nouvelles
        connections (partie en cours).
        """
        if self.type_app == AppManager.APP_SERVER:
            self.TCPMngr.allow_new_connections(allow)

    #-----> Initialisation du jeu
    def _init_game(self):
        """
        Instancie le GameManager.
        """
        self.gameMngr = GameManager(self.type_app, self.game_path)
        self.register_child_component(self.gameMngr)

    #-----> Initialisation de l'interface
    def _init_interface(self):
        """
        Initialisation de l'interface.
        """
        self.gui = None
        if self.interface == AppManager.INTERFACE_CONSOLE:
            # interface gérée en interne
            self.gui = guicons.GUIConsole()
            self.register_child_component(self.gui)
        self.set_GUI_apptype()

    def set_GUI_apptype(self):
        """
        Transmet à l'interface son type d'app.
        """
        # Envoi à la GUI
        channel = appcomp.APPComp.GUI_CHANNEL
        dictargs = {"info": AppTypes.SET_APPTYPE, "type_app": self.type_app}
        self.set_APP_info(channel, dictargs)
