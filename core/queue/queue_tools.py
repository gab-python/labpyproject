#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
**Système de gestion de tâches (Queue) pour des applications multi-threads.**

Todo:
    A dériver pour des applications multi process (en supportant ProcessQueue)
"""
# imports :
import queue
import labpyproject.core.patterns.design_patterns as dp
from queue import Queue

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["QueueManager", "QueueSimpleClient", "QueueSwitcher"]
# classes :
class QueueManager(metaclass=dp.Singleton):
    """
    Gestionnaire de Queue partagé dans toute l'application. 
    Implémenté sous forme de Singleton en première approche (marche en helper 
    statique également).
    """

    def __init__(self):
        """
        Constructeur
        """
        self._queuedict = {}

    def get_queue(self, keycode):
        """
        Retourne un objet Queue unique associé à l'identifiant keycode.
        
        Args:
            keycode (str)
        """
        q = None
        try:
            q = self._queuedict[keycode]
        except KeyError:
            q = self._queuedict[keycode] = Queue()
        return q

    def get(self, keycode, wait=False):
        """
        Retourne la première commande à dépiler de la Queue de code keycode ou None.
        
        Args:
            keycode (str)
            wait (boolean)
            
        Returns:
            cmd (object)
        """
        cmd = None
        q = self.get_queue(keycode)
        if q.empty():
            return cmd
        else:
            try:
                if wait:
                    cmd = q.get()
                else:
                    cmd = q.get_nowait()
            except queue.Empty:
                # raise(queue.Empty)
                pass
            else:
                q.task_done()
        return cmd

    def put(self, cmd, keycode, wait=False):
        """
        Empile une commande dans la queue de code keycode.
        
        Args:
            keycode (str)
            wait (boolean)
        """
        done = False
        if cmd != None:
            q = self.get_queue(keycode)
            try:
                if wait:
                    q.put(cmd)
                else:
                    q.put_nowait(cmd)
            except queue.Full:
                # raise(queue.Full)
                pass
            else:
                done = True
        return done


class QueueSimpleClient:
    """
    Client du manager de queue utilisant deux piles de tâches (entrantes, sortantes).
    """

    def __init__(self, QKCode_in, QKCode_out):
        """
        Constructeur
        
        Args:
            QKCode_in (str): code de la queue de commandes entrantes
            QKCode_out (str): code de la queue de commandes sortantes
        """
        # ref au singleton :
        self._QueueMngr = QueueManager()
        # enregistrement des codes
        self._keycode_in = QKCode_in
        self._keycode_out = QKCode_out
        # état :
        self._queueactive = False
        if QKCode_in != None and QKCode_out != None:
            self._queueactive = True

    def are_queues_active(self):
        """
        Indique si le client est opérationnel.
        """
        return self._queueactive

    def get_cmd_from_queue(self):
        """
        Retourne la première commande à dépiler dans la queue de keycode self._keycode_in
        ou None.
        
        Returns:
            cmd (object)
        """
        cmd = self._QueueMngr.get(self._keycode_in)
        return cmd

    def put_cmd_in_queue(self, cmd):
        """
        Empile une commande dans la queue de keycode self._keycode_out
        
        Args:
            cmd (object)
        """
        if cmd != None:
            done = self._QueueMngr.put(cmd, self._keycode_out)
            return done


class QueueSwitcher:
    """
    Aiguilleur de tâches (queues) multi canaux.
    """

    def __init__(self, queueswitchlist):
        """
        Constructeur, initialise les différents canaux
        
        Args:
            queueswitchlist (list): liste de tuples (channelname, QKCode_in, QKCode_out)
        """
        # ref au singleton :
        self._QueueMngr = QueueManager()
        # enregistrement des canaux et keycodes in/out :
        self._channeldict = dict()
        for cht in queueswitchlist:
            self._channeldict[cht[0]] = {"in": cht[1], "out": cht[2]}

    def get_queuecmd_from_channel(self, channelname):
        """
        Dépile une cmd de la queue in du canal de nom channelname ou retourne None.
        
        Args:
            channelname (str)
            
        Returns:
            cmd (object)
        """
        cmd = None
        try:
            kc_in = self._channeldict[channelname]["in"]
        except KeyError:
            pass
        else:
            cmd = self._QueueMngr.get(kc_in)
        return cmd

    def put_queuecmd_in_channel(self, cmd, channelname):
        """
        Empile une commande dans la queue out du canal de nom channelname.
        
        Args:
            cmd (object)
            channelname (str)
        
        """
        if channelname in self._channeldict.keys():
            kc_out = self._channeldict[channelname]["out"]
            done = self._QueueMngr.put(cmd, kc_out)
            return done
