#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
**Superclasses des GUIs du jeu : logique applicative**
"""
# imports
import time
from labpyproject.core.app import app_components as appcomp
from labpyproject.apps.labpyrinthe.app.app_types import AppTypes
from labpyproject.apps.labpyrinthe.bus.game_manager import GameManager
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import LabHelper
from labpyproject.apps.labpyrinthe.gui.skinBase.zone_partie_base import ZonePartieBase
from labpyproject.apps.labpyrinthe.gui.skinBase.zone_command_base import ZoneCommandBase

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["GUIBase", "GUIBaseNoThread", "GUIBaseThreaded"]
# classes
#-----> Superclasses des interfaces principales de LabPyrinthe
class GUIBase():
    """
    Interface générique du jeu.
    """

    # propriétés statiques
    CONFIG_LOADING = "CONFIG_LOADING" #: mode chargement (initial, partie)
    CONFIG_RESIZE = "CONFIG_RESIZE" #: mode resize 
    CONFIG_MENU = "CONFIG_MENU" #: mode menu (accueil)
    CONFIG_GAME = "CONFIG_GAME" #: mode jeu (partie en cours)
    # méthodes
    def __init__(self):
        """
        Constructeur
        """
        # type d'application (client / serveur / standalone)
        self.type_app = None
        # uid :
        self.uid = None
        # config d'écran :
        self.config_screen = GUIBase.CONFIG_LOADING
        # données liées aux partie :
        self.partie_state = GameManager.INITIAL_PHASIS
        self.partie_created = False
        self.carte_published = False
        self.current_game_mode = None
        self.current_game_level = None
        # enregistrement des index d'objets d'échange (debug)
        self._guiExObj_indexlist = list()
        # création interface :
        self._gui_loaded = False
        self.zone_carte = None  # AbstractZoneCarte
        self.zone_cmd = None  # AbstractZoneCommand
        self.zone_partie = None  # AbstractZonePartie
        self.zone_bots = None  # AbstractZoneBots
        self.zone_menu = None  # AbstractZoneMenu
        self.screen_content = None  # AbstractScreenContent
        self.screen_wait = None  # AbstractScreenWait
        self.create_interface()
        # animation :
        self.animation_running = False
        self.animation_callback = None
        self.animation_dict = None
        self.animation_origdict = None
        # Mémorisation de l'objet d'échange :
        self._current_GUIExObj = None

    #-----> gestion des tâches
    def process_task(self):
        """
        Traitement de la pile d'échange, appelée par les GUIs graphiques.
        
        Rq : GUIConsole héritant de SatelliteComp, handleTask est appelée
        nativement dans la méthode run de son thread.
        """
        # traitement :
        self.handleTask()

    def allow_task_processing(self):
        """
        Permet de désactiver temporairement le dépilement des tâches. 
        Appelée dans les méthodes handleTask de GUIBaseNoThread et
        GUIBaseThreaded
        """
        allow = True
        if self.animation_running:
            # animation en cours, on bloque les tâches :
            allow = False
            self.animation_callback()
        return allow

    #-----> implémentation d'AbstractGUIComp
    def handleTask(self):
        """
        Méthode générique de dépilement de tâche.
        """
        # subclassée dans GUIBaseNoThread et GUIBaseThreaded

    def handleExchangeObject(self, exobj):
        """
        Traite un objet d'échange provenant de l'application métier.
        
        Args:
            exobj (GUIExchangeObject)
        """
        # subclassée dans GUIBaseNoThread et GUIBaseThreaded

    def sendTask(self, obj):
        """
        Empile une réponse à destination de l'application métier.
        """
        # subclassée dans GUIBaseNoThread et GUIBaseThreaded

    def handle_choice(self, obj):
        """
        Retourne l'input utilisateur, particularise la méthode "void" de appcomp.GUIComp. 
        
        Args:
            exobj (GUIExchangeObject)
        """
        # Mémorisation de l'objet :
        self._current_GUIExObj = obj
        # cas particuliers :
        # 1- affichage menu :
        typechoix = obj.dictargs["typechoix"]
        if typechoix == GameManager.CHOOSE_GAME:
            self.show_menu()
        # 2- démarrage partie :
        if typechoix == GameManager.START_GAME:
            if not self.carte_published:
                # choix différé à la fin de la publication :
                return
        # générique :
        # Message d'invite :
        msg_input = None
        if "msg_input_alt" in obj.dictargs.keys():
            # gui graphique
            msg_input = obj.dictargs["msg_input_alt"]
        elif "msg_input" in obj.dictargs.keys():
            # gui console
            msg_input = obj.dictargs["msg_input"]
        if msg_input != None:
            self.show_message(msg_input, True)
        if "msg" in obj.dictargs.keys():
            msg = obj.dictargs["msg"]
            self.show_message(msg, False)

    def erase_choice(self):
        """
        Efface la demande de choix précédente
        """
        self._current_GUIExObj = None
        self.show_message("", True)

    def show_content(self, obj):
        """
        Méthode principale d'affichage de contenu.
        """
        dictargs = obj.dictargs
        content = dictargs["content"]
        # publication :
        if content == GameManager.PUBLISH_CARTE:
            # publication complète de la carte
            self.show_carte_publication(dictargs)
        elif content == GameManager.SHOW_TXT_CARTE:
            # affichage carte txt dans écran de preolad
            self.show_carte_txt_in_preload(dictargs)
        elif content == GameManager.UPDATE_CARTE:
            # publication partielle de la carte
            self.show_carte_update(dictargs)
        elif content == GameManager.CONTENT_GAMBLE_CTX:
            # mise à jour des caractéristiques des joueurs et du coup à jouer
            self.show_content_gamble_context(dictargs)
        elif content == GameManager.CONTENT_PARTIE_SERVER:
            # affichage dédié au serveur
            self.show_content_partie_server(dictargs)
        elif content == GameManager.CONTENT_MESSAGE:
            # message contextuel :
            self.show_content_message(dictargs)
        elif content == GameManager.CONTENT_ANIM_PIXEL:
            # déplacement pixel :
            self.show_content_animation_pixel(dictargs)
        elif content == GameManager.CONTENT_HELP:
            self.toggle_help()
        elif content == GameManager.CONTENT_TYPE_PARTIE:
            self.dispatch_type_partie(dictargs)
        elif content == GameManager.CONTENT_BOT_DEAD:
            self.show_bot_dead(dictargs)
        elif content == GameManager.CONTENT_PLAYER_STATUS:
            self.show_player_status(dictargs)

    def handle_BUS_info(self, obj):
        """
        Réception d'informations en provenance de l'appli métier.
        """
        dictargs = obj.dictargs
        info = dictargs["info"]
        if info == GameManager.SET_UID:
            # mémorisation de l'uid du joueur :
            self.uid = dictargs["uid"]
        elif info == GameManager.LABHELPER_SURCHARGED:
            # paramétrage des commandes après configuration du LabHelper
            if self.zone_cmd != None:
                self.zone_cmd.post_init_controls()
        elif info == GameManager.PARTIE_INIT:
            # une nouvelle partie se crée :
            self.register_partie_state(GameManager.PARTIE_INIT)
            self.init_partie()
        elif info == GameManager.PARTIE_CHOSEN:
            # création d'une nouvelle partie
            self.register_partie_state(GameManager.PARTIE_CHOSEN)
            self.create_partie()
        elif info == GameManager.PARTIE_CREATED:
            # création d'une nouvelle partie
            self.register_partie_state(GameManager.PARTIE_CREATED)
            self.on_partie_created()
        elif info == GameManager.PARTIE_STARTED:
            # démarrage de la partie :
            self.register_partie_state(GameManager.PARTIE_STARTED)
            self.start_partie()
        elif info == GameManager.PARTIE_ENDED:
            # la partie est finie :
            self.register_partie_state(GameManager.PARTIE_ENDED)
            self.on_partie_ended()
        elif info == GameManager.NET_INFOS:
            # publication des infos réseau :
            dictdatas = dictargs["dictdatas"]
            self.show_NETInfos(dictdatas)

    def handle_APP_info(self, exobj):
        """
        L'application envoie une info au satellite.
        
        Args:
            exobj (SatelliteExchangeObject): avec exobj.typeexchange=SatelliteExchangeObject.SET_APP_INFO
        """
        # utilisée pour définir le type d'appli associé
        dictargs = exobj.dictargs
        info = dictargs["info"]
        if info == AppTypes.SET_APPTYPE:
            # définition du type d'appli
            self.type_app = dictargs["type_app"]
            self.on_app_type_defined()

    #-----> Animation :
    def start_animation_pixel(self, dictanim, dictargs):
        """
        Démarre une animation de mouvement.
        """
        # marqueur :
        self.animation_running = True
        self.animation_dict = dictanim
        self.animation_origdict = dictargs
        self.animation_callback = self.play_animation_pixel
        # initialisation :
        case = self.animation_dict["case"]
        x = self.animation_dict["x1"]
        y = self.animation_dict["y1"]
        self.zone_carte.move_case(case, x, y)

    def play_animation_pixel(self):
        """
        Joue une étape d'animation de mouvement. 
        Rq : appelée dans allow_task_processing si self.animation_running = True
        """
        # données :
        case = self.animation_dict["case"]
        x1 = self.animation_dict["x1"]
        y1 = self.animation_dict["y1"]
        x2 = self.animation_dict["x2"]
        y2 = self.animation_dict["y2"]
        duration = self.animation_dict["duration"]
        starttime = self.animation_dict["starttime"]
        prevtime = self.animation_dict["prevtime"]
        currenttime = time.perf_counter()
        ellapsedtime = currenttime - starttime
        if currenttime - prevtime < 1 / 25:
            # on vise un framerate d'animation théorique de 25 imgs / sec
            return
        if ellapsedtime < duration:
            # animation en cours
            prop = ellapsedtime / duration
            x = x1 + (x2 - x1) * prop
            y = y1 + (y2 - y1) * prop
            self.zone_carte.move_case(case, x, y)
        else:
            # fin d'animation
            self.zone_carte.move_case(case, x2, y2)
            self.animation_running = False
            self.animation_dict = None
            # confirmation :
            self.on_content_published(self.animation_origdict)

    #-----> création de l'interface
    def create_interface(self):
        """
        Initialise la création de l'interface.
        """
        # à subclasser
        pass

    def on_interface_created(self):
        """
        Informe l'app métier que la GUI a achevé la publication initiale.
        """
        # marqueur interne :
        self._gui_loaded = True
        # ref interne :
        if self.zone_carte != None:
            self.zone_carte.register_GUI(self)
        # transmission à l'app et au business :
        self.delay_action(0.01, self.signal_GUI_ready)

    #-----> Etats et configuration
    def register_partie_state(self, state):
        """
        Enregistre l'état actuel de la partie.
        """
        self.partie_state = state
        if self.zone_partie != None:
            self.zone_partie.register_partie_state(state)

    def get_partie_state(self):
        """
        Retourne l'état courant de l'interface.
        """
        return self.partie_state

    def set_configuration(self, configname):
        """
        Configure l'interface.
        """
        self.config_screen = configname
        show_wait = False
        show_main = False
        show_menu = False
        show_game = False
        if configname == GUIBase.CONFIG_LOADING:
            show_wait = True
            self.screen_wait.set_state("loading")
        elif configname == GUIBase.CONFIG_MENU:
            show_main = True
            show_menu = True
        elif configname == GUIBase.CONFIG_GAME:
            show_main = True
            show_game = True
        # affichages principaux :
        self.set_config_wait(show_wait)
        self.set_config_content(show_main)
        # contenu de type menu
        self.set_config_menu(show_menu)
        # contenu de type jeu
        if self.zone_partie != None:
            self.zone_partie.on_view_changed(show_game)
        self.set_config_game(show_game)
        # post config :
        self.post_set_configuration()

    def set_config_wait(self, show):
        """
        Configuration écran d'attente
        
        Args:
            show (boolean)
        """
        # à subclasser
        pass

    def set_config_content(self, show):
        """
        Configuration écran de contenu (menu, partie)
        
        Args:
            show (boolean)
        """
        # à subclasser
        pass

    def set_config_menu(self, show):
        """
        Configuration écran menu principal
        
        Args:
            show (boolean)
        """
        # à subclasser
        pass

    def set_config_game(self, show):
        """
        Configuration écran partie
        
        Args:
            show (boolean)
        """
        # à subclasser
        pass

    def post_set_configuration(self):
        """
        Finalisation du process de configuration de l'interface.
        """
        # à subclasser
        pass

    #-----> choix
    def on_choice_made(self, cmd):
        """
        Appelée par les contrôles.
        """
        exobj = self._current_GUIExObj
        if exobj != None:
            # réponse
            exobj.dictargs["choix"] = cmd
            exobj.typeexchange = appcomp.GUIExchangeObject.RETURN_USER_CHOICE
        else:
            # commande spontannée
            code = appcomp.GUIExchangeObject.SEND_USER_COMMAND
            dictargs = {"typechoix": GameManager.QUEUE_CMD, "choix": cmd}
            exobj = appcomp.GUIExchangeObject(code, dictargs)
        self.sendTask(exobj)
        # message et input :
        self.erase_choice()
        self.show_message("", False)

    def user_start_partie(self):
        """
        Envoie une commande de démarrage de la partie.
        """
        exobj = dictargs = None
        if self._current_GUIExObj != None:
            typechoix = self._current_GUIExObj.dictargs["typechoix"]
            if typechoix == GameManager.START_GAME:
                exobj = self._current_GUIExObj
                exobj.typeexchange = appcomp.GUIExchangeObject.RETURN_USER_CHOICE
                dictargs = exobj.dictargs
        if exobj == None:
            dictargs = {"typechoix": GameManager.START_GAME, "uid": self.uid}
            code = appcomp.GUIExchangeObject.RETURN_USER_CHOICE
            exobj = appcomp.GUIExchangeObject(code, dictargs)
        dictargs["choix"] = LabHelper.CHAR_START
        self.sendTask(exobj)

    def ask_goto_menu(self):
        """
        Retour au menu (quitte la partie en cours).
        """
        # transmission à l'app métier :
        code = appcomp.GUIExchangeObject.SET_GUI_INFO
        dictargs = {"ask_action": GameManager.ASK_GOTO_MENU}
        exobj = appcomp.GUIExchangeObject(code, dictargs)
        self.sendTask(exobj)

    def ask_quit_game(self):
        """
        Quitte le jeu.
        """
        # transmission à l'app métier :
        code = appcomp.GUIExchangeObject.SET_GUI_INFO
        dictargs = {"ask_action": GameManager.ASK_QUIT_APP}
        exobj = appcomp.GUIExchangeObject(code, dictargs)
        self.sendTask(exobj)

    #-----> Process de création d'une partie
    def init_partie(self):
        """
        Ré initialise l'interface
        """
        # ré init menu :
        if self.zone_menu != None:
            self.zone_menu.re_initialise()
        # barre de commande :
        if self.zone_cmd != None:
            self.zone_cmd.re_initialise()
            self.zone_cmd.set_state(ZoneCommandBase.STATE_MENU)
        # partie :
        if self.zone_partie != None:
            self.zone_partie.re_initialise()
        # données liées aux partie :
        self.partie_created = False
        self.carte_published = False

    def create_partie(self):
        """
        Partie en cours de création
        """
        # message et input :
        self.erase_choice()
        self.show_message("", False)
        # partie
        if self.zone_partie != None:
            self.zone_partie.set_state(ZonePartieBase.STATE_CREATING)
        # affichage
        self.show_partie()

    def on_partie_created(self):
        """
        Process de création de la partie achevé côté business, la publication peut
        prendre plus de temps
        """
        self.partie_created = True
        # partie : affichage déclenché par zone_partie sur l'evt on_carte_published
        # zone commande : affichée dans _on_carte_published

    def start_partie(self):
        """
        Démarrage de la partie
        """
        # message et input :
        self.erase_choice()
        # activation des commandes de jeu :
        if self.zone_cmd != None:
            self.zone_cmd.set_state(ZoneCommandBase.STATE_GAME)
            if self.current_game_mode == GameManager.GAME_MODE_PARTIE:
                self.zone_cmd.active_commande()

    def on_partie_ended(self):
        """
        Partie terminée
        """
        # désactivation des commandes de jeu :
        if self.zone_cmd != None:
            self.zone_cmd.unactive_commande()

    def _on_carte_published(self):
        """
        Appelée à chaque fois que la carte a été mise à jour graphiquement
        """
        self.carte_published = True
        # premier affichage :
        if self.partie_state in [
            GameManager.PARTIE_CREATED,
            GameManager.PARTIE_STARTED,
        ]:
            # config :
            self.set_configuration(GUIBase.CONFIG_GAME)
            # zone commande :
            if self.zone_cmd != None:
                self.zone_cmd.set_state(ZoneCommandBase.STATE_GAME)
                self.zone_cmd.unactive_commande()
            # choix start :
            if self._current_GUIExObj != None:
                typechoix = self._current_GUIExObj.dictargs["typechoix"]
                if typechoix == GameManager.START_GAME:
                    self.handle_choice(self._current_GUIExObj)

    def on_content_published(self, origdict):
        """
        Indique que le dernier affichage a été réalisé
        """
        # affichage suivi :
        gui_order = None
        if "gui_order" in origdict.keys() and origdict["gui_order"] != None:
            gui_order = int(origdict["gui_order"])
        # Informe le GameManager que la publication est effectuée :
        code = appcomp.GUIExchangeObject.SET_GUI_INFO
        dictargs = {"GUIState": GameManager.CONTENT_PUBLISHED}
        if gui_order != None:
            dictargs["gui_order"] = gui_order
        exobj = appcomp.GUIExchangeObject(code, dictargs)
        self.sendTask(exobj)

    #-----> informations et affichages
    def on_app_type_defined(self):
        """
        Appelée lorsque la GUI connait le type d'application associée (client, serveur, standalone)
        """
        # propagation du type
        if self.zone_partie != None:
            self.zone_partie.register_APPType(self.type_app)
        if self.zone_cmd != None:
            self.zone_cmd.register_APPType(self.type_app)
        # association zone_bots:
        if self.zone_bots != None:
            self.zone_bots.registerGUI(self)
        # à subclasser

    def dispatch_type_partie(self, dictargs):
        """
        Affichage du type de partie.
        """
        # maj des propriétés internes :
        self.current_game_mode = dictargs["mode"]
        self.current_game_level = dictargs["niveau"]
        # commandes de jeu :
        if self.current_game_mode != GameManager.GAME_MODE_PARTIE:
            if self.zone_cmd != None:
                self.zone_cmd.unactive_commande()
        # à subclasser...

    def show_carte_publication(self, dictargs):
        """
        Affichage / mise à jour de la carte
        """
        if not self.carte_published:
            if self.config_screen != GUIBase.CONFIG_GAME:
                # cas d'un client connecté alors que la partie est crée
                # mais non démarrée encore
                self.set_configuration(GUIBase.CONFIG_GAME)
                # zone commande
                if self.zone_cmd != None:
                    self.zone_cmd.set_state(ZoneCommandBase.STATE_MENU)
                self.refresh_view()
            # écran d'attente:
            if self.zone_partie != None:
                self.zone_partie.set_state(ZonePartieBase.STATE_CREATING)
        # affichage des robots :
        if "gambleinfos" in dictargs.keys():
            robotlist = dictargs["robots"]
            gambleinfos = dictargs["gambleinfos"]
            if self.zone_bots != None:
                self.zone_bots.publish_robotlist(robotlist, gambleinfos)
            if self.zone_carte != None:
                self.zone_carte.highlight_player(robotlist, gambleinfos)
        # affichage de la carte
        if self.zone_carte != None:
            self.zone_carte.publish_carte(dictargs)
        # post traitement :
        self._on_carte_published()
        # confirmation :
        self.on_content_published(dictargs)

    def show_carte_txt_in_preload(self, dictargs):
        """
        Affichage de la carte txt dans l'écran de preload de partie
        """
        chaine = dictargs["txt"]
        if self.zone_partie != None:
            self.zone_partie.show_carte_txt_in_preload(chaine)

    def show_carte_update(self, dictargs):
        """
        Update partiel de la carte
        """
        # publication partielle :
        if self.zone_carte != None:
            self.zone_carte.update_carte(dictargs)
        # confirmation :
        self.on_content_published(dictargs)

    def show_content_partie_server(self, dictargs):
        """
        Affichage spécifique serveur : infos partie.
        
        Args:
            dictargs (dict): {"content": GameManager.CONTENT_PARTIE_SERVER, "msg":}
        """
        # à subclasser
        pass

    def show_content_gamble_context(self, dictargs):
        """
        Affichage / mise à jour des infos robots, du coup joué
        """
        robotlist = dictargs["robots"]
        gambleinfos = dictargs["gambleinfos"]
        if robotlist != None:
            if self.uid != None:
                for rd in robotlist:
                    # Synchro commande :
                    if rd["uid"] == self.uid:
                        self.zone_cmd.update_player_power(rd)
                # infos bots :
                if self.zone_bots != None:
                    self.zone_bots.publish_robotlist(robotlist, gambleinfos)
                # highlights :
                if self.zone_carte != None:
                    self.zone_carte.highlight_player(robotlist, gambleinfos)
        # confirmation :
        self.on_content_published(dictargs)

    def show_bot_dead(self, dictargs):
        """
        Appelée pour lors de l'élimination de dictargs["robot"].
        """
        if "robot" in dictargs.keys():
            robot = dictargs["robot"]
            if robot != None:
                if self.zone_bots != None:
                    self.zone_bots.show_bot_dead(robot)
                if self.zone_carte != None:
                    self.zone_carte.show_bot_dead(robot)

    def show_content_message(self, dictargs):
        """
        Affichage d'un message contextuel
        """
        txt = dictargs["txt"]
        self.show_message(txt, False)
        # pas de confirmation pour les messages

    def show_content_animation_pixel(self, dictargs):
        """
        Affichage d'une animation de mouvement par pixel 
        (si LabHelper.ANIMATION_RESOLUTION == LabHelper.ANIMATION_RESOLUTION_PIXEL)
        """
        # données :
        case = dictargs["case"]
        x1, y1 = dictargs["coords1"]
        x2, y2 = dictargs["coords2"]
        duration = dictargs["duration"]
        starttime = time.perf_counter()
        dictanim = {
            "case": case,
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "duration": duration,
            "starttime": starttime,
            "prevtime": starttime,
        }
        # démarre l'animation :
        self.start_animation_pixel(dictanim, dictargs)

    def show_partie(self):
        """
        Ecran partie
        """
        self.set_configuration(GUIBase.CONFIG_GAME)

    def show_menu(self):
        """
        Ecran menu
        """
        self.set_configuration(GUIBase.CONFIG_MENU)

    def show_message(self, msg, is_input):
        """
        Affichage de message ou consigne
        """
        if self.zone_cmd != None:
            self.zone_cmd.show_message(msg, is_input)

    def show_NETInfos(self, dictargs):
        """
        Affichage des infos réseau.
        dictargs : dict généré par la méthode get_network_infos du
        composant réseau associé
        """
        # à subclasser

    def toggle_help(self):
        """
        Affichage / masquage aide
        """
        # à subclasser
        pass

    def refresh_view(self):
        """
        Réalise un update de l'affichage
        """
        # à subclasser
        pass

    #-----> Fermeture de l'application
    def shutdown(self):
        """
        Fermeture de l'interface
        """
        # à subclasser
        pass

    def show_player_status(self, dictargs):
        """
        Affichage des infos de statut du joueur.
        """
        # à subclasser
        pass


# GUIBase sans thread :
class GUIBaseNoThread(GUIBase, appcomp.GUICompNoThread):
    """
    Subclasse de GUIBase destinée à un usage sans thread (Tkinter, Pygame...)
    """

    def __init__(self):
        """
        Constructeur
        """
        # init composant d'interface générique
        appcomp.GUICompNoThread.__init__(self)
        # init GUIBase :
        GUIBase.__init__(self)

    #-----> Surcharge de GUIBase / AbstractGUIComp
    def handleExchangeObject(self, exobj):
        """
        Traite un objet d'échange provenant de l'application métier.
        
        Args:
            exobj (GUIExchangeObject)
        """
        # générique
        appcomp.GUICompNoThread.handleExchangeObject(self, exobj)
        # debug :
        self._guiExObj_indexlist.append(exobj.index)

    def handleTask(self):
        """
        Méthode générique de dépilement de tâche. 
        A appeler dans la méthode run du thread associé au composant
        """
        if self.allow_task_processing():
            # générique
            appcomp.GUICompNoThread.handleTask(self)

    def sendTask(self, obj):
        """
        Empile une réponse à destination de l'application métier
        """
        appcomp.GUICompNoThread.sendTask(self, obj)

    def shutdown(self):
        """
        Fermeture de l'interface
        """
        # générique
        appcomp.GUICompNoThread.shutdown(self)


# GUIBase avec thread
class GUIBaseThreaded(GUIBase, appcomp.GUIComp):
    """
    Subclasse de GUIBase destinée à un usage avec thread (console)
    """

    def __init__(self):
        """
        Constructeur
        """
        # init composant d'interface générique
        appcomp.GUIComp.__init__(self)
        # init GUIBase :
        GUIBase.__init__(self)

    #-----> Surcharge de GUIBase / AbstractGUIComp
    def handleExchangeObject(self, exobj):
        """
        Traite un objet d'échange provenant de l'application métier.
        
        Args:
            exobj (GUIExchangeObject)
        """
        # générique
        appcomp.GUIComp.handleExchangeObject(self, exobj)
        # debug :
        self._guiExObj_indexlist.append(exobj.index)

    def handleTask(self):
        """
        Méthode générique de dépilement de tâche. 
        A appeler dans la méthode run du thread associé au composant
        """
        if self.allow_task_processing():
            # générique
            appcomp.GUIComp.handleTask(self)

    def sendTask(self, obj):
        """
        Empile une réponse à destination de l'application métier
        """
        appcomp.GUIComp.sendTask(self, obj)

    def shutdown(self):
        """
        Fermeture de l'interface
        """
        # générique
        appcomp.GUIComp.shutdown(self)
