#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
**Prototype de framework client/serveur** visant à résoudre les questions soulevées 
dans l'article : https://docs.python.org/3/howto/sockets.html

Protocole(s) supporté(s) : TCP

**Principes :**

* toute requète est découpée (au besoin) en blocs de taille `CustomRequestHelper.BUFFERSIZE`
* une "couche de protocole" identifie chaque bloc avec :

  - un prefix de bloc : `CustomRequestHelper.BLOC_PREFIX` (''<#bp#>'')
  - un entête : `|n° bloc/nombre de blocs|uid|nombre de caractères du message|`
  - la portion de message du bloc
  - un suffixe de bloc : `CustomRequestHelper.BLOC_SUFFIX` (''<#bs#>'')
  
* des codes (et arguments) de commande permettent de gérer : les accusés de réception
  (permettant de "garantir" la réception d'un message), l'identification unique d'un
  client (uid), la communication de son adresse de réception (pour garantir le canal
  serveur vers client, cf limites de `ThreadedTCPServer(socketserver.ThreadingMixIn,
  socketserver.TCPServer)`)

.. admonition:: Exemple 

   Blocs binaires échangés lors de la séquence de connection.

   1- Envoi d'une demande d'uid par le client :   
      b'<#bp#>|1/1|None|18|[cmd:ASK_FOR_UID|]<#bs#>'
      
   2- Réception du bloc par le Serveur, qui retourne l'identifiant uid0 au client :
      b'<#bp#>|1/1|gen_svr_id|4|uid0<#bs#>'
      
   3- Réception du bloc par le client, qui retourne ses infos de connection :
      b'<#bp#>|1/1|uid0|56|[cmd:SET_CLIENT_READ_INFOS|host=192.168.0.7&port=11548]<#bs#>'
      
   4- Réception du bloc par le serveur qui retourne un accusé de réception : 
      b'<#bp#>|1/1|gen_svr_id|26|[cmd:CONFIRM_RECEPTION|]56<#bs#>'
      
   5- Réception de la confirmation par le client avec le bon nombre de caractères (56).
      La communication bilatérale est alors établie.

**Autres fonctionnalités :**

* possibilité de déconnecter / reconnecter les composants "à chaud".
* détection des "déconnections sauvages" distantes pour limiter le nombre de
  reconnection et renvois. 
* informe l'application associée (`BUSINESSComp`) de l'état des différentes
  connections et des erreurs d'envoi.

Todo:
    Evolutions souhaitables:
    
    * supporter plusieurs codes, regrouper codes et msguid en entête
    * paralléliser les envois de requètes côté serveur (voir méthode `send` du serveur frontal)
    * à décliner pour les trois autres protocoles supportés par `socketserver`?

.. admonition:: Application concrète

    Dans le jeu **labpyrinthe** :
    
    **AppManager** (voir :doc:`labpyproject.apps.labpyrinthe.app.application`, 
    dans la méthode privée `_init_network`) crée automatiquement un composant réseau 
    (**CustomTCPServerContainer** ou **CustomTCPThreadedClient**), si l'application 
    est de type serveur (`AppManager.APP_SERVER`) ou respectivement client 
    (`AppManager.APP_CLIENT`).  
     
"""
# imports
import socket
import select
import socketserver
import re
import random
import math
import time
from labpyproject.core.app import app_components as appcomp

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = [
    "CustomTCPServerContainer",
    "ThreadedTCPServer",
    "CustomTCPRequestHandler",
    "ParseDataError",
    "CustomRequestHelper",
    "CustomTCPThreadedClient",
]
# Classes :
#-----> Serveur "frontal"
class CustomTCPServerContainer(appcomp.NETComp):
    """
    **Serveur "frontal"** (conteneur du ThreadedTCPServer).

    **Requètes entrantes :**   
    
    Prises en charge par l'objet server (**ThreadedTCPServer**) via le
    handler(**CustomTCPRequestHandler**) appelant la méthode `handle_indexed_msg()` de cet objet.
    Ce serveur frontal transmet ensuite les données à l'application associée via un mécanisme 
    générique de Queues (ou par un handler externe sinon). 
    Lors de la première connexion d'un client, celui-ci fait une demande d'identifiant unique 
    au serveur. Cet uid permettra par la suite d'identifier le client bien que son adresse 
    distante change au fûr et à mesure de ses reconnections (cf gestion des requètes par 
    `ThreadedTCPServer`).

    **Requètes sortantes (vers les clients) :**
    
    `ThreadedTCPServer` fermant les connexions entrantes après traitement, le client 
    doit communiquer une adresse `(host, port)` qu'il écoute afin que le serveur 
    puisse l'appeler. Dans ce cas le serveur se comporte comme un client et le 
    client comme un serveur.

    Toutes les requètes sont codées (découpées, indéxées, envoyées) / décodées (reçues,
    analysées, recomposées) par l'utilitaire **CustomRequestHelper** qui prend également en charge
    l'insertion de codes et arguments de commandes pour les processus d'identification des
    clients (uid), la communication de leur adresse d'écoute (requètes sortantes) et la gestion
    d'accusés de réception.

    **Logs :**
    
    Le serveur trace les données de connection avec les clients. Il enregistre
    également les erreurs survenues lors des connections, envois et réceptions.
    A chaque occurence d'une action d'envoi ou réception, le serveur envoie au composant
    business (appli métier), un dict d'infos réseau via la méthode `dispatch_network_infos`.

    **Détection des connections clients "rompues sauvagement" :**
    
    A chaque survenue d'une erreur (connection, envoi, réception), on l'analyse afin 
    de mettre à jour le statut du client.
    
    - S'il s'agit d'une `OSError` on considère son degré de gravité (voir 
      `CustomRequestHelper.ERRNO_DICT`, sous ensemble de `errno` cohérent avec les 
      problématiques réseau). 
      
          - Si l'erreur est considérée comme fatale, l'état du client passe à 
            `CustomRequestHelper.STATUS_ERROR_CONNECTION`.
          - Sinon, l'état du client passe à `CustomRequestHelper.STATUS_UNDEFINED` 
            (client probablement déconnecté). Dans ce cas les prochaines tentatives 
            de connection ou envoi se limiteront à un essaipour ce client. Charge à 
            l'appli métier de décider de considérer définitivement ce client comme déconnecté.
      
    - Parfois un envoi ne lève pas d'erreur mais ne reçoit pas le bon accusé de réception 
      (0 au lieu de la longueur du message envoyé). Celà peut se produire du fait d'une erreur 
      d'encodage/décodage utf-8 (voir exemple ci dessous). Après 
      `CustomRequestHelper.SEND_MAX_COUNT` tentatives infructueuses, le serveur communique 
      le problème au composant business (voir sa méthode 
      `NET_signal_send_error(self, exobj)`). L'objet d'échange contient les uids des clients 
      en erreur, le message original et le paramètre d'accusé de réception. 
      Charge au composant business de procéder à un nouvel essai d'envoi.
      
    **Exemple de problème d'encodage/décodage utf-8-bytes-utf-8 :**
    
    
        Erreurs de décodage côté client: ::
            
            CustomRequestHelper._receive_buffer_block ne peut décoder un bloc de données binaires, il retourne :
            
            UnicodeDecodeError('utf-8', b'<#bp#>|1/3|TCPSvr|457|[cmd:NEED_CONFIRMATION|]gamecmd=CHOOSE_GAME&comuid=lpsvr_gcom1002auc&uid=uid2&listeniveaux=[1- La paix sur terre,2- Quasiment non violent,3- De nouveaux participants,4- Ca se corse,5- Sauve qui peut]&msg_input=Choisissez un num\xc3<#bs#>', 249, 250, 'invalid continuation byte')
            
            ou encore:
            
            UnicodeDecodeError('utf-8', b'<#bp#>|2/3|TCPSvr|457|\xa9ro de niveau pour commencer \xc3\xa0 jouer.&msg_input_alt=Choisissez un niveau puis cliquez sur : \\n- partie (pour jouer) \\n- d\xc3\xa9mo (pour regarder une partie automatique)&typechoix=CHOOSE_GAME&comuid=lpsvr_gcom1001abs<MSGUID=TCPSvr_117<#bs#>', 22, 23, 'invalid start byte')
            
            Remarque: le décodage bytes vers utf-8 est effectué de manière stricte.
            
            CustomRequestHelper.receive_indexed_request (le service de réception de requête) retourne alors au client :
            
            ParseDataError("CustomTCP._parse_request_part : invalid bloc of data")
            
            Lors de tentatives de réceptions ultérieures, le service identifiera des blocs incomplets qui ne pourront reconstituer une requète intègre, il retournera alors :
            
            ParseDataError("CustomTCP._analyse_list_mixedblocs : can't reconstruct blocs")
            
            En définitive le client retournera un accusé de réception avec pour valeur 0 indiquant une erreur de réception de données.
        
        Au bout de `CustomRequestHelper.SEND_MAX_COUNT` (15) essais, le serveur appelle `BUSINESSComp.NET_signal_send_error` (via le mécanisme générique de tâches): ::
        
            NET_signal_send_error exobj= SatelliteExchangeObject channelname=NET_CHANNEL typeexchange=SEND_ERROR
            *msg = gamecmd=CHOOSE_GAME&comuid=lpsvr_gcom1002auc&uid=uid2&listeniveaux=[1- La paix sur terre,2- Quasiment non violent,3- De nouveaux participants,4- Ca se corse,5- Sauve qui peut]&msg_input=Choisissez un numéro de niveau pour commencer à jouer.&msg_input_alt=Choisissez un niveau puis cliquez sur : 
            - partie (pour jouer) 
            - démo (pour regarder une partie automatique)&typechoix=CHOOSE_GAME&comuid=lpsvr_gcom1001abs
            *confirmrecept = True
            *clients = ['uid2']
            
            On remarque que les bytes posant problème côté client sont liés aux caractères 
            accentués é et à.
            
        Dans cet exemple le composant métier (`GameManager` de l'application Labpyrinthe) 
        renverra au client d'uid uid2 
        la commande de jeu `CHOOSE_GAME` qui finira par être reçue correctement 
        (au bout de 15 puis 4 essais unitaires).
        
    """

    # méthodes
    def __init__(self, server_address, externalhandler=None, auto_connect=True):
        """
        Constructeur : initie le processus de connection
        
        Args:
            server_address (tuple): (host, port)
            externalhandler (function): fonction externe appelée en fin de traitement 
                d'une requète entrante
            auto_connect (boolean): connection automatique à l'initialisation, vrai par défaut
        
        Rq: plutôt que externalhandler, utiliser de préférence le mécanisme par défaut de Queues 
        hérité de app_components.
        """
        # Init superclasse NETComp :
        appcomp.NETComp.__init__(self)
        # handler externe (méthode éxécutable) optionnel (communication native avec les autres composants via
        # un mécanisme de gestion automatique de Queues multi canaux)
        self.externalhandler = externalhandler
        # dict d'infos réseau :
        self.netdict = dict()
        self.netdict["server"] = {
            "address": None,
            "connection_status": CustomRequestHelper.STATUS_DISCONNECTED,
            "binded": False,
            "connect_errors": list(),
        }
        self.netdict["clients"] = dict()
        # liste d'ids uniques de messages reçus :
        self._received_msguids = list()
        # adresse :
        self.server_host = None
        self.server_port = None
        self._init_server_address(server_address)
        self.binded_to_read = False
        # serveur uid :
        self._uid = "TCPSvr"
        # Serveur TCP interne : crée dans self.connect
        self.server = None
        # Accepte ou non de nouvelles connexions :
        self.accept_new_connections = True
        # Statut :
        self.connection_status = CustomRequestHelper.STATUS_DISCONNECTED
        # Création du thread associé :
        self._need_server_start = False
        self._need_server_shutdown = False
        # thread de démarrage du serveur interne :
        self.server_thread_start = self.create_child_thread(
            self.server_start_loop, suffixname="Svr_start"
        )
        # thread d'arrêt du serveur interne :
        self.server_thread_stop = self.create_child_thread(
            self.server_stop_loop, suffixname="Svr_stop"
        )
        self.set_childthreads_count(2)
        # Incrément / uid clients :
        self.clientincrement = 0
        # Connexion :
        if auto_connect:
            self.connect(None)

    def _init_server_address(self, arg_address):
        """
        Définit l'adresse du serveur.
        """
        # paramètres
        arg_host = None
        arg_port = None
        if isinstance(arg_address, tuple) and len(arg_address) == 2:
            if isinstance(arg_address[0], str):
                arg_host = arg_address[0]
            if isinstance(arg_address[1], int):
                arg_port = arg_address[1]
        # valeurs finales :
        if arg_host == "" or arg_host == "localhost":
            self.server_host = ""
        else:
            self.server_host = CustomRequestHelper.get_ip()
        if arg_port != None:
            self.server_port = arg_port
        else:
            self.server_port = random.randrange(10000, 20000)
        self.netdict["server"]["address"] = (self.server_host, self.server_port)

    #-----> uid
    def _set_uid(self, val):
        if isinstance(val, str):
            self._uid = val

    def _get_uid(self):
        return self._uid

    uid = property(_get_uid, _set_uid)  #: identifiant unique du serveur

    #-----> Threads de gestion du server interne :
    def server_start_loop(self):
        """
        Méthode run du thread de démarrage du serveur interne.
        """
        while True:
            if self._need_server_start:
                # Démarrage du serveur :
                self._start_server_from_thread()

    def server_stop_loop(self):
        """
        Méthode run du thread d'arrêt du serveur interne.
        """
        while True:
            if self._need_server_shutdown:
                # Fin du processus de fermeture :
                self._shutdown_server_from_thread()

    def _shutdown_server_from_thread(self):
        """
        Permet d'appeler server.shutdown depuis un thread dédié à l'arrêt.
        """
        # arrêt de la boucle du serveur :
        self.server.shutdown()
        # Garbage :
        self.server = None
        # Marqueur :
        self._need_server_shutdown = False

    def _start_server_from_thread(self):
        """
        Démarre server.server_forever depuis un thread dédié au démarrage.
        """
        # Marqueur :
        self._need_server_start = False
        # démarrage de la boucle du serveur :
        self.server.serve_forever()

    #-----> Surcharge de appcomp.NETComp
    def sendFromExchangeObject(self, exobj):
        """
        Méthode d'envoi à partir des données comprises dans l'objet NETExchangeObject
        
        Args:
            exobj (appcomp.NETExchangeObject): objet d'échange
        """
        dictargs = exobj.dictargs
        clients = dictargs["clients"]
        msg = dictargs["msg"]
        confirmrecept = True
        if "confirmrecept" in dictargs.keys():
            confirmrecept = dictargs["confirmrecept"]
        self.send(clients, msg, confirmrecept)

    def set_address(self, exobj):
        """
        Affecte l'adresse d'écoute du serveur / adresse d'écriture du client.
        
        Args:
            exobj (appcomp.NETExchangeObject): objet d'échange avec 
                exobj.dictargs={"host":, "port":}
        
        Rq : si host ne pointe pas vers "localhost" (ou ""), l'ip sera déterminée
        via CustomRequestHelper.get_ip().
        """
        dictargs = exobj.dictargs
        host = port = None
        if "host" in dictargs.keys() and "port" in dictargs.keys():
            host = dictargs["host"]
            if isinstance(dictargs["port"], int):
                port = int(dictargs["port"])
        if host != None and port != None:
            self._init_server_address((host, port))

    def connect(self, exobj):
        """
        Ordre de connection à l'adresse pré définie ou à l'adresse éventuellement
        indiquée dans : exobj.dictargs={"host":, "port":}
        
        Args:
            exobj (appcomp.NETExchangeObject): objet d'échange
        """
        # En fonction du statut :
        if self.connection_status == CustomRequestHelper.STATUS_CONNECTED:
            return
        # Re définition éventuelle de l'adresse :
        if exobj != None:
            self.set_address(exobj)
        # Création du serveur TCP interne :
        # Rq : en cas de reconnection après déconnection, réutiliser le même objet, même
        # après l'avoir fermé soigneusement (server.server_close() pour la socket, server.shutdown()
        # pour le thread), conduit à l'erreur (98, 'Adress already in use').
        # Pour avoir les fonctionnalités de connection/déconnection/reconnection..., on doit
        # donc utiliser un nouveau ThreadedTCPServer à chaque connection.
        self.server = ThreadedTCPServer(
            (self.server_host, self.server_port),
            CustomTCPRequestHandler,
            bind_and_activate=False,
        )
        self.server.set_container(self)
        self.server.allow_reuse_address = True
        # Connexion :
        try:
            self.server.server_bind()
            self.server.server_activate()
        except OSError as e:
            # état :
            self.connection_status = CustomRequestHelper.STATUS_ERROR_CONNECTION
            # log
            self._log_connect_errors(e)
            # Remontée de l'erreur
            msg = (
                "Erreur de connection serveur [OSError: "
                + str(e.errno)
                + ", "
                + e.strerror
                + "]."
            )
            self.dispatch_network_status(msg)
            # nettoyage (socket, loop server, ref server)
            self._close_internal()
        else:
            self.binded_to_read = True
            self.netdict["server"]["binded"] = True
            self.connection_status = CustomRequestHelper.STATUS_CONNECTED
            # Informe le composant business:
            msg = "Le serveur est connecté."
            self.dispatch_network_status(msg)
            # Informe les clients précédement connectés :
            msg = CustomRequestHelper.create_cmd_msg(
                CustomRequestHelper.SERVER_CONNECTED
            )
            self._dispatch_to_clients(msg)
            # démarrage du serveur interne :
            self._start_internal()

    def disconnect(self, exobj):
        """
        Déconnexion du serveur.
        
        Args:
            exobj (appcomp.NETExchangeObject): objet d'échange
        
        Rq : on conserve self.netdict en cas de reconnection.
        """
        # Informe les clients :
        msg = CustomRequestHelper.create_cmd_msg(
            CustomRequestHelper.SERVER_DISCONNECTED
        )
        self._dispatch_to_clients(msg)
        # Nettoyage (socket, loop server, ref server) :
        self._close_internal()
        # Etat :
        self.connection_status = CustomRequestHelper.STATUS_DISCONNECTED
        self.binded_to_read = False
        # Informe le composant business:
        msg = "Le serveur est déconnecté."
        self.dispatch_network_status(msg)

    def net_shutdown(self, exobj):
        """
        Ordre de clôture du seul composant réseau.
        
        Args:
            exobj (appcomp.NETExchangeObject): objet d'échange
            
        Rq : on ne clôt pas le process de gestion de tâches, le serveur est
        complètement ré initialisé, mais peut être redémarré.
        """
        self._net_shutdown_internal()

    def shutdown(self):
        """
        Clôture du composant propagé par APPComp
        """
        # arrêt / ré initialisation du serveur :
        self._net_shutdown_internal()
        # générique : arrêt du process d'écoute des tâches
        appcomp.NETComp.shutdown(self)

    def check_connections(self, exobj):
        """
        le composant métier demande au composant réseau de vérifier 
        sa / ses connection(s). 
               
        Args:
            exobj (NETExchangeObject)
        """
        # envoi d'un code CustomRequestHelper.PING aux clients
        dictargs = exobj.dictargs
        if "clients" in dictargs.keys():
            clients = dictargs["clients"]
        else:
            clients = self.netdict["clients"].keys()
        if len(clients) > 0:
            msg = CustomRequestHelper.mark_msg_as_unique(self, "")
            msg = CustomRequestHelper.prefix_msg_with_code(
                msg, CustomRequestHelper.PING
            )
            self.send(clients, msg, confirmrecept=True)

    #-----> Démarrage/arrêt internes
    def _net_shutdown_internal(self):
        """
        Code générque de clôture.
        """
        # Informe les clients :
        msg = CustomRequestHelper.create_cmd_msg(CustomRequestHelper.SERVER_SHUTDOWN)
        self._dispatch_to_clients(msg)
        # Etat :
        self.connection_status = CustomRequestHelper.STATUS_SHUTDOWN
        self.binded_to_read = False
        # suppression de la partie clients de netdict :
        self.netdict["clients"] = dict()
        # Incrément / uid clients :
        self.clientincrement = 0
        # Informe le composant business:
        msg = "Le serveur est arrêté."
        self.dispatch_network_status(msg)
        # Nettoyage (socket, loop server, ref server) :
        self._close_internal()

    def _start_internal(self):
        """
        Démarre le serveur interne
        """
        # Démarrage  de la loop, depuis le thread de démarrage :
        self._need_server_start = True

    def _close_internal(self):
        """
        Lance le processus de fermeture du serveur TCP interne.
        """
        if self.server != None:
            # Clôture de socket :
            try:
                # socket.close() peut engendrer une OSError (new in python 3.6)
                self.server.server_close()
            except OSError as e:
                # log
                self._log_connect_errors(e)
            # Arrêt de la loop, depuis le thread d'arrêt :
            self._need_server_shutdown = True

    #-----> Nouvelles connections
    def allow_new_connections(self, allow):
        """
        Indique si le serveur accepte de nouvelles connections.
        
        Args:
            allow (boolean)
        """
        if allow:
            self.accept_new_connections = True
        else:
            self.accept_new_connections = False

    def do_server_accept_new_connections(self):
        """
        Indique si le serveur accepte de nouvelles connections.
        
        Returns:
            boolean
        """
        return self.accept_new_connections

    #-----> Méthodes internes au "framework"
    #-----> Réception
    def handle_indexed_msg(self, dictreceive):
        """
        Méthode de traitement des requètes entrantes.
        
        Args:
            dictreceive (dict): dict généré par CustomRequestHelper.receive_indexed_request
        
        Returns:
            dict: {"reply":Bool, "reponse":reponse, "return_code":return_code, "dispatch":Bool}
        
        Reçoit le message complet associé à une requète (méthode appelée par le 
        CustomTCPRequestHandler dans sa méthode handle).
        """
        # Dans tous les cas on met à jour la liste des clients (cf reconnections) :
        uid = dictreceive["uid"]
        sock = dictreceive["sock"]
        complete = dictreceive["complete"]
        errors = dictreceive["errors"]
        msguid = dictreceive["msguid"]
        if uid != None:
            # uid inconnu on rejete :
            if uid not in self.netdict["clients"].keys():
                do_reply = True
                return_code = CustomRequestHelper.CONNECTION_REFUSED
                reponse = CustomRequestHelper.prefix_msg_with_code(
                    "Connection refusée", return_code
                )
                return {
                    "reply": do_reply,
                    "reponse": reponse,
                    "return_code": return_code,
                }
            # client enregistré, log :
            clt_add = self._get_address_from_socket(sock)
            rec_err = None
            if len(errors) > 0:
                rec_err = errors[-1]
            self._log_receive(uid, clt_add, rec_err, complete)
        # Traitement des commandes spéciales de la forme "[cmd:CODE_CMD]"
        msg = dictreceive["msg"]
        code_cmd = dictreceive["code_cmd"]
        dict_args = dictreceive["dict_args"]
        if msg == None:
            len_msg = "0"
        else:
            len_msg = str(len(msg))
        # retour par défaut :
        do_reply = False
        reponse = len_msg
        return_code = None
        # accusé de réception par défaut :
        if code_cmd in [
            CustomRequestHelper.NEED_CONFIRMATION,
            CustomRequestHelper.SET_CLIENT_READ_INFOS,
            CustomRequestHelper.CLIENT_CONNECTED,
            CustomRequestHelper.CLIENT_DISCONNECTED,
            CustomRequestHelper.CLIENT_SHUTDOWN,
        ]:
            do_reply = True
            return_code = CustomRequestHelper.CONFIRM_RECEPTION
            reponse = CustomRequestHelper.prefix_msg_with_code(reponse, return_code)
        # prise en charge des commandes :
        if code_cmd == CustomRequestHelper.ASK_FOR_UID:
            # si le serveur accepte de nouvelles connections :
            if self.accept_new_connections:
                # on génère un uid de client :
                uid = self._create_client_uid(sock)
                dictreceive["uid"] = uid
                do_reply = True
                reponse = uid
            else:
                # on indique au client que la connection est refusée :
                do_reply = True
                return_code = CustomRequestHelper.CONNECTION_REFUSED
                reponse = CustomRequestHelper.prefix_msg_with_code(
                    "Connection refusée", return_code
                )
        elif code_cmd == CustomRequestHelper.SET_CLIENT_READ_INFOS:
            # un client identifié commpunique ses infos de connexions réciproques :
            hostout = dict_args["host"]
            portout = dict_args["port"]
            self._register_client_read_address(uid, hostout, portout)
            self._handle_client_connect(uid)
        elif code_cmd == CustomRequestHelper.CLIENT_CONNECTED:
            # le client confirme sa connection :
            self._handle_client_connect(uid)
        elif code_cmd == CustomRequestHelper.CLIENT_DISCONNECTED:
            # le client va se déconnecter :
            self._handle_client_disconnect(uid)
        elif code_cmd == CustomRequestHelper.CLIENT_SHUTDOWN:
            # le client va s'arrêter définitivement :
            self._handle_client_shutdown(uid)
        # logs quantitatifs :
        # - réception
        hasAR = code_cmd == CustomRequestHelper.NEED_CONFIRMATION
        self._log_received_request_count(uid, msguid, hasAR)
        # - envoi
        if do_reply:
            self._log_sended_request_count(uid, True, False)
        # Infos réseau -> application
        self.dispatch_network_infos()
        # retour par défaut :
        return {"reply": do_reply, "reponse": reponse, "return_code": return_code}

    #-----> Retour interne au framework
    def dispatch_to_external_handler(self, dictreceive):
        """
        Transmission à l'application associée en toute fin du traitement de la requète
        
        - de préférence via le mécanisme de Queues hérité de app_components (via queue_tools)
        - sinon via self.externalhandler en appel direct, s'il est défini
        
        Args:
            dictreceive (dict): dict généré par CustomTCPRequestHandler.handle
        
        """
        # params :
        uid = dictreceive["uid"]
        msg_except_cmd = dictreceive["msg_except_cmd"]
        code_cmd = dictreceive["code_cmd"]
        dictargs = {"uid": uid, "msg": msg_except_cmd, "netcode": code_cmd}
        # transmission à l'application :
        if self.are_queues_active():
            # de préférence via le mécanisme de Queues :
            exobj = appcomp.NETExchangeObject(
                appcomp.NETExchangeObject.RECEIVE, dictargs
            )
            self.sendTask(exobj)
        elif self.externalhandler != None and callable(self.externalhandler):
            # appel direct au handler externe sinon :
            self.externalhandler(dictargs)

    #-----> Gestion des clients
    def _create_client_uid(self, sock):
        """
        Génère un identifiant de client unique et l'enregistre dans self.netdict["clients"]
        """
        uid = "uid" + str(self.clientincrement)
        self.netdict["clients"][uid] = {
            "uid": uid,
            "conlistin": list(),
            "hostout": None,
            "portout": None,
            "client_read": None,
            "sockout": None,
            "server_write": None,
            "client_write": None,
            "client_status": CustomRequestHelper.STATUS_CONNECTED,
            "last_connect_error": None,
            "connect_send_error_count": 0,
            "last_send_error": None,
            "send_error_count": 0,
            "last_receive_error": None,
            "uncomplete_receive_count": 0,
            "unit_sended_request_count": 0,
            "AR_sended_request_count": 0,
            "total_sended_request_count": 0,
            "unit_received_request_count": 0,
            "AR_received_request_count": 0,
            "total_received_request_count": 0,
        }
        self.netdict["clients"][uid]["conlistin"].append(
            self._get_address_from_socket(sock)
        )
        self.clientincrement += 1
        return uid

    def _get_address_from_socket(self, sock):
        """
        Tente de déduire l'adresse associée à la socket
        """
        clt_add = None
        try:
            clt_add = sock.getpeername()
        except OSError:
            pass
        return clt_add

    def _get_status_for_client(self, uid):
        """
        Retourne le statut du client 
        """
        return self.netdict["clients"][uid]["client_status"]

    def _handle_client_connect(self, uid):
        """
        Active le client d'uid
        """
        self.netdict["clients"][uid][
            "client_status"
        ] = CustomRequestHelper.STATUS_CONNECTED

    def _handle_client_disconnect(self, uid):
        """
        Désactive temporairement le client d'uid
        """
        self.netdict["clients"][uid][
            "client_status"
        ] = CustomRequestHelper.STATUS_DISCONNECTED
        self.netdict["clients"][uid]["sockout"] = None

    def _handle_client_shutdown(self, uid):
        """
        Désactive définitivement le client d'uid
        """
        self.netdict["clients"][uid][
            "client_status"
        ] = CustomRequestHelper.STATUS_SHUTDOWN
        self.netdict["clients"][uid]["sockout"] = None

    def _dispatch_to_clients(self, msg, confirmrecept=False):
        """
        Envoie msg à tous les clients
        """
        clients = [uid for uid in self.netdict["clients"].keys()]
        self.send(clients, msg, confirmrecept=confirmrecept)

    #-----> Envoi global et unitaire
    def send(self, clients, msg, confirmrecept=True):
        """
        Envoie un message à une liste de clients avec accusé de réception.
        
        Args:
            clients (list): liste d'uid
            msg (str): le message à envoyer
            confirmrecept (boolean) : doit-t'on s'assurer de la réception du message 
                (oui par défaut)
        
        """
        if type(clients) is list and len(clients) > 0:
            # 1- Préparation de la requête :
            # identifiant unique de message :
            msg2send = CustomRequestHelper.mark_msg_as_unique(self, msg)
            # AR 1 : code de commande à ajouter?
            if confirmrecept:
                msg2send = CustomRequestHelper.prefix_msg_with_code(
                    msg2send, CustomRequestHelper.NEED_CONFIRMATION
                )
            # liste de blocs binaires :
            msglen, list2send = CustomRequestHelper.create_indexed_request(
                msg2send, self._uid
            )
            # AR 2 : marqueur interne (cf code de cmd unique en V1)
            code_cmd = CustomRequestHelper.split_cmd_and_msg(msg2send)[0]
            if code_cmd in [
                CustomRequestHelper.NEED_CONFIRMATION,
                CustomRequestHelper.SERVER_CONNECTED,
                CustomRequestHelper.SERVER_DISCONNECTED,
                CustomRequestHelper.SERVER_SHUTDOWN,
            ]:
                confirmrecept = True
            # 2- envois unitaires :
            faillist = list()
            for uid in clients:
                done = self._send_to_client(uid, list2send, msglen, confirmrecept)
                if not done:
                    # on ne considère que les erreurs anormales qui ne sont
                    # pas liées à des erreurs de connections (mais de décodage)
                    # Rq : le statut du client a été mis à jour dans _send_to_client
                    if (
                        self._get_status_for_client(uid)
                        == CustomRequestHelper.STATUS_CONNECTED
                    ):
                        faillist.append(uid)
            # 3- Signalement d'erreurs
            if len(faillist) > 0:
                logargs = {
                    "msg": msg,
                    "confirmrecept": confirmrecept,
                    "clients": faillist,
                }
                exobj = appcomp.NETExchangeObject(
                    appcomp.NETExchangeObject.SEND_ERROR, logargs
                )
                self.sendTask(exobj)
        # Infos réseau -> application
        self.dispatch_network_infos()

    def _send_to_client(self, uid, bytesblocs, msglen, confirmrecept, count=0):
        """
        Envoie une requêye indéxée au client d'uid
        """
        # Si le client s'est déconnecté :
        # Rqs :
        # - STATUS_ERROR_CONNECTION ne peut être connu que localement (du client dans ce cas)
        # - STATUS_REJECTED n'est mémorisé que par le client, mais celà équivaut à uid = None
        # en définitive on essaye d'envoyer si le statut est STATUS_CONNECTED ou STATUS_UNDEFINED,
        # dans ce dernier cas on ne fera qu'un essai.
        if uid not in self.netdict["clients"] or self.netdict["clients"][uid][
            "client_status"
        ] in [
            CustomRequestHelper.STATUS_SHUTDOWN,
            CustomRequestHelper.STATUS_DISCONNECTED,
            CustomRequestHelper.STATUS_ERROR_CONNECTION,
        ]:
            return False
        # log dénombrement d'envoi :
        unit = count == 0
        self._log_sended_request_count(uid, unit, confirmrecept)
        # marqueur d'erreur
        has_error = False
        error = None
        # 1- connection :
        clientdict = self.netdict["clients"][uid]
        send_errors = (clientdict["last_connect_error"] != None) or (
            clientdict["last_send_error"] != None
        )
        sockout = clientdict["sockout"]
        if sockout == None or send_errors:
            hostout = clientdict["hostout"]
            portout = clientdict["portout"]
            # (re) création
            sockout = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sockout.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # (re) connection :
            if portout != None:
                connection_count = 0
                connected = False
                client_unsure = (
                    send_errors
                    or self._get_status_for_client(uid)
                    == CustomRequestHelper.STATUS_UNDEFINED
                )
                while (
                    not connected
                    and connection_count < CustomRequestHelper.CONNECTION_MAX_COUNT
                ):
                    error = None
                    # Réduction du timeout si le client est incertain et après la première 
                    # tentative infructueuse :
                    if client_unsure or connection_count > 0:
                        sockout.settimeout(CustomRequestHelper.RECONNECTION_TIMEOUT)
                    try:
                        sockout.connect((hostout, portout))
                    except OSError as e:
                        error = e
                        # rq : à partir de python 3.3 socket.error devient OSError
                        self._log_connect_send(uid, sockout, error)
                        has_error = True
                        # qualification de l'erreur :
                        fatal_error = CustomRequestHelper.is_error_fatal(error)
                        if not fatal_error:
                            connection_count += 1
                            time.sleep(CustomRequestHelper.RECONNECTION_DELAY)
                        else:
                            break
                    else:
                        self._log_connect_send(uid, sockout, None)
                        has_error = False
                        connected = True
                        break
        # 2- envoi :
        if not has_error:
            error = CustomRequestHelper.send_indexed_request(sockout, bytesblocs)
            if error != None:
                self._log_send(uid, error)
                has_error = True
            else:
                self._log_send(uid, None)
            # 3- test réception :
            if confirmrecept:  # and not has_error:
                dictreceive = CustomRequestHelper.receive_indexed_request(sockout)
                errors = dictreceive["errors"]
                complete = dictreceive["complete"]
                sock = dictreceive["sock"]
                if len(errors) > 0:
                    #  réponse invalide
                    error = errors[-1]
                    has_error = True
                    clt_add = self._get_address_from_socket(sock)
                    self._log_receive(uid, clt_add, error, complete)
                else:
                    bytesreceived = dictreceive["msg_except_cmd"]
                    code_cmd = dictreceive["code_cmd"]
                    if (
                        code_cmd != CustomRequestHelper.CONFIRM_RECEPTION
                        or bytesreceived == None
                        or int(bytesreceived) != msglen
                    ):
                        # accusé de réception invalide
                        errors = dictreceive["errors"]
                        if len(errors) > 0:
                            error = errors[-1]
                        has_error = True
                    else:
                        # log quantitatif réception :
                        msguid = dictreceive["msguid"]
                        self._log_received_request_count(uid, msguid, False)
        # 3- Gestion d'erreur
        if has_error:
            # Est ce raisonnable de ré essayer ?
            if error != None:
                fatal_error = CustomRequestHelper.is_error_fatal(error)
                if fatal_error:
                    # inutile : on arrête
                    return False
            # Si oui, on retente dans la limite de CustomRequestHelper.SEND_MAX_COUNT
            count += 1
            if count < CustomRequestHelper.SEND_MAX_COUNT:
                time.sleep(CustomRequestHelper.RESEND_DELAY)
                return self._send_to_client(
                    uid, bytesblocs, msglen, confirmrecept, count=count
                )
        return not has_error

    #-----> Logs :
    def _register_client_read_address(self, uid, host, port):
        """
        Enregistre l'adresse de réception d'un client
        """
        if uid in self.netdict["clients"].keys():
            self.netdict["clients"][uid]["hostout"] = host
            self.netdict["clients"][uid]["portout"] = int(port)
            self.netdict["clients"][uid]["client_read"] = (host, int(port))

    def _log_connect_errors(self, connect_error):
        """
        Log des erreurs de connections propres à self.server
        """
        self.netdict["server"]["connect_errors"].append(connect_error)

    def _check_client_status_on_error(self, uid, error):
        """
        Met à jour le statut du client en fonction de la nature de l'erreur.
        
        Args:
            uid: identifiant du client
            error: OSError ou ParseDataError
        """
        if uid in self.netdict["clients"].keys():
            if error != None:
                fatal_error = CustomRequestHelper.is_error_fatal(error)
                cltdict = self.netdict["clients"][uid]
                current_status = self._get_status_for_client(uid)
                if fatal_error:
                    # on passe le client en statut CustomRequestHelper.STATUS_ERROR_CONNECTION
                    cltdict[
                        "client_status"
                    ] = CustomRequestHelper.STATUS_ERROR_CONNECTION
                elif current_status == CustomRequestHelper.STATUS_CONNECTED:
                    # on passe le client en statut CustomRequestHelper.STATUS_UNDEFINED
                    cltdict["client_status"] = CustomRequestHelper.STATUS_UNDEFINED

    def _log_connect_send(self, uid, sockout, connect_error):
        """
        Log du dernier essai de connection d'envoi au client identifié par uid
        
        Args:
            uid: identifiant du client
            sockout : socket d'envoi
            connect_error : None (connexion réussie) ou OSError (dernière erreur de 
                connection en date)            
        """
        if uid in self.netdict["clients"].keys():
            cltdict = self.netdict["clients"][uid]
            cltdict["sockout"] = sockout
            cltdict["last_connect_error"] = connect_error
            if connect_error != None:
                cltdict["connect_send_error_count"] += 1
            # Vérification de l'état du client :
            self._check_client_status_on_error(uid, connect_error)
            # maj adresse
            svr_write = None
            if sockout != None:
                try:
                    svr_write = sockout.getsockname()
                except Exception:
                    pass
            cltdict["server_write"] = svr_write

    def _log_send(self, uid, send_error):
        """
        Log du dernier essai d'envoi au client identifié par uid
        
        Args:
            uid: identifiant du client
            send_error : None (envoi réussi) ou OSError (dernière erreur d'envoi en date)        
        """
        if uid in self.netdict["clients"].keys():
            cltdict = self.netdict["clients"][uid]
            cltdict["last_send_error"] = send_error
            if send_error != None:
                cltdict["send_error_count"] += 1
            # Vérification de l'état du client :
            self._check_client_status_on_error(uid, send_error)

    def _log_sended_request_count(self, uid, unit, hasAR):
        """
        Log les envois de requête vers le client :
        
        Args:
            uid: identifiant du client
            unit: est-ce un envoi unitaire ou bien un renvoi
            hasAR: si unit=True, indique si la requête nécessite un accusé de récpetion        
        """
        if uid in self.netdict["clients"].keys():
            cltdict = self.netdict["clients"][uid]
            cltdict["total_sended_request_count"] += 1
            if unit:
                cltdict["unit_sended_request_count"] += 1
                if hasAR:
                    cltdict["AR_sended_request_count"] += 1

    def _log_receive(self, uid, clt_address, receive_error, complete):
        """
        Log du dernier process de réception de requête en provenance du client
        identifié par uid
        
        Args:
            uid: identifiant du client
            clt_address: dernière adresse d'envoi utilisée par le client
            receive_error:  None (réception réussie) ou OSError (dernière erreur 
                de réception en date)            
            complete (Boolean): indique si la requête reçue est complète
        
        """
        if uid in self.netdict["clients"].keys():
            cltdict = self.netdict["clients"][uid]
            cltdict["conlistin"].append(clt_address)
            cltdict["client_write"] = clt_address
            cltdict["last_receive_error"] = receive_error
            cltdict["uncomplete_receive_count"] += int(not complete)
            # Vérification de l'état du client :
            self._check_client_status_on_error(uid, receive_error)

    def _log_received_request_count(self, uid, msguid, hasAR):
        """
        Log les réceptions de messages envoyés par le client
        
        Args:
            uid: identifiant du client
            msguid : identifiant unique de message
            hasAR : un accusé de réception est-il demandé.        
        """
        if uid in self.netdict["clients"].keys():
            cltdict = self.netdict["clients"][uid]
            cltdict["total_received_request_count"] += 1
            if msguid == None or not msguid in self._received_msguids:
                cltdict["unit_received_request_count"] += 1
                if hasAR:
                    cltdict["AR_received_request_count"] += 1
        if not msguid in self._received_msguids:
            self._received_msguids.append(msguid)

    #-----> Etat du réseau
    def dispatch_network_status(self, msg):
        """
        Informe le composant business de l'état de connection principale (réception).
        
        Args:
            msg (str): message d'info
        """
        dictargs = {"connection_status": self.connection_status, "msg": msg}
        # transmission à l'application :
        if self.are_queues_active():
            # de préférence via le mécanisme de Queues :
            code = appcomp.NETExchangeObject.NET_STATUS
            if self.connection_status == CustomRequestHelper.STATUS_ERROR_CONNECTION:
                code = appcomp.NETExchangeObject.NET_ERROR
            exobj = appcomp.NETExchangeObject(code, dictargs)
            self.sendTask(exobj)
        elif self.externalhandler != None and callable(self.externalhandler):
            # appel direct au handler externe sinon :
            self.externalhandler(dictargs)
        # Infos réseau -> application
        self.dispatch_network_infos()

    def dispatch_network_infos(self):
        """
        Envoie au composant Business les infos réseau.
        """
        dictargs = self.get_network_infos()
        # transmission à l'application :
        if self.are_queues_active():
            # de préférence via le mécanisme de Queues :
            exobj = appcomp.NETExchangeObject(
                appcomp.NETExchangeObject.SET_NET_INFO, dictargs
            )
            self.sendTask(exobj)
        elif self.externalhandler != None and callable(self.externalhandler):
            # appel direct au handler externe sinon :
            self.externalhandler(dictargs)

    def get_network_infos(self):
        """
        Retourne un dictionnaire d'infos sur le serveur et les clients.
        Détecte les connections probablement interrompues "sauvagement".
        
        Returns:
            dict: self.netdict
        """
        # Etat de la connection principale (réception) :
        self.netdict["server"]["connection_status"] = self.connection_status
        self.netdict["server"]["binded"] = self.binded_to_read
        return self.netdict


#-----> Server "réel" construit à partir du package socketserver, utilisé par composition
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """
    Serveur TCP prenant en charge chaque requète dans un thread, lui même géré dans 
    un thread par son conteneur **CustomTCPServerContainer**.
    """

    def set_container(self, parent):
        """
        Assigne l'objet container CustomTCPServerContainer
        
        Args:
            parent (CustomTCPServerContainer)
        """
        self.server_container = parent

    def get_container(self):
        """
        Retourne l'objet container CustomTCPServerContainer.
        
        Returns:
            CustomTCPServerContainer
        """
        return self.server_container


#-----> RequestHandler personnalisé
class CustomTCPRequestHandler(socketserver.BaseRequestHandler):
    """
    Objet instancié pour chaque requète entrante (gérée dans un thread par 
    `ThreadedTCPServer`).
    Appelle la méthode `handle_indexed_msg()` du **CustomTCPServerContainer** 
    conteneur.
    """

    def handle(self):
        """
        Prend en charge une requète entrante.
        
            1. Réception des données (via CustomRequestHelper)
            2. Traitement du message (par le CustomTCPServerContainer associé)
            3. Envoi de l'éventuel accusé (via CustomRequestHelper)
            4. Informe le composant métier du message ou d'une erreur
        """
        with self.request:
            # 1- Réception des données :
            dictreceive = CustomRequestHelper.receive_indexed_request(self.request)
            # 2- Traitement du message :
            dicthandle = self.server.get_container().handle_indexed_msg(dictreceive)
            # 3- On retourne la réponse (le nombre de caractères du message reçu par défaut)
            if dicthandle["reply"]:
                # Rq : cet objet n'a pas accès à la ppté uid de l'objet CustomTCPServerContainer
                # on utilise donc un identifiant générique.
                list2send = CustomRequestHelper.create_indexed_request(
                    dicthandle["reponse"], "gen_svr_id"
                )[1]
                error = CustomRequestHelper.send_indexed_request(
                    self.request, list2send
                )
                if error == None:
                    dictreceive["AR_sended"] = True
            # 4- Appel au handler externe après l'envoi de la réponse :
            front_server = self.server.get_container()
            if dicthandle["return_code"] == CustomRequestHelper.CONNECTION_REFUSED:
                # connexion refusée : on informe le business sans transmettre la requête
                clt_add = None
                try:
                    clt_add = dictreceive["sock"].getpeername()
                except:
                    pass
                msg = (
                    "Requête de code "
                    + dictreceive["code_cmd"]
                    + " rejetée. \nConnexion refusée à "
                    + str(clt_add)
                )
                front_server.dispatch_network_status(msg)
            else:
                # on transmet la requète au business
                front_server.dispatch_to_external_handler(dictreceive)


#-----> Exception associée à une erreur de parsing de donnée
class ParseDataError(Exception):
    """
    Exception associée à une erreur de parsing de donnée
    """

    def __init__(self, message):
        """
        Constructeur
        """
        # générique
        super().__init__(message)


#-----> Helper statique
class CustomRequestHelper:
    """
    Utilitaire statique proposant des services :
    
    - de support de codes et arguments de commandes
    - de découpage, indexation, envoi et réception de requêtes 
    - d'analyse d'erreurs
    
    """

    # Variables statiques
    # Taille de buffer par défaut considérée pour les requêtes
    BUFFERSIZE = 1024 * 2  #: Taille de buffer par défaut considérée pour les requêtes
    # Création et compilation de la regex d'interprétation des commandes
    REGEXP_CMD = re.compile(
        "\[cmd:[A-Za-z0-9_]*\|([A-Za-z0-9_]*=[A-Za-z0-9_\.]*&?)*\]"
    )  #: Création et compilation de la regex d'interprétation des commandes
    # et de celle des identifiants uniques de messages :
    REGEXP_MSGUID = re.compile(
        "<MSGUID=[A-Za-z0-9_]*>"
    )  #: Création et compilation de la regex des identifiants uniques de messages
    # marqueur de début de bloc
    BLOC_PREFIX = "<#bp#>"  #: marqueur de début de bloc
    # marqueur de fin de bloc
    BLOC_SUFFIX = "<#bs#>"  #: marqueur de fin de bloc
    # nombre d'erreurs à partir duquel on considère une connection comme probablement inactive :
    INACTIVE_COUNT = 20  #: nombre d'erreurs à partir duquel on considère une connection comme probablement inactive
    # nombre max de tentatives d'envoi
    SEND_MAX_COUNT = 15  #: nombre max de tentatives d'envoi
    # nombre max de tentatives successives de connection
    CONNECTION_MAX_COUNT = 10  #: nombre max de tentatives successives de connection
    # délai avant tentative de re connection
    RECONNECTION_DELAY = 0.05  #: délai avant tentative de re connection
    # time out de reconnection (par défaut 120 sec, on le réduit)
    RECONNECTION_TIMEOUT = (
        10  
    ) #: time out de reconnection (par défaut 120 sec, on le réduit)
    # délai avant nouvelle tentative d'envoi
    RESEND_DELAY = 0.05  #: délai avant nouvelle tentative d'envoi
    # Timeout select
    SELECT_TIMEOUT = 0.05  #: Timeout select
    # Codes de commandes client/serveur hors problématiques de connection pures
    CONFIRM_RECEPTION = (
        "CONFIRM_RECEPTION"  
    ) #: tag un msg comme confirmation de réception
    NEED_CONFIRMATION = (
        "NEED_CONFIRMATION"  
    ) #: indique que le message nécessite un accusé de réception
    ASK_FOR_UID = "ASK_FOR_UID"  #: demande d'id unique de client
    UID_SET_BY_SERVER = (
        "UID_SET_BY_SERVER"  
    ) #: pour informer BUS/externalHandler de l'affectation
    SET_CLIENT_READ_INFOS = "SET_CLIENT_READ_INFOS"  #: indique les données de connexion à client.socket_read
    PING = "PING"  #: vérification de connection
    # Codes d'état serveur (serveur -> clients)
    SERVER_CONNECTED = "SERVER_CONNECTED"  #: le serveur est connecté
    SERVER_DISCONNECTED = "SERVER_DISCONNECTED"  #: le serveur se déconnecte mais ne s'arrête pas totalement
    SERVER_SHUTDOWN = "SERVER_SHUTDOWN"  #: le serveur va s'arrêter
    # Codes d'état client (client -> serveur)
    CLIENT_CONNECTED = "CLIENT_CONNECTED"  #: le client est connecté au serveur
    CLIENT_DISCONNECTED = "CLIENT_DISCONNECTED"  #: le serveur se déconnecte mais ne s'arrête pas totalement
    CLIENT_SHUTDOWN = "CLIENT_SHUTDOWN"  #: le client va s'arrêter
    # statut d'une connection (gestion interne & NET -> BUS)
    STATUS_SHUTDOWN = "STATUS_SHUTDOWN"  #: arrêt définiif
    STATUS_DISCONNECTED = "STATUS_DISCONNECTED"  #: arrêt temporaire
    STATUS_ERROR_CONNECTION = "STATUS_ERROR_CONNECTION"  #: erreur
    STATUS_UNDEFINED = "STATUS_UNDEFINED"  #: probablement en erreur
    STATUS_CONNECTED = "STATUS_CONNECTED"  #: connection active
    STATUS_REJECTED = "STATUS_REJECTED"  #: connection refusée par le serveur
    # Refus de connection (NET -> BUS)
    CONNECTION_REFUSED = "CONNECTION_REFUSED"  #: connection refusée par le serveur
    # incrément d'uid de messages : initialisé aléatoirement
    MSGUID_INCREMENT = random.randrange(1, 1000000)  #: incrément d'uid de messages
    # qualification des ERRNO système et réseau
    # typologies d'erreur
    ERRNO_SYS = "ERRNO_SYS"  #: erreur de type système
    ERRNO_NET = "ERRNO_NET"  #: erreur de type réseau
    ERRNO_CON = "ERRNO_CON"  #: erreur de type connection
    ERRNO_SEND = "ERRNO_SEND"  #: erreur d'envoi
    ERRNO_DATA = "ERRNO_DATA"  #: erreur de donnée
    # dict de qualification des erreurs :
    ERRNO_DICT = {
        113: {
            "os": "linux",
            "errno-str": "EHOSTUNREACH",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "No route to host",
        },
        87: {
            "os": "linux",
            "errno-str": "EUSERS",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "Too many users",
        },
        105: {
            "os": "linux",
            "errno-str": "ENOBUFS",
            "type": "ERRNO_CON",
            "fatal": False,
            "desc": "No buffer space available",
        },
        90: {
            "os": "linux",
            "errno-str": "EMSGSIZE",
            "type": "ERRNO_DATA",
            "fatal": True,
            "desc": "Message too long",
        },
        97: {
            "os": "linux",
            "errno-str": "EAFNOSUPPORT",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Address family not supported by protocol",
        },
        53: {
            "os": "linux",
            "errno-str": "EBADR",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Invalid request descriptor",
        },
        112: {
            "os": "linux",
            "errno-str": "EHOSTDOWN",
            "type": "ERRNO_NET",
            "fatal": True,
            "desc": "Host is down",
        },
        96: {
            "os": "linux",
            "errno-str": "EPFNOSUPPORT",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Protocol family not supported",
        },
        92: {
            "os": "linux",
            "errno-str": "ENOPROTOOPT",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Protocol not available",
        },
        77: {
            "os": "linux",
            "errno-str": "EBADFD",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "File descriptor in bad state",
        },
        106: {
            "os": "linux",
            "errno-str": "EISCONN",
            "type": "ERRNO_CON",
            "fatal": False,
            "desc": "Transport endpoint is already connected",
        },
        108: {
            "os": "linux",
            "errno-str": "ESHUTDOWN",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Cannot send after transport endpoint shutdown",
        },
        64: {
            "os": "linux",
            "errno-str": "ENONET",
            "type": "ERRNO_NET",
            "fatal": True,
            "desc": "Machine is not on the network",
        },
        91: {
            "os": "linux",
            "errno-str": "EPROTOTYPE",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Protocol wrong type for socket",
        },
        114: {
            "os": "linux",
            "errno-str": "EALREADY",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "Operation already in progress",
        },
        100: {
            "os": "linux",
            "errno-str": "ENETDOWN",
            "type": "ERRNO_NET",
            "fatal": True,
            "desc": "Network is down",
        },
        76: {
            "os": "linux",
            "errno-str": "ENOTUNIQ",
            "type": "ERRNO_NET",
            "fatal": True,
            "desc": "Name not unique on network",
        },
        111: {
            "os": "linux",
            "errno-str": "ECONNREFUSED",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Connection refused",
        },
        93: {
            "os": "linux",
            "errno-str": "EPROTONOSUPPORT",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Protocol not supported",
        },
        70: {
            "os": "linux",
            "errno-str": "ECOMM",
            "type": "ERRNO_SEND",
            "fatal": False,
            "desc": "Communication error on send",
        },
        121: {
            "os": "linux",
            "errno-str": "EREMOTEIO",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "Remote I/O error",
        },
        102: {
            "os": "linux",
            "errno-str": "ENETRESET",
            "type": "ERRNO_NET",
            "fatal": False,
            "desc": "Network dropped connection because of reset",
        },
        110: {
            "os": "linux",
            "errno-str": "ETIMEDOUT",
            "type": "ERRNO_CON",
            "fatal": False,
            "desc": "Connection timed out",
        },
        122: {
            "os": "linux",
            "errno-str": "EDQUOT",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "Quota exceeded",
        },
        56: {
            "os": "linux",
            "errno-str": "EBADRQC",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Invalid request code",
        },
        107: {
            "os": "linux",
            "errno-str": "ENOTCONN",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Transport endpoint is not connected",
        },
        89: {
            "os": "linux",
            "errno-str": "EDESTADDRREQ",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Destination address required",
        },
        103: {
            "os": "linux",
            "errno-str": "ECONNABORTED",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Software caused connection abort",
        },
        101: {
            "os": "linux",
            "errno-str": "ENETUNREACH",
            "type": "ERRNO_NET",
            "fatal": True,
            "desc": "Network is unreachable",
        },
        88: {
            "os": "linux",
            "errno-str": "ENOTSOCK",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Socket operation on non-socket",
        },
        86: {
            "os": "linux",
            "errno-str": "ESTRPIPE",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Streams pipe error",
        },
        104: {
            "os": "linux",
            "errno-str": "ECONNRESET",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Connection reset by peer",
        },
        98: {
            "os": "linux",
            "errno-str": "EADDRINUSE",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Address already in use",
        },
        78: {
            "os": "linux",
            "errno-str": "EREMCHG",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Remote address changed",
        },
        85: {
            "os": "linux",
            "errno-str": "ERESTART",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "Interrupted system call should be restarted",
        },
        94: {
            "os": "linux",
            "errno-str": "ESOCKTNOSUPPORT",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Socket type not supported",
        },
        115: {
            "os": "linux",
            "errno-str": "EINPROGRESS",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "Operation now in progress",
        },
        61: {
            "os": "linux",
            "errno-str": "ENODATA",
            "type": "ERRNO_DATA",
            "fatal": True,
            "desc": "No data available",
        },
        120: {
            "os": "windows",
            "errno-str": "ENODATA",
            "type": "ERRNO_DATA",
            "fatal": True,
            "desc": "No data available",
        },
        32: {
            "os": "linux, windows",
            "errno-str": "EPIPE",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Broken pipe",
        },
        4: {
            "os": "linux, windows",
            "errno-str": "EINTR",
            "type": "ERRNO_SYS",
            "fatal": False,
            "desc": "Interrupted system call",
        },
        71: {
            "os": "linux",
            "errno-str": "EPROTO",
            "type": "ERRNO_NET",
            "fatal": True,
            "desc": "Protocol error",
        },
        134: {
            "os": "windows",
            "errno-str": "EPROTO",
            "type": "ERRNO_NET",
            "fatal": True,
            "desc": "Protocol error",
        },
        10: {
            "os": "linux, windows",
            "errno-str": "ECHILD",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "No child processes",
        },
        11: {
            "os": "linux, windows",
            "errno-str": "EAGAIN",
            "type": "ERRNO_SYS",
            "fatal": False,
            "desc": "Try again",
        },
        5: {
            "os": "linux, windows",
            "errno-str": "EIO",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "I/O error",
        },
        13: {
            "os": "linux, windows",
            "errno-str": "EACCES",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "Permission denied",
        },
        1: {
            "os": "linux, windows",
            "errno-str": "EPERM",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "Operation not permitted",
        },
        14: {
            "os": "linux, windows",
            "errno-str": "EFAULT",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Bad address",
        },
        12: {
            "os": "linux, windows",
            "errno-str": "ENOMEM",
            "type": "ERRNO_SYS",
            "fatal": False,
            "desc": "Out of memory",
        },
        62: {
            "os": "linux",
            "errno-str": "ETIME",
            "type": "ERRNO_SYS",
            "fatal": False,
            "desc": "Timer expired",
        },
        137: {
            "os": "windows",
            "errno-str": "ETIME",
            "type": "ERRNO_SYS",
            "fatal": False,
            "desc": "Timer expired",
        },
        6: {
            "os": "linux, windows",
            "errno-str": "ENXIO",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "No such device or address",
        },
        10065: {
            "os": "windows",
            "errno-str": "WSAEHOSTUNREACH",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "No route to host",
        },
        10004: {
            "os": "windows",
            "errno-str": "WSAEINTR",
            "type": "ERRNO_SYS",
            "fatal": False,
            "desc": "Interrupted system call",
        },
        10068: {
            "os": "windows",
            "errno-str": "WSAEUSERS",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "Too many users",
        },
        10055: {
            "os": "windows",
            "errno-str": "WSAENOBUFS",
            "type": "ERRNO_CON",
            "fatal": False,
            "desc": "No buffer space available",
        },
        10040: {
            "os": "windows",
            "errno-str": "WSAEMSGSIZE",
            "type": "ERRNO_DATA",
            "fatal": True,
            "desc": "Message too long",
        },
        10047: {
            "os": "windows",
            "errno-str": "WSAEAFNOSUPPORT",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Address family not supported by protocol",
        },
        10064: {
            "os": "windows",
            "errno-str": "WSAEHOSTDOWN",
            "type": "ERRNO_NET",
            "fatal": True,
            "desc": "Host is down",
        },
        10046: {
            "os": "windows",
            "errno-str": "WSAEPFNOSUPPORT",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Protocol family not supported",
        },
        10042: {
            "os": "windows",
            "errno-str": "WSAENOPROTOOPT",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Protocol not available",
        },
        10056: {
            "os": "windows",
            "errno-str": "WSAEISCONN",
            "type": "ERRNO_CON",
            "fatal": False,
            "desc": "Transport endpoint is already connected",
        },
        10058: {
            "os": "windows",
            "errno-str": "WSAESHUTDOWN",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Cannot send after transport endpoint shutdown",
        },
        10041: {
            "os": "windows",
            "errno-str": "WSAEPROTOTYPE",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Protocol wrong type for socket",
        },
        10037: {
            "os": "windows",
            "errno-str": "WSAEALREADY",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "Operation already in progress",
        },
        10050: {
            "os": "windows",
            "errno-str": "WSAENETDOWN",
            "type": "ERRNO_NET",
            "fatal": True,
            "desc": "Network is down",
        },
        10013: {
            "os": "windows",
            "errno-str": "WSAEACCES",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "Permission denied",
        },
        10061: {
            "os": "windows",
            "errno-str": "WSAECONNREFUSED",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Connection refused",
        },
        10043: {
            "os": "windows",
            "errno-str": "WSAEPROTONOSUPPORT",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Protocol not supported",
        },
        10052: {
            "os": "windows",
            "errno-str": "WSAENETRESET",
            "type": "ERRNO_NET",
            "fatal": False,
            "desc": "Network dropped connection because of reset",
        },
        10060: {
            "os": "windows",
            "errno-str": "WSAETIMEDOUT",
            "type": "ERRNO_CON",
            "fatal": False,
            "desc": "Connection timed out",
        },
        10069: {
            "os": "windows",
            "errno-str": "WSAEDQUOT",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "Quota exceeded",
        },
        10014: {
            "os": "windows",
            "errno-str": "WSAEFAULT",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Bad address",
        },
        10057: {
            "os": "windows",
            "errno-str": "WSAENOTCONN",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Transport endpoint is not connected",
        },
        10039: {
            "os": "windows",
            "errno-str": "WSAEDESTADDRREQ",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Destination address required",
        },
        10053: {
            "os": "windows",
            "errno-str": "WSAECONNABORTED",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Software caused connection abort",
        },
        10051: {
            "os": "windows",
            "errno-str": "WSAENETUNREACH",
            "type": "ERRNO_NET",
            "fatal": True,
            "desc": "Network is unreachable",
        },
        10038: {
            "os": "windows",
            "errno-str": "WSAENOTSOCK",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Socket operation on non-socket",
        },
        10054: {
            "os": "windows",
            "errno-str": "WSAECONNRESET",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Connection reset by peer",
        },
        10048: {
            "os": "windows",
            "errno-str": "WSAEADDRINUSE",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Address already in use",
        },
        10044: {
            "os": "windows",
            "errno-str": "WSAESOCKTNOSUPPORT",
            "type": "ERRNO_CON",
            "fatal": True,
            "desc": "Socket type not supported",
        },
        10036: {
            "os": "windows",
            "errno-str": "WSAEINPROGRESS",
            "type": "ERRNO_SYS",
            "fatal": True,
            "desc": "Operation now in progress",
        },
    }  #: dict de qualification des erreurs
    # méthodes
    #-----> Utilitaire réseau
    def get_ip(cls):
        """
        Retourne l'ip primaire, à la différence de socket.gethostbyname(socket.gethostname()) 
        qui retourne plus systématiquement 127.0.x.1
        
        From https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
        by Jamieson Becker
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(("10.255.255.255", 1))
            IP = s.getsockname()[0]
        except:
            IP = "127.0.0.1"
        finally:
            s.close()
        return IP

    get_ip = classmethod(get_ip)

    #-----> Identification unique d'un message :
    def mark_msg_as_unique(cls, asker, msg):
        """
        Ajoute un identifiant unique de message à msg :
        
        Args:
            asker : serveur ou client à l'origine de la demande
            msg : chaine à marquer
        
        Simplification : on ajoute la marque <MSGUID=valeur> en fin de message
        """
        # le message est il déja marqué ?
        if CustomRequestHelper.REGEXP_MSGUID.search(msg) != None:
            return msg
        # marquage :
        CustomRequestHelper.MSGUID_INCREMENT += 1
        if asker != None:
            muid = str(asker.uid) + "_" + str(CustomRequestHelper.MSGUID_INCREMENT)
        else:
            muid = "CRH_AUTOADD" + "_" + str(CustomRequestHelper.MSGUID_INCREMENT)
        msg = msg + "<MSGUID=" + muid + ">"
        return msg

    mark_msg_as_unique = classmethod(mark_msg_as_unique)

    def split_unique_mark_and_msg(cls, msg):
        """
        Sépare identifiants unique de message et message initial.
        """
        msguid = None
        msginit = msg
        blocsuid = CustomRequestHelper.REGEXP_MSGUID.findall(msg)
        if blocsuid != None and len(blocsuid) > 0:
            b0 = blocsuid[0]
            msguid = b0[8:-1]
            msginit = CustomRequestHelper.REGEXP_MSGUID.split(msg)[0]
        return msguid, msginit

    split_unique_mark_and_msg = classmethod(split_unique_mark_and_msg)

    #-----> Formatage de messages
    def prefix_msg_with_code(cls, msg, code, kwargs=None):
        """
        Préfixe le msg avec un entête de commande.
        """
        entete = CustomRequestHelper.create_cmd_msg(code, kwargs=kwargs)
        return entete + msg

    prefix_msg_with_code = classmethod(prefix_msg_with_code)

    def create_cmd_msg(cls, code, kwargs=None):
        """
        Formate un message de commande client/serveur.
        
        Exemple d'entête ajouté : ``[cmd:CODE_TEST|v1=5&v2=0.0.0.0]``
        """
        msg = "[cmd:" + str(code) + "|"
        if kwargs != None:
            for cle, val in kwargs.items():
                msg += str(cle) + "=" + str(val) + "&"
            msg = msg[: len(msg) - 1]
        msg += "]"
        return msg

    create_cmd_msg = classmethod(create_cmd_msg)

    def split_cmd_and_msg(cls, msg):
        """
        Sépare code de commande, dict d'arguments et fin du message dans un message parsé.
        
        Returns:
            tuple : code, **kwargs, msg sans cmd
        """
        if CustomRequestHelper.REGEXP_CMD.match(msg):
            fin_cmd = msg.find("|")
            code_cmd = msg[5:fin_cmd]
            fin_args = msg.find("]")
            args_cmd = msg[fin_cmd + 1 : fin_args]
            dict_args = dict()
            if len(args_cmd) > 0:
                list_kv = args_cmd.split("&")
                for elt in list_kv:
                    k, v = elt.split("=")
                    dict_args[k] = v
            fin_msg = msg[fin_args + 1 :]
            return code_cmd, dict_args, fin_msg
        else:
            return None, None, msg

    split_cmd_and_msg = classmethod(split_cmd_and_msg)

    #-----> Envoi
    def send_indexed_request(cls, sock, bytesblocs):
        """
        Prend en charge l'envoi via la socket sock de la liste de blocs binaires 
        listbyteblocs.
        
        Args:
            bytesblocs: liste de blocs binaires générée par 
                CustomRequestHelper.create_indexed_request
        
        Retourne None ou la première erreur survenue sinon (dès cette première
        erreur le process d'envoi des blocs a été interrompu).
        """
        error = CustomRequestHelper._send_request_parts(sock, bytesblocs)
        return error

    send_indexed_request = classmethod(send_indexed_request)

    def create_indexed_request(cls, msg, uid):
        """
        Indexe, découpe au besoin la chaine msg envoyée par l'objet d'id uid.
        
        Return:
            msglen: clef de comparaison pour AR (longueur du message), 
            list: une liste de blocs convertis en bytes.
        
        """
        msglen, list2send = CustomRequestHelper._split_and_index_msg(msg, uid)
        return msglen, list2send

    create_indexed_request = classmethod(create_indexed_request)

    def _split_and_index_msg(cls, msg, uniqueid, buffsize=None):
        """
        Découpe et indexe le message afin d'envoyer n requètes (ou blocs) de taille 
        buffsize max, avec
        
        * pour prefix avant entête CustomRequestHelper.BLOC_PREFIX soit ''<#bp#>''
        * pour entête : ``"|"+n°req+"/"+nb req+"|"+uniqueid+"|"+len(msg)+"|"``
        * suivi de l'extrait de message du bloc
        * pour suffixe en fin de bloc CustomRequestHelper.BLOC_SUFFIX soit ''<#bs#>''
        
        Args:
            msg (str) : chaine de caractère (utf-8)
            uniqueid (str) : chaine (utf-8)
            buffsize (int) : taille de buffer personnalisée, par défaut 
                CustomRequestHelper.BUFFERSIZE
            
        Returns:
            msglen: longueur du message (nb chars)
            list: Retourne la liste des blocs binaires indéxés à envoyer
        
        Raise:
            TypeError: si msg n'est pas une str
        
        Exemple :
        
        * message aléatoire de 1641 caractères envoyé par un client en 2 requètes / blocs pour une taille de 
          buffer de 1024 (on suppose msg fait de caractères latin-1 codés sur un byte/char) :
          ``<#bp#>|1/2|uid0|1641|fcWApZt]s[...]<#bs#>  (bloc 1 : tel que len(bytes(bloc 1, "utf-8"))=buffsize=1024)``
          ``<#bp#>|2/2|uid0|1641|ycmJ@q1O[...]<#bs#>   (bloc 2 : du bloc précédent jusqu'à la fin du msg)``
        * message de confirmation de 4 caractères (réception de 1641 chars) retourné par le serveur en une requète :
          ``<#bp#>|1/1|svr|4|1641<#bs#>``
            
        """
        if buffsize == None:
            buffsize = CustomRequestHelper.BUFFERSIZE
        if type(msg) != str:
            error = TypeError(
                "_split_and_index_msg expect a str value for msg argument."
            )
            raise (error)
        msglen = len(msg)
        mybuffsize = buffsize
        # vue binaire du message :
        b_msg = bytes(msg, "utf-8")
        mv_msg = memoryview(b_msg)
        # nombre de bytes du message binaire
        msg_bytes = mv_msg.nbytes
        # 1- Evaluation du nombre de blocs à envoyer :
        nb_blocs = math.ceil(msg_bytes / mybuffsize)
        # header générique :
        headerprefix = CustomRequestHelper.BLOC_PREFIX
        headergen = "|" + str(uniqueid) + "|" + str(msglen) + "|"
        # footer / suffixe de fin de bloc :
        footer = CustomRequestHelper.BLOC_SUFFIX
        b_footer = bytes(footer, "utf-8")
        footer_bytes = len(b_footer)
        # recherche du nombre de blocs nécessaores
        finded = False
        while not finded:
            header_list = list()
            header_bytes = 0
            # liste des entêtes de blocs :
            for i in range(0, nb_blocs):
                headerspec = "|" + str(i + 1) + "/" + str(nb_blocs)
                header = headerprefix + headerspec + headergen
                b_header = bytes(header, "utf-8")
                header_list.append(b_header)
                header_bytes += len(b_header)
            # quantité totale d'info en bytes
            total_bytes = msg_bytes + header_bytes + nb_blocs * footer_bytes
            # test
            if total_bytes <= nb_blocs * mybuffsize:
                finded = True
            else:
                # nombre de blocs insuffisant
                nb_blocs += 1
        # 2- Constitution de la liste de blocs binaires à envoyer
        returnlist = list()
        start = 0
        for b_header in header_list:
            fix_len = len(b_header) + footer_bytes
            maxstop = mybuffsize - fix_len
            stop = min(start + maxstop, msg_bytes)
            b_sub_msg = b_msg[start:stop]
            start = stop
            b_sub_block = b"".join([b_header, b_sub_msg, b_footer])
            returnlist.append(b_sub_block)
        return msglen, returnlist

    _split_and_index_msg = classmethod(_split_and_index_msg)

    def _send_request_parts(cls, sock, list2send):
        """
        Envoie via la socket sock les requètes (blocs binaires) préparé(e)s par 
        _split_and_index_msg dans la liste list2send
        
        Retourne None ou la première erreur survenue sinon (dès cette première
        erreur le process d'envoi des blocs a été interrompu)
        """
        error = None
        i = 0
        while i < len(list2send):
            try:
                bloc = list2send[i]
                sock.send(bloc)
            except OSError as e:
                # rq : python 3.3 IOError devient OSError
                # optimisation : on arrête dès la première erreur
                error = e
                break
            i += 1
        return error

    _send_request_parts = classmethod(_send_request_parts)

    #-----> Réception
    def receive_indexed_request(cls, sock):
        """
        Prend en charge la réception sur la socket sock d'une série de requètes indéxées
        associées à un message.
        
        Retourne le dict généré par CustomRequestHelper.create_dict_receive 
        """
        listeparsedict = list()  # liste de blocs parsés
        listemixedblocs = list()  # liste de blocs partiels
        listetoparse = list()  # liste de blocs partiels ré aggrégés à parser
        errors = list()
        requestdone = False
        requestvalide = True
        dictdatas = None
        while not requestdone:
            if len(listetoparse) > 0:
                # on prend le premier bloc reconstitué
                data = listetoparse.pop(0)
            else:
                # on récupère au max CustomRequestHelper.BUFFERSIZE bytes de données
                data, error = CustomRequestHelper._receive_buffer_block(sock)
                if error != None:
                    errors.append(error)
            # on tente de parser :
            valide, parsedict, mixedblocs = CustomRequestHelper._parse_request_part(
                data
            )
            # en fonction du retour :
            if not valide:
                # erreur bloquante : on stop
                error = ParseDataError(
                    "CustomTCP._parse_request_part : invalid bloc of data"
                )
                errors.append(error)
                requestvalide = False
            elif parsedict != None:
                # un bloc complet de données a été parsé
                parseerrors = parsedict["parseerrors"]
                if parseerrors:
                    requestvalide = False
                    errors += parseerrors
                else:
                    listeparsedict.append(parsedict)
                    (
                        requestdone,
                        dictdatas,
                    ) = CustomRequestHelper._analyse_list_parsedict(listeparsedict)
            elif mixedblocs != None:
                # des données de bloc mélangées ont été reçues
                (
                    valide,
                    blocs_to_parse,
                    listemixedblocs,
                ) = CustomRequestHelper._analyse_list_mixedblocs(
                    listemixedblocs, mixedblocs
                )
                if not valide:
                    requestvalide = False
                    error = ParseDataError(
                        "CustomTCP._analyse_list_mixedblocs : can't reconstruct blocs"
                    )
                    errors.append(error)
                else:
                    listetoparse += blocs_to_parse
            # Test d'arrêt en cas d'erreur :
            if not requestvalide:
                requestdone = True
        # dict de retour par défaut :
        if dictdatas == None:
            dictdatas = CustomRequestHelper._analyse_list_parsedict(listeparsedict)[1]
            requestvalide = False
        dictdatas["requestvalide"] = requestvalide
        dictdatas["sock"] = sock
        dictdatas["errors"] = errors
        # Retour
        return dictdatas

    receive_indexed_request = classmethod(receive_indexed_request)

    def create_dict_receive(cls):
        """
        Génère le dictionnaire non renseigné destiné à retenir les données 
        d'une requête reçue.
        
        ::
            
            dictreceive = {
                    "requestvalide": True,    # validité de la requête
                    "AR_sended":False,        # accusé de réception envoyé sans erreur
                    "sock": None,             # socket destinataire
                    "uid": None               # uid du destinataire
                    "msg": None,              # message reçu
                    "listeparsedict": None,   # liste de blocs parsés (dicts)
                    "code_cmd": None,         # code commande
                    "dict_args": None,        # ensemble de clefs/valeurs sous forme de dict
                    "msg_except_cmd": None,   # message sans code de commande ni uid de message
                    "msguid": None,           # uid de message
                    "errors": None,           # liste d'erreurs
                    "complete": False,        # indicateur de complétion
                    }
        """
        dictreceive = {
            "requestvalide": True,
            "AR_sended": False,
            "sock": None,
            "uid": None,
            "msg": None,
            "listeparsedict": None,
            "code_cmd": None,
            "dict_args": None,
            "msg_except_cmd": None,
            "msguid": None,
            "errors": None,
            "complete": False,
        }
        return dictreceive

    create_dict_receive = classmethod(create_dict_receive)

    def _analyse_list_mixedblocs(cls, bloclist, newbloclist):
        """
        Analyse une nouvelle liste de blocs mélangés
        
        Args
            bloclist (list): liste de blocs partiels déja identifiés
            newbloclist (list): nouvelle liste de blocs partiels retournée par 
                CustomRequestHelper._parse_request_part
            
        Return:
            valide (bool): indique si les données sont cohérentes
            bloc_to_parse (list): liste de blocs complets à parser
            mixedblocs (list): liste de blocs incomplets
        """
        valide = True
        bloc_to_parse = list()
        mixedblocs = list()
        # prefix et suffixe
        bp = CustomRequestHelper.BLOC_PREFIX
        bs = CustomRequestHelper.BLOC_SUFFIX
        # peut on compléter le dernier bloc partiel de bloclist ?
        prevbloc = None
        if len(bloclist) > 1:
            # il ne devrait rester au maximum qu'un bloc partiel
            valide = False
        elif len(bloclist) == 1:
            prevbloc = bloclist[-1]
            # il doit avoir un prefix en entête mais pas de suffixe
            prev_prefix = prevbloc.startswith(bp)
            prev_no_suffix = prevbloc.count(bs) == 0
            prev_valide = prev_prefix and prev_no_suffix
            if not prev_valide:
                valide = False
            else:
                # bloc valide,
                if len(newbloclist) > 0:
                    nextbloc = newbloclist[0]
                    next_suffix = nextbloc.endswith(bs)
                    next_no_prefix = nextbloc.count(bp) == 0
                    next_valide = next_suffix and next_no_prefix
                    if next_valide:
                        # on retire les deux blocs des listes
                        prevbloc = bloclist.pop(-1)
                        nextbloc = newbloclist.pop(0)
                        # on ajoute leur concaténation à la liste à parser
                        bloc_to_parse.append(prevbloc + nextbloc)
        # existe t'il d'autres blocs complets dans newbloclist ?
        for bloc in newbloclist:
            has_prefix = bloc.startswith(bp)
            has_suffix = bloc.endswith(bs)
            if has_prefix and has_suffix:
                bloc_to_parse.append(bloc)
            else:
                mixedblocs.append(bloc)
        # retour :
        return valide, bloc_to_parse, mixedblocs

    _analyse_list_mixedblocs = classmethod(_analyse_list_mixedblocs)

    def _analyse_list_parsedict(cls, listeparsedict):
        """
        Analyse une liste de dict de parsing de blocs de requête
        
        Args:
            listeparsedict (list): liste de dict de parsing sans erreur générés 
                par CustomRequestHelper._parse_request_part
        
        Return :
            complete(bool): indique si la requête est complète
            dictdatas (dict): le dict retourné par CustomRequestHelper.receive_indexed_request
        """
        complete = False
        dictdatas = CustomRequestHelper.create_dict_receive()
        dictdatas["listeparsedict"] = listeparsedict
        if len(listeparsedict) > 0:
            # analyse du premier bloc :
            parsedict = listeparsedict[0]
            nbr = int(parsedict["nbr"])  # nombre de blocs de la requête complète
            uniqueid = parsedict["uid"]
            if uniqueid == "None":
                uniqueid = None
            dictdatas["uid"] = uniqueid
            # requête reçue complètement ?
            if not (nbr > 1 and len(listeparsedict) < nbr):
                complete = True
            # si oui on reconstitue le message :
            if complete:
                sorted(listeparsedict, key=lambda bloc: int(bloc["numr"]))
                msg = ""
                for bloc in listeparsedict:
                    msg += bloc["msgpart"]
                # Traitement des commandes spéciales de la forme "[cmd:CODE_CMD|var=val&...]"
                code_cmd, dict_args, fin_msg = CustomRequestHelper.split_cmd_and_msg(
                    msg
                )
                # Extraction de l'id unique de message et du message original :
                msguid, fin_msg = CustomRequestHelper.split_unique_mark_and_msg(fin_msg)
                # données à retourner :
                dictdatas["msg"] = msg
                dictdatas["code_cmd"] = code_cmd
                dictdatas["dict_args"] = dict_args
                dictdatas["msg_except_cmd"] = fin_msg
                dictdatas["msguid"] = msguid
                dictdatas["complete"] = complete
        # retour :
        return complete, dictdatas

    _analyse_list_parsedict = classmethod(_analyse_list_parsedict)

    def _receive_buffer_block(cls, sock):
        """
        Traite la récepion d'un bloc de données de taille CustomRequestHelper.BUFFERSIZE.
        
        Retourne le tupple : data, error avec

        * data (str) : données converties en str
        * error (OSError, UnicodeDecodeError) : erreur éventuelle survenue   
        """
        bytesdata = data = error = None
        # réception :
        try:
            bytesdata = sock.recv(CustomRequestHelper.BUFFERSIZE)
        except OSError as e:
            # rq : python 3.3 socket.error devient OSError
            error = e
        # conversion :
        if error == None:
            try:
                data = str(bytesdata, "utf8")
            except UnicodeDecodeError as e:
                error = e
        return data, error

    _receive_buffer_block = classmethod(_receive_buffer_block)

    def _parse_request_part(cls, requestpart):
        """
        Traite une partie (ou bloc) de requête générée par _split_and_index_msg
        
        Retourne le tupple : valide, parsedict, mixedblocs
        
            - valide (bool): False si la données est nulle
            - parsedict (dict): les infos du bloc s'il est complet ou None
            - blocslist (list): une liste de blocs ou parties de blocs 
                (avec prefix et ou suffix) ou None
        
        Avec parsedict:    {parseerrors:bool,
                            numr:n°requête, 
                            nbr:nb requêtes, 
                            uid:uniqueid, 
                            msglen:totalmsglen, 
                            msgpart:msgpart}
        """
        valide = False
        parsedict = None
        blocslist = None
        if requestpart not in [None, ""]:
            # Des données sont exploitables
            valide = True
            # En fonction du nombre et des positions des prefix et suffix :
            bp = CustomRequestHelper.BLOC_PREFIX
            bs = CustomRequestHelper.BLOC_SUFFIX
            # nombre d'occurences des prefix et suffix :
            prefix_count = requestpart.count(bp)
            suffix_count = requestpart.count(bs)
            # positions attendues :
            has_prefix = requestpart.startswith(bp)
            has_suffix = requestpart.endswith(bs)
            # Cas idéal :
            if prefix_count == suffix_count == 1 and has_prefix and has_suffix:
                # Bloc unique complet :
                # réduction du bloc :
                requestpart = requestpart[len(bp) : -len(bs)]
                #  recherche de données
                numr = nbr = uniqueid = msglen = msgpart = None
                parseerrors = False
                nbpipe = requestpart.count("|")
                if nbpipe < 4 or requestpart[0] != "|":
                    parseerrors = True
                elif nbpipe >= 4:
                    # On ne considère que les 4 premiers |
                    i = 0
                    start = 1
                    liste = list()
                    while i < 3:
                        stop = int(requestpart.find("|", start + 1))
                        liste.append(requestpart[start:stop])
                        start = int(stop + 1)
                        i += 1
                    liste.append(requestpart[stop + 1 :])
                    liste2 = str(liste[0]).rsplit("/")
                    if len(liste2) != 2:
                        # données invalides (requètes non numérotées)
                        parseerrors = True
                    else:
                        numr = int(liste2[0])
                        nbr = int(liste2[1])
                    uniqueid = liste[1]
                    msglen = liste[2]
                    msgpart = liste[3]
                # le dict d'infos du bloc :
                parsedict = {
                    "parseerrors": parseerrors,
                    "numr": numr,
                    "nbr": nbr,
                    "uid": uniqueid,
                    "msglen": msglen,
                    "msgpart": msgpart,
                }
            else:
                # Bloc incomplet ou données partielles de plusieurs blocs :
                # On sépare les données associées aux différents blocs
                mixedblocs = list()
                done = False
                while not done:
                    prefix_count = requestpart.count(bp)
                    suffix_count = requestpart.count(bs)
                    if prefix_count == 0 and suffix_count == 0:
                        # dernière donnée de bloc
                        mixedblocs.append(requestpart)
                        done = True
                    else:
                        prefix_index = requestpart.find(bp)
                        suffix_index = requestpart.find(bs)
                        if prefix_count * suffix_count == 0:
                            # 2 dernières données de bloc
                            if prefix_index > -1:
                                lastblocs = requestpart.split(bp)
                                lastblocs.insert(1, bp)
                            else:
                                lastblocs = requestpart.split(bs)
                                lastblocs.insert(1, bs)
                            mixedblocs += lastblocs
                            done = True
                        elif prefix_index < suffix_index:
                            # data + prefix + mixed
                            seplist = requestpart.split(bp, maxsplit=1)
                            mixedblocs += [seplist[0], bp]
                            requestpart = seplist[1]
                        else:
                            # data + suffix + mixed
                            seplist = requestpart.split(bs, maxsplit=1)
                            mixedblocs += [seplist[0], bs]
                            requestpart = seplist[1]
                # on enlève les éventuelles chaines vides
                mixedblocs = [b for b in mixedblocs if b != ""]
                # on reconstitue les blocs complets : bp, data, bs -> bp + data + bs
                blocslist = list()
                newbloc = ""
                for bloc in mixedblocs:
                    newbloc += bloc
                    if bloc == bs:
                        blocslist.append(str(newbloc))
                        newbloc = ""
                if len(newbloc) > 0:
                    blocslist.append(str(newbloc))
        # retour :
        return valide, parsedict, blocslist

    _parse_request_part = classmethod(_parse_request_part)

    #-----> Gestion des ERRNO réseau
    def is_error_fatal(cls, error):
        """
        Indique si l'erreur reçue est fatale ou bien si l'on peut ré essayer 
        l'action tentée.
        
        Args:
            error (OSError ou autre)
            
        Returns:
            boolean: False par défaut
        """
        fatal = False
        if isinstance(error, OSError):
            key = error.errno
            if key in CustomRequestHelper.ERRNO_DICT:
                fatal = CustomRequestHelper.ERRNO_DICT[key]["fatal"]
        return fatal

    is_error_fatal = classmethod(is_error_fatal)

    #-----> Tests
    def create_test_msg(cls, confirmrecept=True, latin1=True):
        """
        Crée un message de test d'une longueur > buffsize pour forcer l'envoi
        de plusieurs blocs
        
        Args:
            confirmrecept (bool): ajoute le code d'accusé de réception
            latin1 (bool): limite les caractères à la plage latin-1, plage unicode 
                complète sinon
        
        Rq: les chars latin-1 sont codés 1 byte / char, les chars unicodes peuvent 
        aller jusqu'à 4 bytes / char mais peuvent lever une exception lors d'un print 
        (surrogates).
        """
        if latin1 == True:
            # caractères latin+1 uniquement
            char_range = range(48, 122)
        else:
            # plage unicode complète
            char_range = range(0, 1114111)
        nbmin = CustomRequestHelper.BUFFERSIZE + 1
        nbmax = random.randint(1, 10) * nbmin
        list_int = random.choices(char_range, k=random.randint(nbmin, nbmax))
        list_letters = [chr(n) for n in list_int]
        msg = "".join(list_letters)
        if confirmrecept:
            entete = CustomRequestHelper.create_cmd_msg(
                CustomRequestHelper.NEED_CONFIRMATION
            )
            msg = entete + msg
        return msg

    create_test_msg = classmethod(create_test_msg)


#-----> Client "from scratch"
class CustomTCPThreadedClient(appcomp.NETComp):
    """
    **Objet client** du serveur CustomTCPServerContainer
    
    Le client trace les données de connection vers le serveur. Il enregistre
    également les dernières erreurs survenues lors des connections, envois et réceptions.
    
    A chaque occurence d'une action d'envoi ou réception, le client envoie au composant
    business (appli métier), un dict d'infos réseau via la méthode `dispatch_network_infos`.

    **Détection des problèmes de connections :**
    
    * client: analyse des erreurs en fonction de leur degré de gravité (même principe que 
      le serveur frontal).
    * serveur: analyse des logs d'envoi et réception (fonction des dernières erreurs et 
      du nombre total d'erreurs).
    
    Lorsque le statut du serveur passe à `CustomRequestHelper.STATUS_UNDEFINED` on le considère
    comme probablement déconnecté. Dans ce cas les prochaines tentatives d'envoi se limiteront 
    à un essai. Charge à l'appli métier de décider de considérer définitivement le serveur comme 
    déconnecté.
    """

    # méthodes :
    def __init__(self, server_address, externalhandler=None, auto_connect=True):
        """
        Constructeur
        
        Args:
            server_address (tuple)
            externalhandler (function): fonction externe appelée à l'issue du traitement 
                d'une requète entrante
            auto_connect (Boolean): connection automatique à l'initialisation
        
        Rq: externalhandler est une option, utiliser de préférence le mécanisme par défaut 
        de Queues hérité de app_components
        """
        # Init superclasse appcomp.NETComp :
        appcomp.NETComp.__init__(self)
        # handler externe (méthode éxécutable) optionnel (communication native avec les 
        # autres composants via un mécanisme de gestion automatique de Queues multi canaux)
        self.externalhandler = externalhandler
        # unique id de client :
        self._uid = None
        # socket entrante (read) :
        self.socket_read = None
        self.host_read = None
        self.port_read = None
        self.binded_to_read = False
        # thread de réception :
        self.thread_read_active = False
        self.thread_read = None
        # nombre de threads internes :
        # thread_read ne peut être démarré qu'en cours de connection, on le "masque" donc
        # au process générique de APPComp. Le fait qu'il ne soit pas joint ne pose pas de problèmes.
        self.set_childthreads_count(0)
        # socket sortante (write) :
        # Rq le thread write est en fait le thread principal de ce composant,
        # soit self.own_thread (voir appcomp.ThreadableComp)
        self.server_host = None
        self.server_port = None
        self.socket_write = None
        self.connected_to_server = False
        self.connection_status = CustomRequestHelper.STATUS_DISCONNECTED
        self.refused_by_server = False
        self.server_status = None
        # dict d'infos réseau :
        self.netdict = None
        self._init_net_dict()
        # liste d'ids uniques de messages reçus :
        self._received_msguids = list()
        # indicateur d'activité du thread principal du composant
        self.thread_write_active = False
        # Adresse :
        if server_address != None:
            self.server_host = server_address[0]
            self.server_port = server_address[1]
        # lance le process de connection :
        if auto_connect:
            self.connect(None)

    def _init_net_dict(self):
        """
        Initialise le dict de logs.
        """
        self.netdict = dict()
        self.netdict["server"] = {
            "address": None,
            "connected": False,
            "refused": False,
            "connection_status": self.connection_status,
            "server_status": self.server_status,
        }
        self.netdict["client"] = {"read_address": None, "binded": False}
        self.netdict["errors"] = {
            "last_connect_send_error": None,
            "connect_send_error_count": 0,
            "last_send_error": None,
            "send_error_count": 0,
            "last_connect_receive_error": None,
            "connect_receive_error_count": 0,
            "last_receive_error": None,
            "receive_error_count": 0,
            "uncomplete_received_count": 0,
            "unit_sended_request_count": 0,
            "AR_sended_request_count": 0,
            "total_sended_request_count": 0,
            "unit_received_request_count": 0,
            "AR_received_request_count": 0,
            "total_received_request_count": 0,
        }

    #-----> uid
    def _set_uid(self, val):
        if isinstance(val, str):
            self._uid = val

    def _get_uid(self):
        return self._uid

    uid = property(
        _get_uid, _set_uid
    )  #: identifiant unique du client (défini par le serveur)

    #-----> Surcharge de appcomp.NETComp
    def on_component_thread_started(self):
        """
        Pseudo événement : indique que le thread principal du composant est démarré
        (Méthode de appcomp.ThreadableComp)
        """
        self.thread_write_active = True

    def sendFromExchangeObject(self, exobj):
        """
        Méthode d'envoi à partir des données comprises dans l'objet NETExchangeObject
        
        Args:
            exobj (NETExchangeObject): objet d'échange 
        """
        dictargs = exobj.dictargs
        msg = dictargs["msg"]
        confirmrecept = True
        if "confirmrecept" in dictargs.keys():
            confirmrecept = dictargs["confirmrecept"]
        self.send(msg, confirmrecept)

    def set_address(self, exobj):
        """
        Affecte l'adresse d'écoute du serveur / adresse d'écriture du client.
        
        Args:
            exobj (NETExchangeObject): objet d'échange avec 
                exobj.dictargs={"host":, "port":}
        """
        dictargs = exobj.dictargs
        host = port = None
        if "host" in dictargs.keys() and "port" in dictargs.keys():
            host = dictargs["host"]
            if isinstance(dictargs["port"], int):
                port = int(dictargs["port"])
        if host != None and port != None:
            self.server_host = host
            self.server_port = port

    def connect(self, exobj):
        """
        Ordre de connection à l'adresse pré définie ou à l'adresse éventuellement
        indiquée dans exobj.dictargs={"host":, "port":}
        
        Args:
            exobj (NETExchangeObject): objet d'échange 
        """
        # En fonction du statut :
        if self.connection_status == CustomRequestHelper.STATUS_CONNECTED:
            return
        # Re définition éventuelle de l'adresse :
        if exobj != None:
            self.set_address(exobj)
        # Connexion :
        self._start_write_process()

    def disconnect(self, exobj):
        """
        Ordre de déconnexion.
        
        Args:
            exobj (NETExchangeObject): objet d'échange 
        """
        # envoi du message de déconnection au serveur :
        if self.server_status == CustomRequestHelper.STATUS_CONNECTED:
            msg = CustomRequestHelper.create_cmd_msg(
                CustomRequestHelper.CLIENT_DISCONNECTED
            )
            self.send(msg, confirmrecept=False)
        # Nettoyage :
        self._close_internal()
        # Etat :
        self.connection_status = CustomRequestHelper.STATUS_DISCONNECTED
        # Informe le composant business:
        msg = "Le client est déconnecté."
        self.dispatch_network_status(msg)

    def net_shutdown(self, exobj):
        """
        Ordre de clôture du réseau.
        
        Rq : on ne clôt pas le process de gestion de tâches, le client est
        complètement ré initialisé, mais peut être redémarré.
        
        Args:
            exobj (NETExchangeObject): objet d'échange 
        """
        self._net_shutdown_internal()

    def shutdown(self):
        """
        Clôture définitive du composant propagé par APPComp.
        """
        # arrêt / ré initialisation du client :
        self._net_shutdown_internal()
        # générique : arrêt du process d'écoute des tâches
        appcomp.NETComp.shutdown(self)

    def _net_shutdown_internal(self):
        """
        Code générque de clôture.
        """
        # envoi du message d'arrêt au serveur :
        if self.server_status == CustomRequestHelper.STATUS_CONNECTED:
            msg = CustomRequestHelper.create_cmd_msg(
                CustomRequestHelper.CLIENT_SHUTDOWN
            )
            self.send(msg, confirmrecept=False)
        # Etat :
        self.connection_status = CustomRequestHelper.STATUS_SHUTDOWN
        # Informe le composant business:
        msg = "Le client est arrêté."
        self.dispatch_network_status(msg)
        # Nettoyage :
        self._close_internal()
        # Ré initialisation :
        self.uid = None
        self.refused_by_server = False
        self._init_net_dict()
        self.server_status = None

    #-----> Méthodes internes au framework
    #-----> Envoi de message
    def send(self, msg, confirmrecept=True):
        """
        Envoie msg au serveur avec accusé de réception par défaut.
        
        Args:
            msg (str): message à envoyer
            confirmrecept (boolean): avec accusé de réception?
        """
        # 1- Préparation du message
        # identifiant unique de message :
        msg = CustomRequestHelper.mark_msg_as_unique(self, msg)
        # AR :
        msg2send = msg
        if confirmrecept:
            msg2send = CustomRequestHelper.prefix_msg_with_code(
                msg2send, CustomRequestHelper.NEED_CONFIRMATION
            )
        # 2- envoi :
        done = self._send_msg(msg2send)
        # 3- Retour
        # Etat réseau -> application
        self.dispatch_network_infos()
        # signalement d'erreur :
        if not done:
            # retour systématique quelques soient les statuts de connection
            logargs = {
                "msg": msg,
                "confirmrecept": confirmrecept,
            }
            exobj = appcomp.NETExchangeObject(
                appcomp.NETExchangeObject.SEND_ERROR, logargs
            )
            self.sendTask(exobj)

    #-----> Clôture des sockets et arrêt des threads
    def _close_internal(self):
        """
        Méthode de fermeture (cloture des sockets) appelée lors de la 
        fermeture du serveur.
        """
        if self.thread_read_active:
            self.thread_read_active = False
            try:
                self.socket_read.shutdown(socket.SHUT_RDWR)
                self.socket_read.close()
            except OSError as e:
                self._log_connect_receive(e)
        if self.thread_write_active:
            self.thread_write_active = False
            try:
                self.socket_write.shutdown(socket.SHUT_RDWR)
                self.socket_write.close()
            except OSError as e:
                self._log_connect_send(e)
        self.connected_to_server = False
        self.connection_status = CustomRequestHelper.STATUS_DISCONNECTED
        self.binded_to_read = False

    #-----> Initialisation et gestion des envois de requètes vers le serveur
    def _start_write_process(self):
        """
        Initie le process d'écriture.
        """
        # connection initiale :
        self._connect_to_write()

    def _connect_to_write(self):
        """
        Connecte ou reconnecte (avec un port différent) socket_write au serveur.
        """
        # Fermeture "propre" :
        if self.socket_write != None:
            try:
                self.socket_write.shutdown(socket.SHUT_RDWR)
                self.socket_write.close()
            except OSError as e:
                self._log_connect_send(e)
        # (re) création :
        self.socket_write = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_write.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Boucle de tentatives de connection :
        connected = False
        connection_count = 0
        while (
            not connected
            and connection_count < CustomRequestHelper.CONNECTION_MAX_COUNT
        ):
            try:
                self.socket_write.connect((self.server_host, self.server_port))
            except OSError as e:
                self._log_connect_send(e)
                self.connected_to_server = False
                self.connection_status = CustomRequestHelper.STATUS_ERROR_CONNECTION
                self.server_status = CustomRequestHelper.STATUS_ERROR_CONNECTION
                connection_count += 1
                time.sleep(CustomRequestHelper.RECONNECTION_DELAY)
            else:
                connected = True
                self._log_connect_send(None)
                self.server_status = CustomRequestHelper.STATUS_CONNECTED
                self.connected_to_server = True
                self.connection_status = CustomRequestHelper.STATUS_CONNECTED
                # Informe le composant business:
                msg = "Le client est connecté."
                self.dispatch_network_status(msg)
                if self.uid == None:
                    self._ask_server_for_uid()
                elif self.thread_read_active == False:
                    # on essaye de lancer à nouveau le process d'écoute :
                    self._start_read_process()
        # Tentatives infructueuses on transmet l'info :
        if not connected:
            # Remontée de l'erreur
            msg = (
                "Impossible de se connecter au serveur à l'adresse : "
                + str(self.server_host)
                + ":"
                + str(self.server_port)
            )
            self.dispatch_network_status(msg)

    def _ask_server_for_uid(self, count=0):
        """
        Demande au serveur d'affecter à ce client un uniqueId.
        """
        # marqueur d'erreur :
        has_error = False
        # 1- envoi d'une requète d'identification unique
        msg = CustomRequestHelper.create_cmd_msg(CustomRequestHelper.ASK_FOR_UID)
        list2send = CustomRequestHelper.create_indexed_request(msg, self.uid)[1]
        error = CustomRequestHelper.send_indexed_request(self.socket_write, list2send)
        self._log_sended_request_count(count == 0, True)
        if error != None:
            # l'envoi a échoué :
            self._log_send(error)
            has_error = True
        else:
            # envoi réussi
            self._log_send(None)
        # 2- Réception de la réponse du serveur
        if not has_error:
            dictreceive = CustomRequestHelper.receive_indexed_request(self.socket_write)
            errors = dictreceive["errors"]
            complete = dictreceive["complete"]
            if len(errors) > 0:
                #  réponse invalide
                error = errors[-1]
                self._log_receive(error, complete)
                has_error = True
            else:
                # réponse valide
                self._log_receive(None, complete)
                reponse = dictreceive["msg_except_cmd"]
                code_cmd = dictreceive["code_cmd"]
                msguid = dictreceive["msguid"]
                self._log_received_request_count(msguid, False)
                # Traitement de la réponse du serveur :
                if code_cmd == CustomRequestHelper.CONNECTION_REFUSED:
                    # connection refusée par le serveur :
                    self.dispatch_to_external_handler(
                        {"uid": None, "netcode": CustomRequestHelper.CONNECTION_REFUSED}
                    )
                    self.connected_to_server = False
                    self.connection_status = CustomRequestHelper.STATUS_DISCONNECTED
                    self.refused_by_server = True
                    # Infos réseau -> application
                    self.dispatch_network_infos()
                else:
                    self.refused_by_server = False
                    if reponse != None:
                        self.uid = reponse
                        # appel du handler externe :
                        self.dispatch_to_external_handler(
                            {
                                "uid": self.uid,
                                "netcode": CustomRequestHelper.UID_SET_BY_SERVER,
                            }
                        )
                        # on défini le port d'écoute initial :
                        self._create_read_address()
                        # on essaye de lancer le process d'écoute immédiatement :
                        self._start_read_process()
        # 3- Gestion d'erreur
        if has_error:
            # on retente dans la limite de CustomRequestHelper.SEND_MAX_COUNT
            # sans mesurer la gravité de l'erreur
            count += 1
            if count < CustomRequestHelper.SEND_MAX_COUNT:
                time.sleep(CustomRequestHelper.RESEND_DELAY)
                self._ask_server_for_uid(count=count)

    def _send_msg(self, msg, count=0):
        """
        Envoi d'un message au serveur via la socket socket_write.
        
        Return:
            done (bool): indicateur de réussite
        """
        with self.socket_write:
            # re-connection obligatoire (le serveur clôture systématiquement les sockets)
            self._connect_to_write()
            # en cas d'échec
            if not self.connected_to_server:
                return False
            # gestion de l'AR :
            confirmrecept = False
            code_cmd = CustomRequestHelper.split_cmd_and_msg(msg)[0]
            if code_cmd in [
                CustomRequestHelper.NEED_CONFIRMATION,
                CustomRequestHelper.SET_CLIENT_READ_INFOS,
                CustomRequestHelper.CLIENT_CONNECTED,
                CustomRequestHelper.CLIENT_DISCONNECTED,
                CustomRequestHelper.CLIENT_SHUTDOWN,
            ]:
                confirmrecept = True
            # nombre de tentatives :
            maxcount = CustomRequestHelper.SEND_MAX_COUNT
            if code_cmd == CustomRequestHelper.SET_CLIENT_READ_INFOS:
                maxcount *= 5
            # log quantitatif envoi :
            unit = count == 0
            self._log_sended_request_count(unit, confirmrecept)
            # marqueur d'erreur :
            has_error = False
            # 1- Envoi de la requête :
            msglen, list2send = CustomRequestHelper.create_indexed_request(
                msg, self.uid
            )
            error = CustomRequestHelper.send_indexed_request(
                self.socket_write, list2send
            )
            if error != None:
                # l'envoi a échoué :
                self._log_send(error)
                has_error = True
            else:
                # envoi réussi
                self._log_send(None)
            # 2- test de réception :
            if confirmrecept and not has_error:
                dictreceive = CustomRequestHelper.receive_indexed_request(
                    self.socket_write
                )
                errors = dictreceive["errors"]
                complete = dictreceive["complete"]
                if len(errors) > 0:
                    #  réponse invalide
                    error = errors[-1]
                    self._log_receive(error, complete)
                    has_error = True
                else:
                    # réponse valide
                    self._log_receive(None, complete)
                    bytesreceived = dictreceive["msg_except_cmd"]
                    code_cmd = dictreceive["code_cmd"]
                    if code_cmd == CustomRequestHelper.CONNECTION_REFUSED:
                        self.connection_status = CustomRequestHelper.STATUS_REJECTED
                        msg = "Connection refusée par le serveur."
                        self.dispatch_network_status(msg)
                        return
                    elif (
                        code_cmd != CustomRequestHelper.CONFIRM_RECEPTION
                        or bytesreceived == None
                        or int(bytesreceived) != msglen
                    ):
                        # réception non confirmée
                        has_error = True
                    else:
                        # log quantitatif réception :
                        msguid = dictreceive["msguid"]
                        self._log_received_request_count(msguid, False)
            # 3- Gestion d'erreur
            if has_error:
                # Est ce raisonnable de ré essayer ?
                if error != None:
                    fatal_error = CustomRequestHelper.is_error_fatal(error)
                    if fatal_error:
                        # inutile : on arrête
                        return False
                # erreur lors de l'envoi ou de la réception de l'accusé de réception
                count += 1
                if count < maxcount:
                    time.sleep(CustomRequestHelper.RESEND_DELAY)
                    return self._send_msg(msg, count)
            # 4- retour final :
            return not has_error

    #-----> Gestion de l'écoute des requètes envoyées par le serveur
    def _start_read_process(self):
        """
        Après affectation de l'uid, met en place le processus d'écoute du serveur sur 
        socket_read.
        """
        self.socket_read = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_read.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Boucle de tentatives de connection :
        connection_count = 0
        connected = False
        while (
            not connected
            and connection_count < CustomRequestHelper.CONNECTION_MAX_COUNT
        ):
            # Si self.port_read est occupé on prend le suivant etc... :
            self.port_read = self.port_read + connection_count
            try:
                self.socket_read.bind((self.host_read, self.port_read))
            except OSError as e:
                # la socket est occupée, on relance le process en incrémentant le port :
                self.binded_to_read = False
                self._log_connect_receive(e)
                connection_count += 1
                time.sleep(CustomRequestHelper.RECONNECTION_DELAY)
            else:
                connected = True
                self._log_connect_receive(None)
                # Lance le process d'écoute :
                self.socket_read.listen(5)
                self.thread_read_active = True
                self.binded_to_read = True
                self._listen_to_server()
                # Informe le serveur que la connection est activée :
                self._set_server_client_read_infos()
        # Infos réseau -> application
        self.dispatch_network_infos()

    def _create_read_address(self):
        """
        Génère l'adresse d'écoute du serveur :
        
        * en local (server_host='' ou 'localhost') : prend le même hôte, et ajoute à 
          son port une quantité dérivée de l'uid. Chaque client local a sa propre plage 
          de ports locaux (largeur = 200).
        * en ligne : choisi au hasard n'importe quel port entre 10000 et 20000        
        """
        if self.server_host == "" or self.server_host == "localhost":
            self.host_read = ""
            num = int(self.uid[3:]) + 1
            self.port_read = self.server_port + 200 * num
        else:
            self.host_read = CustomRequestHelper.get_ip()
            self.port_read = random.randrange(10000, 20000)

    def _set_server_client_read_infos(self):
        """
        Transmet au serveur les données de connexion à socket_read.
        """
        msg = CustomRequestHelper.create_cmd_msg(
            CustomRequestHelper.SET_CLIENT_READ_INFOS,
            {"host": self.host_read, "port": self.port_read},
        )
        self._send_msg(msg)

    def _listen_to_server(self):
        """
        Lance le process d'écoute du serveur.
        """
        self.thread_read = self.create_child_thread(
            self._read_thread_loop, suffixname="clt_read"
        )

    def _read_thread_loop(self):
        """
        "Boucle" d'écoute du serveur.
        """
        connections_distantes = list()
        while self.thread_read_active:
            # Le serveur a t'il fait une demande de connexion ?
            connexions_demandees = select.select(
                [self.socket_read], [], [], CustomRequestHelper.SELECT_TIMEOUT
            )[0]
            for connexion in connexions_demandees:
                try:
                    connexion_avec_client = connexion.accept()[0]
                    connections_distantes.append(connexion_avec_client)
                except OSError as e:
                    self._log_connect_receive(e)
            # Le serveur a t'il envoyé un message?
            sock_to_read = []
            try:
                sock_to_read = select.select(
                    connections_distantes, [], [], CustomRequestHelper.SELECT_TIMEOUT
                )[0]
            except OSError as e:
                # rq : python 3.3 select.error devient OSError
                self._log_connect_receive(e)
            else:
                # On reçoit les messages :
                for sock in sock_to_read:
                    # 1- Réception des données :
                    dictreceive = CustomRequestHelper.receive_indexed_request(sock)
                    # 2- Traitement du message (dont logs):
                    dicthandle = self._handle_server_msg(dictreceive)
                    # 3- On retourne la réponse (le nombre de caractères du message reçu par défaut)
                    if dicthandle["reply"]:
                        list2send = CustomRequestHelper.create_indexed_request(
                            dicthandle["reponse"], self.uid
                        )[1]
                        error = CustomRequestHelper.send_indexed_request(
                            sock, list2send
                        )
                        self._log_send(error)

    def _handle_server_msg(self, dictreceive):
        """
        Traite un message du serveur reçu sur la socket read
        
        Args:
            dictreceive : dict généré par CustomRequestHelper.receive_indexed_request
        
        Returns:
            dict: {"reply":Bool, "reponse":}
        """
        dispatch_msg = True
        dispatch_infos = True
        # Logs :
        complete = dictreceive["complete"]
        errors = dictreceive["errors"]
        if len(errors) > 0:
            self._log_receive(errors[-1], complete)
            dispatch_msg = False
        else:
            self._log_receive(None, complete)
        if not complete:
            dispatch_msg = False
        # Filtrage des requêtes nulles (cas d'un serveur déconnecté sauvagement)
        # ou non décodées (décodage unicode en erreur)
        msguid = dictreceive["msguid"]
        if msguid == None:
            # retournera un AR en erreur (len(msg)=0)
            return {"reply": True, "reponse": "0"}
        # Traitement
        uid = dictreceive["uid"]
        msg = dictreceive["msg"]
        msg_except_cmd = dictreceive["msg_except_cmd"]
        code_cmd = dictreceive["code_cmd"]
        if msg == None:
            len_msg = "0"
        else:
            len_msg = str(len(msg))
        # retour par défaut :
        do_reply = False
        do_close = False
        reponse = len_msg
        return_code = None
        # accusé de réception :
        if code_cmd in [
            CustomRequestHelper.NEED_CONFIRMATION,
            CustomRequestHelper.SERVER_CONNECTED,
            CustomRequestHelper.SERVER_DISCONNECTED,
            CustomRequestHelper.SERVER_SHUTDOWN,
            CustomRequestHelper.PING,
        ]:
            # Envoi d'un accusé de réception
            do_reply = True
            return_code = CustomRequestHelper.CONFIRM_RECEPTION
            reponse = CustomRequestHelper.prefix_msg_with_code(reponse, return_code)
        # Traitement des commandes spéciales de la forme "[cmd:CODE_CMD]"
        if code_cmd == CustomRequestHelper.SERVER_CONNECTED:
            # le serveur se reconnecte :
            self.server_status = CustomRequestHelper.STATUS_CONNECTED
            dispatch_msg = True
            dispatch_infos = True
        elif code_cmd == CustomRequestHelper.SERVER_DISCONNECTED:
            # le serveur se déconnecte
            self.server_status = CustomRequestHelper.STATUS_DISCONNECTED
            dispatch_msg = True
            dispatch_infos = True
        elif code_cmd == CustomRequestHelper.SERVER_SHUTDOWN:
            # le serveur va se fermer définitivement, on arrête :
            do_close = True
            self.server_status = CustomRequestHelper.STATUS_SHUTDOWN
            dispatch_msg = True
            dispatch_infos = True
        elif code_cmd == CustomRequestHelper.PING:
            pass
        # appel du handler externe :
        if dispatch_msg:
            # optimisation : propagation uniquement si la requête est complète et sans erreurs
            self.dispatch_to_external_handler(
                {"uid": uid, "netcode": code_cmd, "msg": msg_except_cmd}
            )
        # logs quantitatifs :
        # - réception
        hasAR = code_cmd == CustomRequestHelper.NEED_CONFIRMATION
        self._log_received_request_count(msguid, hasAR)
        # - envoi
        if do_reply:
            self._log_sended_request_count(True, False)
        # retour par défaut :
        if do_close:
            self.disconnect(None)
        # Infos réseau -> application
        if dispatch_infos:
            self.dispatch_network_infos()
        return {"reply": do_reply, "reponse": reponse}

    #-----> Retour interne au framework
    def dispatch_to_external_handler(self, dicthandler):
        """
        Transmission à l'application associée en toute fin du traitement de la requète
        
        - de préférence via le mécanisme de Queues hérité de app_components 
          (via queue_tools)
        - sinon via self.externalhandler en appel direct s'il est défini
                
        """
        # transmission à l'application :
        if self.are_queues_active():
            # de préférence via le mécanisme de Queues :
            exobj = appcomp.NETExchangeObject(
                appcomp.NETExchangeObject.RECEIVE, dicthandler
            )
            self.sendTask(exobj)
        elif self.externalhandler != None and callable(self.externalhandler):
            # appel direct au handler externe sinon :
            self.externalhandler(dicthandler)

    #-----> Logs
    def _log_connect_send(self, connect_error):
        """
        Log de la dernière tentative de connection d'envoi
        
        Args
            connect_error : OSError ou None
        """
        self.netdict["errors"]["last_connect_send_error"] = connect_error
        if connect_error != None:
            self.netdict["errors"]["connect_send_error_count"] += 1
        self._check_client_status_on_error(connect_error)

    def _log_send(self, send_error):
        """
        Log du dernier essai d'envoi au serveur
        
        Args:
            send_error : OSError ou None
        """
        self.netdict["errors"]["last_send_error"] = send_error
        if send_error != None:
            self.netdict["errors"]["send_error_count"] += 1
        self._check_client_status_on_error(send_error)

    def _log_sended_request_count(self, unit, hasAR):
        """
        Log les envois de requête vers le serveur :
        
        Args:
            unit : est-ce un envoi unitaire ou bien un renvoi
            hasAR : si unit=True, indique si la requête nécessite un accusé de récpetion          
        """
        self.netdict["errors"]["total_sended_request_count"] += 1
        if unit:
            self.netdict["errors"]["unit_sended_request_count"] += 1
            if hasAR:
                self.netdict["errors"]["AR_sended_request_count"] += 1

    def _log_connect_receive(self, connect_error):
        """
        Log de la dernière tentative de connection de réception
        connect_error : OSError ou None
        """
        self.netdict["errors"]["last_connect_receive_error"] = connect_error
        if connect_error != None:
            self.netdict["errors"]["connect_receive_error_count"] += 1
        self._check_client_status_on_error(connect_error)

    def _log_receive(self, receive_error, complete):
        """
        Log du dernier essai d'envoi au serveur
        
        Args:
            receive_error : OSError ou None
            complete (boolean)
        """
        self.netdict["errors"]["last_receive_error"] = receive_error
        if receive_error != None:
            self.netdict["errors"]["receive_error_count"] += 1
        self.netdict["errors"]["uncomplete_received_count"] += int(not complete)
        self._check_client_status_on_error(receive_error)

    def _log_received_request_count(self, msguid, hasAR):
        """
        Log les réceptions de messages envoyés par le serveur
        
        Args:
            msguid : identifiant unique de message
            hasAR : un accusé de réception est-il demandé.        
        """
        self.netdict["errors"]["total_received_request_count"] += 1
        if msguid == None or not msguid in self._received_msguids:
            self.netdict["errors"]["unit_received_request_count"] += 1
            if hasAR:
                self.netdict["errors"]["AR_received_request_count"] += 1
        if not msguid in self._received_msguids:
            self._received_msguids.append(msguid)

    #-----> Analyse d'erreurs
    def _check_client_status_on_error(self, error):
        """
        Met à jour son statut en fonction de la nature de l'erreur.
        
        Args:
            error: OSError ou ParseDataError
        """
        prev_states = str(self.connection_status) + str(self.server_status)
        if error != None:
            fatal_error = CustomRequestHelper.is_error_fatal(error)
            if fatal_error:
                # on passe le client en statut CustomRequestHelper.STATUS_ERROR_CONNECTION
                self.connection_status = CustomRequestHelper.STATUS_ERROR_CONNECTION
            elif self.connection_status == CustomRequestHelper.STATUS_CONNECTED:
                # on passe le client en statut CustomRequestHelper.STATUS_UNDEFINED
                self.connection_status = CustomRequestHelper.STATUS_UNDEFINED
            self._detect_server_state()
        elif self.connection_status not in [
            CustomRequestHelper.STATUS_SHUTDOWN,
            CustomRequestHelper.STATUS_DISCONNECTED,
        ]:
            self.connection_status = CustomRequestHelper.STATUS_CONNECTED
            # self.server_status = CustomRequestHelper.STATUS_CONNECTED
        # Envoi conditionnel des infos réseau : évite de mettre constamment à jour
        # la GUI lorsque le serveur est déconnecté.
        new_states = str(self.connection_status) + str(self.server_status)
        if new_states != prev_states:
            self.dispatch_network_infos()

    #-----> Etat du réseau
    def dispatch_network_status(self, msg):
        """
        Informe le composant business de l'état de connection
        
        Args:
            msg : message d'info
        """
        dictargs = {"connection_status": self.connection_status, "msg": msg}
        # transmission à l'application :
        if self.are_queues_active():
            # de préférence via le mécanisme de Queues :
            code = appcomp.NETExchangeObject.NET_STATUS
            if self.connection_status == CustomRequestHelper.STATUS_ERROR_CONNECTION:
                code = appcomp.NETExchangeObject.NET_ERROR
            exobj = appcomp.NETExchangeObject(code, dictargs)
            self.sendTask(exobj)
        elif self.externalhandler != None and callable(self.externalhandler):
            # appel direct au handler externe sinon :
            self.externalhandler(dictargs)
        # Infos réseau -> application
        self.dispatch_network_infos()

    def dispatch_network_infos(self):
        """
        Envoi au composant Business les infos réseau.
        """
        dictargs = self.get_network_infos()
        # transmission à l'application :
        if self.are_queues_active():
            # de préférence via le mécanisme de Queues :
            exobj = appcomp.NETExchangeObject(
                appcomp.NETExchangeObject.SET_NET_INFO, dictargs
            )
            self.sendTask(exobj)
        elif self.externalhandler != None and callable(self.externalhandler):
            # appel direct au handler externe sinon :
            self.externalhandler(dictargs)

    def get_network_infos(self):
        """
        Mise à jour des infos réseau.
        """
        # Serveur :
        self.netdict["server"]["address"] = (self.server_host, self.server_port)
        self.netdict["server"]["connected"] = self.connected_to_server
        self.netdict["server"]["refused"] = self.refused_by_server
        self.netdict["server"]["connection_status"] = self.connection_status
        self.netdict["server"]["server_status"] = self.server_status
        # Client :
        self.netdict["client"]["read_address"] = (self.host_read, self.port_read)
        self.netdict["client"]["binded"] = self.binded_to_read
        # Erreurs : mises à jour via les logs
        return self.netdict

    def _detect_server_state(self):
        """
        Identifie la possible déconnection "sauvage" du serveur.
        """
        nd = self.netdict["errors"]
        # envoi :
        last_con_send = nd["last_connect_send_error"]
        last_send = nd["last_send_error"]
        fact_send = max(int(last_con_send != None), int(last_send != None))
        nb_send = nd["send_error_count"]
        test_send = fact_send * nb_send > CustomRequestHelper.INACTIVE_COUNT
        # réception
        last_con_rec = nd["last_connect_receive_error"]
        last_rec = nd["last_receive_error"]
        fact_rec = max(int(last_con_rec != None), int(last_rec != None))
        nb_rec = nd["receive_error_count"]
        test_receive = fact_rec * nb_rec > CustomRequestHelper.INACTIVE_COUNT
        # détection d'un déconnection "sauvage" du serveur :
        if test_send or test_receive:
            # on peut considérer que le serveur s'est déconnecté sauvagement
            # limite les prochaines tentatives de connection/réception à un essai
            self.server_status = CustomRequestHelper.STATUS_UNDEFINED
        elif self.server_status not in [
            CustomRequestHelper.STATUS_SHUTDOWN,
            CustomRequestHelper.STATUS_DISCONNECTED,
            CustomRequestHelper.STATUS_ERROR_CONNECTION,
        ]:
            # on suppose le serveur connecté
            self.server_status = CustomRequestHelper.STATUS_CONNECTED
