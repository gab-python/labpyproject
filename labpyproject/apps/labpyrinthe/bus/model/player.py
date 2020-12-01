#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modélisation d'un joueur
"""
# imports
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseRobot

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["LabPlayer"]
# classe
class LabPlayer:
    """
    Modélise un joueur
    """

    # types de joueurs :
    HUMAN = "HUMAN"  #: marqueur de joueur humain
    BOT = "BOT"  #: marqueur de joueur automatique

    def __init__(self, uid, nom, local, human, number, human_number, behavior=None):
        """
        Constructeur
        
        Args:
            uid : identifiant unique
            nom : nom utilisé pour l'affichage
            local : boolean (True : joueur local, false : joueur distant)
            human : boolean (True : joueur humain, false : joueur automatique)        
        """
        self.uid = uid
        self.nom = nom
        self.local = local
        if human:
            self.player_type = LabPlayer.HUMAN
        else:
            self.player_type = LabPlayer.BOT
        self.number = number
        self.human_number = human_number
        self.behavior = behavior
        self.color = None
        self.published = False
        self.robot = None
        self.cmdqueue = list()
        self.joignable = False  # indicateur de connection d'un joueur distant
        self.connection_status = None  # valeur informative
        self.viewer = False  # mode spectateur
        self.killed = False
        self.vitesse = CaseRobot.VITESSE_INITIALE
        self._order = None
        # indice de synchronisation à comparer à GameManager.carte_version
        # utilisé pour la synchro des clients
        self.sync_marker = 0

    def re_initialise(self):
        """
        Ré initialisation avant une nouvelle partie
        """
        self.published = False
        self.robot = None
        self.cmdqueue = list()
        self.killed = False
        self.viewer = False
        self.vitesse = CaseRobot.VITESSE_INITIALE
        self.sync_marker = 0

    def can_play(self):
        """
        Indique si le joueur peut jouer
        """
        if self.player_type == LabPlayer.HUMAN:
            if self.viewer:
                # un spectateur ne joue pas
                return False
            if not self.local and not self.joignable:
                # un joueur distant non joignable ne peut pas jouer
                return False
        # par défaut :
        return not self.killed

    def _get_order(self):
        return self._order

    def _set_order(self, val):
        self._order = val
        if self.robot != None:
            self.robot.order = val

    order = property(_get_order, _set_order)  #: ordre du joueur

    def set_robot(self, robot):
        """
        Associe une CaseRobot au joueur
        """
        self.robot = robot
        self.robot.order = self.order

    def get_robot(self):
        """
        Retourne la CaseRobot associée
        """
        return self.robot

    def update_vitesse(self, val):
        """
        Met à jour la vitesse (nb de coups / tour) du joueur
        """
        self.vitesse = val

    def kill(self):
        """
        Marque le joueur comme éliminé
        """
        self.killed = True

    def addcmdtoqueue(self, cmd):
        """
        Ajoute une commande à la liste des commandes enregistrées
        """
        if cmd != None:
            self.cmdqueue.append(cmd)

    def resetcmdqueue(self):
        """
        Ré initialise la liste
        """
        self.cmdqueue = list()

    def getcmdqueue(self):
        """
        Retourne la liste des commandes enregistrées
        """
        return self.cmdqueue

    def get_cmd(self):
        """
        Retourne une cmd ou None
        """
        if len(self.cmdqueue) > 0:
            cmd = self.cmdqueue.pop(0)
            return cmd
        return None

    def has_cmd(self):
        """
        Indique si une commande est en attente
        """
        if len(self.cmdqueue) > 0:
            return True
        return False
