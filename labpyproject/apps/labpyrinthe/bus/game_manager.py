#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
**GameManager**: composant BUSINESS de l'application.
"""
# imports :
import time
import socket
import labpyproject.core.random.custom_random as cr
import labpyproject.core.net.custom_TCP as ctcp
from labpyproject.core.app import app_components as appcomp
from labpyproject.apps.labpyrinthe.app.app_types import AppTypes
from labpyproject.apps.labpyrinthe.gui.skinBase.colors import ColorHelper
from labpyproject.apps.labpyrinthe.bus.helpers.exchange_helper import ExchangeHelper
from labpyproject.apps.labpyrinthe.bus.helpers.lab_manager import LabManager
from labpyproject.apps.labpyrinthe.bus.helpers.game_configuration import (
    GameConfiguration,
)
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import LabHelper
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseRobot
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseBonus
from labpyproject.apps.labpyrinthe.bus.model.player import LabPlayer
from labpyproject.apps.labpyrinthe.bus.commands.cmd_helper import CommandHelper

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["GameManager"]
# classes
class GameManager(appcomp.BUSINESSComp):
    """
    **Manager principal du jeu**, supportant les rôles standalone, client ou serveur.
    
    Utilise par composition une instance de LabManager (utilisant elle même d'autres
    managers/helpers par composition).
    
    .. note::
       Prototype fonctionnel. Classe trop lourde (> 3000 lignes), à reconcevoir de façon 
       plus générique dans une version de production.
    
    .. highlight:: none
    Plan du code source :
    
    ::
    
        A- Tâches : NET & GUI
            A.1- Réception tâches GUI
            A.2- Réception tâches NET
            A.3- Envoi vers GUI et NET 
            A.4- Unicité des requêtes
        B- Phases de l'application
            B.1- Phase initiale
            B.2- Phases Partie
                B.2.1- PARTIE_INIT
                B.2.2- PARTIE_CHOSEN
                B.2.3- PARTIE_CREATED
                B.2.4- PARTIE_STARTED
                B.2.5- PARTIE_ENDED
            B.3- Phases jeu (coups)
                B.3.1- Loop Master
                B.3.2- Utilitaires Master
                B.3.3- Méthodes Slave
                B.3.4- Application d'un coup
                B.3.5- Evénéments de jeu
            B.4- Interruptions
        C- Connection/ids des joueurs
            C.1- Gestion des uids des joueurs
            C.2- Connection(s) client(s)
            C.3- Structure de suivi des clients
        D- Contrôle de cohérence (client/serveur)
            D.1- Cohérence (serveur)
            D.2- Cohérence (client)
        E- Gestion des choix utilisateurs
            E.1- Mécanique générale
            E.2- Saisie adresse serveur
            E.3- Choix partie
            E.4- Démarrer la partie
            E.5- Commande de jeu
        F- Affichages (GUI)
            F.1- Affichages non suivis
            F.2- Affichages suivis (carte)
                F.2.1- Mécanique générique
                F.2.2- Affichages avec callback
            F.3- Statut de publication (carte)
        G- Création d'une partie
        H- Gestion des couleurs associées aux joueurs
    .. highlight:: default    
    """

    # Propriétés statiques
    # Phase initiale :
    INITIAL_PHASIS = "INITIAL_PHASIS"  #: phase globale d'initialisation
    # Phases d'une partie :
    PARTIE_INIT = "PARTIE_INIT"  #: phase partie init
    PARTIE_CHOSEN = "PARTIE_CHOSEN"  #: phase partie choisie
    PARTIE_CREATED = "PARTIE_CREATED"  #: phase partie crée
    PARTIE_STARTED = "PARTIE_STARTED"  #: phase partie démarrée
    PARTIE_ENDED = "PARTIE_ENDED"  #: phase partie terminée
    SHUTDOWN = "SHUTDOWN"  #: phase globale d'arrêt
    # Modes : partie ou démo
    GAME_MODE_PARTIE = "GAME_MODE_PARTIE"  #: mode de jeu interactif (partie)
    GAME_MODE_DEMO = "GAME_MODE_DEMO"  #: mode de jeu auto (démo)
    # Commandes & infos client / serveur
    # durée d'attente avant vérification des connections clients (par ping)
    PING_DELAY = 4  #: durée d'attente avant vérification des connections clients
    #  * server -> client :
    SET_UID = "SET_UID"  #: [svr-> clt] affectation uid client
    CHOOSE_GAME = "CHOOSE_GAME"  #: [svr-> clt] choix du jeu
    START_GAME = "START_GAME"  #: [svr-> clt] démarrage du jeu
    SHOW_MESSAGE = "SHOW_MESSAGE"  #: [svr-> clt] affichage d'un message
    ENTER_CMD = "ENTER_CMD"  #: [svr-> clt] demande une action de jeu
    BUILD_LAB = "BUILD_LAB"  #: [svr-> clt] publication intégrale de la carte
    UPDATE_XTRAS = "UPDATE_XTRAS"  #: [svr-> clt] mise à jour mines et bonus
    UPDATE_BOTS = "UPDATE_BOTS"  #: [svr-> clt] mise à jour des joueurs
    REORDER_BOTS = "REORDER_BOTS"  #: [svr-> clt] modification de l'ordre des joueurs
    PLAY_CMD = "PLAY_CMD"  #: [svr-> clt] application d'une action de jeu
    UPDATE_GAMBLE_CONTEXT = (
        "UPDATE_GAMBLE_CONTEXT"  
    ) #: [svr-> clt] mise à jour du contexte du coup
    UPDATE_PLAYER_STATUS = (
        "UPDATE_PLAYER_STATUS"  
    ) #: [svr-> clt] mise à jour du statut d'un joueur
    SYNC_LAB_CODES = [
        UPDATE_GAMBLE_CONTEXT,
        PLAY_CMD,
        UPDATE_XTRAS,
    ]  #: [svr] codes commandes réservés aux clients synchronisés
    #  * client -> serveur
    GAME_CHOICE = "GAME_CHOICE"  #: [clt -> svr] retourne le jeu choisi
    GET_FULL_LAB = "GET_FULL_LAB"  #: [clt -> svr] demande de resynchro de la carte
    QUEUE_CMD = "QUEUE_CMD"  #: [clt -> svr] empile une action (non implémenté)
    RESET_QUEUE = (
        "RESET_QUEUE"  
    ) #: [clt -> svr] efface les actions empilées (non implémenté)
    CHECK_CHANGELOG_KEY = "CHECK_CHANGELOG_KEY"  #: [clt -> svr] retourne la clef de vérification de synchro de la carte
    BUILD_LAB_DONE = "BUILD_LAB_DONE"  #: [clt -> svr] indique que la publication de la carte est achevée
    # codes de commande à envoyer sans accusé de réception
    UNCONFIRMED_CODES = [SHOW_MESSAGE]  #: code de commande sans accusé de réception
    # Interractions BUS / GUI :
    #  * BUS->GUI
    ENTER_NET_ADDRESS = (
        "ENTER_NET_ADDRESS"  
    ) #: [bus -> gui] demande de saisie de l'adresse du serveur
    SET_APPTYPE = "SET_APPTYPE"  #: [bus -> gui] définition du type d'application
    NET_INFOS = "NET_INFOS"  #: [bus -> gui] infos réseau génériques
    LABHELPER_SURCHARGED = "LABHELPER_SURCHARGED"  #: [bus -> gui] modification des chars de parsing, affichage et commande
    # * GUI->BUS infos
    CONTENT_PUBLISHED = "CONTENT_PUBLISHED"  #: [gui -> bus] indique que l'affichage demandé a été effectué
    ASK_GOTO_MENU = "ASK_GOTO_MENU"  #: [gui -> bus] demande de retour au menu
    ASK_QUIT_APP = "ASK_QUIT_APP"  #: [gui -> bus] demande à quitter le jeu
    # * types de contenus à afficher :
    PUBLISH_CARTE = (
        "PUBLISH_CARTE"  
    ) #: [type de contenu] publication complète de la carte
    SHOW_TXT_CARTE = "SHOW_TXT_CARTE"  #: [type de contenu]  affichage carte txt dans écran de preload
    UPDATE_CARTE = (
        "UPDATE_CARTE"  
    ) #: [type de contenu]  publication partielle de la carte
    CONTENT_TYPE_PARTIE = "CONTENT_TYPE_PARTIE"  #: [type de contenu] infos partie
    CONTENT_GAMBLE_CTX = "CONTENT_GAMBLE_CTX"  #: [type de contenu] contexte du coup
    CONTENT_PARTIE_SERVER = (
        "CONTENT_PARTIE_SERVER"  
    ) #: [type de contenu] résumé du coup (svr)
    CONTENT_MESSAGE = "CONTENT_MESSAGE"  #: [type de contenu] message
    CONTENT_ANIM_PIXEL = (
        "CONTENT_ANIM_PIXEL"  
    ) #: [type de contenu] animation de déplacement fine
    CONTENT_BOT_DEAD = "CONTENT_BOT_DEAD"  #: [type de contenu] mort d'un joueur
    CONTENT_HELP = "CONTENT_HELP"  #: [type de contenu] aide
    CONTENT_PLAYER_STATUS = (
        "CONTENT_PLAYER_STATUS"  
    ) #: [type de contenu] statut d'un joueur
    # constructeur :
    def __init__(self, type_app, game_path):
        """
        Constructeur
        
        Args:
            type_app : AppTypes.APP_SERVER (serveur), AppTypes.APP_CLIENT (client) ou AppTypes.APP_STANDALONE
            game_path : racine du jeu
        """
        # Init superclasse appcomp.BUSINESSComp :
        appcomp.BUSINESSComp.__init__(self)
        # lock de traitement des tâches réseau :
        self._lock_NET_tasks = False
        # liste de tâches réseau différées :
        self._differed_tasks_list = list()
        # état de l'interface :
        self._GUI_ready = False
        # uid :
        self.uid = None
        # type d'application (client / serveur / standalone)
        self.type_app = type_app
        if self.type_app == AppTypes.APP_SERVER:
            self.uid = "lpsvr"
        # list d'uid de requêtes :
        self.requestuidlist = list()
        # Manager principal du jeu?
        if self.type_app == AppTypes.APP_CLIENT:
            self.master = False
        else:
            self.master = True
        # racine du jeu :
        self.game_path = game_path
        # manager de carte :
        self.labMngr = LabManager(self)
        # liste de joueurs :
        self.playerlist = list()
        # gestion des couleurs des joueurs
        self.playercolors = None
        self._init_players_colors()
        # config : surcharge éventuelle des params par défaut
        # self.configure_labyrinthe()
        # connection initiale :
        self.initial_connection_done = False
        # état de la connection principale :
        self.connection_status = ctcp.CustomRequestHelper.STATUS_DISCONNECTED
        # état de la connection serveur (pour un client) :
        self.server_connection_status = ctcp.CustomRequestHelper.STATUS_DISCONNECTED
        # phase partie :
        self.partie_phasis = GameManager.INITIAL_PHASIS
        # "versionning" de la carte : préfixée à changelog_key pour les contrôles de cohérence
        # 0 : non publiée
        # 1 : publication initiale
        # 2 : ordre des bots (si serveur)
        # 3... : coups et ajouts d'Extras successifs
        self.carte_version = 0
        # paramètres de jeu :
        # - partie
        self.check_creation = False  # active la boucle de synchro des clients lors de la création d'une partie
        self._clients_pub_launched = (
            False  # publication initiale du lab lancée côté clients?
        )
        self.partie_init_done = False
        self.current_game_mode = None
        self.current_game_level = None
        self.carte_initiale = None
        self.carte_created = False
        self.carte_builded = False
        self.bots_added = False
        self.partie_started = False  # à gérer avec self.partie_phasis todo
        # - synchro des clients
        self._current_sync_uid_list = (
            None  # liste d'uid de clients à contrôller / synchro
        )
        self._sync_clients_dict = None  # dict de gestion de synchro des clients
        self.wait_clients_gamble_keys = False
        self.wait_client_resync = False
        self.wait_clients_XTras_keys = False
        self._wait_start_time = 0
        # - clef de synchro
        self._gamble_key = None
        # - tour de jeu
        self.gamble_start_time = None
        self.current_player_indice = None
        self.current_cmd_asked = False
        self.current_cmd = None
        self.current_cmd_validated = False
        self.current_dictcmd = None
        self.current_consequences = None
        self.current_gamble_case = None
        self.current_gamble_indice = None  # indice du coup joué durant le tour
        self.current_gamble_total = None  # nombre total de coups à jouer durant le tour
        self.gamblenumber = 0  # dénombrement des coups d'une partie
        self._bots_killed_during_gamble = None
        self.gambleinfos = None
        # - sous étapes de gestion d'un coup
        self.gambleloopdone = True
        self.wait_player_choice = False
        self.applying_gamble = False
        self.gamble_applied = False
        self.gamble_XTras_updated = False
        self.gamble_ended = False
        # contrôle de l'affichage de la carte :
        self.gui_increment = 0
        self.gui_orders_dict = None
        self.content_published = False

    def handleTask(self):
        """
        Méthode générique de dépilement de tâche.
        
        Plutôt que de créer un thread fils dédié à la boucle de gestion du jeu, 
        on surcharge cette méthode.
        """
        # générique :
        appcomp.BUSINESSComp.handleTask(self)
        # spécifique :
        if self.master:
            if self.partie_started:
                # gestion des coups
                self.manage_game_loop()
            elif self.check_creation:
                # process de création de partie (sync clients)
                self.manage_creation_loop()

    def is_master(self):
        """
        Indique si le manager de jeu est maitre (server, standalone) ou esclave (client).
        """
        return self.master

    #-----> A- Tâches : NET & GUI
    #-----> A.1- Réception tâches GUI :
    def on_GUI_Ready(self, exobj):
        """
        L'interface indique qu'elle est prête à réagir.
        """
        # marqueur :
        self._GUI_ready = True

    def handle_returned_choice(self, exobj):
        """
        La GUI retourne le choix utilisateur en réponse à ASK_USER_CHOICE.
        """
        self.check_user_choice(exobj)

    def handle_user_command(self, exobj):
        """
        La GUI envoie une commande utilisateur spontannée.
        
        avec exobj.dictargs = {"typechoix":GameManager.QUEUE_CMD, "choix":}
        """
        cmd = exobj.dictargs["choix"]
        if cmd in ["net_dis", "net_conn", "net_shut", "net_add"]:
            # debug : test réseau
            net_code = dictargs = None
            if cmd == "net_dis":
                net_code = appcomp.NETExchangeObject.DISCONNECT
            elif cmd == "net_conn":
                net_code = appcomp.NETExchangeObject.CONNECT
            elif cmd == "net_shut":
                net_code = appcomp.NETExchangeObject.NET_SHUTDOWN
            elif cmd == "net_add":
                net_code = appcomp.NETExchangeObject.SET_ADDRESS
                dictargs = {"port": 5800}
            if net_code != None:
                exobj = appcomp.NETExchangeObject(net_code, dictargs=dictargs)
                self.sendTask(exobj)
        else:
            # cas général
            exobj.dictargs["uid"] = self.uid
            self.check_user_choice(exobj)

    def handle_GUI_info(self, exobj):
        """
        La GUI envoie une information
        """
        dictargs = exobj.dictargs
        if "GUIState" in dictargs.keys():
            # indicateur d'état de l'interface :
            if dictargs["GUIState"] == GameManager.CONTENT_PUBLISHED:
                # dernière action d'affichage de contenu confirmée :
                self.on_content_published(dictargs)
        elif "ask_action" in dictargs.keys():
            if dictargs["ask_action"] == GameManager.ASK_GOTO_MENU:
                # demande de retour au menu
                self.goto_menu()
            if dictargs["ask_action"] == GameManager.ASK_QUIT_APP:
                # demande de fermeture de l'application
                self.quit_game()

    #-----> A.2- Réception tâches NET:
    def handle_NET_info(self, exobj):
        """
        Le composant réseau envoie une information.
        """
        dictargs = exobj.dictargs
        # Traitement interne :
        if self.type_app == AppTypes.APP_SERVER:
            self._server_check_connections(dictargs)
        elif self.type_app == AppTypes.APP_CLIENT:
            self._client_check_connections(dictargs)
        # Envoi à la GUI :
        self.dispatch_NETInfos(dictargs)
        # Phase initiale :
        if self.partie_phasis == GameManager.INITIAL_PHASIS:
            self.init_game()

    def _server_check_connections(self, dictargs):
        """
        Met à jour l'état des connections à partir des logs transmis par le
        composant serveur.
        """
        # connection du serveur :
        self.connection_status = dictargs["server"]["connection_status"]
        # connection des clients :
        clientdict = dictargs["clients"]
        for uid in clientdict:
            conn_status = clientdict[uid]["client_status"]
            player = self.get_player_by_uid(uid)
            if player != None:
                was_joignable = bool(player.joignable)
                if conn_status == ctcp.CustomRequestHelper.STATUS_CONNECTED:
                    player.joignable = True
                else:
                    player.joignable = False
                player.connection_status = conn_status
                if player.joignable != was_joignable:
                    self.on_player_connection_status_changed(uid)

    def _client_check_connections(self, dictargs):
        """
        Met à jour l'état des connections à partir des logs transmis par le
        composant client.
        """
        # connection client :
        self.connection_status = dictargs["server"]["connection_status"]
        # état du serveur :
        self.server_connection_status = dictargs["server"]["server_status"]
        # ...

    def NET_signal_error(self, exobj):
        """
        Le composant réseau informe d'une erreur de connection.
        
        Remarques : 
        
        - connection concernée = la connection principale client -> serveur,
          soit read pour le serveur et write pour le client. 
        - l'état des autres connections est décrit dans le dict reçu par handle_NET_info.
        """
        # Affichage du message d'erreur :
        msg = exobj.dictargs["msg"]
        self.affiche_message(msg)
        # Input saisie d'adresse :
        if self.type_app == AppTypes.APP_CLIENT and not self.initial_connection_done:
            self.ask_user_choice({"typechoix": GameManager.ENTER_NET_ADDRESS})

    def NET_send_status(self, exobj):
        """
        Le composant réseau informe de son état de connection.
        
        exobj.dictargs={"connection_status":, "netcode":NETExchangeObject.NET_STATUS, "msg":}
        
        avec connection_status ayant pour valeur :
        
        - STATUS_SHUTDOWN = "STATUS_SHUTDOWN" # arrêt définiif
        - STATUS_DISCONNECTED = "STATUS_DISCONNECTED" # arrêt temporaire
        - STATUS_ERROR_CONNECTION = "STATUS_ERROR_CONNECTION" # erreur
        - STATUS_UNDEFINED = "STATUS_UNDEFINED" # probablement en erreur
        - STATUS_CONNECTED = "STATUS_CONNECTED" # active
        - STATUS_REJECTED = "STATUS_REJECTED" # connection refusée
        
        Rq : V1 ne concerne que la connection principale au serveur.
        """
        # Statut de la connection principale :
        conn_status = exobj.dictargs["connection_status"]
        if (
            not self.initial_connection_done
            and conn_status == ctcp.CustomRequestHelper.STATUS_CONNECTED
        ):
            self.initial_connection_done = True
        # Affichage du message :
        if conn_status != ctcp.CustomRequestHelper.STATUS_CONNECTED:
            msg = exobj.dictargs["msg"]
            self.affiche_message(msg)

    def NET_signal_send_error(self, exobj):
        """
        Le composant réseau signale un envoi en erreur.
        
        Server : ne signale que les erreurs non fatales (le client est bien connecté), 
        l'erreur est probablement liée à un problème de décodage unicode (du à une erreur 
        d'encodage utf8 en bytes).
        exob.dictargs = {"msg":message initial, "confirmrecept":bool, "clients":liste non vide d'uids}
        
        Client : signale toutes les erreurs d'envoi, quelques soient les statuts de 
        connection du serveur et du client.
        exob.dictargs = {"msg":message initial, "confirmrecept":bool}
        """
        # serveur :
        if self.type_app == AppTypes.APP_SERVER:
            dictargs = exobj.dictargs
            confirmrecept = dictargs["confirmrecept"]
            if confirmrecept:
                # catégorie de requètes importantes :
                clients = dictargs["clients"]
                msg = dictargs["msg"]
                # on décode le message :
                cmd, kwargs = CommandHelper.split_game_cmd(msg)
                if cmd == None or kwargs == None:
                    return
                # on retente l'envoi:
                self.fire_game_event(cmd, dictargs=kwargs, uid=clients, suffix="resend")

    def handle_NET_request(self, exobj):
        """
        Le composant réseau transmet une requête reçue.
        """
        # La tâche doit elle être différée?
        if not self.ready_for_NET_tasks():
            self._differed_tasks_list.append(exobj)
            return
        # Traitement immédiat :
        dictargs = exobj.dictargs
        uid = dictargs["uid"]
        netcode = dictargs["netcode"]
        msg = None
        if "msg" in dictargs.keys():
            msg = dictargs["msg"]
        game_related = False
        # Traitement des requêtes liées aux problématiques réseau :
        if self.type_app == AppTypes.APP_SERVER:
            # contexte serveur :
            if netcode == ctcp.CustomRequestHelper.ASK_FOR_UID:
                # enregistrement d'un client distant (on le suppose humain)
                self.player_connected(uid)
            elif netcode == ctcp.CustomRequestHelper.SET_CLIENT_READ_INFOS:
                # canal serveur -> client défini :
                self.player_joignable(uid)
            elif netcode in [
                ctcp.CustomRequestHelper.CLIENT_SHUTDOWN,
                ctcp.CustomRequestHelper.CLIENT_DISCONNECTED,
                ctcp.CustomRequestHelper.CLIENT_CONNECTED,
            ]:
                # modification de la connection d'un client :
                self.on_player_connection_status_changed(uid)
            else:
                game_related = True
        elif self.type_app == AppTypes.APP_CLIENT:
            # contexte client connecté :
            if netcode in [
                ctcp.CustomRequestHelper.SERVER_SHUTDOWN,
                ctcp.CustomRequestHelper.SERVER_DISCONNECTED,
                ctcp.CustomRequestHelper.SERVER_CONNECTED,
            ]:
                # modification de la connection du serveur :
                # todo
                pass
            elif netcode == ctcp.CustomRequestHelper.CONNECTION_REFUSED:
                # connection refusée par le serveur (client TCP déconnecté)
                # todo
                pass
            elif netcode == ctcp.CustomRequestHelper.UID_SET_BY_SERVER:
                # le serveur vient d'affecter l'uid :
                self.register_my_uid(uid)
            else:
                game_related = True
        # Traitement des requêtes liées au jeu :
        if game_related:
            uid = dictargs["uid"]
            # Filtrage des requêtes invalides
            cmd, kwargs = CommandHelper.split_game_cmd(msg)
            if cmd == None or kwargs == None:
                return
            # Traitement unique des requètes :
            if "comuid" in kwargs.keys() and kwargs["comuid"] == None:
                kwargs["comuid"] = self._generate_request_uid("abs")
            comuid = kwargs["comuid"]
            done = self._is_request_done(comuid)
            if done:
                # Requête déja traitée
                return
            self._valide_request_entry(comuid)
            # Traitement unique d'une requête valide :
            if self.type_app == AppTypes.APP_SERVER:
                self._server_handle_game_cmd(uid, cmd, kwargs)
            elif self.type_app == AppTypes.APP_CLIENT:
                self._client_handle_game_cmd(uid, cmd, kwargs)

    def _server_handle_game_cmd(self, uid, cmd, kwargs):
        """
        Traitement des commandes de jeu par le serveur.
        """
        if "uid" not in kwargs.keys():
            kwargs["uid"] = uid
        # Analyse de la commande
        handler, args = None, None
        if cmd == GameManager.QUEUE_CMD:
            # envoi d'une cmd client (sur demande ou spontanément)
            code = appcomp.GUIExchangeObject.RETURN_USER_CHOICE
            dictvars = kwargs
            obj = ExchangeHelper.createGUIObj(code, dictvars)
            handler = self.handle_user_choice
            args = obj
        elif cmd == GameManager.CHECK_CHANGELOG_KEY:
            # contrôle de cohérence du labyrinthe du client
            handler = self.server_register_client_changelog_key
            args = kwargs
        elif cmd == GameManager.RESET_QUEUE:
            handler = self.reset_cmd_queue
            args = uid
        elif cmd == GameManager.GAME_CHOICE:
            code = appcomp.GUIExchangeObject.RETURN_USER_CHOICE
            dictvars = kwargs
            obj = ExchangeHelper.createGUIObj(code, dictvars)
            handler = self.handle_user_choice
            args = obj
        elif cmd == GameManager.START_GAME:
            handler = self.start_partie
        elif cmd == GameManager.GET_FULL_LAB:
            handler = self._resync_client_labyrinthe
            args = uid
        elif cmd == GameManager.BUILD_LAB_DONE:
            handler = self.server_register_client_lab_resync
            args = kwargs
        # Application
        if handler != None:
            if args != None:
                handler(args)
            else:
                handler()

    def _client_handle_game_cmd(self, uid, cmd, kwargs):
        """
        Traitement des commandes de jeu par le client.
        """
        if "uid" not in kwargs.keys():
            kwargs["uid"] = uid
        # Analyse de la commande
        handler, args = None, None
        if cmd == GameManager.ENTER_CMD:
            # le serveur attend une commande :
            code = None
            dictvars = kwargs
            obj = ExchangeHelper.createGUIObj(code, dictvars)
            handler = self.ask_user_choice
            args = obj
        elif cmd == GameManager.BUILD_LAB:
            # publication ou republication intégrale
            handler = self._buid_labyrinthe
            args = kwargs
        elif cmd == GameManager.UPDATE_XTRAS:
            # mise à jour danger et bonus
            handler = self._update_XTras
            args = kwargs
        elif cmd == GameManager.REORDER_BOTS:
            # modif ordre des bots :
            handler = self._reorder_bots
            args = kwargs
        elif cmd == GameManager.UPDATE_BOTS:
            # mise à jour bots :
            handler = self._update_bots
            args = kwargs
        elif cmd == GameManager.START_GAME:
            # démarrage de la partie :
            code = None
            dictvars = kwargs
            obj = ExchangeHelper.createGUIObj(code, dictvars)
            handler = self.ask_user_choice
            args = obj
        elif cmd == GameManager.CHOOSE_GAME:
            # choix de la partie
            code = None
            dictvars = kwargs
            obj = ExchangeHelper.createGUIObj(code, dictvars)
            handler = self.ask_user_choice
            args = obj
        elif cmd == GameManager.PARTIE_INIT:
            # partie en cours d'initialisation :
            handler = self._on_partie_initialized_by_master
            args = None
        elif cmd == GameManager.PARTIE_CHOSEN:
            # partie en cours de publication :
            handler = self._on_partie_chosen_by_master
            args = kwargs
        elif cmd == GameManager.PARTIE_CREATED:
            # partie publiée :
            handler = self._on_partie_created_by_master
            args = None
        elif cmd == GameManager.PARTIE_STARTED:
            # partie démarrée :
            handler = self._on_partie_started_by_master
            args = kwargs
        elif cmd == GameManager.PARTIE_ENDED:
            # partie terminée :
            handler = self._on_partie_ended_by_master
            args = kwargs
        elif cmd == GameManager.PLAY_CMD:
            # exécution d'une cmd validée par le serveur :
            handler = self._play_cmd_from_master
            args = kwargs
        elif cmd == GameManager.UPDATE_GAMBLE_CONTEXT:
            # update du contexte du coup à venir
            handler = self._update_gamble_ctx_from_master
            args = kwargs
        elif cmd == GameManager.SHOW_MESSAGE:
            # message contextuel :
            handler = self.affiche_message
            args = kwargs["msg"]
        elif cmd == GameManager.UPDATE_PLAYER_STATUS:
            handler = self.on_player_status_updated_by_master
            args = kwargs
        # client :
        self._check_client_partie_init()
        # Application
        if handler != None:
            if args != None:
                handler(args)
            else:
                handler()

    def ready_for_NET_tasks(self):
        """
        Indique si l'objet peut prendre en charge une tâche réseau.
        """
        if self._lock_NET_tasks:
            # On bloque :
            return False
        return True

    def lock_NET_tasks(self):
        """
        Met en attente le traitement des tâches réseau entrantes.
        """
        self._lock_NET_tasks = True

    def unlock_NET_tasks(self):
        """
        Ré active le traitement des tâches réseau.
        """
        self._lock_NET_tasks = False
        # traitement des tâches réseau entrantes en attente :
        if len(self._differed_tasks_list) > 0:
            for task in self._differed_tasks_list:
                self.handle_NET_request(task)
            self._differed_tasks_list = list()

    def ping_connections(self, uid=None):
        """
        Envoie au composant réseau on ordre de vérification des connections
        
        Args:
            uid : peut être un uid unique ou une liste d'uid
        """
        if self.type_app == AppTypes.APP_SERVER:
            remoteuid = self._get_clients_uid_list()
            if uid != None:
                if isinstance(uid, list):
                    listuid = uid
                else:
                    listuid = [uid]
            else:
                listuid = remoteuid
        else:
            listuid = None
        dictargs = {"clients": listuid}
        exobj = ExchangeHelper.createNETObj(
            appcomp.NETExchangeObject.CHECK_CONN, dictargs
        )
        self.sendTask(exobj)

    #-----> A.3- Envoi vers GUI et NET :
    def sendNetworkContent(self, msg, confirmrecept, uid=None):
        """
        Interface d'envoi de contenu sur le réseau
        
        Args:
            msg (str): contenu à envoyer
            confirmrecept (bool): avec accusé de réception?
            uid: peut être un uid unique ou une liste d'uid
        """
        if self.type_app == AppTypes.APP_STANDALONE:
            return
        if self.type_app == AppTypes.APP_SERVER:
            if uid != None:
                if isinstance(uid, list):
                    listuid = uid
                else:
                    listuid = [uid]
            else:
                listuid = self._get_clients_uid_list()
        else:
            listuid = None
        # On empile
        dictargs = {"clients": listuid, "msg": msg}
        exobj = ExchangeHelper.createNETObj(appcomp.NETExchangeObject.SEND, dictargs)
        self.sendTask(exobj)

    def sendGuiCmd(self, exobj):
        """
        Interface d'envoi d'un message à la GUI
        
        Args:
            exobj (GUIExchangeObject)
        """
        self.sendTask(exobj)

    def sendNetworkMessage(self, msg, uid=None):
        """
        Envoie un message aux clients
        
        Args:
            msg (str)
            uid : peut être un uid unique ou une liste d'uid
        """
        if self.type_app == AppTypes.APP_SERVER:
            code = GameManager.SHOW_MESSAGE
            dictargs = {"msg": msg}
            self.fire_game_event(code, dictargs, uid=uid)

    def fire_game_event(self, code, dictargs=None, uid=None, suffix=""):
        """
        Interface d'envoi de messages avec code de commande sur le réseau.
        
        Args:
            code (str): une constante statique
            dictargs (dict): paramètres
            uid: id ou liste d'ids
            suffix (str): suffix de marquage de requète
        """
        # sérialisation et envoi :
        comuid = self._generate_request_uid(suffix)
        msg = CommandHelper.format_game_cmd(code, comuid, dictargs)
        if self.type_app == AppTypes.APP_SERVER:
            uid = self._filter_clients_with_code(code, uid=uid)
        confirmrecept = self._filter_confirmrecept_with_code(code)
        self.sendNetworkContent(msg, confirmrecept, uid=uid)

    def _filter_clients_with_code(self, code, uid=None):
        """
        Filtre les clients si uid est indéfini en fonction du code de commande.
        """
        if uid != None:
            ruid = uid
        else:
            sync_only = False
            if code in GameManager.SYNC_LAB_CODES:
                sync_only = True
            ruid = self._get_clients_uid_list(sync_only=sync_only)
        return ruid

    def _filter_confirmrecept_with_code(self, code):
        """
        Indique si le code de commande suppose l'envoi avec accusé de réception.
        """
        if code in GameManager.UNCONFIRMED_CODES:
            return False
        return True

    #-----> A.4- Unicité des requêtes
    def _generate_request_uid(self, suffix=""):
        """
        Génère un identifiant unique de requête TCP
        """
        n = len(self.requestuidlist)
        uid = str(self.uid) + "_gcom" + str(n) + suffix
        self.requestuidlist.append({"uid": uid, "done": False})
        return uid

    def _valide_request_entry(self, comuid):
        """
        Indique que la requète a été traitée
        """
        for comdict in self.requestuidlist:
            if comdict["uid"] == comuid:
                comdict["done"] = True

    def _is_request_done(self, comuid):
        """
        Indique si la requète a déja été traitée
        """
        done = False
        finded = False
        for comdict in self.requestuidlist:
            if comdict["uid"] == comuid:
                done = comdict["done"]
                finded = True
                break
        if not self.master and not finded:
            # on ajoute l'entrée :
            self.requestuidlist.append({"uid": comuid, "done": False})
        return done

    #-----> B- Phases de l'application :
    #-----> B.1- Phase initiale
    def init_game(self):
        """
        Appelée par l'application lorsque tous les composants ont été initialisés.
        """
        # En fonction du type d'appli :
        can_start_partie = False
        if self.type_app == AppTypes.APP_STANDALONE:
            can_start_partie = True
        elif (
            self.type_app == AppTypes.APP_SERVER or self.type_app == AppTypes.APP_CLIENT
        ):
            can_start_partie = self.is_object_connected()
        # Initialisation de la partie
        if can_start_partie and not self.partie_init_done:
            self.init_partie()

    def is_object_connected(self):
        """
        Retourne un boolean indiquant l'état de connection.
        """
        connected = False
        if self.type_app == AppTypes.APP_SERVER:
            if self.connection_status == ctcp.CustomRequestHelper.STATUS_CONNECTED:
                connected = True
        elif self.type_app == AppTypes.APP_CLIENT:
            if (
                self.connection_status == ctcp.CustomRequestHelper.STATUS_CONNECTED
                and self.server_connection_status
                == ctcp.CustomRequestHelper.STATUS_CONNECTED
            ):
                connected = True
        return connected

    def configure_labyrinthe(self):
        """
        Configure les caractères :
        
        * de commande (direction, aide, quitter, création de mur et porte)
        * de parsing des cartes txt
        * d'affichage graphique des objets Labyrinthe
            
        V1 : ces paramétrages sont gérés en dur dans cette méthode, on pourrait les charger dynamiquement
        dans des fichiers de config, des préférences propres aux joueurs...
        """
        LabHelper.set_navigation_chars(
            left="o",
            right="e",
            top="n",
            bottom="s",
            aide="h",
            menu="a",
            quitter="q",
            mur="m",
            porte="p",
            start="c",
            reset_queue="r",
            kill="k",
            mine="b",
            grenade="g",
        )
        LabHelper.set_parsing_chars(
            vide=" ",
            mur="o",
            porte=".",
            sortie="u",
            robot="x",
            danger="d",
            bonus="s",
            grenade="g",
        )
        LabHelper.set_graphic_chars(
            vide=" ",
            mur=chr(9608),
            porte=chr(9618),
            sortie="S",
            robot="x",
            danger="-",
            bonus="+",
            grenade="*",
        )
        # Envoi à la GUI
        code = appcomp.GUIExchangeObject.SET_BUS_INFO
        obj = ExchangeHelper.createGUIObj(
            code, {"info": GameManager.LABHELPER_SURCHARGED}
        )
        self.sendGuiCmd(obj)

    #-----> B.2- Phases Partie
    #-----> B.2.1- PARTIE_INIT
    def init_partie(self):
        """
        Initialisation d'une partie, appelée à la fin de l'initialisation de l'AppManager.
        """
        # Ré initialisations :
        self.re_initialise()
        # Master
        if self.master:
            # initialisations (locale / clients distants)
            self._on_partie_initialized_by_master()
            self.fire_game_event(GameManager.PARTIE_INIT)
            # choix :
            listuid = self._get_clients_uid_list()
            for uid in listuid:
                self.ask_user_choice({"uid": uid, "typechoix": GameManager.CHOOSE_GAME})
        # Serveur :
        if self.type_app == AppTypes.APP_SERVER:
            self.affiche_partie_infos_for_server()
        # Standalone
        if self.type_app == AppTypes.APP_STANDALONE:
            # création d'un joueur humain local
            if self.uid == None:
                self.register_my_uid("firstp")
                self._register_new_player("firstp", True, True, publish=False)
            # choix de la partie :
            # self.on_human_player_ready(self.uid)
            self.ask_user_choice(
                {"uid": self.uid, "typechoix": GameManager.CHOOSE_GAME}
            )

    def re_initialise(self):
        """
        Ré initialisation complète avant la création d'une partie.
        """
        # paramètres de jeu :
        self.carte_version = 0
        # - partie
        self.check_creation = False
        self._clients_pub_launched = False
        self.current_game_mode = None
        self.current_game_level = None
        self.dispatch_type_partie()
        self.carte_initiale = None
        self.carte_created = False
        self.carte_builded = False
        self.bots_added = False
        self._listbotsbehaviors = None
        self.partie_started = False
        # - tour de jeu
        self.gamble_start_time = None
        self.current_player_indice = -1
        self.current_cmd_asked = False
        self.current_cmd = None
        self.current_cmd_validated = False
        self.current_dictcmd = None
        self.current_consequences = None
        self.current_gamble_case = None
        self.current_gamble_indice = 0
        self.current_gamble_total = 1
        self.gamblenumber = 0
        self._bots_killed_during_gamble = None
        self.gambleinfos = None
        self.gambleloopdone = True
        self.wait_player_choice = False
        self.applying_gamble = False
        self.gamble_applied = False
        self.gamble_XTras_updated = False
        self.wait_clients_gamble_keys = False
        self._gamble_key = None
        self.wait_client_resync = False
        self.wait_clients_XTras_keys = False
        self.gamble_ended = False
        self.content_published = False
        # contrôle de l'affichage de la carte :
        self.init_gui_order_system()
        # Joueurs :
        if self.master:
            templist = list()
            for player in self.playerlist:
                if player.player_type == LabPlayer.HUMAN:
                    player.re_initialise()
                    cond_stand = self.type_app == AppTypes.APP_STANDALONE
                    cond_svr = self.type_app == AppTypes.APP_SERVER and player.joignable
                    if cond_stand or cond_svr:
                        templist.append(player)
            self.playerlist = templist
            self._re_init_players_colors()
        else:
            self.playerlist = list()
        # initialisation dict de synchro des clients
        if self.type_app == AppTypes.APP_SERVER:
            self._create_clients_sync_dict()
        # Managers et Helpers :
        self.labMngr.re_initialise()
        if self.master:
            GameConfiguration.re_initialise()
        self.partie_init_done = True

    def _check_client_partie_init(self):
        """
        Vérifie l'initialisation lors de la définition de phases de partie.
        Un client qui se connecte en cours de partie n'est pas initialisé.
        """
        if self.type_app == AppTypes.APP_CLIENT and not self.partie_init_done:
            self.re_initialise()

    def _on_partie_initialized_by_master(self):
        """
        Indicateur d'initialisation d'une nouvelle partie  (Slave).
        """
        # Phase :
        self.partie_phasis = GameManager.PARTIE_INIT
        # Initialisations :
        if not self.master:
            self.re_initialise()
        # Efface le message précédent
        self.affiche_message("")
        # Envoi à la GUI
        code = appcomp.GUIExchangeObject.SET_BUS_INFO
        obj = ExchangeHelper.createGUIObj(code, {"info": GameManager.PARTIE_INIT})
        self.sendGuiCmd(obj)

    #-----> B.2.2- PARTIE_CHOSEN
    def on_game_choice_made(self, dictargs):
        """
        Appelée lorsque le premier joueur a choisit le niveau.
        
        Process : 
        
            1. handle_user_choice est appelée lorsque le choix de partie est valide
            2. elle appelle alors cette méthode (maj phase)
            3. enfin elle appelle le callback define_game qui lance le process de création de la partie
        
        Suite du process : voir on_partie_created
        """
        if self.master:
            # type partie :
            self.current_game_level = dictargs["indice"]
            self.current_game_mode = dictargs["mode"]
            # gui
            self._on_partie_chosen_by_master(None)
            # clients
            cltdict = {"mode": self.current_game_mode, "level": self.current_game_level}
            self.fire_game_event(GameManager.PARTIE_CHOSEN, dictargs=cltdict)

    def _on_partie_chosen_by_master(self, dictargs):
        """
        Indicateur de choix de partie
        """
        # Phase :
        self.partie_phasis = GameManager.PARTIE_CHOSEN
        # type de partie :
        if not self.master:
            self._update_partie_type_with_dict(dictargs)
        self.dispatch_type_partie()
        # GUI en mode partie
        code = appcomp.GUIExchangeObject.SET_BUS_INFO
        obj = ExchangeHelper.createGUIObj(code, {"info": GameManager.PARTIE_CHOSEN})
        self.sendGuiCmd(obj)

    #-----> B.2.3- PARTIE_CREATED
    def on_partie_created(self):
        """
        Appelée lorsque le modèle (lablevel) a été généré.
        """
        # phase :
        self._on_partie_created_by_master()
        self.fire_game_event(GameManager.PARTIE_CREATED)
        # version de la carte :
        self.carte_version = 1
        # publication initiale master :
        msg = "[7/7] Publication initiale du labyrinthe, veuillez patienter quelques instants..."
        self.affiche_message(msg)
        clb = self._on_partie_published
        self.show_carte_txt_in_preload()
        # time.sleep(0.5)
        self.publish_carte(clb)

    def _on_partie_created_by_master(self):
        """
        Indicateur de création de la partie choisie
        """
        # Phase :
        self.partie_phasis = GameManager.PARTIE_CREATED
        # GUI en mode partie
        code = appcomp.GUIExchangeObject.SET_BUS_INFO
        obj = ExchangeHelper.createGUIObj(code, {"info": GameManager.PARTIE_CREATED})
        self.sendGuiCmd(obj)

    def _on_partie_published(self):
        """
        Appelée lorsque la publication initiale a été effectuée côté master.
        
        Poursuite du process de création de la partie...
        """
        self.affiche_message("")
        if self.type_app == AppTypes.APP_STANDALONE:
            # statut :
            self.on_player_status_changed(self.uid)
            # démarrage de la partie :
            self.start_partie()
        if self.type_app == AppTypes.APP_SERVER:
            # activation de manage_creation_loop...
            self.check_creation = True

    def manage_creation_loop(self):
        """
        Méthode appelée par handleTask si self.check_creation == True, vérifie l'état 
        de publication initial des clients.
        """
        if not self._clients_pub_launched:
            # en attente de clients à synchroniser
            listuid = self._get_clients_uid_list()
            if len(listuid) > 0:
                self._clients_pub_launched = True
                # msg contextuel :
                msg = "[7/7] Publication initiale du labyrinthe, veuillez patienter quelques instants..."
                self.sendNetworkMessage(msg)
                # mémorisation des clients à synchroniser
                self._register_uid_list_to_sync(listuid)
                # init du process de surveillance
                self._start_wait_sync_process()
                self.wait_client_resync = True
                # publication initiale côté clients
                self.update_players_labyrinthe(GameManager.BUILD_LAB, listuid=listuid)
        else:
            # vérification de l'état de synchro des clients :
            self.server_check_clients_lab_resync()
            # appelle _on_clients_init_pub_done lorsque tous les clients sont prêts...

    def _on_client_joignable_during_creation(self, uid):
        """
        Un nouveau client est compètement connecté alors que la phase est PARTIE_CREATED
        """
        if self._clients_pub_launched:
            # la publication initiale a déja été lancée, dans le cas contraire ce
            # client sera traité avec les autres.
            # publication initiale de ce client
            self.sendNetworkMessage(
                "Affichage initial de la carte, celà peut "
                + "prendre quelques instants...",
                uid=uid,
            )
            self.update_players_labyrinthe(GameManager.BUILD_LAB, listuid=uid)
            # contrôle de synchro :
            if not self.check_creation:
                # on relance le process de synchro
                # mémorisation des clients à synchroniser
                self._register_uid_list_to_sync([uid])
                # init du process de surveillance
                self._start_wait_sync_process()
                self.wait_client_resync = True
                self.check_creation = True
            else:
                # on étend la liste des clients à synchroniser :
                listuid = self._get_uid_list_to_sync()
                listuid.append(uid)
                self._register_uid_list_to_sync(listuid)

    def _on_clients_init_pub_done(self):
        """
        Appelée par server_check_clients_lab_resync lorsque tous les clients 
        ont confirmé la publication du labyrinthe.
        """
        # désactivation du process de création :
        self.check_creation = False
        self.wait_client_resync = False
        # choix démarrage :
        listuid = self._get_clients_uid_list()
        for uid in listuid:
            # statut :
            self.on_player_status_changed(uid)
            # en fonction du type de jeu :
            if self.current_game_mode == GameManager.GAME_MODE_PARTIE:
                # invite démarrage :
                self.ask_user_choice({"uid": uid, "typechoix": GameManager.START_GAME})
            else:
                # démarrage direct :
                self.start_partie()

    #-----> B.2.4- PARTIE_STARTED
    def start_partie(self):
        """
        Démarre la partie une fois la carte choisie et les joueurs enregistrés
        """
        if self.master:
            # trie de la liste des joueurs :
            if self.type_app == AppTypes.APP_SERVER:
                self._random_sort_players()
            # démarrage de la partie
            self._on_partie_started_by_master(None)
            # synchro clients : on redonne le ctx de la partie
            cltdict = {"mode": self.current_game_mode, "level": self.current_game_level}
            self.fire_game_event(GameManager.PARTIE_STARTED, dictargs=cltdict)
            # mise à jour interne des listes de robots
            self._dispatch_liste_robots()
            # définition du premier joueur :
            self._define_next_player()
            # initialisation du tour de jeu : géré dans re_initialise
            # activation boucle de gestion des coups
            self.start_game_loop()

    def _random_sort_players(self):
        """
        Trie aléatoire des joueurs, synchro des managers
        """
        # Trie aléatoire :
        cr.CustomRandom.shuffle(self.playerlist)
        # ordres :
        i = 0
        for p in self.playerlist:
            p.order = i
            i += 1
        # trie
        self.labMngr.sort_bots_by_order()
        # affichage :
        self.affiche_gamble_context()
        # synchro des clients :
        self.carte_version = 2
        self.update_players_labyrinthe(GameManager.REORDER_BOTS)

    def _on_partie_started_by_master(self, dictargs):
        """
        Indicateur de démarrage de la partie
        
        Rq : dictargs mêmes données que celles de _on_partie_chosen_by_master.
        Redondant pour les clients initialement connectés mais nécessaires aux
        clients donnectés en cours de partie.
        """
        # Phase :
        self.partie_phasis = GameManager.PARTIE_STARTED
        self.partie_started = True
        # cas d'un client connecté en cours de partie :
        if self.type_app == AppTypes.APP_CLIENT and dictargs != None:
            # mode et niveau
            self._update_partie_type_with_dict(dictargs)
        # Envoi à la GUI
        code = appcomp.GUIExchangeObject.SET_BUS_INFO
        obj = ExchangeHelper.createGUIObj(code, {"info": GameManager.PARTIE_STARTED})
        self.sendGuiCmd(obj)

    #-----> B.2.5- PARTIE_ENDED
    def end_partie(self, winner):
        """
        Arrêt de la partie en cours
        
        Args:
            winner : le joueur gagnant ou None
        """
        if self.master:
            # arrêt de la boucle :
            self.stop_game_loop()
            # message :
            if winner != None:
                msg = winner.nom + " a gagné, la partie est finie.\n"
            else:
                msg = "La partie est terminée sans gagnant.\n"
            msg += "Retour au menu dans 5 secondes..."
            dictargs = {"msg": msg}
            # localement :
            self._on_partie_ended_by_master(dictargs)
            # infos
            if self.type_app == AppTypes.APP_SERVER:
                self.affiche_partie_infos_for_server()
            # clients :
            self.fire_game_event(GameManager.PARTIE_ENDED, dictargs=dictargs)
            # Nouvelle partie :
            self.delay_action(5, self.init_partie)

    def _on_partie_ended_by_master(self, kwargs):
        """
        La partie est terminée
        """
        # Phase :
        self.partie_phasis = GameManager.PARTIE_ENDED
        self.partie_started = False
        # Envoi à la GUI
        # état
        code = appcomp.GUIExchangeObject.SET_BUS_INFO
        obj = ExchangeHelper.createGUIObj(code, {"info": GameManager.PARTIE_ENDED})
        self.sendGuiCmd(obj)
        # message :
        msg = kwargs["msg"]
        self.affiche_message(msg)

    #-----> B.3- Phases jeu (coups)
    #-----> B.3.1- Loop Master
    def start_game_loop(self):
        """
        Démarre la boucle de gestion de la partie (master)
        """
        self.gambleloopdone = True  # delock
        self.partie_started = True

    def stop_game_loop(self):
        """
        Stop la boucle de gestion de la partie (master)
        """
        self.partie_started = False

    def manage_game_loop(self):
        """
        Méthode appelée par handleTask si self.partie_started == True, dédiée 
        à la gestion des coups (master)
        """
        try:
            self.game_loop()
        except Exception as e:
            # si la partie est en cours il s'agit effectivement d'une erreur
            # sinon, la partie a été ré initialisée en cours d'exécution de
            # la boucle (retour au menu, quitter)
            if self.partie_started:
                raise (e)

    def game_loop(self):
        """
        Gestion des coups (master)
        
        Rq : aucune "sous boucle" dans ce code. Les traitements graphiques et
        les traitements métiers s'enchainent grâce à un mécanisme de callback de
        publication.
        """
        # """
        if self.applying_gamble:
            return
        # """
        #
        player = self.playerlist[self.current_player_indice]
        # Etape 1 : initialisation du coup
        if self.gambleloopdone:
            # Lock :
            self.gambleloopdone = False
            self.init_before_gamble(
                player.uid, self.current_gamble_indice, self.current_gamble_total
            )
        # Etape 2 : obtention d'une commande
        if (
            self.current_cmd == None
            and not player.has_cmd()
            and self.current_cmd_asked == False
        ):
            # "demande" initiale
            self.current_cmd_asked = True
            if player.player_type == LabPlayer.HUMAN:
                self.ask_user_choice(
                    {
                        "uid": player.uid,
                        "typechoix": GameManager.ENTER_CMD,
                        "gambleid": self.gamblenumber,
                    }
                )
                self.wait_player_choice = True
            else:
                self.current_cmd = self.labMngr.compute_cmd_for_autobot(
                    player.uid,
                    self.current_gamble_indice + 1,
                    self.current_gamble_total,
                    self.gamblenumber,
                )
                # interruption durant le calcul?
                if not self.partie_started:
                    return
        elif player.has_cmd() and player.player_type == LabPlayer.HUMAN:
            # cas particulier d'un joueur humain ayant envoyé des cmds en avance
            self.wait_player_choice = True
        if self.wait_player_choice:
            # en attente d'une commande d'un joueur humain...
            if player.has_cmd():
                cmd = player.get_cmd()
                if cmd != None:
                    self.current_cmd = cmd
                    self.wait_player_choice = False
            elif not player.can_play():
                # le joueur a pu se déconnecter
                self.wait_player_choice = False
                # on clot le tour (changement de joueur) :
                self.gamble_ended = True
            elif player.player_type == LabPlayer.HUMAN:
                # on vérifie la connection
                now = time.perf_counter()
                dt = now - self.gamble_start_time
                if dt > GameManager.PING_DELAY:
                    self.gamble_start_time = now
                    self.ping_connections(uid=player.uid)
                    # Infos supp:
                    if self.type_app == AppTypes.APP_SERVER:        
                        self.affiche_partie_infos_for_server()
        # Etape 3 : validation de la commande
        if self.current_cmd != None and not self.current_cmd_validated:
            (
                self.current_cmd_validated,
                self.current_dictcmd,
                self.current_consequences,
                self.current_gamble_case,
            ) = self.labMngr.analyse_cmd_for_robot(self.current_cmd, player.uid)
            if not self.current_cmd_validated:
                # invalidation de la commande : gérée par le CmdManager
                # retour à l'étape 2...
                self.current_cmd = None
                self.current_cmd_asked = False
                self.current_dictcmd = self.current_consequences = None
                return
        # Etape 4 : application graphique de la commande
        if (
            self.current_cmd_validated
            and not self.applying_gamble
            and not self.gamble_applied
        ):
            self.applying_gamble = True
            self.on_gamble_defined(
                player.uid,
                self.current_cmd,
                self.current_dictcmd,
                self.current_consequences,
            )
        # Etape 5 : attente de confirmation des joueurs distants (serveur)
        if self.type_app == AppTypes.APP_SERVER:
            if self.wait_clients_gamble_keys:
                # contrôle de cohérence des clients : après application du coup
                self.server_check_players_gamble_keys()
            if self.wait_client_resync:
                # vérification de la synchro des labyrinthes republiés :
                self.server_check_clients_lab_resync()
            if self.wait_clients_XTras_keys:
                # contrôle de cohérence des clients : après ajout des XTras
                self.server_check_players_XTras_keys()
        # Etape 6 : finalisation du coup, appelée à l'issue des
        #           étapes 4 (STANDALONE) ou 5 (SERVER)
        # Etape 7 : poursuite du jeu
        if self.gamble_ended:
            # Le joueur a t'il gagné?
            if self.labMngr.has_robot_won(player.uid):
                # la partie est finie:
                self.end_partie(player)
                return
            # Reste t'il des humains, winner, hunter?
            if self.labMngr.is_partie_ended():
                # la partie est finie sans gagnant:
                self.end_partie(None)
                return
            # incréments
            self.gamblenumber += 1
            self.current_gamble_indice += 1
            # changement de joueur ?
            if not (
                self.current_gamble_indice < self.current_gamble_total
                and player.can_play()
            ):
                self._define_next_player()
                if self.current_player_indice == None:
                    # partie finie, sans gagnant :
                    self.end_partie(None)
                    return
            # Delock :
            self.gambleloopdone = True

    #-----> B.3.2- Utilitaires Master
    def _define_next_player(self, count=0):
        """
        Recherche du prochain joueur actif
        """
        if count >= len(self.playerlist):
            self.current_player_indice = None
            return
        i = self.current_player_indice
        if i == len(self.playerlist) - 1:
            i = -1
        self.current_player_indice = i + 1
        player = self.playerlist[self.current_player_indice]
        # conditions de sélection :
        cond_mode = (
            self.current_game_mode == GameManager.GAME_MODE_PARTIE
            or player.player_type == LabPlayer.BOT
        )
        cond_play = player.can_play()
        if not (cond_mode and cond_play):
            self._define_next_player(count + 1)
        else:
            # changement de joueur
            newplayer = self.playerlist[self.current_player_indice]
            self.current_gamble_indice = 0
            self.current_gamble_total = newplayer.vitesse

    def init_before_gamble(self, uid, coup, totalcoups):
        """
        Transmission du contexte du prochain coup (synchro interface(s))
        """
        # propriétés liées au tour de jeu :
        self.gamble_start_time = time.perf_counter()
        self.current_cmd_asked = False
        self.current_cmd = None
        self.current_cmd_validated = False
        self.current_dictcmd = None
        self.current_consequences = None
        self.current_gamble_case = None
        # self._bots_killed_during_gamble : réinitialisé dans self.init_changelogs
        # self.gambleinfos : réinitialisé plus bas
        # self.gambleloopdone : géré dans self.game_loop
        self.wait_player_choice = False
        self.applying_gamble = False
        self.gamble_applied = False
        self.gamble_XTras_updated = False
        self.wait_clients_gamble_keys = False
        self._gamble_key = None
        self.wait_client_resync = False
        self.wait_clients_XTras_keys = False
        self.gamble_ended = False
        # on incrémente la version de la carte après :
        self.carte_version += 1
        # init changelog :
        self.init_changelogs()
        # Initialisation du joueur :
        self.labMngr.init_robot_before_gamble(uid, coup, totalcoups)
        # données :
        self.gambleinfos = {
            "uid": uid,
            "coup": coup,
            "total_coups": totalcoups,
            "gamblenumber": self.gamblenumber,
        }
        # affichage local :
        self.affiche_gamble_context()
        # synchro des clients distants :
        if self.type_app == AppTypes.APP_SERVER:
            code = GameManager.UPDATE_GAMBLE_CONTEXT
            # données bots : limitées aux données ayant changé lors du dernier coup
            dictargs = self.labMngr.get_bots_datas(full=False)
            # ajout données coups :
            for k in self.gambleinfos.keys():
                dictargs[k] = self.gambleinfos[k]
            self.fire_game_event(code, dictargs)

    def on_gamble_defined(self, uid, cmd, dictcmd, consequences):
        """
        Prise en charge master du coup venant d'être défini
        """
        # on complète le dict (msg contextuel)
        player = self.get_player_by_uid(uid)
        dictcmd["player_name"] = player.nom
        dictcmd["cmd"] = cmd
        # Serveur : envoi de la commande avant application (animations bloquantes)
        if self.type_app == AppTypes.APP_SERVER:
            # mémorisation des clients à synchroniser
            uidlist = self._filter_clients_with_code(GameManager.PLAY_CMD)
            self._register_uid_list_to_sync(uidlist)
            # commande :
            self.fire_game_event(
                GameManager.PLAY_CMD,
                {
                    "uid": uid,
                    "player_name": player.nom,
                    "cmd": cmd,
                    "gambleid": self.gamblenumber,
                    "carte_version": self.carte_version,
                },
            )
            # infos
            self.affiche_partie_infos_for_server()
        # Traitement local :
        self.apply_gamble(uid, dictcmd, consequences)
        # => poursuite du process dans self.on_gamble_played

    def update_players_labyrinthe(self, case, listuid=None, dictargs=None):
        """
        Synchro du labyrinthe des clients distants
        
        Args:
            case : parmi BUILD_LAB, UPDATE_XTRAS, UPDATE_BOTS, REORDER_BOTS
            listuid : uid ou liste d'uid de joueurs concernés par l'envoi ou None (ie tous les joueurs)
            dictargs : dict associé aux derniers bonus/dangers ajoutés ou à la liste de bots (cas part déconnection)
        """
        msgdict = None
        # En fonction du cas :
        if case == GameManager.BUILD_LAB:
            # parsing et publication complets :
            msgdict = self.labMngr.get_parsing_datas()
            # on ajoute les infos de type de partie
            msgdict["mode"] = self.current_game_mode
            msgdict["level"] = self.current_game_level
        elif case == GameManager.UPDATE_XTRAS:
            # bonus et dangers venant d'être ajoutés :
            msgdict = dictargs
        elif case == GameManager.UPDATE_BOTS:
            # mise à jour de la liste de bots :
            if dictargs != None:
                msgdict = dictargs
            else:
                msgdict = self.labMngr.get_bots_datas()
        elif case == GameManager.REORDER_BOTS:
            # réordonne la liste de bots :
            msgdict = self.labMngr.get_bots_datas()
        if msgdict != None:
            # ajout du versionning de carte :
            msgdict["carte_version"] = self.carte_version
            # envoi
            self.fire_game_event(case, dictargs=msgdict, uid=listuid, suffix="ulp")

    def _resync_client_labyrinthe(self, uid):
        """
        Un client demande à resynchroniser son labyrinthe.
        """
        # rebuid :
        self.update_players_labyrinthe(GameManager.BUILD_LAB, listuid=uid)

    def master_closing_gamble(self):
        """
        Pré finalisation du coup par le master.
        """
        # modèle :
        if self.current_player_indice != None:
            player = self.playerlist[self.current_player_indice]
            robot = player.robot
            self.labMngr.on_cmd_for_robot_done(
                self.current_dictcmd,
                robot,
                self.current_gamble_case,
                self._bots_killed_during_gamble,
                self.gamblenumber,
                self.current_gamble_indice + 1,
                self.current_gamble_total,
            )
        # XTras :
        self._check_XTras_after_gamble()

    def _check_XTras_after_gamble(self):
        """
        Ajoute au besoin des bonus et dangers
        """
        change = False
        if self.labMngr.need_to_complete_XTras_after_gamble():
            # init changelog :
            self.init_changelogs()
            self.init_step_changelogs()
            # on rajoute des XTras :
            xtraslist = self._add_XTras_cases()
            if len(xtraslist) > 0:
                change = True
        # marqueur
        self.gamble_XTras_updated = True
        # callback :
        clb = self.on_gamble_closed
        if change:
            self.carte_version += 1
            # synchro des clients distants :
            if self.type_app == AppTypes.APP_SERVER:
                # mémorisation des clients à synchroniser (les clients actifs)
                uidlist = self._filter_clients_with_code(GameManager.UPDATE_XTRAS)
                self._register_uid_list_to_sync(uidlist)
                # init du process de surveillance
                self._start_wait_sync_process()
                # marqueur
                self.wait_clients_XTras_keys = True
                # clef de comparaison
                self._gamble_key = self.create_changelog_key()
                # message :
                self.sendNetworkMessage("Ajout de bonus et de mines...")
                # mise à jour
                dictargs = self.labMngr.get_parsedicts_for_listcases(xtraslist)
                self.update_players_labyrinthe(
                    GameManager.UPDATE_XTRAS, dictargs=dictargs
                )
                # info clients :
                self.sendNetworkMessage("Contrôle de cohérence des clients...")
                # on désactive le callback (verif cohérence)
                clb = None
            # on publie localement :
            self.update_carte(clb)
        else:
            # pas de changement on clôture le coup
            clb()

    def on_gamble_closed(self):
        """
        Le coup est intégralement traité.
        """
        # Marqueurs de fin :
        self.gamble_ended = True

    def _split_queue_action(self, dictargs):
        """
        Sépare au besoin les commandes unitaires comprises dans dictargs
        """
        splitlist = list()
        action = dictargs["action"]
        pastxt = str(dictargs["pas"])
        if LabHelper.REGEXP_INT.match(pastxt):
            pas = int(pastxt)
        else:
            pas = 0
        cmd_txt = dictargs["choix"]
        if action == LabHelper.ACTION_MOVE and pas > 1:
            # on décompose en mouvement d'un pas
            cmd_unit = cmd_txt[0]
            while pas > 0:
                splitlist.append(cmd_unit)
                pas -= 1
        else:
            splitlist.append(cmd_txt)
        return splitlist

    def reset_cmd_queue(self, uid):
        """
        Efface les commandes pré enregistrées par le joueur
        """
        player = self.get_player_by_uid(uid)
        player.resetcmdqueue()

    #-----> B.3.3- Méthodes Slave
    def _update_partie_type_with_dict(self, dictargs):
        """
        Recherche dans les dict les entrées mode et level décrivant le
        type de partie (slave).
        """
        if isinstance(dictargs, dict):
            if "mode" in dictargs.keys() and "level" in dictargs.keys():
                self.current_game_mode = dictargs["mode"]
                self.current_game_level = dictargs["level"]

    def _buid_labyrinthe(self, kwargs):
        """
        Parsing et publication complets du labyrinthe
        """
        self.lock_NET_tasks()
        # version de la carte :
        if "carte_version" in kwargs.keys():
            self.carte_version = kwargs["carte_version"]
        # type de partie ;
        self._update_partie_type_with_dict(kwargs)
        self.dispatch_type_partie()
        # parsing
        self.labMngr.parse_labyrinthe(kwargs)
        self.carte_builded = True
        # callbalck (client)
        clb = None
        if self.type_app == AppTypes.APP_CLIENT:
            clb = self.client_confirm_lab_resync
        # affichage
        self.publish_carte(clb)

    def _reorder_bots(self, kwargs):
        """
        La liste des robots a été ré ordonnée avant de démarrer la partie
        """
        if self.carte_builded:
            # version de la carte :
            if "carte_version" in kwargs.keys():
                self.carte_version = kwargs["carte_version"]
            # parsing :
            self.labMngr.update_bots_or_XTras(kwargs)
            # trie
            self.labMngr.sort_bots_by_order()
            # affichage :
            self.affiche_gamble_context()

    def _update_bots(self, kwargs):
        """
        Mise à jour des joueurs avant démarrage de la partie
        """
        if self.carte_builded:
            # version de la carte :
            if "carte_version" in kwargs.keys():
                self.carte_version = kwargs["carte_version"]
            # init changelog :
            self.init_changelogs()
            # cas particulier :
            if "deconnected" in kwargs.keys():
                # un joueur déconnecté avant démarrage de la partie, on
                # supprime le robot:
                deluid = kwargs["deconnected"]
                delete = not self.partie_started
                self.labMngr.on_robot_killed(deluid, delete=delete)
            # parsing générique :
            self.labMngr.update_bots_or_XTras(kwargs)
            # affichage
            self.update_carte(None)

    def _update_XTras(self, kwargs):
        """
        Mise à jour des bonus et dangers
        """
        if self.carte_builded:
            # version de la carte :
            if "carte_version" in kwargs.keys():
                self.carte_version = kwargs["carte_version"]
            # init changelog :
            self.init_changelogs()
            # parsing
            self.labMngr.update_bots_or_XTras(kwargs)
            # callbalck (client)
            clb = None
            if self.type_app == AppTypes.APP_CLIENT:
                clb = self.client_send_changelog_key
            # affichage
            self.update_carte(clb)

    def _play_cmd_from_master(self, kwargs):
        """
        Exécute une commande validée par le master
        """
        if self.carte_builded:
            # version de la carte :
            if "carte_version" in kwargs.keys():
                self.carte_version = kwargs["carte_version"]
            # init changelog :
            self.init_changelogs()
            # paramètres :
            uid = kwargs["uid"]
            cmd = kwargs["cmd"]
            self.gamblenumber = kwargs["gambleid"]
            cmd_study = self.labMngr.analyse_cmd_for_robot(cmd, uid)
            dictcmd = cmd_study[1]
            consequences = cmd_study[2]
            # on complète le dict (msg contextuel)
            dictcmd["player_name"] = kwargs["player_name"]
            dictcmd["cmd"] = cmd
            # application de la commande :
            self.apply_gamble(uid, dictcmd, consequences)

    def _update_gamble_ctx_from_master(self, kwargs):
        """
        Mise à jour du contexte du prochain coup transmise par le serveur
        """
        if self.carte_builded:
            # bots :
            self._update_bots(kwargs)
            # coup :
            uid = kwargs["uid"]
            coup = int(kwargs["coup"])
            total_coups = int(kwargs["total_coups"])
            self.gamblenumber = kwargs["gamblenumber"]
            # Initialisation du joueur :
            self.labMngr.init_robot_before_gamble(uid, coup, total_coups)
            # affichage
            self.gambleinfos = {
                "uid": uid,
                "coup": coup,
                "total_coups": total_coups,
                "gamblenumber": self.gamblenumber,
            }
            self.affiche_gamble_context()

    #-----> B.3.4- Application d'un coup :
    def init_changelogs(self):
        """
        Ré initialise les logs avant modification du lablevel. 
        Logs à l'échelle du coup complet.
        """
        self.labMngr.init_changelogs()
        # bots éliminés durant le coup
        self._bots_killed_during_gamble = list()

    def init_step_changelogs(self):
        """
        Ré initialise les logs d'étape avant modification du lablevel. 
        Logs à l'échelle d'une étape du coup complet.
        """
        self.labMngr.init_step_changelogs()

    def apply_gamble(self, uid, dictcmd, consequences):
        """
        Traitement local d'un coup à jouer
        """
        # lock tâches réseau
        self.lock_NET_tasks()
        # init step changelog :
        self.init_step_changelogs()
        # message d'info:
        if self.type_app != AppTypes.APP_SERVER:
            msg = (
                "Coup "
                + str(self.gamblenumber)
                + " "
                + dictcmd["player_name"]
                + " joue "
                + str(dictcmd["cmd"])
            )
            self.affiche_message(msg)
        # En fonction de l'action :
        action = dictcmd["action"]
        if action == LabHelper.ACTION_MOVE:
            csqdict = self._get_csqdict("bot_move", consequences)
            robot = csqdict["robot"]
            coords1 = csqdict["coords1"]
            coords2 = csqdict["coords2"]
            # maj du LabLevel :
            self.labMngr.move_case(robot, coords2[0], coords2[1])
            # affichage :
            clb = self.on_first_action_done
            args = [uid, dictcmd, consequences]
            dur = LabHelper.ANIMATION_MOVE_DURATION
            self.play_animation_move(robot, coords1, coords2, dur, 1, clb, *args)
        elif action == LabHelper.ACTION_GRENADE:
            csqdict = self._get_csqdict("launch_grenade", consequences)
            grenade = csqdict["grenade"]
            coords1 = csqdict["coords1"]
            coords2 = csqdict["coords2"]
            nb_cases = csqdict["nb_cases"]
            # maj du LabLevel :
            self.labMngr.add_case(grenade)
            # affichage :
            clb = self.on_first_action_done
            args = [uid, dictcmd, consequences]
            dur = LabHelper.ANIMATION_MOVE_DURATION * nb_cases
            self.play_animation_move(
                grenade, coords1, coords2, dur, nb_cases, clb, *args
            )
        elif action == LabHelper.ACTION_KILL:
            self.on_first_action_done(uid, dictcmd, consequences)
        elif action in [
            LabHelper.ACTION_CREATE_DOOR,
            LabHelper.ACTION_CREATE_WALL,
            LabHelper.ACTION_MINE,
        ]:
            csqdict = self._get_csqdict("case_to_add", consequences)
            case = csqdict["case"]
            # maj du LabLevel :
            self.labMngr.add_case(case)
            # affichage suivi :
            self.update_carte(self.on_first_action_done, uid, dictcmd, consequences)

    def _get_csqdict(self, csqtype, csqlist):
        for csqdict in csqlist:
            if csqdict["type"] == csqtype:
                return csqdict
        return None

    def set_bot_killed(self, robot, affiche=False, callback=None, clbargs=None):
        """
        Elimination d'un robot. 
        
        Rq : l'affichage est à revoir ("écrasé" par un update 
        immédiat de la carte), d'où des appels avec affiche=False.
        """
        robot.alive = False
        # affichage suivi:
        if affiche:
            gui_order = None
            if callback:
                gui_order = self.create_gui_order_number()
                self.register_gui_order_callback(gui_order, callback, clbargs)
            dictvars = {
                "content": GameManager.CONTENT_BOT_DEAD,
                "robot": robot,
                "gui_order": gui_order,
            }
            code = appcomp.GUIExchangeObject.SHOW_CONTENT
            obj = ExchangeHelper.createGUIObj(code, dictvars)
            # Envoi à la GUI
            self.sendGuiCmd(obj)
        # maj données :
        delete = not self.partie_started
        self.labMngr.on_robot_killed(robot.uid, delete=delete)
        if self.master:
            player = self.get_player_by_uid(robot.uid)
            player.kill()
            # statut :
            if player.player_type == LabPlayer.HUMAN:
                self.on_player_status_changed(robot.uid)
        if self._bots_killed_during_gamble != None:
            self._bots_killed_during_gamble.append(robot)

    def play_animation_move(
        self, case, coords1, coords2, duration, nbcases, callback, *args
    ):
        """
        Joue une animation de mouvement (robot ou grenade).
        """
        # en fonction du type d'animation supporté :
        if LabHelper.ANIMATION_RESOLUTION == LabHelper.ANIMATION_RESOLUTION_PIXEL:
            # animation de mouvement / pixels :
            self.affiche_animation_pixel(
                case, coords1, coords2, duration, callback, *args
            )
        else:
            # animation case à case :
            stepduration = duration / nbcases
            listcoords = list()
            step = 0
            while step < nbcases:
                step += 1
                prop = step / nbcases
                x = coords1[0] + (coords2[0] - coords1[0]) * prop
                y = coords1[1] + (coords2[1] - coords1[1]) * prop
                listcoords.append((x, y))
            self.start_animation_cases(case, listcoords, stepduration, callback, *args)

    def start_animation_cases(self, case, listcoords, stepduration, callback, *args):
        """
        Lance une animation suivie case à case
        """
        # paramètres :
        now = time.perf_counter()
        w, h = self.labMngr.get_dimensions()
        dictanim = {
            "case": case,
            "current_step": 0,
            "step_count": len(listcoords),
            "listcoords": listcoords,
            "w": w,
            "h": h,
            "finalcallback": callback,
            "finalargs": args,
            "stepduration": stepduration,
            "prevtime": now,
            "txt": None,
        }
        self.run_animation_cases(dictanim)

    def run_animation_cases(self, dictanim):
        """
        Applique les étapes de transformation de l'animation case à case
        """
        current_step = dictanim["current_step"]
        if current_step < dictanim["step_count"]:
            # init step changelog :
            self.init_step_changelogs()
            # données d'affichage :
            x, y = dictanim["listcoords"][current_step]
            case = dictanim["case"]
            self.labMngr.move_case(case, x, y)
            dictanim["txt"] = self.labMngr.get_repr_view()  # pour GUI console
            # incrément :
            dictanim["current_step"] += 1
            # tempo :
            prevtime = dictanim["prevtime"]
            currenttime = time.perf_counter()
            stepduration = dictanim["stepduration"]
            deltatime = stepduration - (currenttime - prevtime)
            if current_step > 0 and deltatime > 0:
                time.sleep(deltatime)
            dictanim["prevtime"] = time.perf_counter()
            # affichage suivi :
            self.update_carte(self.run_animation_cases, dictanim)
        else:
            # callback final:
            clb = dictanim["finalcallback"]
            args = dictanim["finalargs"]
            clb(*args)

    def on_first_action_done(self, uid, dictcmd, consequences):
        """
        Callback appelé lorsque la première action a été effectuée (animation
        de déplacement, ajout de case)
        """
        action = dictcmd["action"]
        csqdict_danger = self._get_csqdict("danger_activated", consequences)
        if action == LabHelper.ACTION_GRENADE or csqdict_danger != None:
            # création du scénario
            case_danger = robotuid = None
            if action == LabHelper.ACTION_GRENADE:
                csqdict = self._get_csqdict("launch_grenade", consequences)
                case_danger = csqdict["grenade"]
            else:
                csqdict = self._get_csqdict("danger_activated", consequences)
                case_danger = csqdict["case"]
                robot = csqdict["robot"]
                if robot != None:
                    robotuid = robot.uid
            scenariodict = self.labMngr.get_explosion_scenario(robotuid, case_danger)
            # lecture du scénario :
            self.play_explosion_scenario(uid, dictcmd, consequences, scenariodict)
        else:
            # cas simples :
            self.handle_simple_consequences(uid, consequences, self.on_gamble_played)

    def play_explosion_scenario(self, uid, dictcmd, consequences, scenariodict):
        """
        Prend en charge une explosion
        """
        step_count = scenariodict["step_count"]
        current_step = scenariodict["current_step"]
        if current_step <= step_count:
            # init step changelog :
            self.init_step_changelogs()
            # Maj du modèle :
            botkilled = self.labMngr.handle_animation_step(scenariodict, current_step)
            # robots éliminés :
            for robot in botkilled:
                self.set_bot_killed(robot)
            # incrément :
            scenariodict["current_step"] += 1
            # tempo :
            scenariodict["prevtime"] = time.perf_counter()
            # affichage suivi :
            self.update_carte(
                self.play_explosion_scenario, uid, dictcmd, consequences, scenariodict
            )
        else:
            # init step changelog :
            self.init_step_changelogs()
            # maj modèle :
            self.labMngr.explosion_callback(scenariodict)
            # affichage suivi :
            self.update_carte(self.on_gamble_played)

    def handle_simple_consequences(self, uid, consequences, callback):
        """
        Prise en charge des conséquences simples
        """
        change = False
        # init step changelog :
        self.init_step_changelogs()
        # bonus ?
        csqdict_bonus = self._get_csqdict("bonus_win", consequences)
        if csqdict_bonus != None:
            # bonus gagné :
            casebonus = csqdict_bonus["case"]
            self.on_bonus_win(uid, casebonus)
            change = True
        # plusieurs robots peuvent être éliminés (explosion)
        for csqdict in consequences:
            if csqdict["type"] == "robot_killed":
                robot = csqdict["robot"]
                self.set_bot_killed(robot)
                change = True
        # maj affichage :
        if change:
            # affichage suivi :
            self.update_carte(callback)
        else:
            callback()

    def on_bonus_win(self, uid, casebonus):
        """
        Appelée lorsque le robot d'uid passe sur une case bonus
        """
        # master :
        if self.is_master():
            robot = self.get_player_by_uid(uid).robot
            # configuration du bonus en fonction du robot :
            gameconf = None
            if GameConfiguration.is_game_configured():
                gameconf = GameConfiguration
            casebonus.adapt_bonus_to_robot(robot, gameconf, True)
            # application du bonus
            if casebonus.bonus_type == CaseBonus.BONUS_AUGMENTE_VITESSE:
                # appel au game manager :
                self.on_player_vitesse_change(uid, robot.vitesse)
        # gestion LabLevel :
        self.labMngr.on_bonus_win(casebonus)

    def on_gamble_played(self):
        """
        Le coup a été traité graphiquement
        """
        # marque la fin du traitement graphique :
        self.gamble_applied = True
        self.applying_gamble = False
        # unlock et traitement des tâches réseau en attente :
        self.unlock_NET_tasks()
        # en fonction du type d'appli :
        if self.type_app == AppTypes.APP_SERVER:
            # init du process de surveillance
            self._start_wait_sync_process()
            # contrôle de cohérence des clients :
            self._gamble_key = self.create_changelog_key()
            self.wait_clients_gamble_keys = True
            # infos
            self.affiche_partie_infos_for_server()
        elif self.type_app == AppTypes.APP_CLIENT:
            # envoi de la clef de changelog
            self.client_send_changelog_key()
        elif self.type_app == AppTypes.APP_STANDALONE:
            # finalisation du coup :
            self.master_closing_gamble()

    #-----> B.3.5- Evénéments de jeu
    def on_queue_cmd_added(self, dictargs):
        """
        Le joueur d'uid uid a envoyé une nouvelle cmd (action)
        """
        uid = dictargs["uid"]
        if "dictcmd" in dictargs.keys():
            # cas particulier l'objet n'a pas été sérialisé/désérialisé
            for k, v in dictargs["dictcmd"].items():
                dictargs[k] = v
        player = self.get_player_by_uid(uid)
        unitactions = self._split_queue_action(dictargs)
        for item in unitactions:
            player.addcmdtoqueue(item)

    def on_player_vitesse_change(self, uid, val):
        """
        Le joueur d'uid, uid vient de gagner un bonus
        """
        if self.master:
            player = self.get_player_by_uid(uid)
            player.vitesse = val

    #-----> B.4- Interruptions :
    def goto_menu(self):
        """
        L'utilisateur veut retourner au menu, en quittant la partie éventuellement
        en cours.
        """
        # En fonction du type d'appli :
        if self.type_app == AppTypes.APP_STANDALONE:
            # arrêt loop :
            self.stop_game_loop()
            # on relance l'initialisation d'une partie :
            self.init_partie()

    def quit_game(self):
        """
        L'utilisateur veut quitter le jeu.
        """
        # arrêt loop :
        self.stop_game_loop()
        # Fermeture générique de l'ensemble de l'application :
        self.close_APP()

    #-----> C- Connection/ids des joueurs
    #-----> C.1- Gestion des uids des joueurs
    def register_my_uid(self, uid):
        """
        Contexte client connecté : le serveur distant vient d'affecter l'uid. 
        Contexte standalone : auto affectation.
        """
        # Enregistrement
        self.uid = uid
        # Envoi à la GUI
        code = appcomp.GUIExchangeObject.SET_BUS_INFO
        obj = ExchangeHelper.createGUIObj(
            code, {"info": GameManager.SET_UID, "uid": self.uid}
        )
        self.sendGuiCmd(obj)

    def _generate_uid(self):
        """
        Génère un identifiant de joueur unique
        """
        n = len(self.playerlist)
        return str("gmuid" + str(n))

    def get_player_by_uid(self, uid):
        """
        Retourne le LabPlayer d'uid passé en paramètre
        """
        for player in self.playerlist:
            if player.uid == uid:
                return player
        return None

    #-----> C.2- Connection client
    def player_connected(self, uid):
        """
        Un joueur distant vient d'obtenir son uid de la part du serveur.
        """
        # Enregistrement initial.
        # A ce stade le joueur ne peut pas encore être contacté.
        if self.get_player_by_uid(uid) == None:
            publish = (
                self.current_game_mode == GameManager.GAME_MODE_PARTIE
                and not self.partie_started
            )
            self._register_new_player(uid, False, True, publish=publish)

    def player_joignable(self, uid):
        """
        Indique que la connexion bilatérale avec le client est établie.
        """
        player = self.get_player_by_uid(uid)
        if player == None:
            self.player_connected(uid)
            player = self.get_player_by_uid(uid)
        otheruids = [
            p.uid
            for p in self.playerlist
            if p.uid != uid and p.player_type == LabPlayer.HUMAN and p.joignable
        ]
        if player != None:
            player.joignable = True
            if (
                player.player_type == LabPlayer.HUMAN
            ):  # Rq: le contraire ne devrait pas arriver
                # on l'ajoute au dict de synchro des clients
                self._update_sync_dict_with_client(uid)
                # synchro de la phase du joueur :
                if self.partie_phasis != GameManager.PARTIE_STARTED:
                    self.fire_game_event(self.partie_phasis, uid=uid)
                # en fonction de la phase actuelle :
                if self.partie_phasis == GameManager.PARTIE_INIT:
                    # choix de partie :
                    self.ask_user_choice(
                        {"uid": uid, "typechoix": GameManager.CHOOSE_GAME}
                    )
                elif self.partie_phasis == GameManager.PARTIE_CREATED:
                    # autres joueurs
                    if self.current_game_mode == GameManager.GAME_MODE_PARTIE:
                        self.sendNetworkMessage(
                            "Un nouveau joueur a rejoint la partie.", uid=otheruids
                        )
                        # synchros labyrinthe :
                        self.update_players_labyrinthe(
                            GameManager.UPDATE_BOTS, listuid=otheruids
                        )
                    # nouveau joueur à synchroniser :
                    self._on_client_joignable_during_creation(uid)
                elif self.partie_phasis == GameManager.PARTIE_STARTED:
                    # mode spectateur uniquement :
                    player.viewer = True
                    # phase + infos partie :
                    cltdict = {
                        "mode": self.current_game_mode,
                        "level": self.current_game_level,
                    }
                    self.fire_game_event(
                        GameManager.PARTIE_STARTED, uid=uid, dictargs=cltdict
                    )
                    # on le synchronisera à la fin du coup en cours
                elif self.partie_phasis == GameManager.PARTIE_ENDED:
                    # à voir
                    pass

    def on_player_connection_status_changed(self, uid):
        """
        Appelée lorsque le statut de connection du client change de valeur.
        Rq: player.joignable est déja actualisé (handle_NET_info appelant 
        _server_check_connections).
        """
        # mise à jour du dict de synchro des clients
        self._update_sync_dict_with_client(uid)
        # mise à jour du robot :
        player = self.get_player_by_uid(uid)
        if not player.joignable:
            if player.robot != None:
                # on élimine le robot
                self.set_bot_killed(player.robot)
                # synchro des autres joueurs
                otheruids = [
                    p.uid
                    for p in self.playerlist
                    if p.uid != uid and p.player_type == LabPlayer.HUMAN and p.joignable
                ]
                # nouvelles données :
                dictargs = self.labMngr.get_bots_datas()
                # ajout de l'info de déconnection :
                dictargs["deconnected"] = uid
                # synchro des autres joueurs
                self.update_players_labyrinthe(
                    GameManager.UPDATE_BOTS, listuid=otheruids, dictargs=dictargs
                )
        else:
            # si reconnection : on passe le joueur en spectateur
            if (
                player.robot != None
                and self.partie_phasis == GameManager.PARTIE_STARTED
            ):
                player.viewer = True
            self.on_player_status_changed(uid)

    def on_player_status_changed(self, uid):
        """
        Mise à jour du statut du joueur
        """
        player = self.get_player_by_uid(uid)
        if player:
            # données :
            statusdict = {
                "client": not player.local,
                "connected": player.joignable,
                "type_partie": self.current_game_mode,
                "viewer": player.viewer,
                "color": player.color,
                "killed": player.killed,
            }
            # update :
            if self.type_app == AppTypes.APP_SERVER:
                # envoi au client
                self.fire_game_event(
                    GameManager.UPDATE_PLAYER_STATUS,
                    dictargs=statusdict,
                    uid=uid,
                    suffix="ups",
                )
            elif self.type_app == AppTypes.APP_STANDALONE:
                # application locale
                self.on_player_status_updated_by_master(statusdict)

    def on_player_status_updated_by_master(self, dictargs):
        """
        Mise à jour du statut du joueur : sdynchro graphique de la zone commande.
        """
        dictargs["content"] = GameManager.CONTENT_PLAYER_STATUS
        dictargs["robot"] = None
        if self.labMngr:
            dictargs["robot"] = self.labMngr.get_robot_by_uid(self.uid)
        code = appcomp.GUIExchangeObject.SHOW_CONTENT
        obj = ExchangeHelper.createGUIObj(code, dictargs)
        # Envoi à la GUI
        self.sendGuiCmd(obj)

    #-----> C.3- Structure de suivi des clients
    def _get_clients_uid_list(self, sync_only=False):
        """
        Retourne la liste d'uid associée aux clients distants joignables.
        
        Args:
            sync_only (bool): limite l'envoi aux clients dont la carte est synchronisée.
        """
        uid_list = list()
        if self._sync_clients_dict != None:
            for player, playerdict in self._sync_clients_dict.items():
                cond = cond_join = playerdict["joignable"]
                if sync_only:
                    cond = cond_join and playerdict["lab_sync"]
                if cond:
                    uid_list.append(player.uid)
        else:
            for player in self.playerlist:
                if not player.local and player.player_type == LabPlayer.HUMAN:
                    if player.joignable:
                        uid_list.append(player.uid)
        return uid_list

    def _register_uid_list_to_sync(self, uidlist=None):
        """
        Enregistre dans self._current_sync_uid_list la 
        liste d'uid de clients qui seront à contrôller / synchro
        """
        # mémorisation des clients à synchroniser :
        if uidlist == None:
            # on copie la liste de clients actifs avant envoi :
            uidlist = self._get_clients_uid_list().copy()
        self._current_sync_uid_list = uidlist

    def _get_uid_list_to_sync(self):
        """
        Retourne la liste d'uid de clients à contrôller / synchro
        """
        return self._current_sync_uid_list

    def _create_clients_sync_dict(self):
        """
        Crée le dict de contrôle de cohérence des clients à l'initialisation 
        de la partie par le serveur.
        """
        self._sync_clients_dict = dict()
        # entrées par clients
        for player in self.playerlist:
            uid = player.uid
            self._add_client_to_sync_dict(uid)

    def _add_client_to_sync_dict(self, uid):
        """
        Ajoute le client identifié par uid au dict de synchro
        """
        player = self.get_player_by_uid(uid)
        if player != None and player not in self._sync_clients_dict.keys():
            # joueur humain distant uniquement :
            if not player.local and player.player_type == LabPlayer.HUMAN:
                self._sync_clients_dict[player] = {
                    "carte_version": player.sync_marker,
                    "joignable": player.joignable,
                    "sync_key": None,
                    "lab_sync": True,
                    "lab_sync_done": False,
                }

    def _update_sync_dict_with_client(self, uid):
        """
        Ajoute ou met à jour l'entrée du dict de synchro pour le client identifié par uid
        """
        if self._sync_clients_dict != None:
            player = self.get_player_by_uid(uid)
            # création de l'entrée au besoin :
            if not player in self._sync_clients_dict.keys():
                self._add_client_to_sync_dict(uid)
            # si le joueur est bien un client enregistré :
            if player in self._sync_clients_dict.keys():
                playerdict = self._sync_clients_dict[player]
                clt_sync = True
                if self.partie_phasis == GameManager.PARTIE_STARTED:
                    clt_sync = player.sync_marker == self.carte_version
                playerdict["carte_version"] = player.sync_marker
                playerdict["joignable"] = player.joignable
                playerdict["lab_sync"] = clt_sync

    #-----> D- Contrôle de cohérence (client/serveur)
    def create_changelog_key(self):
        """
        Crée une clef pour le contrôle de cohérence
        """
        key = str(self.carte_version) + "_" + str(self.labMngr.get_changelogs_key())
        return key

    #-----> D.1- Cohérence (serveur)
    def _start_wait_sync_process(self):
        """
        Initie le process de contrôle de cohérence en enregistrement le t0.
        """
        self._wait_start_time = time.perf_counter()

    def _on_wait_sync_passed(self, uidlist):
        """
        Appelée à chaque passe de contrôle de cohérence si le process 
        est toujours en cours
        """
        now = time.perf_counter()
        dt = now - self._wait_start_time
        if dt > GameManager.PING_DELAY:
            # on ré initialise :
            self._wait_start_time = time.perf_counter()
            # détection des déconnections sauvages :
            self.ping_connections(uid=uidlist)

    def server_register_client_changelog_key(self, dictargs):
        """
        Enregistrement de la clef de cohérence du client
        """
        # mise à jour de la version de carte du client
        uid = dictargs["uid"]
        player = self.get_player_by_uid(uid)
        client_cversion = dictargs["carte_version"]
        player.sync_marker = client_cversion
        # enregistrement de la clef
        clientkey = dictargs["changelogs_key"]
        self._sync_clients_dict[player]["sync_key"] = clientkey

    def server_check_players_changelog_keys(self, callback):
        """
        Méthode générique de contrôle de cohérence des clients. Compare self._gamble_key 
        aux clés enregistrées dans self._sync_clients_dict, après :
        
        - l'exécution d'un coup 
        - la mise à jour des XTras
        
        En cas d'incohérences, le serveur resynchronise les clients le nécessitant (via 
        le code GameManager.BUILD_LAB), la propriété self.wait_client_resync passe alors 
        à True. Dans le cas contraire, le callback de poursuite de traitement est appelé.
        
        Args:
            callback (function): callback à appeler en absence d'incohérences.
        """
        count = 0
        nbplayers = 0
        # 1- Etats de synchro des clients associés au coup :
        uidlist = self._get_uid_list_to_sync()
        newuidlist = list()
        for uid in uidlist:
            player = self.get_player_by_uid(uid)
            nbplayers += 1
            cltdict = self._sync_clients_dict[player]
            cltkey = cltdict["sync_key"]
            if not player.joignable:
                # client déconnecté, on ne l'attend pas
                cltdict["lab_sync"] = False
                count += 1
            elif cltkey == self._gamble_key:
                # la clef est bonne :
                cltdict["lab_sync"] = True
                count += 1
            elif cltkey != None:
                # la clef n'est pas bonne, on resynchronise le client :
                cltdict["lab_sync"] = False
                count += 1
            else:
                # client en attente
                newuidlist.append(uid)
        # maj de la liste :
        self._register_uid_list_to_sync(uidlist=newuidlist)
        if len(newuidlist) > 0:
            self._on_wait_sync_passed(newuidlist)
        if count == nbplayers:
            # phase de vérification achevée :
            # 2- Resynchro des clients le nécessitant:
            uid_to_resync = list()
            for player in self._sync_clients_dict.keys():
                cltdict = self._sync_clients_dict[player]
                # ré initialisation des clefs de changelog
                cltdict["sync_key"] = None
                # marqueur de resynchro
                lab_sync = cltdict["lab_sync"]
                if player.joignable and not lab_sync:
                    uid_to_resync.append(player.uid)
                    cltdict["lab_sync_done"] = False
                else:
                    cltdict["lab_sync_done"] = True
            if len(uid_to_resync) > 0:
                # mémorisation de la liste :
                self._register_uid_list_to_sync(uidlist=uid_to_resync)
                # init du process de surveillance
                self._start_wait_sync_process()
                # ordre de resynchro
                self.update_players_labyrinthe(GameManager.BUILD_LAB, uid_to_resync)
                # info autres clients;
                othersuid = [
                    x for x in self._get_clients_uid_list() if x not in uid_to_resync
                ]
                self.sendNetworkMessage(
                    "Resynchronisation de clients en cours...", uid=othersuid
                )
                # marqueurs :
                self.wait_clients_gamble_keys = False
                self.wait_clients_XTras_keys = False
                self.wait_client_resync = True
            # infos
            self.affiche_partie_infos_for_server()
            # 3- Poursuite de la gestion du coup ;
            if not self.wait_client_resync:
                callback()

    def server_register_client_lab_resync(self, dictargs):
        """
        Réception de la confirmation par un client de la resynchro du labyrinthe.
        """
        # mise à jour de la version de carte du client
        uid = dictargs["uid"]
        player = self.get_player_by_uid(uid)
        client_cversion = int(dictargs["carte_version"])
        player.sync_marker = client_cversion
        # cas particulier des clients viewer :
        if player.viewer:
            self.on_player_status_changed(uid)
        # contrôle de synchro :
        if client_cversion == self.carte_version:
            if self.wait_client_resync:
                cltdict = self._sync_clients_dict[player]
                cltdict["lab_sync"] = True
                cltdict["lab_sync_done"] = True
        else:
            # on relance une commande de synchro
            self.update_players_labyrinthe(GameManager.BUILD_LAB, listuid=uid)

    def server_check_clients_lab_resync(self):
        """
        Vérifie que les clients identifiés dans self._sync_clients_dict comme 
        non synchronisés aient renvoyé le code GameManager.BUILD_LAB_DONE
        """
        unsync_count = 0
        uidlist = self._get_uid_list_to_sync()
        newuidlist = list()
        for uid in uidlist:
            player = self.get_player_by_uid(uid)
            cltdict = self._sync_clients_dict[player]
            lab_sync_done = cltdict["lab_sync_done"]
            if player.joignable and not lab_sync_done:
                # on ignore les clients déconnectés
                unsync_count += 1
                newuidlist.append(uid)
        # maj de la liste :
        self._register_uid_list_to_sync(uidlist=newuidlist)
        if len(newuidlist) > 0:
            # pings au besoin
            self._on_wait_sync_passed(newuidlist)
        elif unsync_count == 0:
            # tous les clients sont synchronisés
            self.wait_client_resync = False
        if len(newuidlist) != len(uidlist):
            # infos
            self.affiche_partie_infos_for_server()
        if unsync_count == 0:
            # poursuite des traitements :
            if self.partie_phasis == GameManager.PARTIE_STARTED:
                # partie en cours
                if not self.gamble_XTras_updated:
                    # pré finalisation du coup :
                    self.master_closing_gamble()
                else:
                    # finalisation :
                    self.on_gamble_closed()
            elif self.partie_phasis == GameManager.PARTIE_CREATED:
                # phase d'initialisation
                self._on_clients_init_pub_done()

    def server_check_players_gamble_keys(self):
        """
        Contrôle de cohérence des clients après application du coup.
        """
        clb = self._on_clients_gamble_keys_checked
        self.server_check_players_changelog_keys(clb)

    def _on_clients_gamble_keys_checked(self):
        """
        Callback appelé lorsque tous les clients sont synchronisés après 
        application du coup.
        """
        # marqueur
        self.wait_clients_gamble_keys = False
        # pré finalisation du coup : maj des XTras
        self.master_closing_gamble()

    def server_check_players_XTras_keys(self):
        """
        Contrôle de cohérence des clients après mise à jour des XTras.
        """
        clb = self._on_clients_XTras_keys_checked
        self.server_check_players_changelog_keys(clb)

    def _on_clients_XTras_keys_checked(self):
        """
        Callback appelé lorsque tous les clients sont synchronisés après 
        mise à jour des XTras.
        """
        # marqueur
        self.wait_clients_XTras_keys = False
        # finalisation complète du coup
        self.on_gamble_closed()

    #-----> D.2- Cohérence (client)
    def client_send_changelog_key(self):
        """
        Le client envoie au serveur sa clef de changelog pour
        contrôle de cohérence.
        """
        dictargs = {
            "uid": self.uid,
            "carte_version": self.carte_version,
            "changelogs_key": self.create_changelog_key(),
        }
        self.fire_game_event(
            GameManager.CHECK_CHANGELOG_KEY, dictargs=dictargs, suffix="clt"
        )

    def client_confirm_lab_resync(self):
        """
        A l'issue de la publication complète du labyrinthe le client envoie 
        un message de confirmation au serveur.
        """
        dictargs = {
            "uid": self.uid,
            "carte_version": self.carte_version,
        }
        self.fire_game_event(
            GameManager.BUILD_LAB_DONE, dictargs=dictargs, suffix="clt"
        )
        self.unlock_NET_tasks()

    #-----> E- Gestion des choix utilisateurs
    #-----> E.1- Mécanique générale
    #-----> E.1.1- Choix globaux
    def handle_global_choice(self, exobj):
        """
        Prend en charge une éventuelle commande globale (afficher aide, quitter), 
        retourne un booleen indiquant si l'on doit interrompre le process éventuel 
        d'attente de choix pré existant.
        """
        do_stop = False
        action = None
        if type(exobj) == appcomp.GUIExchangeObject:
            dictargs = exobj.dictargs
            if "choix" in dictargs.keys():
                cmd = dictargs["choix"]
                dictcmd = None
                action = None
                try:
                    dictcmd = CommandHelper.translate_cmd(cmd)
                except ValueError:
                    return do_stop
                action = dictcmd["action"]
                if action in [
                    LabHelper.ACTION_HELP,
                    LabHelper.ACTION_QUIT,
                    LabHelper.ACTION_MENU,
                    LabHelper.ACTION_RESET_QUEUE,
                ]:
                    # on applique :
                    if action == LabHelper.ACTION_HELP:
                        self.affiche_aide()
                    elif action == LabHelper.ACTION_QUIT:
                        self.quit_game()
                        do_stop = True
                    elif action == LabHelper.ACTION_MENU:
                        self.goto_menu()
                        do_stop = True
                    elif action == LabHelper.ACTION_RESET_QUEUE:
                        # todo
                        pass
        return do_stop

    #-----> E.1.2- Réponse à une question
    def ask_user_choice(self, params):
        """
        Etape 1 : envoie la demande de choix à l'utilisateur ciblé.
        """
        if type(params) == appcomp.GUIExchangeObject:
            dictargs = params.dictargs
        elif type(params) == dict:
            dictargs = params
        else:
            return
        # paramètres
        uid = None
        if "uid" in dictargs.keys():
            uid = dictargs["uid"]
        typechoix = dictargs["typechoix"]
        if typechoix == GameManager.ENTER_NET_ADDRESS:
            newdictargs = self._enter_server_add_step1()
        elif typechoix == GameManager.ENTER_CMD:
            newdictargs = self._enter_cmd_step1(uid)
        elif typechoix == GameManager.CHOOSE_GAME:
            newdictargs = self._choose_game_step1(uid)
        elif typechoix == GameManager.START_GAME:
            newdictargs = self._start_partie_step1(uid)
        newdictargs["typechoix"] = typechoix
        if "uid" not in newdictargs.keys():
            newdictargs["uid"] = uid
        if "comuid" in dictargs.keys():
            newdictargs["comuid"] = dictargs["comuid"]
        else:
            newdictargs["comuid"] = self._generate_request_uid("abs")
        # traitement
        if self.type_app == AppTypes.APP_SERVER and uid != self.uid:
            # on envoie la demande au client :
            self.fire_game_event(typechoix, dictargs=newdictargs, uid=uid, suffix="auc")
        else:
            # on choisit localement :
            code = appcomp.GUIExchangeObject.ASK_USER_CHOICE
            dictvars = newdictargs
            obj = ExchangeHelper.createGUIObj(code, dictvars)
            self.sendGuiCmd(obj)

    def check_user_choice(self, obj):
        """
        Etape 2 : vérifie la validité du choix utilisateur
        
        Args:
            obj : GUIExchangeObject généré à l'étape 1 ou envoyé spontanément via la GUI
        """
        # paramètres
        valide = False
        typechoix = obj.dictargs["typechoix"]
        # commande globale ?
        do_stop = self.handle_global_choice(obj)
        # réponse à une question ?
        if not do_stop:
            # Réponse ou commande globale n'interrompant pas le process en cours
            if typechoix == GameManager.ENTER_NET_ADDRESS:
                valide, obj = self._enter_server_add_step2(obj)
            elif typechoix in [GameManager.ENTER_CMD, GameManager.QUEUE_CMD]:
                valide, obj = self._enter_cmd_step2(obj)
            elif typechoix == GameManager.CHOOSE_GAME:
                valide, obj = self._choose_game_step2(obj)
            elif typechoix == GameManager.START_GAME:
                valide, obj = self._start_partie_step2(obj)
            # Traitement :
            if valide:
                # on passe à l'étape 3
                self.handle_user_choice(obj)
            else:
                # on redemande un input valide
                obj.typeexchange = appcomp.GUIExchangeObject.ASK_USER_CHOICE
                self.sendGuiCmd(obj)

    def handle_user_choice(self, obj):
        """
        Etape 3 : traite un choix utilisateur valide
        
        Args:
            obj : GUIExchangeObject généré à l'étape 1
        """
        # paramètres
        comuid = None
        if "comuid" in obj.dictargs.keys():
            comuid = obj.dictargs["comuid"]
        typechoix = obj.dictargs["typechoix"]
        code, handler, newdictargs, handlerargs = None, None, None, None
        if typechoix == GameManager.ENTER_NET_ADDRESS:
            # cas particulier : on applique en interne :
            self._enter_server_add_step3(obj)
            return
        elif typechoix == GameManager.ENTER_CMD or typechoix == GameManager.QUEUE_CMD:
            code = GameManager.QUEUE_CMD
            handler = None
            newdictargs, handlerargs = self._enter_cmd_step3(obj)
        elif (
            typechoix == GameManager.CHOOSE_GAME or typechoix == GameManager.GAME_CHOICE
        ):
            code = GameManager.GAME_CHOICE
            handler = self._define_game
            newdictargs, handlerargs = self._choose_game_step3(obj)
        elif typechoix == GameManager.START_GAME:
            code = GameManager.START_GAME
            handler = self.start_partie
            newdictargs = {}
            # pas de params particuliers
        newdictargs["typechoix"] = code
        newdictargs["comuid"] = comuid
        # Traitement :
        if self.master:
            # Pseudos événements
            if code == GameManager.QUEUE_CMD:
                self.on_queue_cmd_added(newdictargs)
            if code == GameManager.GAME_CHOICE:
                self.on_game_choice_made(newdictargs)
            # on applique
            if handler != None:
                handler(handlerargs)
        else:
            # on retourne au serveur
            self.fire_game_event(code, dictargs=newdictargs, suffix="huc")

    #-----> E.2- Saisie adresse serveur :
    def _enter_server_add_step1(self):
        """
        Demande de saisie de l'adresse du serveur
        """
        msg_input = "Saisissez l'adresse du serveur."
        return {"msg_input": msg_input}

    def _enter_server_add_step2(self, obj):
        """
        Validation de l'ip saisie
        """
        valide = False
        host, port = None, None
        choix = obj.dictargs["choix"]
        splited = choix.split(":")
        if len(splited) == 2:
            host, port = splited[0], splited[1]
            host_val, port_val = False, False
            # validation de l'host :
            if host in ["", "localhost"]:
                host_val = True
            else:
                try:
                    socket.inet_aton(host)
                except OSError:
                    pass
                else:
                    host_val = True
            # validation du port :
            try:
                port = int(port)
            except:
                pass
            else:
                if port in range(2000, 65535):
                    port_val = True
            # validation finale :
            if host_val and port_val:
                valide = True
        # retour :
        if valide:
            obj.dictargs["host"] = host
            obj.dictargs["port"] = port
        else:
            # on renvoit à la GUI :
            msg = "Erreur : connection impossible à l'adresse : " + str(choix) + "."
            obj.dictargs["msg"] = msg
            if self.type_app == AppTypes.APP_SERVER:
                msg_input = "Le port saisi est probablement indisponible, choisissez un port dans la plage 2000 - 65535."
            else:
                msg_input = "Assurez vous qu'un serveur LabPyrinthe soit lancé puis saisissez son adresse au format ip:port (ex: 192.168.0.4:10326)."
            obj.dictargs["msg_input"] = msg_input
            del obj.dictargs["choix"]
        # retour
        return valide, obj

    def _enter_server_add_step3(self, obj):
        """
        Lance le processus de connection après mise à jour de l'adresse serveur.
        """
        # connection
        net_code = appcomp.NETExchangeObject.CONNECT
        dictargs = {"host": obj.dictargs["host"], "port": obj.dictargs["port"]}
        exobj = appcomp.NETExchangeObject(net_code, dictargs=dictargs)
        self.sendTask(exobj)
        # efface le message précédent
        self.affiche_message("")

    #-----> E.3- Choix partie
    def _choose_game_step1(self, uid):
        """
        Présente la liste des parties et envoie une demande d'input à la GUI
        """
        msg_input = "Saisissez un numéro de niveau puis : \n"
        msg_input += "- [Entrée] pour lancer une partie \n"
        msg_input += "- d puis [Entrée] pour lancer une démo."
        msg_input_alt = msg_input
        listeniveaux = [
            "1- Facile",
            "2- Moyen",
            "3- Difficile",
        ]
        # retour
        return {
            "uid": uid,
            "listeniveaux": listeniveaux,
            "msg_input": msg_input,
            "msg_input_alt": msg_input_alt,
        }

    def _choose_game_step2(self, obj):
        """
        Méthode de validation de l'input
        """
        valide = False
        c = 0
        choix = obj.dictargs["choix"]
        # choix : soit un num de niveau seul, soit suivi de p (partie) ou d (démo)
        numniv = modestr = None
        if len(choix) == 1:
            numniv = choix
            modestr = "p"
        elif len(choix) == 2:
            numniv = choix[0]
            modestr = choix[1]
        # mode (par défaut partie) :
        mode = GameManager.GAME_MODE_PARTIE
        if modestr == "d":
            mode = GameManager.GAME_MODE_DEMO
        # niveau :
        listeniveaux = obj.dictargs["listeniveaux"]
        if LabHelper.REGEXP_INT.match(str(numniv)):
            c = int(numniv)
            if c >= 1 and c <= len(listeniveaux):
                # input valide
                obj.dictargs["indice"] = c
                obj.dictargs["mode"] = mode
                valide = True
        if not valide:
            # on renvoit à la GUI :
            obj.dictargs["msg_input"] = (
                "Commande invalide, saisissez un entier entre 1 et "
                + str(len(listeniveaux))
                + "."
            )
            obj.dictargs["msg_input_alt"] = (
                "Commande invalide, saisissez un entier entre 1 et "
                + str(len(listeniveaux))
                + "."
            )
            del obj.dictargs["choix"]
        # retour
        return valide, obj

    def _choose_game_step3(self, obj):
        """
        Traite le choix utilisateur
        """
        indice = int(obj.dictargs["indice"])
        mode = obj.dictargs["mode"]
        return {"indice": indice, "mode": mode}, {"indice": indice, "mode": mode}

    #-----> E.4- Démarrer la partie
    def _start_partie_step1(self, uid):
        """
        Propose de démarrer la partie
        """
        self.affiche_message("")
        msg_input = (
            "Attendez que d'autres joueurs rejoignent la partie ou saisissez "
            + LabHelper.CHAR_START
            + " + [Entrée] pour commencer à jouer."
        )
        return {"uid": uid, "msg_input": msg_input, "msg_input_alt": ""}

    def _start_partie_step2(self, obj):
        """
        Validation de la commande de démarrage
        """
        valide = False
        choix = obj.dictargs["choix"]
        if choix == LabHelper.CHAR_START:
            valide = True
        return valide, obj

    #-----> E.5- Commande de jeu
    def _enter_cmd_step1(self, uid):
        """
        Demande au joueur d'uid d'entrer une commande
        """
        player = self.get_player_by_uid(uid)
        msg_input = ""
        if player != None:
            msg_input = player.nom + " c'est à votre tour de jouer. "
        msg_input += "Veuillez entrer une commande. "
        return {"uid": uid, "msg_input": msg_input}

    def _enter_cmd_step2(self, obj):
        """
        Méthode de validation d'un input de cmd
        - obj : GUIExchangeObject crée à l'étape 1
        """
        choix = obj.dictargs["choix"]
        uid = obj.dictargs["uid"]
        # cas général :
        valide, dictcmd = False, None
        if self.partie_started:
            cmd_study = self.labMngr.analyse_cmd_for_robot(choix, uid)
            valide = cmd_study[0]
            dictcmd = cmd_study[1]
        if dictcmd == None:
            valide = False
        if valide == False:
            typechoix = obj.dictargs["typechoix"]
            # s'il s'agit d'une question explicite
            if typechoix == GameManager.ENTER_CMD:
                # on renvoit à la GUI :
                obj.dictargs["msg_input"] = "Veuillez saisir une commande valide."
                del obj.dictargs["choix"]
        else:
            obj.dictargs["dictcmd"] = dictcmd
        return valide, obj

    def _enter_cmd_step3(self, obj):
        """
        Traite le choix utilisateur
        """
        return obj.dictargs, obj.dictargs

    #-----> F- Affichages (GUI)
    #-----> F.1- Affichages non suivis
    def dispatch_NETInfos(self, dictargs):
        """
        Transmet à l'interface les infos réseau pour publication
        """
        code = appcomp.GUIExchangeObject.SET_BUS_INFO
        obj = ExchangeHelper.createGUIObj(
            code, {"info": GameManager.NET_INFOS, "dictdatas": dictargs}
        )
        # Envoi à la GUI
        self.sendGuiCmd(obj)

    def dispatch_type_partie(self):
        """
        Affichage du type de partie et du niveau.
        """
        dictvars = {
            "content": GameManager.CONTENT_TYPE_PARTIE,
            "mode": self.current_game_mode,
            "niveau": self.current_game_level,
        }
        code = appcomp.GUIExchangeObject.SHOW_CONTENT
        obj = ExchangeHelper.createGUIObj(code, dictvars)
        # Envoi à la GUI
        self.sendGuiCmd(obj)
        # statut:
        self.on_player_status_changed(self.uid)

    def affiche_message(self, txt):
        """
        Affichage d'un message contextuel
        """
        dictvars = {"content": GameManager.CONTENT_MESSAGE, "txt": txt}
        code = appcomp.GUIExchangeObject.SHOW_CONTENT
        obj = ExchangeHelper.createGUIObj(code, dictvars)
        # Envoi à la GUI
        self.sendGuiCmd(obj)

    def affiche_gamble_context(self):
        """
        Transmet à l'interface le contexte du coup à venir
        """
        if self.type_app == AppTypes.APP_SERVER:
            # méthode dédiée
            self.affiche_partie_infos_for_server()
        else:
            # contexte
            dictvars = {
                "content": GameManager.CONTENT_GAMBLE_CTX,
                "robots": self.labMngr.get_robotlist(),
                "gambleinfos": self.gambleinfos,
            }
            code = appcomp.GUIExchangeObject.SHOW_CONTENT
            obj = ExchangeHelper.createGUIObj(code, dictvars)
            # Envoi à la GUI
            self.sendGuiCmd(obj)
            # numéro du coup
            txt = "Coup n° " + str(self.gamblenumber) + "..."
            self.affiche_message(txt)

    def affiche_partie_infos_for_server(self):
        """
        Transmet à l'interface des infos sur la partie
        """
        if self.type_app == AppTypes.APP_SERVER:
            msg = self._create_partie_abstract_for_server()
            dictvars = {
                "content": GameManager.CONTENT_PARTIE_SERVER,
                "msg": msg,
            }
            code = appcomp.GUIExchangeObject.SHOW_CONTENT
            obj = ExchangeHelper.createGUIObj(code, dictvars)
            # Envoi à la GUI
            self.sendGuiCmd(obj)

    def _create_partie_abstract_for_server(self):
        """
        Génère un texte résumant l'état de la partie.
        
        Provisoire : mise en forme à gérer côté GUI (cf pub_helper dans skinConsole).
        """         
        txt = "\n"
        has_details = True
        if self.partie_phasis in [GameManager.INITIAL_PHASIS, GameManager.PARTIE_INIT]:
            txt = "Aucune partie en cours."
            has_details = False
        elif self.partie_phasis == GameManager.PARTIE_CHOSEN:
            txt = "Partie choisie, mode : " + str(self.current_game_mode)
            has_details = False
        elif self.partie_phasis == GameManager.PARTIE_CREATED:
            txt = "Partie crée, mode : " + str(self.current_game_mode)
        elif self.partie_phasis == GameManager.PARTIE_STARTED:
            txt = "Partie démarrée, mode : " + str(self.current_game_mode)
        elif self.partie_phasis == GameManager.PARTIE_ENDED:
            txt = "Partie terminée, mode : " + str(self.current_game_mode)
        if has_details:
            txt += "\n" + GameConfiguration.get_game_repr()
            if self.partie_phasis == GameManager.PARTIE_STARTED:
                txt += "\n"
                txt += "\n" + "Joueur : "
                if self.current_player_indice == None:
                    txt += "aucun joueur actif"
                else:
                    newplayer = self.playerlist[self.current_player_indice]
                    txt += newplayer.nom
                    txt += " [attente cmd : " + str(self.wait_player_choice) + "]"
                rslist = self._get_uid_list_to_sync()
                txt += "\n"
                txt += "\n" + "Coup : " + str(self.gamblenumber)
                if self.gamble_ended:
                    txt += "     |======|"
                elif self.gamble_applied:
                    txt += "     |====  |"
                elif self.applying_gamble:
                    txt += "     |==    |"
                else:
                    txt += "     |      |"
                txt += "\n"
                txt += "\n" + "Commande jouée : " + str(self.current_cmd)
                txt += " [cmd valide : " + str(self.current_cmd_validated) + "]"
                txt += "\n"
                if self.wait_clients_gamble_keys:
                    txt += (
                        "\nVérification des clefs de synchronisation en cours (coup)..."
                    )
                    # txt += "\n - clef : " + str(self._gamble_key)
                    txt += "\n - uids : " + " ".join(rslist)
                elif self.wait_clients_XTras_keys:
                    txt += "\nVérification des clefs de synchronisation en cours (XTras)..."
                    # txt += "\n - clef : " + str(self._gamble_key)
                    txt += "\n - uids : " + " ".join(rslist)
                elif self.wait_client_resync:
                    txt += "\nEn attente de la resynchronisation des clients..."
                    txt += "\n - uids : " + " ".join(rslist)
        return txt

    def affiche_aide(self):
        """
        Affichage / masquage aide.
        """
        dictvars = {"content": GameManager.CONTENT_HELP}
        code = appcomp.GUIExchangeObject.SHOW_CONTENT
        obj = ExchangeHelper.createGUIObj(code, dictvars)
        # Envoi à la GUI
        self.sendGuiCmd(obj)

    #-----> F.2- Affichages suivis (carte)
    #-----> F.2.1- Mécanique générique
    def init_gui_order_system(self):
        """
        Initialise la gestion du suivi d'ordres d'affichages
        """
        self.gui_increment = 0
        self.gui_orders_dict = dict()

    def create_gui_order_number(self):
        """
        Génère un identifiant d'ordre d'affichage (maj carte)
        """
        self.gui_increment += 1
        return self.gui_increment

    def register_gui_order_callback(self, gui_order, clb, *args):
        """
        Enregistre un callback à appeler lorsque la GUI confirmera l'affichage
        de l'ordre n° gui_order.
        """
        self.gui_orders_dict[gui_order] = {"clb": clb, "args": args}

    def handle_gui_order_callback(self, dictargs):
        """
        Applique l'éventuel callback d'affichage suivi.
        
        Rq : appelée par self.on_content_published (confirmation affichage par GUI)
        """
        if "gui_order" in dictargs.keys():
            gui_order = int(dictargs["gui_order"])
            if gui_order in self.gui_orders_dict.keys():
                # données du callback
                clb = self.gui_orders_dict[gui_order]["clb"]
                args = self.gui_orders_dict[gui_order]["args"]
                # suppression de l'ordre
                self.gui_orders_dict.pop(gui_order)
                # application du callback
                if args != (None,):
                    clb(*args)
                else:
                    clb()

    #-----> F.2.2- Affichages avec callback
    def publish_carte(self, callback, *args):
        """
        Envoie une commande d'affichage complet de la carte à la GUI
        """
        # Discard pub :
        self.discard_publication_status()
        # Affichage suivi?
        gui_order = None
        if callback != None:
            gui_order = self.create_gui_order_number()
            self.register_gui_order_callback(gui_order, callback, *args)
        # Données d'affichage :
        chaine = self.labMngr.get_repr_view()
        w, h = self.labMngr.get_dimensions()
        dictvars = {
            "content": GameManager.PUBLISH_CARTE,
            "txt": chaine,
            "w": w,
            "h": h,
            "matrices": self.labMngr.get_graph_matrices(),
            "robots": self.labMngr.get_robotlist(),
            "gambleinfos": self.gambleinfos,
            "gui_order": gui_order,
        }
        # Envoi à la GUI
        code = appcomp.GUIExchangeObject.SHOW_CONTENT
        obj = ExchangeHelper.createGUIObj(code, dictvars)
        self.sendGuiCmd(obj)

    def show_carte_txt_in_preload(self):
        """
        Affichage de la carte txt dans l'écran de preload de partie
        """
        chaine = self.labMngr.get_repr_view()
        dictvars = {"content": GameManager.SHOW_TXT_CARTE, "txt": chaine}
        code = appcomp.GUIExchangeObject.SHOW_CONTENT
        obj = ExchangeHelper.createGUIObj(code, dictvars)
        self.sendGuiCmd(obj)

    def update_carte(self, callback, *args):
        """
        Mise à jour partielle de la carte.
        """
        # Discard pub :
        self.discard_publication_status()
        # Affichage suivi?
        gui_order = None
        if callback != None:
            gui_order = self.create_gui_order_number()
            self.register_gui_order_callback(gui_order, callback, *args)
        # Données d'affichage :
        chaine = self.labMngr.get_repr_view()
        w, h = self.labMngr.get_dimensions()
        diffdatas = self.labMngr.get_diff_graph_datas()
        dictvars = {
            "content": GameManager.UPDATE_CARTE,
            "txt": chaine,
            "w": w,
            "h": h,
            "updatedict": diffdatas,
            "robots": self.labMngr.get_robotlist(),
            "gui_order": gui_order,
        }
        # Envoi à la GUI
        code = appcomp.GUIExchangeObject.SHOW_CONTENT
        obj = ExchangeHelper.createGUIObj(code, dictvars)
        self.sendGuiCmd(obj)

    def affiche_animation_pixel(
        self, case, coords1, coords2, duration, callback, *args
    ):
        """
        Animation de déplacement fine (pixel)
        """
        # Discard pub :
        self.discard_publication_status()
        # Affichage suivi?
        gui_order = None
        if callback != None:
            gui_order = self.create_gui_order_number()
            self.register_gui_order_callback(gui_order, callback, *args)
        # Données d'affichage :
        dictvars = {
            "content": GameManager.CONTENT_ANIM_PIXEL,
            "case": case,
            "coords1": coords1,
            "coords2": coords2,
            "duration": duration,
            "gui_order": gui_order,
        }
        # Envoi à la GUI
        code = appcomp.GUIExchangeObject.SHOW_CONTENT
        obj = ExchangeHelper.createGUIObj(code, dictvars)
        self.sendGuiCmd(obj)

    #-----> F.3- Statut de publication (carte)
    def discard_publication_status(self):
        """
        Invalide le statut de publication de la GUI
        """
        self.content_published = False

    def on_content_published(self, dictargs):
        """
        Confirmation par la GUI de la dernière demande d'affichage de contenu.
        """
        self.content_published = True
        # affichage suivi :
        self.handle_gui_order_callback(dictargs)

    def get_publication_status(self):  # à supprimer
        """
        Retourne le statut de publication
        """
        # Actions GUI en attente ?
        # Rq : méthode appelée pendant des boucles bloquantes
        appcomp.BUSINESSComp.handleTask(self)
        return self.content_published

    #-----> G- Création d'une partie
    def _define_game(self, gamedict):
        """
        Initialise la partie une fois le niveau de difficulté choisi
        """
        # Infos
        msgdict = dict()
        msgdict[0] = "[1/7] Configuration de la partie..."
        msgdict[1] = "[2/7] Création d'une nouvelle carte..."
        msgdict[2] = "[3/7] Publication des joueurs..."
        msgdict[3] = "[4/7] Echantillonnage..."
        msgdict[4] = "[5/7] Publication des dangers et bonus..."
        msgdict[5] = "[6/7] Fin de l'initialisation..."
        # Batch :
        step = 0
        while step < 6:
            # message :
            msg = msgdict[step]
            msg += "\n" + GameConfiguration.get_game_repr()
            self._dispatch_step_info(msg)
            # batch de création :
            if step == 0:
                # 1- Configuration :
                self._configure_partie(gamedict)
            elif step == 1:
                # 2- Création de la carte de base
                self._create_base_carte()
            elif step == 2:
                # 3- Publication des joueurs :
                self._complete_players()
                self.labMngr.publish_players(self.playerlist)
            elif step == 3:
                # 4- Init distributions aléatoires :
                self._init_random_distribution()
            elif step == 4:
                # 5- Ajout des Xtras :
                self._add_XTras_cases(initialpub=True)
                # self.labMngr._trace_samples_after_distribution()
            elif step == 5:
                # 6- config partie (locale / clients distants)
                self.on_partie_created()
            step += 1

    def _dispatch_step_info(self, msg):
        """
        Affichage local/distant des infos
        """
        # distant :
        self.sendNetworkMessage(msg)
        # local :
        self.affiche_message(msg)

    def _configure_partie(self, gamedict):
        """
        Configure le mode (partie/démo) et le niveau
        """
        # Config :
        GameConfiguration.set_difficulty(self.current_game_level)

    def _create_base_carte(self):
        """
        Génération de la carte de base (vide, portes, murs, sortie), parsing et
        création du LabLevel
        """
        # Création de la carte texte et parsing :
        lignes = self.labMngr.create_random_carte()
        self.carte_initiale = lignes
        self.carte_created = True
        parsedict = {"cartetxt": lignes}
        self.labMngr.parse_labyrinthe(parsedict)

    def _init_random_distribution(self):
        """
        Initialise la distribution aléatoire de bonus/mines et de bots :
            - échantillonage des sous matrices de cases vides
            - liste de comportements de bots
        """
        # échantillonnage :
        self.labMngr.define_initial_samples()

    def _add_XTras_cases(self, initialpub=False):
        """
        Ajoute des cases bonus et danger après le parsing initial
        """
        bonuslist, dangerlist = self.labMngr.random_distribute_XTras(
            initialpub=initialpub
        )
        rlist = list()
        if len(bonuslist) > 0:
            rlist.extend(bonuslist)
        if len(dangerlist) > 0:
            rlist.extend(dangerlist)
        return rlist

    def _complete_players(self):
        """
        Ajoute les bots après configuration de la partie, finalise l'initialisation
        """
        # comportements :
        self._listbotsbehaviors = GameConfiguration.get_behaviors_list()
        # Création des robots non publiés pour les joueurs humains:
        if self.current_game_mode == GameManager.GAME_MODE_PARTIE:
            if self.playerlist != None and len(self.playerlist) > 0:
                for player in self.playerlist:
                    self._create_robot_for_player(player)
        # Création des bots :
        numb = GameConfiguration.get_bots_number()
        i = 0
        while i < numb:
            self._register_new_player(None, True, False, publish=False)
            i += 1
        self.bots_added = True

    def _register_new_player(self, uid, local, human, behavior=None, publish=False):
        """
        Contexte master : enregistre un nouveau joueur
        """
        # création du joueur :
        if self.playerlist == None:
            self.playerlist = list()
        num = str(len(self.playerlist) + 1)
        hum_num = 1
        for pl in self.playerlist:
            if pl.player_type == LabPlayer.HUMAN:
                hum_num += 1
        nom = "Joueur " + num
        if uid == None:
            # joueur ajouté par ce GameManager, on génère un id :
            uid = self._generate_uid()
        player = LabPlayer(uid, nom, local, human, num, hum_num, behavior)
        # enregistrement :
        self.playerlist.append(player)
        # Robot :
        if GameConfiguration.is_game_configured():
            # création et initialisation du robot :
            self._create_robot_for_player(player)
            if publish and self.carte_created:
                self.labMngr.publish_players(self.playerlist)

    def _create_robot_for_player(self, player):
        """
        Génère l'objet robot assoié au joueur une fois la partie configurée
        """
        # comportement :
        if player.player_type == LabPlayer.HUMAN:
            if self.current_game_mode == GameManager.GAME_MODE_DEMO:
                # pas de robots humains dans ce mode
                return
            elif self.partie_started:
                # partie déja en cours
                return
            behavior = CaseRobot.BEHAVIOR_HUMAN
            human = True
        else:
            human = False
            if player.behavior == None:
                listcomp = self._listbotsbehaviors
                cr.CustomRandom.shuffle(listcomp)
                behavior = cr.CustomRandom.choice(listcomp)
                listcomp.remove(behavior)
            else:
                behavior = player.behavior
        player.behavior = behavior
        if player.color == None:
            self._get_color_for_player(player)
        color = player.color
        # face :
        face = CaseRobot.get_char_repr(behavior)
        # dict de paramétrage :
        dictrobot = CaseRobot.get_default_dict()
        dictrobot["uid"] = player.uid
        dictrobot["face"] = face
        dictrobot["human"] = human
        dictrobot["number"] = player.number
        dictrobot["human_number"] = player.human_number
        dictrobot["behavior"] = behavior
        dictrobot["color"] = color
        # Création et initialisation du robot:
        robot = self.labMngr.register_robot(dictrobot)
        player.set_robot(robot)

    def _dispatch_liste_robots(self):
        """
        Contexte master : définit la liste des robots utilisée par LabManager
        et CommandManager
        """
        listr = list()
        for player in self.playerlist:
            robot = player.get_robot()
            if robot != None:
                listr.append(robot)
        self.labMngr.update_robotlist(listr)

    #-----> H- Gestion des couleurs associées aux joueurs
    def _init_players_colors(self):
        """
        Initialise l'affectation des couleurs
        """
        self.playercolors = dict()
        for behavior in CaseRobot.ALL_BEHAVIORS:
            self.playercolors[behavior] = list()
        self.playercolors["full"] = list()

    def _re_init_players_colors(self):
        """
        Ré initialise les couleurs affectées aux bots
        """
        for behavior in CaseRobot.FAMILLE_BEHAVIOR:
            self.playercolors[behavior] = list()
        list_h = self.playercolors[CaseRobot.BEHAVIOR_HUMAN]
        self.playercolors["full"] = list_h.copy()

    def _get_color_for_player(self, player):
        """
        Affecte une couleur à un joueur
        """
        behavior = player.behavior
        list_b = self.playercolors[behavior]
        list_full = self.playercolors["full"]
        done = False
        while not done:
            if behavior == CaseRobot.BEHAVIOR_HUMAN:
                col = ColorHelper.get_random_color()
            else:
                col = ColorHelper.get_color()
            if col not in list_b:
                done = True
                player.color = col
                list_b.append(col)
                list_full.append(col)
                break
