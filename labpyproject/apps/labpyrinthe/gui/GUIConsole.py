#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
**GUI du jeu : implémentation console**
"""
# imports :
import threading
from labpyproject.core.app import app_components as appcomp
from labpyproject.apps.labpyrinthe.app.app_types import AppTypes
from labpyproject.apps.labpyrinthe.bus.game_manager import GameManager
from labpyproject.apps.labpyrinthe.gui.skinBase.GUIBase import GUIBaseThreaded
from labpyproject.apps.labpyrinthe.gui.skinConsole.pub_helper import PublicationHelper

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["GUIConsole", "ThreadInput"]
# Classes :
class GUIConsole(GUIBaseThreaded):
    """
    Interface graphique de type console
    """

    def __init__(self):
        """
        Constructeur
        """
        # chaine txt précédement publiée
        self._prev_txt = ""
        # Helper de publication :
        self._pubHelper = PublicationHelper()
        # initialisation générique du composant d'interface
        GUIBaseThreaded.__init__(self)
        # mécanisme interne dédié aux inputs
        # question posée :
        self._question_object = None
        self._question_input = None
        # réponse apportée :
        self._reponse_input = None
        # Evénement assurant la synchro entre ce thread et le thread d'input :
        self.question_event = None
        # Thread dédié aux inputs non bloquants :
        self._input_thread = None
        # Initialisation du processus :
        self._init_input_process()

    #-----> Mécanisme de thread interne dédié aux inputs
    def _init_input_process(self):
        """
        Initialise le mécanisme d'input
        """
        # Création des objets :
        self.question_event = threading.Event()
        self._input_thread = ThreadInput(self.input_callback, self.question_event)
        self._input_thread.setDaemon(True)
        # Enregistrement du thread (dans la logique de appcomp.ThreadableComp ) :
        self.inner_threads.append(self._input_thread)
        self.threads_to_start.append(self._input_thread)
        self.set_childthreads_count(1)
        # input libre :
        self.let_user_send_command()

    def ask_input_question(self, guiexobj):
        """
        Déclenche une demande de réponse utilisateur via l'input
        """
        # question posée :
        self._question_object = guiexobj
        if "msg_input" in guiexobj.dictargs.keys():
            self._question_input = guiexobj.dictargs["msg_input"]
            self.show_message(self._question_input, True)
        # messages :
        if "msg" in guiexobj.dictargs.keys():
            msg = guiexobj.dictargs["msg"]
            self.show_message(msg, False)
        # réponse :
        self._reponse_input = None
        # Event :
        if self.question_event.is_set():
            self.question_event.clear()
        self.question_event.set()

    def let_user_send_command(self):
        """
        En l'absence de question explicitement posée par le composant business,
        ouvre l'input pour l'envoi d'une commande spontannée.
        """
        guiexobj = appcomp.GUIExchangeObject(
            appcomp.GUIExchangeObject.SEND_USER_COMMAND,
            dictargs={"msg_input": None, "cmd": None},
        )
        self.ask_input_question(guiexobj)

    def input_callback(self, reponse):
        """
        Callback appelé par le Thread d'input lorsque l'utilisateur a répondu.
        """
        # réponse :
        self._reponse_input = reponse
        if self._question_object != None:
            if (
                self._question_object.typeexchange
                == appcomp.GUIExchangeObject.SEND_USER_COMMAND
            ):
                # cas d'une commande spontanée :
                self._question_object.dictargs["typechoix"] = GameManager.QUEUE_CMD
                self._question_object.dictargs["choix"] = self._reponse_input
            else:
                # cas d'une réponse :
                self._question_object.dictargs["choix"] = self._reponse_input
                self._question_object.typeexchange = (
                    appcomp.GUIExchangeObject.RETURN_USER_CHOICE
                )
            # on retourne, le GameManager prend en charge la validation :
            self.sendTask(self._question_object)
        # input libre :
        self.let_user_send_command()

    #-----> implémentation d'AbstractGUIComp
    def handle_choice(self, obj):
        """
        Retourne l'input utilisateur, particularise la méthode "void" de appcomp.GUIComp
        
        Args:
            obj (GUIExchangeObject)
        """
        # affichage menu :
        typechoix = obj.dictargs["typechoix"]
        if typechoix == GameManager.CHOOSE_GAME:
            self.show_menu()
        # On pose la question :
        self.ask_input_question(obj)

    #-----> Affichages :
    def on_app_type_defined(self):
        """
        Appelée lorsque la GUI connait le type d'application associée (client, serveur, standalone)
        """
        # générique :
        GUIBaseThreaded.on_app_type_defined(self)
        # helper :
        self._pubHelper.type_app = self.type_app
        # mise à jour du header :
        txt = "LabPyrinthe | "
        if self.type_app == AppTypes.APP_SERVER:
            txt += "Serveur [console]"
        elif self.type_app == AppTypes.APP_CLIENT:
            txt += "Client [console]"
        elif self.type_app == AppTypes.APP_STANDALONE:
            txt += "Standalone [console]"
        self._pubHelper.update_content("header", msg=txt)
        # redraw :
        self._update_screen()

    def show_carte_publication(self, dictargs):
        """
        Affichage / mise à jour de la carte
        """
        # mise à jour des robots :
        if "gambleinfos" in dictargs.keys():
            self._pubHelper.update_content("bots", dictargs=dictargs)
        # mise à jour de la carte :
        self._pubHelper.update_content("carte", dictargs=dictargs)
        # affichage :
        self._show_screen("partie")
        # post traitement :
        self._on_carte_published()
        # confirmation :
        self.on_content_published(dictargs)

    def show_carte_update(self, dictargs):
        """
        Update partiel de la carte
        """
        # mise à jour de la carte :
        self._pubHelper.update_content("carte", dictargs=dictargs)
        # affichage :
        self._show_screen("partie")
        # confirmation :
        self.on_content_published(dictargs)

    def show_content_gamble_context(self, dictargs):
        """
        Affichage / mise à jour des infos robots, du coup joué
        """
        # mise à jour des robots :
        self._pubHelper.update_content("bots", dictargs=dictargs)
        # affichage :
        self._show_screen("partie")
        # confirmation :
        self.on_content_published(dictargs)

    def show_content_partie_server(self, dictargs):
        """
        Affichage spécifique serveur : infos partie.
        
        Args:
            dictargs (dict): {"content": GameManager.CONTENT_PARTIE_SERVER, "msg":}
        """
        if self.type_app == AppTypes.APP_SERVER:
            self._pubHelper.update_content("server_partie", dictargs=dictargs)
            # affichage :
            self._show_screen("partie")
            # confirmation :
            self.on_content_published(dictargs)

    def show_content_message(self, dictargs):
        """
        Affichage d'un message contextuel
        """
        txt = dictargs["txt"]
        self.show_message(txt, False)

    def show_content_cases(self, dictargs):
        """
        Affichage d'une liste réduite de cases
        """
        # mise à jour de la carte :
        self._pubHelper.update_content("carte", dictargs=dictargs)
        # affichage :
        self._show_screen("partie")
        # confirmation :
        self.on_content_published(dictargs)

    def show_menu(self):
        """
        Ecran menu
        """
        self._show_screen("menu")

    def create_partie(self):
        """
        Partie en cours de création
        """
        if self.type_app != AppTypes.APP_SERVER:
            msg = "Création de la partie en cours..."
            self._pubHelper.update_content("wait", msg=msg)
            self._show_screen("wait")

    def on_partie_created(self):
        """
        Process de création de la partie achevé
        """
        # générique :
        GUIBaseThreaded.on_partie_created(self)

    def show_message(self, msg, is_input):
        """
        Affichage de message ou consigne
        """
        dictargs = {"msg": msg, "is_input": is_input}
        self._update_msg_screen(dictargs)

    #-----> Publication des infos réseau :
    def show_NETInfos(self, dictargs):
        """
        Affichage des infos réseau.
        
        Args:
            dictargs : dict généré par la méthode get_network_infos du composant réseau associé
        """
        if self.type_app == AppTypes.APP_SERVER:
            self._pubHelper.update_content("footer", dictargs=dictargs)
            self._pubHelper.update_content("server_list", dictargs=dictargs)
            self._show_screen("server")
        elif self.type_app == AppTypes.APP_CLIENT:
            self._pubHelper.update_content("footer", dictargs=dictargs)
            self._update_screen()

    #-----> Configuration (état) :
    def register_partie_state(self, state):
        """
        Enregistre l'état actuel de la partie
        """
        # spécifique :
        self._pubHelper.register_partie_state(state)
        # générique :
        GUIBaseThreaded.register_partie_state(self, state)

    #-----> création de l'interface
    def create_interface(self):
        """
        Initialise la création de l'interface
        """
        # 1- Pré définition des contenus :
        # écran de chargement :
        msg_wait = "Chargement de l'application..."
        self._pubHelper.update_content("wait", msg=msg_wait)
        # header :
        msg_header = "LabPyrinthe | console"
        self._pubHelper.update_content("header", msg=msg_header)
        # footer : dynamique
        msg_partie = "Aucune partie n'est définie."
        self._pubHelper.update_content("server_partie", dictargs={"msg": msg_partie})
        # menu :
        tab = "     "
        eol = "\n"
        msg_menu = "MENU" + 2 * eol
        msg_menu += tab + "Niveau 1" + eol
        msg_menu += tab + "Niveau 2" + eol
        msg_menu += tab + "Niveau 3" + eol
        msg_menu += eol
        msg_menu += tab + "Partie : tapez 'n° niveau' + ENTREE (ex: 3 + ENTREE)" + eol
        msg_menu += (
            tab + "Démo : tapez 'n° niveau' + 'd' + ENTREE (ex: 2d + ENTREE)" + eol
        )
        self._pubHelper.update_content("menu", msg=msg_menu)
        # 2- Affichage écran d'attente :
        self._show_screen("wait")
        # 3- Fin publi :
        self.on_interface_created()

    def _show_screen(self, name, **kwargs):
        """
        Affichage d'écran
        
        Args:
            name : "wait", "menu", "partie"
        """
        if name in ["wait", "menu", "partie", "server"]:
            if self.type_app == AppTypes.APP_SERVER and name in ["menu", "partie"]:
                name = "server"
            txt = self._pubHelper.get_screen(name, **kwargs)
            screen = self._format_screen(txt)
            self._do_print(screen)

    def _update_screen(self):
        """
        Mise à jour de l'écran après modification d'un contenu
        """
        txt = self._pubHelper.update_screen()
        screen = self._format_screen(txt)
        self._do_print(screen)

    def _update_msg_screen(self, dictargs):
        """
        Réaffichage avec mise à jour du message
        """
        txt = self._pubHelper.update_screen_with_info(dictargs)
        if txt != None:
            screen = self._format_screen(txt)
            self._do_print(screen)

    def _format_screen(self, txt):
        """
        Sur formatage
        """
        eol = "\n"
        margin = eol * 10
        screen = margin + txt
        return screen

    def _do_print(self, screen):
        if screen != self._prev_txt:
            self._prev_txt = str(screen)
            print(screen, flush=True)


#-----> Gestion non bloquante de l'input texte :
class ThreadInput(threading.Thread):
    """
    Thread dédié à la gestion non bloquante de l'input texte.
    """

    def __init__(self, response_callback, question_event):
        """
        Constructeur
        """
        # générique
        threading.Thread.__init__(self)
        # setter :
        self._response_callback = response_callback
        # event :
        self._question_event = question_event
        # paramétrage
        self.setDaemon(True)

    def run(self):
        """
        Méthode run
        """
        while True:
            self._question_event.wait()
            if self._question_event.is_set():
                try:
                    rep = input("[Commande]:")
                    self._response_callback(rep)
                except:
                    # console fermée
                    pass
