#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pseudos interfaces des composants de la GUI.
"""
# imports :
import abc

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = [
    "AbstractZoneCarte",
    "AbstractZoneCommand",
    "AbstractZonePartie",
    "AbstractZoneBots",
    "AbstractZoneMenu",
    "AbstractScreenContent",
    "AbstractScreenWait",
    "AbstractSwitch",
    "AbstractInput",
]
#-----> Pseudos interfaces des composantes de l'interface
class AbstractZoneCarte(metaclass=abc.ABCMeta):
    """
    Pseudo interface de la zone de publication de la carte.
    """

    @abc.abstractmethod
    def re_initialise(self):
        """
        Ré initialise l'objet
        """
        raise NotImplementedError(
            "AbstractZoneCarte need implementation for re_initialise"
        )

    @abc.abstractmethod
    def highlight_player(self, robotlist, gambleinfos):
        """
        Identification du prochain joueur
        """
        raise NotImplementedError(
            "AbstractZoneCarte need implementation for highlight_player"
        )

    @abc.abstractmethod
    def publish_carte(self, dictargs):
        """
        Affichage de la carte
        """
        raise NotImplementedError(
            "AbstractZoneCarte need implementation for publish_carte"
        )

    @abc.abstractmethod
    def update_carte(self, dictargs):
        """
        Mise à jour de la carte à partir des change logs d'étape.
        """
        raise NotImplementedError(
            "AbstractZoneCarte need implementation for update_carte"
        )


class AbstractZoneCommand(metaclass=abc.ABCMeta):
    """
    Pseudo interface de la zone des contrôles de commande
    """

    @abc.abstractmethod
    def active_commande(self):
        """
        Activation des commandes de jeu
        """
        raise NotImplementedError(
            "AbstractZoneCommand need implementation for active_commande"
        )

    @abc.abstractmethod
    def unactive_commande(self):
        """
        Désctivation des commandes de jeu
        """
        raise NotImplementedError(
            "AbstractZoneCommand need implementation for unactive_commande"
        )

    @abc.abstractmethod
    def set_state(self, state):
        """
        Changement d'état de la barre de commande
        
        Args:
            state: ZoneCommandBase.STATE_MENU ou ZoneCommandBase.STATE_GAME
        """
        raise NotImplementedError(
            "AbstractZoneCommand need implementation for set_state"
        )

    @abc.abstractmethod
    def re_initialise(self):
        """
        Ré initialise l'objet
        """
        raise NotImplementedError(
            "AbstractZoneCommand need implementation for re_initialise"
        )

    @abc.abstractmethod
    def show_message(self, msg, is_input):
        """
        Affichage d'un message dans la zone info
        """
        raise NotImplementedError(
            "AbstractZoneCommand need implementation for show_message"
        )

    @abc.abstractmethod
    def update_player_power(self, robotdict):
        """
        Mise à jour des caractéristiques du joueur
        """
        raise NotImplementedError(
            "AbstractZoneCommand need implementation for update_player_power"
        )

    @abc.abstractmethod
    def post_init_controls(self):
        """
        Appelée si le LabHelper a été surchargé
        """
        raise NotImplementedError(
            "AbstractZoneCommand need implementation for post_init_controls"
        )


class AbstractZonePartie(metaclass=abc.ABCMeta):
    """
    Pseudo interface de la zone partie (carte et infos robots)
    """

    @abc.abstractmethod
    def set_state(self, state):
        """
        Changement d'état : resize, création partie, jeu
        """
        raise NotImplementedError(
            "AbstractZonePartie need implementation for set_state"
        )

    @abc.abstractmethod
    def re_initialise(self):
        """
        Ré initialise l'objet
        """
        raise NotImplementedError(
            "AbstractZonePartie need implementation for re_initialise"
        )

    @abc.abstractmethod
    def on_view_changed(self, visible):
        """
        Appelée par la GUI avant un changement d'affichage.
        
        Args:
            visible : boolean indiquant l'état prochain d'affichage
        """
        raise NotImplementedError(
            "AbstractZonePartie need implementation for on_view_changed"
        )

    @abc.abstractmethod
    def register_partie_state(self, state):
        """
        Enregistre l'état actuel de la partie
        """
        raise NotImplementedError(
            "AbstractZonePartie need implementation for register_partie_state"
        )

    @abc.abstractmethod
    def on_resize_start(self):
        """
        Appelée par la carte au début de son processus de resize. Permet d'afficher 
        un écran d'attente.
        """
        raise NotImplementedError(
            "AbstractZonePartie need implementation for on_resize_start"
        )

    @abc.abstractmethod
    def on_resize_end(self):
        """
        Appelée par la carte à la fin du processus de resize. Masquage de l'éventuel 
        écran d'attente.
        """
        raise NotImplementedError(
            "AbstractZonePartie need implementation for on_resize_end"
        )


class AbstractZoneBots(metaclass=abc.ABCMeta):
    """
    Pseudo interface de la zone d'affichage des infos robots.
    """

    @abc.abstractmethod
    def re_initialise(self):
        """
        Ré initialise l'objet
        """
        raise NotImplementedError(
            "AbstractZoneBots need implementation for re_initialise"
        )

    @abc.abstractmethod
    def publish_robotlist(self, robotlist, gambleinfos):
        """
        Méthode d'affichage publique
        """
        raise NotImplementedError(
            "AbstractZoneBots need implementation for publish_robotlist"
        )


class AbstractZoneMenu(metaclass=abc.ABCMeta):
    """
    Pseudo interface de la zone d'affichage du menu principal.
    """

    @abc.abstractmethod
    def re_initialise(self):
        """
        Ré initialise l'objet
        """
        raise NotImplementedError(
            "AbstractZoneMenu need implementation for re_initialise"
        )


class AbstractScreenContent(metaclass=abc.ABCMeta):
    """
    Pseudo interface de l'écran de contenu
    """

    # pour usage futur éventuel


class AbstractScreenWait(metaclass=abc.ABCMeta):
    """
    Pseudo interface de l'écran d'attente
    """

    @abc.abstractmethod
    def set_state(self, statename):
        """
        Modification du visuel
        """
        raise NotImplementedError(
            "AbstractScreenWait need implementation for set_state"
        )


#-----> Pseudo interface des contrôles
class AbstractSwitch(metaclass=abc.ABCMeta):
    """
    Pseudo interface des boutons (ou switchs)
    """

    # états des contrôles : les implémentations des switchs devront avoir
    # les mêmes variables statiques d'état.
    UNSELECTED = "UNSELECTED" #: marqueur d'état
    OVER = "OVER" #: marqueur d'état
    PRESSED = "PRESSED" #: marqueur d'état
    SELECTED = "SELECTED" #: marqueur d'état
    DISABLED = "DISABLED" #: marqueur d'état
    ENABLED = "ENABLED" #: marqueur d'état
    STATES = [UNSELECTED, OVER, PRESSED, SELECTED, DISABLED] #: liste des marqueurs d'état
    # méthodes :
    @abc.abstractmethod
    def get_state(self):
        """
        Retourne l'état du bouton
        """
        raise NotImplementedError("AbstractSwitch need implementation for get_state")

    @abc.abstractmethod
    def is_switch(self):
        """
        Indique si le bouton se comporte comme un switch
        """
        raise NotImplementedError("AbstractSwitch need implementation for is_switch")

    @abc.abstractmethod
    def set_state(self, state):
        """
        Modifie l'état du bouton
        """
        raise NotImplementedError("AbstractSwitch need implementation for set_state")


class AbstractInput(metaclass=abc.ABCMeta):
    """
    Pseudo interface de texte input
    """

    @abc.abstractmethod
    def register_callback(self, clb):
        """
        Enregistre le callback à appeler après validation (appui touche entrée)
        """
        raise NotImplementedError(
            "AbstractInput need implementation for register_callback"
        )

    @abc.abstractmethod
    def take_focus(self):
        """
        Méthode d'acquisition du focus input
        """
        raise NotImplementedError("AbstractInput need implementation for take_focus")

    @abc.abstractmethod
    def get_input_value(self):
        """
        Getter du texte input
        """
        raise NotImplementedError(
            "AbstractInput need implementation for get_input_value"
        )

    @abc.abstractmethod
    def set_input_value(self, val):
        """
        Setter du texte input
        """
        raise NotImplementedError(
            "AbstractInput need implementation for set_input_value"
        )
