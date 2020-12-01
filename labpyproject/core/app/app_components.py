#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
**Ebauche de framework applicatif multi-thread.**

Composants de base d'une application multi-thread :

* **APPComp** : routage des Queues entre les trois composants (ou satellites) suivants :
* **NETComp** : composant réseau (TCP actuellement)
* **GUIComp**, **GUICompNoThread** : composant d'interface
* **BUSINESSComp** : composant "métier" de l'application

Application et composants ont également la possibilité d'interagir directement via :

* les méthodes suivantes de APPComp :

    * `handle_SAT_info` et `ask_APP_info` dans le sens SAT -> APP
    * `get_SAT_info` et `set_APP_info` dans le sens APP -> SAT
    
* les méthodes suivantes de l'interface de AbstractSatelliteComp implémentées dans
  les superclasses des composants : get_SAT_info et handle_APP_info
    
Ces fonctionnalités ont été implémentées pour usage futur. Dans le cadre du projet
LabPyrinthe, la communication inter-composants suffit, APPComp n'ayant qu'un rôle de
routeur de tâches.

**GUICompNoThread** (et sa superclasse SatelliteCompNoThread) sont dédiés à des composants
d'interfaces nécessitant d'être lancés dans le thread principal (cas des GUIs telles que
Tkinter, Pygame...). Le suffix "NoThread" ne signifie donc pas qu'ils ne sont pas associés à
des threads, mais que l'application dérivant d'AppComp ne pourra pas les lancer dans un
thread secondaire. En pratique le script main d'une telle application sera du type : ::

    my_gui = subclasse_GUICompNoThread()
    my_app = subclasse_AppComp() # génère et lance des threads secondaires
    my_gui.method_start_thread() # lance la boucle d'exécution du thread principal (nom de méthode imaginaire)

Todo: 
    A décliner pour des applications multi process (en dérivant :doc:`labpyproject.core.queue.queue_tools` pour supporter **ProcessQueue**)

.. admonition:: Application concrète

    Dans le jeu **labpyrinthe** :
    
    * **AppManager** (voir :doc:`labpyproject.apps.labpyrinthe.app.application`) 
        hérite de **APPComp**.
    * **GameManager** (voir :doc:`labpyproject.apps.labpyrinthe.bus.game_manager`) 
        hérite de **BUSINESSComp**.
    * Les **interfaces graphiques** (voir :doc:`labpyproject.apps.labpyrinthe.gui`) 
        héritent de **AbstractGUIComp** puis de **GUIComp** ou **GUICompNoThread**.
    * Les **composants réseaux génériques** (voir :doc:`labpyproject.core.net.custom_TCP`) 
        héritent de **NETComp**.
    
"""
# imports :
import time
import threading
import abc
import labpyproject.core.queue.queue_tools as qt

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = [
    "ThreadableComp",
    "APPComp",
    "SatelliteExchangeObject",
    "AbstractSatelliteComp",
    "DelayedAction",
    "SatelliteComp",
    "SatelliteCompNoThread",
    "GUIExchangeObject",
    "AbstractGUIComp",
    "GUIComp",
    "GUICompNoThread",
    "NETExchangeObject",
    "NETComp",
    "BUSINESSComp",
]
# classes
#-----> Composant générique dédié à un usage en thread
class ThreadableComp:
    """
    Superclasse des composants dédiés à un usage en thread.
    """

    # statique :
    THREAD_FRAMERATE = (
        60  
    ) #: "framerate" du thread (60 appels max / seconde à la méthode run)
    THREAD_TEMPO = 1 / THREAD_FRAMERATE  #: temporisation associée au framerate
    # méthodes
    def __init__(self, postfixname=None):
        """
        Constructeur
        
        Args:
            postfixname (str): permet de particulariser le nom du thread (pour debug).
        """
        # thread principal du composant :
        self.own_thread = None
        self.thread_started = False
        # temporisation du thread
        self._run_call_tempo = ThreadableComp.THREAD_TEMPO
        # temps du dernier appel à la méthode run
        self._last_run_call_time = None
        # nombre de threads enfants (en dehors de self.own_thread) permanents attendus :
        self.childthreadscount = 0
        # nom par défaut :
        self.thread_name = "ThreadComp_" + str(id(self))
        if postfixname != None:
            self.thread_name = postfixname + "_" + str(id(self))
        # liste des threads internes :
        self.inner_threads = list()
        # liste des threads à démarrer avant d'effectuer un join
        self.threads_to_start = list()
        # création du thread associé :
        self.create_component_thread()

    def create_component_thread(self):
        """
        Crée le thread associé à ce composant
        """
        self.own_thread = threading.Thread(name=self.thread_name)
        self.own_thread.run = self._run_component_thread_internal
        self.own_thread.daemon = True
        self.inner_threads.append(self.own_thread)

    def set_childthreads_count(self, count):
        """
        Définit le nombre de threads enfants permanents que ce composant va créer.
        
        Args:
            count (int): nombre de threads enfants à créer
        """
        self.childthreadscount = count

    def create_child_thread(self, runhandler, suffixname=None, autostart=True):
        """
        Crée et enregistre un thread enfant :
        
        Args:
            runhandler (function): méthode run associée
            suffixname (str): suffix de nommage optionnel
            autostart (boolean): démarre t'on le thread automatiquement (oui par défaut)
        
        Returns: 
            Thread: le thread crée
        """
        new_child_thread = None
        if callable(runhandler):
            child_name = self.thread_name + "_child" + str(len(self.inner_threads))
            if suffixname != None:
                child_name = self.thread_name + "_" + suffixname
            new_child_thread = threading.Thread(name=child_name)
            new_child_thread.run = runhandler
            new_child_thread.setDaemon(True)
            self.inner_threads.append(new_child_thread)
            if autostart:
                new_child_thread.start()
            else:
                self.threads_to_start.append(new_child_thread)
        return new_child_thread

    def can_join_threads(self):
        """
        Indique si l'ensemble des threads internes sont prêts à être joints.
        
        Returns:
            boolean
        """
        if len(self.inner_threads) >= self.childthreadscount + 1:
            return True
        return False

    def start_component_thread(self):
        """
        Démarre le thread associé ainsi que tous les threads enfants.
        """
        if not self.can_join_threads():
            time.sleep(0.01)
            self.start_component_thread()
        if not self.thread_started:
            self.thread_started = True
            self._last_run_call_time = time.perf_counter()
            # démarrage des threads internes :
            for th in self.threads_to_start:
                th.start()
            self.threads_to_start = list()
            self.on_component_thread_started()
            self.own_thread.start()

    def on_component_thread_started(self):
        """
        Pseudo événement : indique que le thread principal du composant est démarré.
        """
        # à particulariser au besoin
        pass

    def get_threads_list(self):
        """
        Retourne la liste des threads internes crées ou None si ceux ci ne sont pas encore
        prêts à être joints.
        
        Returns:
            list or None
        """
        if self.can_join_threads():
            return self.inner_threads
        return None

    def _run_component_thread_internal(self):
        """
        Boucle d'exécution interne : appelle run_component_thread toutes les 
        ThreadableComp.THREAD_TEMPO secondes. 
        """
        while self.thread_started:
            # tempo :
            now = time.perf_counter()
            delta = now - self._last_run_call_time
            if delta >= self._run_call_tempo:
                # ré init tempo :
                self._last_run_call_time = now
                # appel à la méthode run publique
                self.run_component_thread()

    def run_component_thread(self):
        """
        Méthode run publique du thread associé.
        """
        # à particulariser dans les subclasses
        pass

    def stop_component_thread(self):
        """
        Stop la boucle while de la méthode run (à appeler via une tâche).
        """
        self.thread_started = False


#-----> Composant d'application principale
class APPComp(ThreadableComp, qt.QueueSwitcher):
    """
    Composant d'application servant de routeur pour la gestion des piles de tâches.
    """

    # variables statiques :
    # canaux d'échanges :
    NET_CHANNEL = "NET_CHANNEL"  #: canal d'échange réseau
    GUI_CHANNEL = "GUI_CHANNEL"  #: canal d'échange d'interface
    BUSINESS_CHANNEL = "BUSINESS_CHANNEL"  #: canal d'échange métier
    # codes Queue:
    # GUI -> APP
    GUITOAPP_KEYCODE = "GUITOAPP_KEYCODE"  #: marque un queue_code de gui à app
    # APP -> GUI
    APPTOGUI_KEYCODE = "APPTOGUI_KEYCODE"  #: marque un queue_code de app à gui
    # TCP -> APP
    NETTOAPP_KEYCODE = "NETTOAPP_KEYCODE"  #: marque un queue_code de net vers app
    # APP -> TCP
    APPTONET_KEYCODE = "APPTONET_KEYCODE"  #: marque un queue_code de app vers net
    # BUSINESS -> APP
    BUSINESSTOAPP_KEYCODE = (
        "BUSINESSTOAPP_KEYCODE"  
    ) #: marque un queue_code de métier vers app
    # APP -> BUSINESS
    APPTOBUSINESS_KEYCODE = (
        "APPTOBUSINESS_KEYCODE"  
    ) #: marque un queue_code de app vers métier

    # méthodes :
    def __init__(self, channellist=None):
        """
        Constructeur
        
        Args:
            channellist : liste de tuples (nom de canal, queue_code_in, queue_code_out)
        
        Rq: codes dans le sens COMP -> APP.
        """
        # init superclasse ThreadableComp :
        ThreadableComp.__init__(self, postfixname="APPComp")
        # composants enfants :
        self.childs_ThreadableComp = list()
        # canaux et codes par défaut :
        qsl = [
            (APPComp.NET_CHANNEL, APPComp.NETTOAPP_KEYCODE, APPComp.APPTONET_KEYCODE),
            (APPComp.GUI_CHANNEL, APPComp.GUITOAPP_KEYCODE, APPComp.APPTOGUI_KEYCODE),
            (
                APPComp.BUSINESS_CHANNEL,
                APPComp.BUSINESSTOAPP_KEYCODE,
                APPComp.APPTOBUSINESS_KEYCODE,
            ),
        ]
        # surcharge éventuelle :
        if channellist != None:
            qsl = channellist
        # init switch Queues :
        qt.QueueSwitcher.__init__(self, qsl)

    #-----> Initialisation des threads internes :
    def register_child_component(self, child):
        """
        Enregistre un composant interne.
        
        Args:
            child (ThreadableComp)
        """
        if isinstance(child, ThreadableComp):
            self.childs_ThreadableComp.append(child)

    def start_and_join_threads(self, join=True, count=0):
        """
        Démarre et joint au besoin tous les threads de la hiérarchie de composants.
        
        Args:
            join (boolean): doit on joindre les threads
            count (int): nombre de tentatives successives
        """
        # peut on opérer les join?
        ready = self.can_join_threads()
        for child in self.childs_ThreadableComp:
            if not child.can_join_threads():
                ready = False
                break
        if not ready:
            time.sleep(0.05)
            self.start_and_join_threads(count=count + 1)
        # starts :
        self.start_component_thread()
        for child in self.childs_ThreadableComp:
            child.start_component_thread()
        # process de join :
        joinlist = list()
        for child in self.childs_ThreadableComp:
            childlist = child.get_threads_list()
            for th in childlist:
                joinlist.append(th)
        for th in self.get_threads_list():
            if th not in joinlist:
                joinlist.append(th)
        # pseudo événement de fin de process
        self.on_threads_started()
        # join final
        if join:
            for th in joinlist:
                th.join()

    def on_threads_started(self):
        """
        Pseudo événement appelé à la fin du process de démarrage et join des threads.
        """
        # à particulariser
        pass

    #-----> Exécution du thread principal : routage
    def run_component_thread(self):
        """
        Méthode run du thread associé.
        """
        # dépilement des tâches
        self.handleAPPQueues()

    #-----> Routage des tâches
    def handleAPPQueues(self):
        """
        Route les piles de cmd en attente provenant des canaux d'échanges.
        
        A appeler dans la méthode run du thread associé à l'application.
        """
        channels = [APPComp.NET_CHANNEL, APPComp.GUI_CHANNEL, APPComp.BUSINESS_CHANNEL]
        for ch in channels:
            task = self.get_queuecmd_from_channel(ch)
            if task != None:
                if isinstance(task, SatelliteExchangeObject):
                    typeexchange = task.typeexchange
                    channelname = None
                    exobj = task
                    # Routage des tâches GUI / NET / BUS:
                    if isinstance(task, GUIExchangeObject):
                        if self.handleGUIExchange(task):
                            # On reroute la tâche :
                            # GUI_CHANNEL :
                            if typeexchange in [
                                GUIExchangeObject.ASK_USER_CHOICE,
                                GUIExchangeObject.SHOW_CONTENT,
                                GUIExchangeObject.SET_BUS_INFO,
                                GUIExchangeObject.GET_GUI_INFO,
                            ]:
                                # Business -> GUI
                                channelname = APPComp.GUI_CHANNEL
                            elif typeexchange in [
                                GUIExchangeObject.GUI_READY,
                                GUIExchangeObject.RETURN_USER_CHOICE,
                                GUIExchangeObject.SEND_USER_COMMAND,
                                GUIExchangeObject.GET_BUS_INFO,
                                GUIExchangeObject.SET_GUI_INFO,
                            ]:
                                # GUI -> Business
                                channelname = APPComp.BUSINESS_CHANNEL
                    elif isinstance(task, NETExchangeObject):
                        if self.handleNETExchange(task):
                            # On reroute la tâche :
                            # NET_CHANNEL :
                            if typeexchange in [
                                NETExchangeObject.SEND,
                                NETExchangeObject.SET_BUS_INFO,
                                NETExchangeObject.GET_NET_INFO,
                                NETExchangeObject.SET_ADDRESS,
                                NETExchangeObject.CONNECT,
                                NETExchangeObject.DISCONNECT,
                                NETExchangeObject.NET_SHUTDOWN,
                                NETExchangeObject.CHECK_CONN,
                            ]:
                                # BUSINESS -> NET
                                channelname = APPComp.NET_CHANNEL
                            elif typeexchange in [
                                NETExchangeObject.RECEIVE,
                                NETExchangeObject.GET_BUS_INFO,
                                NETExchangeObject.SET_NET_INFO,
                                NETExchangeObject.NET_ERROR,
                                NETExchangeObject.NET_STATUS,
                                NETExchangeObject.SEND_ERROR,
                            ]:
                                # NET -> BUSINESS
                                channelname = APPComp.BUSINESS_CHANNEL
                    else:
                        # Gestion des tâches génériques SAT <=> APP
                        # APP -> SAT : on route
                        if typeexchange in [
                            SatelliteExchangeObject.GET_SAT_INFO,
                            SatelliteExchangeObject.SET_APP_INFO,
                        ]:
                            channelname = task.channelname
                        # SAT -> APP : inutile de router
                        elif typeexchange == SatelliteExchangeObject.CLOSE_APP:
                            self.shutdown()
                        elif typeexchange == SatelliteExchangeObject.SET_SAT_INFO:
                            self.handle_SAT_info(exobj)
                        elif typeexchange == SatelliteExchangeObject.GET_APP_INFO:
                            self.ask_APP_info(exobj)
                    if channelname != None:
                        self.put_queuecmd_in_channel(exobj, channelname)
                elif callable(task):
                    # Fonction à appeler
                    task()

    #-----> Prise en charge des tâches génériques SAT <=> APP
    def handle_SAT_info(self, exobj):
        """
        Un satellite transmet une infos à l'application.
        
        Args:
            exobj (SatelliteExchangeObject) avec 
                exobj.typeexchange=SatelliteExchangeObject.SET_SAT_INFO
        """
        # à subclasser au besoin (usage futur)
        pass

    def ask_APP_info(self, exobj):
        """
        Un satellite demande une infos à l'application.
        
        Args:
            exobj (SatelliteExchangeObject) avec 
                exobj.typeexchange=SatelliteExchangeObject.GET_APP_INFO
        """
        # à subclasser au besoin (usage futur)
        pass

    #-----> Adresse une tâche directement à un satellite
    def get_SAT_info(self, channelname, dictargs):
        """
        L'application envoie au satellite associé à channelname une demande d'info 
        décrite dans dictargs. 
        
        Args:
            channelname (str): nom de canal dans [APPComp.NET_CHANNEL, APPComp.GUI_CHANNEL, 
                APPComp.BUSINESS_CHANNEL]
            dictargs (dict)
            
        Returns:
            SatelliteExchangeObject: objet d'échange générique avec exobj.typeexchange=SatelliteExchangeObject.GET_SAT_INFO
        """
        if channelname in [
            APPComp.NET_CHANNEL,
            APPComp.GUI_CHANNEL,
            APPComp.BUSINESS_CHANNEL,
        ]:
            exobj = SatelliteExchangeObject(
                SatelliteExchangeObject.GET_SAT_INFO,
                channelname=channelname,
                dictargs=dictargs,
            )
            self.put_queuecmd_in_channel(exobj, channelname)

    def set_APP_info(self, channelname, dictargs):
        """
        L'application transmet au satellite associé à channelname une information 
        décrite dans dictargs.
        
        Args:
            channelname (str): nom de canal dans [APPComp.NET_CHANNEL, APPComp.GUI_CHANNEL, 
                APPComp.BUSINESS_CHANNEL]
            dictargs (dict)
            
        Returns:
            SatelliteExchangeObject: objet d'échange générique avec exobj.typeexchange=SatelliteExchangeObject.SET_APP_INFO
        """
        if channelname in [
            APPComp.NET_CHANNEL,
            APPComp.GUI_CHANNEL,
            APPComp.BUSINESS_CHANNEL,
        ]:
            exobj = SatelliteExchangeObject(
                SatelliteExchangeObject.SET_APP_INFO,
                channelname=channelname,
                dictargs=dictargs,
            )
            self.put_queuecmd_in_channel(exobj, channelname)

    #-----> Filtrage des tâches GUI
    def handleGUIExchange(self, exobj):
        """
        Appelée dans la méthode APPComp.handleAPPQueues avant routage de l'objet
        d'échange.
        
        Args:
            exobj (GUIExchangeObject)
        
        Returns:
            boolean: indiquant si la tâche doit être routée
        """
        if exobj.typeexchange == GUIExchangeObject.GUI_READY:
            self.on_GUI_Ready(exobj)
        return True

    def on_GUI_Ready(self, exobj):
        """
        Méthode appelée lorsque l'application détecte un GUIExchangeObject de type
        GUI_READY signalant que l'interface est prête à réagir.
        
        Args:
            exobj(GUIExchangeObject)
        """
        pass

    #-----> Filtrage des tâches NET
    def handleNETExchange(self, exobj):
        """
        Appelée dans la méthode APPComp.handleAPPQueues avant routage de l'objet
        d'échange.
        
        Args:
            exobj (NETExchangeObject)
            
        Returns:
            boolean: indiquant si la tâche doit être routée
        """
        return True

    #-----> Adresse une tâche filtrée au composant BUSINESS
    def sendBusinessTask(self, task):
        """
        En cas de filtrage du routage, permet d'envoyer une tâche spécifique au
        composant métier.
        
        Args:
            task (object)
        """
        self.put_queuecmd_in_channel(task, APPComp.BUSINESS_CHANNEL)

    #-----> Clôture de l'application et de tous ses composants
    def shutdown(self):
        """
        Clôture de l'application après propagation d'un ordre de clôture
        à l'ensemble des composants.
        """
        # clôture des composants :
        channels = [APPComp.NET_CHANNEL, APPComp.GUI_CHANNEL, APPComp.BUSINESS_CHANNEL]
        for ch in channels:
            exobj = SatelliteExchangeObject(
                SatelliteExchangeObject.SHUTDOWN, channelname=ch, dictargs=None
            )
            self.put_queuecmd_in_channel(exobj, ch)
        # arrêt de la boucle run :
        self.stop_component_thread()


#-----> Superclasses des composants satellites (NET, GUI, BUSINESS...)
#-----> Objet d'échange générique
class SatelliteExchangeObject:
    """
    Objet d'échange entre composant satellite (NET, GUI, BUSINESS...) et application
    principale.
    """

    # variables statiques :
    # types d'échanges génériques :
    # satellite -> Application
    SET_SAT_INFO = "SET_SAT_INFO"  #: le satellite transmet une info à l'application
    GET_APP_INFO = "GET_APP_INFO"  #: le satellite demande une info à l'application
    CLOSE_APP = "CLOSE_APP"  #: le satellite transmet l'ordre de shutdown global
    # Application -> Satellite
    GET_SAT_INFO = "GET_SAT_INFO"  #: l'application demande une info au satellite
    SET_APP_INFO = "SET_APP_INFO"  #: l'application transmet une info au satellite
    SHUTDOWN = "SHUTDOWN"  #: ordre de clôture du satellite par l'application
    # méthodes
    def __init__(self, typeexchange, channelname=None, dictargs=None):
        """
        Constructeur :
        
        Args:
            typeexchange (str): identifiant de type d'échange
            channelname (str): nom du canal associé
            dictargs (dict): paramètres        
        """
        self.typeexchange = typeexchange
        self.channelname = channelname
        self.dictargs = dict()
        if dictargs != None:
            self.dictargs = dictargs
        # debug
        self.creation_time = time.perf_counter()

    def ellapsed(self):
        """
        Retourne le temps écoulé depuis sa création
        """
        now = time.perf_counter()
        return now - self.creation_time

    def __repr__(self):
        chaine = (
            "SatelliteExchangeObject channelname="
            + str(self.channelname)
            + " typeexchange="
            + str(self.typeexchange)
            + "\n"
        )
        for k, v in self.dictargs.items():
            chaine = chaine + "*" + k + " = " + str(v) + "\n"
        return chaine


#-----> Pseudo interface :
class AbstractSatelliteComp(metaclass=abc.ABCMeta):
    """
    "Pseudo interface" des composants satellites.
    """

    @abc.abstractmethod
    def handleExchangeObjectType(self, exchangeobjecttype):
        """
        Indique si le composant prend en charge le type d'objet d'échange.
        
        Args:
            exchangeobjecttype (SatelliteExchangeObject)
        """
        raise NotImplementedError(
            "AbstractSatelliteComp need implementation for handleExchangeObjectType"
        )

    @abc.abstractmethod
    def handleTask(self):
        """
        Méthode générique de dépilement de tâche. 
        A appeler dans la méthode run du thread associé au composant.
        """
        raise NotImplementedError(
            "AbstractSatelliteComp need implementation for handleTask"
        )

    @abc.abstractmethod
    def handleExchangeObject(self, exobj):
        """
        Traite un objet d'échange de type compris dans self.exchangeobjecttype : à particulariser.
        
        Args:
            exobj (SatelliteExchangeObject)
        """
        raise NotImplementedError(
            "AbstractSatelliteComp need implementation for handleExchangeObject"
        )

    @abc.abstractmethod
    def get_SAT_info(self, exobj):
        """
        L'application adresse une demande d'information au satellite.
        
        Args:
            exobj (SatelliteExchangeObject): avec 
                exobj.typeexchange=SatelliteExchangeObject.GET_SAT_INFO
        """
        raise NotImplementedError(
            "AbstractSatelliteComp need implementation for get_SAT_info"
        )

    @abc.abstractmethod
    def handle_APP_info(self, exobj):
        """
        L'application envoie une info au satellite.
        
        Args:
            exobj (SatelliteExchangeObject): avec 
                exobj.typeexchange=SatelliteExchangeObject.SET_APP_INFO
        """
        raise NotImplementedError(
            "AbstractSatelliteComp need implementation for handle_APP_info"
        )

    @abc.abstractmethod
    def sendTask(self, obj):
        """
        Empile une réponse à destination de l'application métier.
        
        Args:
            obj (object)
        """
        raise NotImplementedError(
            "AbstractSatelliteComp need implementation for sendTask"
        )

    @abc.abstractmethod
    def shutdown(self):
        """
        Clôture du composant propagé par APPComp.
        """
        raise NotImplementedError(
            "AbstractSatelliteComp need implementation for shutdown"
        )

    @abc.abstractmethod
    def delay_action(self, interval, function, args=None, kwargs=None):
        """
        Diffère l'exécution d'une action sans bloquer (via threading.Timer).
        """
        raise NotImplementedError(
            "AbstractSatelliteComp need implementation for delay_action"
        )

    @abc.abstractmethod
    def clean_delayed_actions(self, clean_all=False):
        """
        Suppression des actions différées effectuées ou annulées.
        
        Args:
            clean_all (boolean): si True annule et supprime toutes les actions.
        """
        raise NotImplementedError(
            "AbstractSatelliteComp need implementation for clean_delayed_actions"
        )


#-----> Action différée
class DelayedAction:
    """
    Objet de gestion d'une action différée utilisant threading.Timer par composition.
    """

    def __init__(
        self,
        interval,
        function,
        args=None,
        kwargs=None,
        autostart=True,
        external_callback=None,
    ):
        """
        Constructeur.
        
        Args:
            interval (sec): identique à threading.Timer
            function (function): identique à threading.Timer
            args (list): identique à threading.Timer
            kwargs (dict): identique à threading.Timer
            autostart (boolean)
            external_callback (function): appelée lorsque l'action est effectuée ou annulée
         """
        # paramètres du Timer :
        self.interval = interval
        self.function = function
        self.args = args if args is not None else []
        self.kwargs = kwargs if kwargs is not None else {}
        # callback externe (pour nettoyage) :
        self.external_callback = external_callback
        # Timer :
        self._timer = threading.Timer(interval, function, args=args, kwargs=kwargs)
        # Etat de l'objet :
        self.action_done = False
        self.action_cancelled = False
        # autostart
        if autostart:
            self._timer.start()

    def start(self):
        """
        Identique à Timer.start
        """
        self._timer.start()

    def cancel(self):
        """
        Identique à Timer.cancel
        """
        self._timer.cancel()
        self.action_cancelled = True
        # callback externe
        if self.external_callback != None:
            self.external_callback()

    def timer_callback(self):
        """
        Callback réel du Timer
        """
        # Action :
        self.function(*self.args, **self.kwargs)
        # Etat :
        self.action_done = True
        # callback externe
        if self.external_callback != None:
            self.external_callback()

    def is_removable(self):
        """
        Indique si l'objet peut être supprimé.
        """
        if self.action_done or self.action_cancelled:
            return True
        return False


#-----> Composant générique
class SatelliteComp(ThreadableComp, AbstractSatelliteComp, qt.QueueSimpleClient):
    """
    Superclasse des composants d'application satellites.
    """

    def __init__(
        self,
        channelname=None,
        queue_code_in=None,
        queue_code_out=None,
        exchangeobjecttypes=[SatelliteExchangeObject],
    ):
        """
        Constructeur
        
        Args:
            channelname (str): nom de canal dans [APPComp.NET_CHANNEL, 
                APPComp.GUI_CHANNEL, APPComp.BUSINESS_CHANNEL]
            queue_code_in (str), queue_code_out (str): codes associés au canal 
                dans le sens APP->Satellite
            exchangeobjecttypes (list): liste de classes d'objets d'échange 
                associés au canal        
        """
        # liste des actions différées :
        self._delayed_actions = list()
        # init superclasse ThreadableComp :
        ThreadableComp.__init__(self, postfixname=channelname)
        # init superclasse QueueSimpleClient :
        qt.QueueSimpleClient.__init__(self, queue_code_in, queue_code_out)
        self.channelname = channelname
        self.exchangeobjecttypes = exchangeobjecttypes

    def handleExchangeObjectType(self, exchangeobjecttype):
        """
        Indique si le composant prend en charge le type d'objet d'échange.
        
        Args:
            exchangeobjecttype (SatelliteExchangeObject)
        """
        if exchangeobjecttype in self.exchangeobjecttypes:
            return True
        return False

    def run_component_thread(self):
        """
        Méthode run du thread associé.
        """
        # dépilement des tâches
        self.handleTask()

    def handleTask(self):
        """
        Méthode générique de dépilement de tâche (à appeler dans la méthode run 
        du thread associé au composant).
        """
        # Rq : inutile de tester si self.are_queues_active() == True
        task = self.get_cmd_from_queue()
        if task != None:
            if self.handleExchangeObjectType(type(task)):
                # Objet d'échange dédié
                self.handleExchangeObject(task)
            elif isinstance(task, SatelliteExchangeObject):
                # Objet d'échange générique (APP -> SAT)
                typeexchange = task.typeexchange
                if typeexchange == SatelliteExchangeObject.GET_SAT_INFO:
                    self.get_SAT_info(task)
                elif typeexchange == SatelliteExchangeObject.SET_APP_INFO:
                    self.handle_APP_info(task)
                elif typeexchange == SatelliteExchangeObject.SHUTDOWN:
                    self.shutdown()
            elif callable(task):
                # Fonction à appeler
                task()

    def handleExchangeObject(self, exobj):
        """
        Traite un objet d'échange de type compris dans self.exchangeobjecttype : à particulariser.
        
        Args:
            exobj (SatelliteExchangeObject)
        """
        pass

    def get_SAT_info(self, exobj):
        """
        L'application adresse une demande d'information au satellite.
        
        Args:
            exobj (SatelliteExchangeObject): avec 
                exobj.typeexchange=SatelliteExchangeObject.GET_SAT_INFO
        """
        # à subclasser
        pass

    def handle_APP_info(self, exobj):
        """
        L'application envoie une info au satellite.
        
        Args:
            exobj (SatelliteExchangeObject): avec 
                exobj.typeexchange=SatelliteExchangeObject.SET_APP_INFO
        """
        # à subclasser
        pass

    def sendTask(self, obj):
        """
        Empile une réponse à destination de l'application métier.
        
        Args:
            obj (object)
        """
        if self.are_queues_active():
            task = None
            if isinstance(obj, SatelliteExchangeObject):
                # objet d'échange
                task = obj
            elif callable(task):
                # méthode
                task = obj
            if task != None:
                self.put_cmd_in_queue(task)

    def close_APP(self):
        """
        Envoie un ordre de clôture globale de l'application.
        """
        exobj = SatelliteExchangeObject(SatelliteExchangeObject.CLOSE_APP)
        self.sendTask(exobj)

    def shutdown(self):
        """
        Clôture du composant propagé par APPComp.
        """
        # arrêt de la boucle run :
        self.stop_component_thread()
        # nettoyage des actions différées :
        self.clean_delayed_actions(clean_all=True)

    def delay_action(self, interval, function, args=None, kwargs=None):
        """
        Diffère l'exécution d'une action sans bloquer.
        Crée et enregistre un objet DelayedAction.
        """
        # création de l'objet :
        daObj = DelayedAction(
            interval,
            function,
            args=args,
            kwargs=kwargs,
            external_callback=self.clean_delayed_actions,
        )
        # enregistrement :
        self._delayed_actions.append(daObj)

    def clean_delayed_actions(self, clean_all=False):
        """
        Suppression des actions différées effectuées ou annulées.
        
        Args:
            clean_all (boolean): si True annule et supprime toutes les actions.
        """
        if clean_all:
            # annulation de toutes les actions
            for daobj in self._delayed_actions:
                daobj.cancel()
            self._delayed_actions = []
        else:
            # actions à conserver :
            keeplist = [
                daobj for daobj in self._delayed_actions if not daobj.is_removable()
            ]
            self._delayed_actions = keeplist


#-----> Version sans thread (usage : Tk, Pygame)
class SatelliteCompNoThread(AbstractSatelliteComp, qt.QueueSimpleClient):
    """
    Superclasse des composants d'application satellites qui ne peuvent être lancés
    en dehors du thread principal (cas des GUI : Tkinter, Pygame...).
    
    Attention: appeler manuellement self.handleTask().
    """

    def __init__(
        self,
        channelname=None,
        queue_code_in=None,
        queue_code_out=None,
        exchangeobjecttypes=[SatelliteExchangeObject],
    ):
        """
        Constructeur
        
        Args:
            channelname (str): nom de canal dans [APPComp.NET_CHANNEL, 
                APPComp.GUI_CHANNEL, APPComp.BUSINESS_CHANNEL]
            queue_code_in (str), queue_code_out (str): codes associés au canal 
                dans le sens APP->Satellite
            exchangeobjecttypes (list): liste de classes d'objets d'échange 
                associés au canal 
        """
        # liste des actions différées :
        self._delayed_actions = list()
        # init superclasse QueueSimpleClient :
        qt.QueueSimpleClient.__init__(self, queue_code_in, queue_code_out)
        self.channelname = channelname
        self.exchangeobjecttypes = exchangeobjecttypes

    def handleExchangeObjectType(self, exchangeobjecttype):
        """
        Indique si le composant prend en charge le type d'objet d'échange.
        
        Args:
            exchangeobjecttype (SatelliteExchangeObject)
        """
        if exchangeobjecttype in self.exchangeobjecttypes:
            return True
        return False

    def handleTask(self):
        """
        Méthode générique de dépilement de tâche.
        """
        # Rq : inutile de tester si self.are_queues_active() == True
        task = self.get_cmd_from_queue()
        if task != None:
            if self.handleExchangeObjectType(type(task)):
                # Objet d'échange dédié
                self.handleExchangeObject(task)
            elif isinstance(task, SatelliteExchangeObject):
                # Objet d'échange générique (APP -> SAT)
                typeexchange = task.typeexchange
                if typeexchange == SatelliteExchangeObject.GET_SAT_INFO:
                    self.get_SAT_info(task)
                elif typeexchange == SatelliteExchangeObject.SET_APP_INFO:
                    self.handle_APP_info(task)
                elif typeexchange == SatelliteExchangeObject.SHUTDOWN:
                    self.shutdown()
            elif callable(task):
                # Fonction à appeler
                task()

    def handleExchangeObject(self, exobj):
        """
        Traite un objet d'échange de type compris dans self.exchangeobjecttype : à particulariser.
        
        Args:
            exobj (SatelliteExchangeObject)
        """
        pass

    def get_SAT_info(self, exobj):
        """
        L'application adresse une demande d'information au satellite.
        
        Args:
            exobj (SatelliteExchangeObject): avec 
                exobj.typeexchange=SatelliteExchangeObject.GET_SAT_INFO
        """
        # à subclasser
        pass

    def handle_APP_info(self, exobj):
        """
        L'application envoie une info au satellite.
        
        Args:
            exobj (SatelliteExchangeObject): avec 
                exobj.typeexchange=SatelliteExchangeObject.SET_APP_INFO
        """
        # à subclasser
        pass

    def sendTask(self, obj):
        """
        Empile une réponse à destination de l'application métier.
        
        Args:
            obj (object)
        """
        if self.are_queues_active():
            task = None
            if isinstance(obj, SatelliteExchangeObject):
                # objet d'échange
                task = obj
            elif callable(task):
                # méthode
                task = obj
            if task != None:
                self.put_cmd_in_queue(task)

    def close_APP(self):
        """
        Envoie un ordre de clôture globale de l'application.
        """
        exobj = SatelliteExchangeObject(SatelliteExchangeObject.CLOSE_APP)
        self.sendTask(exobj)

    def shutdown(self):
        """
        Clôture du composant propagé par APPComp
        """
        # nettoyage des actions différées :
        self.clean_delayed_actions(clean_all=True)

    def delay_action(self, interval, function, args=None, kwargs=None):
        """
        Diffère l'exécution d'une action sans bloquer.
        Crée et enregistre un objet DelayedAction.
        """
        # création de l'objet :
        daObj = DelayedAction(
            interval,
            function,
            args=args,
            kwargs=kwargs,
            external_callback=self.clean_delayed_actions,
        )
        # enregistrement :
        self._delayed_actions.append(daObj)

    def clean_delayed_actions(self, clean_all=False):
        """
        Suppression des actions différées effectuées ou annulées.
        
        Args:
            clean_all (boolean): si True annule et supprime toutes les actions.
        """
        if clean_all:
            # annulation de toutes les actions
            for daobj in self._delayed_actions:
                daobj.cancel()
            self._delayed_actions = []
        else:
            # actions à conserver :
            keeplist = [
                daobj for daobj in self._delayed_actions if not daobj.is_removable()
            ]
            self._delayed_actions = keeplist


#-----> Interface
#-----> Objet d'échange GUI
class GUIExchangeObject(SatelliteExchangeObject):
    """
    Objet d'échange entre composant d'interface et application.
    """

    # variables statiques : types d'échanges dédiés
    _CURRENT_INDEX = 0
    # (Business ->) APP -> GUI
    ASK_USER_CHOICE = "ASK_USER_CHOICE"  #: business demande un choix utilisateur
    SHOW_CONTENT = "SHOW_CONTENT"  #: business transmet un ordre d'affichage de contenu
    SET_BUS_INFO = "SET_BUS_INFO"  #: business transmet une info à l'interface
    GET_GUI_INFO = "GET_GUI_INFO"  #: business fait une demande d'info à l'interface
    # GUI -> APP (-> Business)
    GUI_READY = "GUI_READY"  #: la gui signale qu'elle est initialisée
    RETURN_USER_CHOICE = "RETURN_USER_CHOICE"  #: la gui retourne un choix utilisateur
    SEND_USER_COMMAND = "SEND_USER_COMMAND"  #: la gui retourne une commande utilisateur
    GET_BUS_INFO = "GET_BUS_INFO"  #: l'interface fait une demande d'info au business
    SET_GUI_INFO = "SET_GUI_INFO"  #: l'interface transmet une info au business
    # méthodes statiques
    def _index_guiObject(cls, guiExObj):
        """
        Numérotation automatique des objets à fins de debug.
        """
        cls._CURRENT_INDEX += 1
        return cls._CURRENT_INDEX

    _index_guiObject = classmethod(_index_guiObject)
    # méthodes
    def __init__(self, typeexchange, dictargs=None):
        """
        Constructeur :
        
        Args:
            typeexchange (str): GUIExchangeObject.ASK_USER_CHOICE, ...
            dictargs (dict): paramètres
        
        """
        SatelliteExchangeObject.__init__(
            self, typeexchange, channelname=APPComp.GUI_CHANNEL, dictargs=dictargs
        )
        self.index = GUIExchangeObject._index_guiObject(self)


#-----> Pseudo interface :
class AbstractGUIComp():
    """
    "Pseudo interface" des composants d'interface.
    """

    @abc.abstractmethod
    def handle_choice(self, exobj):
        """
        Retourne l'input utilisateur : à particulariser
        
        Args:
            exobj (GUIExchangeObject)
        """
        raise NotImplementedError(
            "AbstractGUIComp need implementation for handle_choice"
        )

    @abc.abstractmethod
    def show_content(self, dictargs):
        """
        Méthode principale d'affichage de contenu : à particulariser
        
        Args:
            dictargs (dict): attribut dictargs d'un objet GUIExchangeObject
        """
        raise NotImplementedError(
            "AbstractGUIComp need implementation for show_content"
        )

    @abc.abstractmethod
    def refresh_view(self):
        """
        Réalise un update de l'affichage.
        """
        raise NotImplementedError(
            "AbstractGUIComp need implementation for refresh_view"
        )

    @abc.abstractmethod
    def handle_BUS_info(self, exobj):
        """
        Réception d'informations en provenance du composant métier : à particulariser.
        
        Args:
            exobj (GUIExchangeObject)
        """
        raise NotImplementedError(
            "AbstractGUIComp need implementation for handle_BUS_info"
        )

    @abc.abstractmethod
    def ask_GUI_info(self, exobj):
        """
        Demande d'information relative à la GUI émanant du composant métier.
        
        Args:
            exobj (GUIExchangeObject)
        """
        raise NotImplementedError(
            "AbstractGUIComp need implementation for ask_GUI_info"
        )

    @abc.abstractmethod
    def signal_GUI_ready(self):
        """
        Signale à l'application et au composant business que l'interface est prête.
        """
        raise NotImplementedError(
            "AbstractGUIComp need implementation for signal_GUI_ready"
        )


#-----> Composant GUI standard
class GUIComp(SatelliteComp, AbstractGUIComp):
    """
    Composant d'interface.
    """

    def __init__(
        self,
        channelname=APPComp.GUI_CHANNEL,
        queue_code_in=APPComp.APPTOGUI_KEYCODE,
        queue_code_out=APPComp.GUITOAPP_KEYCODE,
        exchangeobjecttypes=[GUIExchangeObject],
    ):
        """
        Constructeur
        
        Args:
            channelname (str): canal de communication
            queue_code_in (str), queue_code_out (str): codes associés au canal 
                GUI_CHANNEL (sens APP->GUI)
            exchangeobjecttype (list): objets d'échange attendus   
        """
        # générique :
        SatelliteComp.__init__(
            self, channelname, queue_code_in, queue_code_out, exchangeobjecttypes
        )
        # activation du traitement des tâches :
        # appeler manuellement self.on_component_ready() lorsque l'interface est publiée.

    def handleExchangeObject(self, exobj):
        """
        Traite un objet d'échange provenant de l'application métier
        
        Args:
            exobj ( GUIExchangeObject)
        """
        handler = arg = None
        typeexchange = exobj.typeexchange
        if typeexchange == GUIExchangeObject.ASK_USER_CHOICE:
            handler = self.handle_choice
            arg = exobj
        elif typeexchange == GUIExchangeObject.SHOW_CONTENT:
            handler = self.show_content
            arg = exobj
        elif typeexchange == GUIExchangeObject.SET_BUS_INFO:
            handler = self.handle_BUS_info
            arg = exobj
        elif typeexchange == GUIExchangeObject.GET_GUI_INFO:
            handler = self.ask_GUI_info
            arg = exobj
        # on applique :
        if handler != None:
            handler(arg)

    def handle_choice(self, exobj):
        """
        Retourne l'input utilisateur : à particulariser
        
        Args:
            exobj ( GUIExchangeObject)
        """
        pass

    def show_content(self, dictargs):
        """
        Méthode principale d'affichage de contenu : à particulariser
        
        Args:
            dictargs (dict): attribut dictargs d'un objet GUIExchangeObject
        """
        pass

    def refresh_view(self):
        """
        Réalise un update de l'affichage
        """
        pass

    def handle_BUS_info(self, exobj):
        """
        Réception d'informations en provenance du composant métier : à particulariser.
        
        Args:
            exobj (GUIExchangeObject)
        """
        pass

    def ask_GUI_info(self, exobj):
        """
        Demande d'information relative à la GUI émanant du composant métier.
        
        Args:
            exobj (GUIExchangeObject)
        """
        pass

    def signal_GUI_ready(self):
        """
        Signale à l'application et au composant business que l'interface est prête.
        """
        exobj = GUIExchangeObject(GUIExchangeObject.GUI_READY)
        self.sendTask(exobj)


#-----> Composant GUI sans thread (usage : Tk, Pygame)
class GUICompNoThread(SatelliteCompNoThread, AbstractGUIComp):
    """
    Composant d'interface ne pouvant être lancés en dehors du thread
    principal (GUI : Tkinter, Pygame...). 
    Attention: appeler manuellement self.handleTask().
    """

    def __init__(
        self,
        channelname=APPComp.GUI_CHANNEL,
        queue_code_in=APPComp.APPTOGUI_KEYCODE,
        queue_code_out=APPComp.GUITOAPP_KEYCODE,
        exchangeobjecttypes=[GUIExchangeObject],
    ):
        """
        Constructeur
        
        Args:
            channelname (str): canal de communication
            queue_code_in (str), queue_code_out (str): codes associés au canal 
                GUI_CHANNEL (sens APP->GUI)
            exchangeobjecttype (list): objets d'échange attendus 
        """
        # générique :
        SatelliteCompNoThread.__init__(
            self, channelname, queue_code_in, queue_code_out, exchangeobjecttypes
        )
        # activation du traitement des tâches :
        # appeler manuellement self.on_component_ready() lorsque l'interface est publiée.

    def handleExchangeObject(self, exobj):
        """
        Traite un objet d'échange provenant de l'application métier
        
        Args:
            exobj ( GUIExchangeObject)
        """
        handler = arg = None
        typeexchange = exobj.typeexchange
        if typeexchange == GUIExchangeObject.ASK_USER_CHOICE:
            handler = self.handle_choice
            arg = exobj
        elif typeexchange == GUIExchangeObject.SHOW_CONTENT:
            handler = self.show_content
            arg = exobj
        elif typeexchange == GUIExchangeObject.SET_BUS_INFO:
            handler = self.handle_BUS_info
            arg = exobj
        elif typeexchange == GUIExchangeObject.GET_GUI_INFO:
            handler = self.ask_GUI_info
            arg = exobj
        # on applique :
        if handler != None:
            handler(arg)

    def handle_choice(self, exobj):
        """
        Retourne l'input utilisateur : à particulariser
        
        Args:
            exobj ( GUIExchangeObject)
        """
        pass

    def show_content(self, dictargs):
        """
        Méthode principale d'affichage de contenu : à particulariser
        
        Args:
            dictargs (dict): attribut dictargs d'un objet GUIExchangeObject
        """
        pass

    def refresh_view(self):
        """
        Réalise un update de l'affichage
        """
        pass

    def handle_BUS_info(self, exobj):
        """
        Réception d'informations en provenance du composant métier : à particulariser.
        
        Args:
            exobj (GUIExchangeObject)
        """
        pass

    def ask_GUI_info(self, exobj):
        """
        Demande d'information relative à la GUI émanant du composant métier.
        
        Args:
            exobj (GUIExchangeObject)
        """
        pass

    def signal_GUI_ready(self):
        """
        Signale à l'application et au composant business que l'interface est prête.
        """
        exobj = GUIExchangeObject(GUIExchangeObject.GUI_READY)
        self.sendTask(exobj)


#-----> Réseau (TCP)
#-----> Objet d'échange NET
class NETExchangeObject(SatelliteExchangeObject):
    """
    Objet d'échange entre composant réseau et application
    """

    # variables statiques : types d'échanges dédiés
    # (Business ->) APP -> NET
    SET_ADDRESS = "SET_ADDRESS"  #: business défini l'adresse réseau
    CONNECT = "CONNECT"  #: buseness transmet un ordre de connection
    DISCONNECT = "DISCONNECT"  #: business transmet un ordre de déconnection
    NET_SHUTDOWN = (
        "NET_SHUTDOWN"  
    ) #: business demande la clôture du composant réseau seul
    CHECK_CONN = (
        "CHECK_CONN"  
    ) #: business transmet une demande de vérification des connections
    # (non propagé globalement par APPComp)
    SEND = "SEND"  #: business fait une demande d'envoi de message
    SET_BUS_INFO = "SET_BUS_INFO"  #: business transmet une info au réseau
    GET_NET_INFO = "GET_NET_INFO"  #: business fait une demande d'info au réseau
    # NET -> APP (-> Business)
    RECEIVE = "RECEIVE"  #: le réseau transmet au business un message
    GET_BUS_INFO = "GET_BUS_INFO"  #: le réseau fait une demande d'info au business
    SET_NET_INFO = (
        "SET_NET_INFO"  
    ) #: le réseau transmet au business des infos sur le réseau
    NET_ERROR = "NET_ERROR"  #: le réseau rencontre une erreur importante
    NET_STATUS = (
        "NET_STATUS"  
    ) #: le réseau informe du changement de son état de connection
    SEND_ERROR = (
        "SEND_ERROR"  
    ) #: le composant réseau n'a pas pu effectuer l'envoi correctement
    # méthodes
    def __init__(self, typeexchange, dictargs=None):
        """
        Constructeur :
        
        Args:
            typeexchange (str): NETExchangeObject.SEND...
            dictargs (dict): dict de paramètres
        
        """
        SatelliteExchangeObject.__init__(
            self, typeexchange, channelname=APPComp.NET_CHANNEL, dictargs=dictargs
        )


#-----> Composant NET
class NETComp(SatelliteComp):
    """
    Composant réseau.
    """

    def __init__(
        self,
        channelname=APPComp.NET_CHANNEL,
        queue_code_in=APPComp.APPTONET_KEYCODE,
        queue_code_out=APPComp.NETTOAPP_KEYCODE,
        exchangeobjecttypes=[NETExchangeObject],
    ):
        """
        Constructeur
        
        Args:
            channelname (str): canal de communication
            queue_code_in (str), queue_code_out (str): codes associés au canal 
                NET_CHANNEL (sens APP->NET)
            exchangeobjecttype (list): objets d'échange attendus
        
        """
        # générique :
        SatelliteComp.__init__(
            self, channelname, queue_code_in, queue_code_out, exchangeobjecttypes
        )

    def handleExchangeObject(self, exobj):
        """
        Traite un objet d'échange provenant de l'application métier
        
        Args:
            exobj (NETExchangeObject)
        """
        handler = arg = None
        typeexchange = exobj.typeexchange
        if typeexchange == NETExchangeObject.SEND:
            handler = self.sendFromExchangeObject
            arg = exobj
        elif typeexchange == NETExchangeObject.SET_BUS_INFO:
            handler = self.handle_BUS_info
            arg = exobj
        elif typeexchange == NETExchangeObject.GET_NET_INFO:
            handler = self.ask_NET_info
            arg = exobj
        elif typeexchange == NETExchangeObject.SET_ADDRESS:
            handler = self.set_address
            arg = exobj
        elif typeexchange == NETExchangeObject.CONNECT:
            handler = self.connect
            arg = exobj
        elif typeexchange == NETExchangeObject.DISCONNECT:
            handler = self.disconnect
            arg = exobj
        elif typeexchange == NETExchangeObject.NET_SHUTDOWN:
            handler = self.net_shutdown
            arg = exobj
        elif typeexchange == NETExchangeObject.CHECK_CONN:
            handler = self.check_connections
            arg = exobj
        # on applique :
        if handler != None:
            handler(arg)

    def sendFromExchangeObject(self, exobj):
        """
        Méthode d'envoi à partir des données comprises dans l'objet NETExchangeObject.
        
        Args:
            exobj (NETExchangeObject)
        """
        # à particulariser
        pass

    def handle_BUS_info(self, exobj):
        """
        Réception d'informations en provenance du composant métier : à particulariser.
        
        Args:
            exobj (NETExchangeObject)
        """
        pass

    def ask_NET_info(self, exobj):
        """
        Demande d'information relative au réseau émanant du composant métier : à particulariser.
        
        Args:
            exobj (NETExchangeObject)
        """
        pass

    def set_address(self, exobj):
        """
        Affecte l'adresse d'écoute du serveur / adresse d'écriture du client.
        exobj : objet NETExchangeObject avec exobj.dictargs={"host":, "port":}
        """
        pass

    def connect(self, exobj):
        """
        Ordre de connection à l'adresse pré définie ou à l'adresse éventuellement
        indiquée dans : exobj.dictargs={"host":, "port":}
        
        Args:
            exobj (NETExchangeObject)
        """
        pass

    def disconnect(self, exobj):
        """
        Ordre de déconnexion.
        
        Args:
            exobj (NETExchangeObject)
        """
        pass

    def net_shutdown(self, exobj):
        """
        Ordre de clôture du seul composant réseau.
        
        Args:
            exobj (NETExchangeObject)
        """
        pass

    def check_connections(self, exobj):
        """
        le composant métier demande au composant réseau de vérifier 
        sa / ses connection(s).        
        Args:
            exobj (NETExchangeObject)
        """
        pass


#-----> Business : application métier
#-----> Composant BUSINESS
class BUSINESSComp(SatelliteComp):
    """
    Composant métier.
    A la diffréence des composants GUI et NET, le composant métier n'a pas 
    d'objet d'échange dédié.
    """

    def __init__(
        self,
        channelname=APPComp.BUSINESS_CHANNEL,
        queue_code_in=APPComp.APPTOBUSINESS_KEYCODE,
        queue_code_out=APPComp.BUSINESSTOAPP_KEYCODE,
        exchangeobjecttypes=[GUIExchangeObject, NETExchangeObject],
    ):
        """
        Constructeur
        
        Args:
            channelname (str): canal de communication
            queue_code_in (str), queue_code_out (str): codes associés au canal 
                BUSINESS_CHANNEL (sens APP->BUSINESS)
            exchangeobjecttype : objet d'échange attendu (générique dans ce cas)
        
        """
        # générique :
        SatelliteComp.__init__(
            self, channelname, queue_code_in, queue_code_out, exchangeobjecttypes
        )

    def handleExchangeObject(self, exobj):
        """
        Traite un objet d'échange provenant d'un autre satellite.
        
        Args:
            exobj : objet GUIExchangeObject ou NETExchangeObject
        """
        handler = arg = None
        if isinstance(exobj, GUIExchangeObject):
            # réception d'un "message" d'interface
            handler = self.handleGUIExchange
            arg = exobj
        elif isinstance(exobj, NETExchangeObject):
            # réception d'un "message" réseau
            handler = self.handleNETExchange
            arg = exobj
        # on applique :
        if handler != None:
            handler(arg)

    #-----> En provenance de la GUI :
    def handleGUIExchange(self, exobj):
        """
        Traitement d'une demande envoyée par l'interface.
        
        Args:
            exobj (GUIExchangeObject)
        """
        typeexchange = exobj.typeexchange
        if typeexchange == GUIExchangeObject.GUI_READY:
            self.on_GUI_Ready(exobj)
        elif typeexchange == GUIExchangeObject.RETURN_USER_CHOICE:
            self.handle_returned_choice(exobj)
        elif typeexchange == GUIExchangeObject.SEND_USER_COMMAND:
            self.handle_user_command(exobj)
        elif typeexchange == GUIExchangeObject.SET_GUI_INFO:
            self.handle_GUI_info(exobj)
        elif typeexchange == GUIExchangeObject.GET_BUS_INFO:
            self.GUI_ask_BUS_info(exobj)

    def on_GUI_Ready(self, exobj):
        """
        L'interface indique qu'elle est prête à réagir.
        
        Args:
            exobj (GUIExchangeObject)
        """
        # à particulariser
        pass

    def handle_returned_choice(self, exobj):
        """
        La GUI retourne le choix utilisateur en réponse à ASK_USER_CHOICE.
        
        Args:
            exobj (GUIExchangeObject)
        """
        # à particulariser
        pass

    def handle_user_command(self, exobj):
        """
        La GUI envoie une commande utilisateur spontannée.
        
        Args:
            exobj (GUIExchangeObject)
        """
        # à particulariser
        pass

    def handle_GUI_info(self, exobj):
        """
        La GUI envoie une information.
        
        Args:
            exobj (GUIExchangeObject)
        """
        # à particulariser
        pass

    def GUI_ask_BUS_info(self, exobj):
        """
        La GUI fait une demande d'information.
        
        Args:
            exobj (GUIExchangeObject)
        """
        # à particulariser
        pass

    #-----> En provenance du réseau :
    def handleNETExchange(self, exobj):
        """
        Traitement d'une demande envoyée par le composant réseau.
        
        Args:
            exobj (NETExchangeObject)
        """
        typeexchange = exobj.typeexchange
        if typeexchange == NETExchangeObject.RECEIVE:
            self.handle_NET_request(exobj)
        elif typeexchange == NETExchangeObject.SET_NET_INFO:
            self.handle_NET_info(exobj)
        elif typeexchange == NETExchangeObject.GET_BUS_INFO:
            self.NET_ask_BUS_info(exobj)
        elif typeexchange == NETExchangeObject.NET_ERROR:
            self.NET_signal_error(exobj)
        elif typeexchange == NETExchangeObject.NET_STATUS:
            self.NET_send_status(exobj)
        elif typeexchange == NETExchangeObject.SEND_ERROR:
            self.NET_signal_send_error(exobj)

    def handle_NET_request(self, exobj):
        """
        Le composant réseau trasmet une requête reçue.
        
        Args:
            exobj (NETExchangeObject)
        """
        # à particulariser
        pass

    def handle_NET_info(self, exobj):
        """
        Le composant réseau envoie une information.
        
        Args:
            exobj (NETExchangeObject)
        """
        # à particulariser
        pass

    def NET_ask_BUS_info(self, exobj):
        """
        Le composant réseau fait une demande d'information.
        
        Args:
            exobj (NETExchangeObject)
        """
        # à particulariser
        pass

    def NET_signal_error(self, exobj):
        """
        Le composant réseau informe d'une erreur de connection.
        exobj.dictargs similaire à NET_send_status, le message
        contient des détails sur l'erreur.
        
        Args:
            exobj (NETExchangeObject)
        """
        # à particulariser
        pass

    def NET_send_status(self, exobj):
        """
        Le composant réseau informe de son état de connection.
        
        Args:
            exobj (NETExchangeObject): avec exobj.dictargs={"connection_status":,  
                "netcode":NETExchangeObject.NET_STATUS,  "msg":}
        
        avec connection_status ayant pour valeur :
        
        * STATUS_SHUTDOWN = "STATUS_SHUTDOWN" # arrêt définiif
        * STATUS_DISCONNECTED = "STATUS_DISCONNECTED" # arrêt temporaire
        * STATUS_ERROR_CONNECTION = "STATUS_ERROR_CONNECTION" # erreur
        * STATUS_UNDEFINED = "STATUS_UNDEFINED" # probablement en erreur
        * STATUS_CONNECTED = "STATUS_CONNECTED" # active
        * STATUS_REJECTED = "STATUS_REJECTED" # connection refusée
        
        Rq : V1 ne concerne que la connection principale au serveur.
        """
        # à particulariser
        pass

    def NET_signal_send_error(self, exobj):
        """
        Le composant réseau signale un envoi en erreur
        """
        # à particulariser
        pass
