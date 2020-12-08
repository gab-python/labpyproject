#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Données de modélisation et services statiques :

    * LabHelper : Helper statique portant des données de modélisation

Part géométrique de la modélisation du jeu :

    * LabLevel : modélise le labyrinthe (pile de matrices & couches animées)
    * Matrice : modélise une couche  de cases (avec gestion de cache)
    * AnimatedLayer : couche dédiée aux animations
    * Case : classe de base d'une case
    * CaseRobot, CaseDanger, CaseGrenade, CaseAnimation, CaseBonus : subclasses de Case

.. note::
   Idéalement ce module aurait été découpé mais des problèmes d'import circulaire
   (et le manque de temps pour créer des pseudos interfaces via abc.ABCMeta) imposent
   cette forme.
"""
# imports :
import re
import math
from fractions import Fraction
from operator import attrgetter, itemgetter
import labpyproject.core.random.custom_random as cr

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = [
    "LabHelper",
    "LabLevel",
    "Matrice",
    "AnimatedLayer",
    "Case",
    "CaseRobot",
    "CaseDanger",
    "CaseGrenade",
    "CaseAnimation",
    "CaseBonus",
]
# classes
class LabHelper:
    """
    Helper statique
    """
    #-----------------------------------------------------------------------------------------------
    # Variables statiques
    #-----------------------------------------------------------------------------------------------
    # rôles des différentes cases :
    CASE_VIDE = "vide"  #: identifie une case vide
    CASE_MUR = "mur"  #: identifie une case mur
    CASE_MUR_PERIMETRE = "mur_perimetre"  #: identifie une case mur de périmètre
    CASE_PORTE = "porte"  #: identifie une case porte
    CASE_SORTIE = "sortie"  #: identifie une case sortie
    CASE_ROBOT = "robot"  #: identifie une case robot
    CASE_BONUS = "bonus"  #: identifie une case bonus
    CASE_DANGER = "danger"  #: identifie une case danger
    CASE_GRENADE = "grenade"  #: identifie une case grenade
    CASE_ANIMATION = "animation"  #: identifie une case animation
    CASE_TARGET = "target"  #: identifie une case cible
    CASE_DEBUG = "debug"  #: identifie une case de debug
    FULL_CASETYPES = [
        CASE_VIDE,
        CASE_MUR,
        CASE_MUR_PERIMETRE,
        CASE_PORTE,
        CASE_SORTIE,
        CASE_ROBOT,
        CASE_BONUS,
        CASE_DANGER,
        CASE_GRENADE,
        CASE_ANIMATION,
        CASE_TARGET,
        CASE_DEBUG,
    ]  #: liste des types de cases supportés
    # liste des cases avec notion de z-index :
    ZINDEX_CASE_LIST = (
        {"z": 0, "typecase": CASE_MUR_PERIMETRE},
        {"z": 1, "typecase": CASE_SORTIE},
        {"z": 2, "typecase": CASE_VIDE},
        {"z": 3, "typecase": CASE_PORTE},
        {"z": 4, "typecase": CASE_MUR},
        {"z": 5, "typecase": CASE_DANGER},
        {"z": 6, "typecase": CASE_BONUS},
        {"z": 7, "typecase": CASE_ROBOT},
        {"z": 8, "typecase": CASE_GRENADE},
        {"z": 9, "typecase": CASE_ANIMATION},
        {"z": 10, "typecase": CASE_TARGET},
        {"z": 11, "typecase": CASE_DEBUG},
    )  #: répartition des types de cases par zindex
    # change log : liste des zindexs pour la génération de clef de comparaison (réseau)
    # couches de sortie à robots inclus
    ZINDEX_LOGS_KEY = range(
        1, 8
    )  #: liste réduite de zindex pour la génération de clefs de cohérence
    # interdépendances entre types de cases :
    LINKED_CASETYPES = [
        CASE_MUR_PERIMETRE,
        CASE_MUR,
        CASE_VIDE,
        CASE_PORTE,
        CASE_SORTIE,
    ]  #: cases interdépendantes
    # liste réduite des cases pour création de cartes texte à parser
    LIMITED_CASETYPES = LINKED_CASETYPES  #: liste réduite de types de cases pour la génération de carte texte
    # Types de cases à exclure des changelogs d'étape :
    STEP_CHANGE_LOGS_EXCLUDED = [
        CASE_ANIMATION
    ]  #: types de cases à exclure des changelogs d'étapes
    # Liste des zindexs pour la recherche de cases de mêmes coords :
    # couches de sortie à robots inclus
    ZINDEX_COORDS_SEARCH = range(
        1, 8
    )  #: liste des zindexs pour la recherche de cases superposées
    # autres variables liées aux cases
    FAMILLE_CASES_LIBRES = [
        CASE_VIDE,
        CASE_PORTE,
        CASE_SORTIE,
        CASE_BONUS,
    ]  #: famille de cases libres
    FAMILLE_CASES_DANGERS = [CASE_DANGER]  #: famille de cases dangers
    FAMILLE_CASES_RISQUES = [CASE_DANGER, CASE_ROBOT]  #: famille de cases risquées
    FAMILLE_CASES_ADVERSAIRES = [CASE_ROBOT]  #: famille de cases adversaires
    FAMILLE_CASES_BONUS = [CASE_BONUS]  #: famille de cases bonus
    FAMILLE_CASES_MURS = [CASE_MUR]  #: famille de cases mur
    FAMILLE_CASES_PERIMETRE = [
        CASE_MUR_PERIMETRE,
        CASE_SORTIE,
    ]  #: famille de cases périmètre
    FAMILLE_CASES_NO_ACTION = [
        CASE_MUR_PERIMETRE
    ]  #: famille de cases ne pouvant subir d'action
    FAMILLE_CASES_UNDELETABLE = [
        CASE_VIDE,
        CASE_MUR_PERIMETRE,
        CASE_SORTIE,
        CASE_ROBOT,
    ]  #: famille de cases indestructibles
    FAMILLE_CASES_NO_ANIMATION = [
        CASE_MUR_PERIMETRE,
        CASE_SORTIE,
    ]  #: famille de cases non animées
    FAMILLE_TARGET = [
        CASE_VIDE,
        CASE_PORTE,
        CASE_SORTIE,
        CASE_BONUS,
        CASE_MUR,
    ]  #: famille de cases cibles
    FAMILLE_NO_TARGET = [CASE_MUR_PERIMETRE]  #: famille de cases non cibles
    FAMILLE_DESTRUCTION = [
        CASE_MUR,
        CASE_ROBOT,
        CASE_DANGER,
        CASE_BONUS,
    ]  #: famille de cases destructibles
    FAMILLE_MOVE = [
        CASE_VIDE,
        CASE_PORTE,
        CASE_SORTIE,
        CASE_BONUS,
        CASE_DANGER,
    ]  #: famille de cases sur lesquelles on peut bouger
    FAMILLE_BUILD_DOOR = [
        CASE_MUR
    ]  #: famille de cases sur lesquelles contruire une porte
    FAMILLE_BUILD_WALL = [
        CASE_VIDE,
        CASE_PORTE,
    ]  #: famille de cases sur lesquelles construire un mur
    FAMILLE_KILL = [CASE_ROBOT]  #: famille de cases pouvant être tuées
    FAMILLE_GRENADE = [
        CASE_ROBOT,
        CASE_VIDE,
        CASE_PORTE,
        CASE_MUR,
        CASE_DANGER,
        CASE_BONUS,
    ]  #: famille de cases pouvant recevoir une grenade
    FAMILLE_MINE = [
        CASE_VIDE,
        CASE_PORTE,
    ]  #: famille de cases pouvant recevoir une mine
    FAMILLE_EXPORT_DICT = [
        CASE_ROBOT,
        CASE_BONUS,
        CASE_DANGER,
        CASE_GRENADE,
    ]  #: famille de cases à exporter par dict
    TYPE_CASES_LIBRES = "TYPE_CASES_LIBRES"  #: type de la famille FAMILLE_CASES_LIBRES
    TYPE_CASES_RISQUES = (
        "TYPE_CASES_RISQUES"  
    ) #: type de la famille FAMILLE_CASES_RISQUES
    TYPE_CASES_ADVERSAIRES = (
        "TYPE_CASES_ADVERSAIRES"  
    ) #: type de la famille FAMILLE_CASES_ADVERSAIRES
    TYPE_CASES_BONUS = "TYPE_CASES_BONUS"  #: type de la famille FAMILLE_CASES_BONUS
    TYPE_CASES_DANGERS = (
        "TYPE_CASES_DANGERS"  
    ) #: type de la famille FAMILLE_CASES_DANGERS
    TYPE_CASES_MURS = "TYPE_CASES_MURS"  #: type de la famille FAMILLE_CASES_MURS
    TYPE_CASES_PERIMETRE = (
        "TYPE_CASES_PERIMETRE"  
    ) #: type de la famille FAMILLE_CASES_PERIMETRE
    TYPE_CASES_NO_ACTION = (
        "TYPE_CASES_NO_ACTION"  
    ) #: type de la famille FAMILLE_CASES_NO_ACTION
    # clefs de mesure
    NOMBRE_CASES_LIBRES = (
        "NOMBRE_CASES_LIBRES"  
    ) #: clef de mesure nombre de cases libres
    DELTA_MAIN = "DELTA_MAIN"  #: clef de mesure distance à la cible principale
    # géométrie
    AXIS_X = "x"  #: axe x
    AXIS_Y = "y"  #: axe y
    DIR_POS = 1  #: sens +
    DIR_NEG = -1  #: sens -
    # paramètres liés aux extras
    BONUS_DENSITE = 4 / 100  #: densité de bonus (par défaut)
    DANGER_DENSITE = 8 / 100  #: densité de mines (par défaut)
    # animations :
    CHAR_REPR_EXPLOSION = "x"  #: caractère d'affichage explosion
    CHAR_REPR_EXPLOSION_1 = "X"  #: caractère d'affichage explosion 1
    CHAR_REPR_EXPLOSION_2 = "x"  #: caractère d'affichage explosion 2
    CHAR_REPR_EXPLOSION_3 = "#"  #: caractère d'affichage explosion 3
    CHAR_REPR_EXPLOSION_4 = "*"  #: caractère d'affichage explosion 4
    CHAR_REPR_EXPLOSION_5 = "."  #: caractère d'affichage explosion 5
    CHAR_REPR_EXPLOSION_6 = " "  #: caractère d'affichage explosion 6
    ANIMATION_EXPLOSION_FACES = [
        CHAR_REPR_EXPLOSION_1,
        CHAR_REPR_EXPLOSION_2,
        CHAR_REPR_EXPLOSION_3,
        CHAR_REPR_EXPLOSION_4,
        CHAR_REPR_EXPLOSION_5,
        CHAR_REPR_EXPLOSION_6,
    ]  #: liste des caractères d'affichage d'explosion
    # ANIMATION_STEP_DURATION = 1 / 8
    ANIMATION_MOVE_DURATION = 1 / 4  #: durée d'un déplacement d'une case (secondes)
    ANIMATION_FACE_DURATION = 1 / 6  #: durée d'un changement d'apparence (secondes)
    # tempos :
    GAMBLE_TEMPO = 1 / 12  #: deprecated
    # scénarios d'animation pris en charge
    ANIMATION_SCENARIO = dict() #: scénarios d'animations
    ANIMATION_SCENARIO["EXPLOSION"] = "EXPLOSION"  #: scénarios d'animations
    # résolution d'animation : case (défaut) ou pixels (si GUI graphique)
    ANIMATION_RESOLUTION_CASE = (
        "ANIMATION_RESOLUTION_CASE"  
    ) #: gui console mouvement case à case obligatoire
    ANIMATION_RESOLUTION_PIXEL = (
        "ANIMATION_RESOLUTION_PIXEL"  
    ) #: gui graphique mouvement en pixel possible
    ANIMATION_RESOLUTION = ANIMATION_RESOLUTION_CASE  #: résolution d'animation
    # caractères associés aux rôles dans les fichiers txt des cartes (valeurs par défaut)
    CHAR_TXT_VIDE = " "  #: caractère de parsing case vide
    CHAR_TXT_MUR = "o"  #: caractère de parsing mur
    CHAR_TXT_PORTE = "."  #: caractère de parsing porte
    CHAR_TXT_SORTIE = "u"  #: caractère de parsing sortie
    CHAR_TXT_ROBOT = "x"  #: deprecated
    CHAR_TXT_DANGER = "d"  #: deprecated
    CHAR_TXT_BONUS = "b"  #: deprecated
    CHAR_TXT_GRENADE = "g"  #: deprecated
    # caractères d'affichage des différents rôles (valeurs par défaut)
    CHAR_REPR_VIDE = " "  #: caractère d'affichage case vide
    CHAR_REPR_MUR = chr(9608)  #: caractère d'affichage mur
    CHAR_REPR_PORTE = chr(9618)  #: caractère d'affichage porte
    CHAR_REPR_SORTIE = "S"  #: caractère d'affichage sortie
    CHAR_REPR_ROBOT = "R"  #: caractère d'affichage robot
    CHAR_REPR_DANGER = "-"  #: caractère d'affichage mine
    CHAR_REPR_BONUS = "+"  #: caractère d'affichage bonus
    CHAR_REPR_GRENADE = "*"  #: caractère d'affichage grenade
    CHAR_REPR_TARGET = "$"  #: caractère d'affichage cible
    # en multi joueur les char_repr des robots sont gérés au niveau supérieur
    # Directions :
    LEFT = "left"  #: identifie la direction gauche
    RIGHT = "right"  #: identifie la direction droite
    TOP = "top"  #: identifie la direction haut
    BOTTOM = "bottom"  #: identifie la direction bas
    LIST_DIRECTIONS = [LEFT, RIGHT, TOP, BOTTOM]  #: liste des ids de directions
    # Caractères de commandes (valeurs par défaut)
    CHAR_LEFT = "o"  #: caractère de commande gauche
    CHAR_RIGHT = "e"  #: caractère de commande droite
    CHAR_TOP = "n"  #: caractère de commande haut
    CHAR_BOTTOM = "s"  #: caractère de commande bas
    CHAR_HELP = "h"  #: caractère de commande aide
    CHAR_MENU = "a"  #: caractère de commande menu
    CHAR_QUIT = "q"  #: caractère de commande quitter
    CHAR_MUR = "m"  #: caractère de commande construire mur
    CHAR_PORTE = "p"  #: caractère de commande construire porte
    CHAR_START = "c"  #: caractère de commande commencer la partie
    CHAR_RESET_QUEUE = (
        "r"  
    ) #: caractère de commande effacer les commandes (non implémenté)
    CHAR_KILL = "k"  #: caractère de commande tuer un voisin
    CHAR_GRENADE = "g"  #: caractère de commande lancer de grenade
    CHAR_MINE = "b"  #: caractère de commande poser une mine
    # commandes générales
    ACTION_HELP = "ACTION_HELP"  #: identifie la commande globale aide
    ACTION_MENU = "ACTION_MENU"  #: identifie la commande globale menu
    ACTION_QUIT = "ACTION_QUIT"  #: identifie la commande globale quitter
    ACTION_START = "ACTION_START"  #: identifie la commande globale commencer
    ACTION_RESET_QUEUE = "ACTION_RESET_QUEUE"  #: identifie la commande globale effacer les commandes (non implémenté)
    # commandes de robot :
    ACTION_MOVE = "ACTION_MOVE"  #: identifie la commande se déplacer
    ACTION_CREATE_DOOR = "ACTION_CREATE_DOOR"  #: identifie la commande créer une porte
    ACTION_CREATE_WALL = "ACTION_CREATE_WALL"  #: identifie la commande créer un mur
    ACTION_KILL = "ACTION_KILL"  #: identifie la commande tuer
    ACTION_GRENADE = "ACTION_GRENADE"  #: identifie la commande lancer de grenade
    ACTION_MINE = "ACTION_MINE"  #: identifie la commande poser une mine
    # regexp des commandes liées au jeu :
    REGEXP_GAME = re.compile(
        "gamecmd=[A-Za-z0-9_]+&?"
    )  #: expression régulière d'une commande à parser
    REGEXP_SEQ_LIST = re.compile(
        "\[[A-Za-z0-9_\.,\+\-]*\]"
    )  #: expression régulière liste
    REGEXP_SEQ_TUPLE = re.compile(
        "\([A-Za-z0-9_\.,\+\-]*\)"
    )  #: expression régulière tuple
    REGEXP_SEQ_DICT = re.compile(
        "\{[A-Za-z0-9_\.,:\+\-#]*\}"
    )  #: expression régulière dict
    REGEXP_INT = re.compile("0{1}|^[1-9]{1}[0-9]*")  #: expression régulière int
    REGEXP_FLOAT = re.compile("[0-9]{1}\.[0-9]*")  #: expression régulière float
    # distances considérées pour les mesures de densité
    DENSITE_LARGEUR = 5  #: largeur par défaut pour les mesures de densité
    DENSITE_PROFONDEUR = 8  #: hauteur par défaut pour les mesures de densités
    #-----> Paramétrage : setter
    def set_navigation_chars(cls, **params):
        """
        Modifie les caractères de navigation par défaut
        
        Args:
            **params : un dict {"left":char, ...}
        """
        for cle, val in params.items():
            if cle == "left":
                cls.CHAR_LEFT = val
            elif cle == "right":
                cls.CHAR_RIGHT = val
            elif cle == "top":
                cls.CHAR_TOP = val
            elif cle == "bottom":
                cls.CHAR_BOTTOM = val
            elif cle == "aide":
                cls.CHAR_HELP = val
            elif cle == "menu":
                cls.CHAR_MENU = val
            elif cle == "quitter":
                cls.CHAR_QUIT = val
            elif cle == "mur":
                cls.CHAR_MUR = val
            elif cle == "porte":
                cls.CHAR_PORTE = val
            elif cle == "start":
                cls.CHAR_START = val
            elif cle == "reset_queue":
                cls.CHAR_RESET_QUEUE = val
            elif cle == "kill":
                cls.CHAR_KILL = val
            elif cle == "grenade":
                cls.CHAR_GRENADE = val
            elif cle == "mine":
                cls.CHAR_MINE = val

    set_navigation_chars = classmethod(set_navigation_chars)

    def set_parsing_chars(cls, **params):
        """
        Modifie les caractères à identifier lors du parsing des cartes txt
        
        Args:
            **params : un dict {"vide":char, ...}
        """
        for cle, val in params.items():
            if cle == "vide":
                cls.CHAR_TXT_VIDE = val
            elif cle == "mur":
                cls.CHAR_TXT_MUR = val
            elif cle == "porte":
                cls.CHAR_TXT_PORTE = val
            elif cle == "sortie":
                cls.CHAR_TXT_SORTIE = val
            elif cle == "robot":
                cls.CHAR_TXT_ROBOT = val
            elif cle == "danger":
                cls.CHAR_TXT_DANGER = val
            elif cle == "bonus":
                cls.CHAR_TXT_BONUS = val
            elif cle == "grenade":
                cls.CHAR_TXT_GRENADE = val

    set_parsing_chars = classmethod(set_parsing_chars)

    def set_graphic_chars(cls, **params):
        """
        Modifie les caractères d'affichages des cartes
        
        Args:
            **params : un dict {"vide":char, ...}
        """
        for cle, val in params.items():
            if cle == "vide":
                cls.CHAR_REPR_VIDE = val
            elif cle == "mur":
                cls.CHAR_REPR_MUR = val
            elif cle == "porte":
                cls.CHAR_REPR_PORTE = val
            elif cle == "sortie":
                cls.CHAR_REPR_SORTIE = val
            elif cle == "robot":
                cls.CHAR_REPR_ROBOT = val
            elif cle == "danger":
                cls.CHAR_REPR_DANGER = val
            elif cle == "bonus":
                cls.CHAR_REPR_BONUS = val
            elif cle == "grenade":
                cls.CHAR_REPR_GRENADE = val

    set_graphic_chars = classmethod(set_graphic_chars)
    #-----> Paramétrage : getters
    def get_role_of_char(cls, c):
        """
        Retourne le rôle (mur, porte, sortie, vide, robot...) associé à un caractère
        d'une carte textuelle
        """
        c = c.lower()
        if c == cls.CHAR_TXT_VIDE:
            return cls.CASE_VIDE
        elif c == cls.CHAR_TXT_MUR:
            return cls.CASE_MUR
        elif c == cls.CHAR_TXT_PORTE:
            return cls.CASE_PORTE
        elif c == cls.CHAR_TXT_SORTIE:
            return cls.CASE_SORTIE
        elif c == cls.CHAR_TXT_ROBOT:
            return cls.CASE_ROBOT
        elif c == cls.CHAR_TXT_DANGER:
            return cls.CASE_DANGER
        elif c == cls.CHAR_TXT_BONUS:
            return cls.CASE_BONUS
        else:
            return None

    get_role_of_char = classmethod(get_role_of_char)

    def get_repr_for_role(cls, role):
        """
        Retourne le caractère d'affichage associé à un rôle
        """
        if role == cls.CASE_VIDE:
            return cls.CHAR_REPR_VIDE
        elif role == cls.CASE_MUR or role == cls.CASE_MUR_PERIMETRE:
            return cls.CHAR_REPR_MUR
        elif role == cls.CASE_PORTE:
            return cls.CHAR_REPR_PORTE
        elif role == cls.CASE_SORTIE:
            return cls.CHAR_REPR_SORTIE
        elif role == cls.CASE_ROBOT:
            return cls.CHAR_REPR_ROBOT
        elif role == cls.CASE_DANGER:
            return cls.CHAR_REPR_DANGER
        elif role == cls.CASE_BONUS:
            return cls.CHAR_REPR_BONUS
        else:
            return ""

    get_repr_for_role = classmethod(get_repr_for_role)

    def get_txt_for_role(cls, role):
        """
        Retourne le caractère de parsing associé à un rôle
        """
        if role == cls.CASE_VIDE:
            return cls.CHAR_TXT_VIDE
        elif role == cls.CASE_MUR or role == cls.CASE_MUR_PERIMETRE:
            return cls.CHAR_TXT_MUR
        elif role == cls.CASE_PORTE:
            return cls.CHAR_TXT_PORTE
        elif role == cls.CASE_SORTIE:
            return cls.CHAR_TXT_SORTIE
        elif role == cls.CASE_ROBOT:
            return cls.CHAR_TXT_ROBOT
        elif role == cls.CASE_DANGER:
            return cls.CHAR_TXT_DANGER
        elif role == cls.CASE_BONUS:
            return cls.CHAR_TXT_BONUS
        else:
            return ""

    get_txt_for_role = classmethod(get_txt_for_role)


class LabLevel:
    """
    Niveau multi-couches (matrices, couches animées) modélisant la carte d'une partie.
    """

    def __init__(self):
        """
        Constructeur
        """
        # Applat complet :
        self._full_flat_matrice = Matrice()
        # Applat partiel dédié au parsing :
        self._parsing_flat_matrice = Matrice()
        # Indicateur de mise à jour :
        self._flat_matrice_updated = False
        # Cache de typecase sur l'applat complet :
        self._fullflat_typecase_cache = dict()
        # cache d'applats :
        self._full_cache_applats = dict()
        self._cache_zindex = None
        self._cache_zindex_list = list()
        # Couches :
        self._zindex_list = list()
        self._limited_zindex_list = list()
        self._layersdict = dict()
        self._create_layers()
        # ref de la sortie :
        self._case_sortie = None
        # log de modifications :
        self._change_log = None
        self._step_change_log = None
        self._change_log_increment = 0
        self.init_level_before_changes()

    #-----> Méthodes de base
    def _create_layers(self):
        """
        Initialise les différentes couches
        """
        # init :
        n = len(LabHelper.ZINDEX_CASE_LIST)
        i = 0
        while i < n:
            self._zindex_list.append(None)
            i += 1
        # couches par type de case
        for zdict in LabHelper.ZINDEX_CASE_LIST:
            z = zdict["z"]
            typecase = zdict["typecase"]
            if typecase in [LabHelper.CASE_ANIMATION, LabHelper.CASE_DEBUG]:
                self._layersdict[typecase] = AnimatedLayer()
                self._full_cache_applats[z] = AnimatedLayer()
            else:
                self._layersdict[typecase] = Matrice()
                self._full_cache_applats[z] = Matrice()
            self._zindex_list[z] = self._layersdict[typecase]
        # liste limitée d'indexs pour parsing :
        limitedtypes = LabHelper.LIMITED_CASETYPES
        for layermat in self._zindex_list:
            for k, v in self._layersdict.items():
                if v == layermat and k in limitedtypes:
                    self._limited_zindex_list.append(layermat)

    def _get_zindex(self, typecase):
        """
        Retourne le zindex de la couche associée à typecase
        """
        for zdict in LabHelper.ZINDEX_CASE_LIST:
            z = zdict["z"]
            tc = zdict["typecase"]
            if tc == typecase:
                return z
        return None

    def _get_typecase(self, z):
        """
        Réciproque de _get_zindex
        """
        for zdict in LabHelper.ZINDEX_CASE_LIST:
            zi = zdict["z"]
            typecase = zdict["typecase"]
            if zi == z:
                return typecase
        return None

    def move_case(self, case, nextx, nexty):
        """
        Déplace une case aux coordonnées nextx, nexty
        """
        coords1 = (int(case.x), int(case.y))
        coords2 = (nextx, nexty)
        # change log :
        coords = [coords1, coords2]
        self._register_change_log("move", case, coords)
        # déplacement :
        self._layersdict[case.type_case].move_case(case, nextx, nexty)
        # gestion des interdépendances (suppressions, discard de cache) :
        self._handle_dependancies(case.type_case, case.x, case.y)

    def set_case(self, case):
        """
        Ajoute ou modifie une case
        """
        typecase = case.type_case
        # debug : à supprimer
        if typecase == LabHelper.CASE_TARGET:
            lc = self._layersdict[LabHelper.CASE_TARGET].get_list_cases()
            for c in lc:
                self._layersdict[LabHelper.CASE_TARGET].delete_case(c)
        # change log :
        self._register_change_log("add", case, [(case.x, case.y)])
        # ajout à la couche concernée :
        self._layersdict[typecase].set_case(case)
        case.on_case_added()
        # gestion des interdépendances (suppressions, discard de cache) :
        self._handle_dependancies(typecase, case.x, case.y)
        # cas particulier des robots :
        if typecase == LabHelper.CASE_ROBOT:
            # on enlève l'éventuel bonus ou danger antérieur
            others = self.get_cases_with_same_coords(case)
            dellist = [
                c
                for c in others
                if c.type_case in [LabHelper.CASE_BONUS, LabHelper.CASE_DANGER]
            ]
            for c in dellist:
                self.delete_case(c)

    def _handle_dependancies(self, typecase, x, y):
        """
        Prend en charge les interdépendances entre cases (suppression, discard de cache). 
        Les paramètres correspondent à une case crée ou modifiée
        """
        linkedtypes = LabHelper.LINKED_CASETYPES
        case_remove = None
        list_tc = [typecase]
        if typecase in linkedtypes:
            for tc in linkedtypes:
                if tc != typecase:
                    linkedmat = self._layersdict[tc]
                    case_remove = linkedmat.get_case(x, y)
                    if case_remove != None:
                        # change log :
                        self._register_change_log("delete", case_remove, [(x, y)])
                        # suppression :
                        linkedmat.delete_case(case_remove)
                        list_tc.append(tc)
        # Gestion du cache :
        for tc in list_tc:
            self.discard_cache(tc)

    def get_cases_with_same_coords(self, target):
        """
        Retourne toutes les cases de même coords que target
        """
        rset = set()
        k = (target.x, target.y)
        for i in LabHelper.ZINDEX_COORDS_SEARCH:
            layermat = self._zindex_list[i]
            if isinstance(layermat, Matrice):
                matdict = layermat.get_inner_dict()
                if k in matdict.keys():
                    rset.add(matdict[k])
            elif isinstance(layermat, AnimatedLayer):
                layset = layermat.get_set_cases()
                for c in layset:
                    if (c.x, c.y) == k:
                        rset.add(c)
        rset = rset.difference({target})
        return rset

    def delete_case(self, case):
        """
        Supprime une case
        """
        typecase = case.type_case
        if typecase not in LabHelper.FAMILLE_CASES_UNDELETABLE:
            # change log :
            self._register_change_log("delete", case, [(case.x, case.y)])
            # suppression :
            self._layersdict[typecase].delete_case(case)
            self.discard_cache(typecase)

    def mark_case_as_modified(self, case):
        """
        Ajoute la case à la liste "add" des changelogs d'étape
        """
        if case not in self._step_change_log["cases_added"]:
            self._step_change_log["cases_added"].append(case)

    def clear(self, typecase=None, complete=False):
        """
        Efface une ou toutes les couches du niveau
        
        Args:
            typecase : typage du LabHelper
            complete : efface toutes les couches        
        """
        done = False
        if typecase in self._layersdict.keys():
            self._layersdict[typecase].clear()
            self._clear_change_log(typecase)
            self._on_typecase_cleared(typecase)
            done = True
        if complete:
            for k in self._layersdict.keys():
                self._layersdict[k].clear()
                self._on_typecase_cleared(k)
                self._clear_change_log(k)
            done = True
        if done:
            if typecase in self._layersdict.keys():
                self.discard_cache(typecase)
            if complete:
                self.discard_cache(full=True)

    def _on_typecase_cleared(self, typecase):
        """
        Enregistre le clear dans les changements d'étape
        """
        if typecase not in self._step_change_log["cleared_typecases"]:
            self._step_change_log["cleared_typecases"].append(typecase)

    def get_dimensions(self):
        """
        Retourne w, h
        """
        fmat = self.get_flat_matrice()
        if fmat != None:
            return fmat.get_dimensions()
        return 0, 0

    def get_layer(self, typecase):
        """
        Retourne la matrice associée au type_case
        """
        if typecase in self._layersdict.keys():
            return self._layersdict[typecase]
        return None

    def get_sublevel(self, x, y, w, h):
        """
        Retourne le sous niveau d'origine x, y et de dims w, h
        """
        sl = LabLevel()
        for k, v in self._layersdict.items():
            sl._layersdict[k] = v.get_submatrice(x, y, w, h)
        return sl

    def get_animation_matrice(self):
        """
        Retourne la projection de la couche d'animation sous forme de matrice. 
        Usage : animation de type "face"
        """
        anim_lay = self.get_layer(LabHelper.CASE_ANIMATION)
        anim_mat = anim_lay.project_layer_on_matrice("anim_uid")
        return anim_mat

    def __repr__(self):
        ch = "LabLevel :\n"
        for k, v in self._layersdict.items():
            ch += k + " len=" + str(len(v.get_list_cases())) + "\n"
        return ch

    #-----> Cache
    def discard_cache(self, typecase, full=False):
        """
        Appelée lorsqu'un changement de case (coords ou type) rend les applats obsolètes
        """
        if typecase != None:
            if typecase in LabHelper.LINKED_CASETYPES:
                n0 = len(self._full_cache_applats[0].get_list_cases())
                n1 = len(self._full_cache_applats[1].get_list_cases())
                if n0 * n1 == 0:
                    # périmètre et sortie non crées
                    z = 0
                else:
                    z = 2
            else:
                z = self._get_zindex(typecase)
        elif full:
            z = 0
        if z != None:
            self._cache_zindex_list.append(z - 1)
        self._flat_matrice_updated = False

    def update_cache(self):
        """
        Met à jour les applats
        """
        self._update_flat_matrices()
        self._flat_matrice_updated = True
        self._build_fullflat_typecase_cache()

    #-----> Applats du LabLevel en Matrices
    def get_flat_matrice(self, full=True, guidedicated=False):
        """
        Retourne la matrice représentant l'applat de couches
        
        * si full = True : toutes les couches sont publiées
        * si full = False : seules les couches nécessaires au parsing le sont
        * si guidedicated = True : matrice dédiée aux GUIs graphiques, en pratique 
          la même matrice que celle dédiée au parsing
        
        """
        if not self._flat_matrice_updated:
            self.update_cache()
        if full:
            if not guidedicated:
                return self._full_flat_matrice
            else:
                return self._parsing_flat_matrice
        else:
            return self._parsing_flat_matrice

    def _update_flat_matrices(self):
        """
        Met à jour :
        
        * la matrice représentant les couches nécessaires au parsing
        * la matrice représentant l'applat de toutes les couches
        
        """
        # recherche de l'index :
        self._cache_zindex_list.sort()
        if len(self._cache_zindex_list) > 0:
            self._cache_zindex = self._cache_zindex_list[0]
        # cache invariant :
        invcache = self._full_flat_matrice.get_invariant_cache()
        # on repart du dernier index à jour :
        layer0 = self._limited_zindex_list[0]
        maxzparse = len(self._limited_zindex_list) - 1
        if self._cache_zindex != None and self._cache_zindex >= 0:
            zstart = self._cache_zindex
            full_matstart = self._full_cache_applats[zstart]
            parsezstart = min(zstart, maxzparse)
            parse_matstart = self._full_cache_applats[parsezstart]
        else:
            zstart = 0
            full_matstart = parse_matstart = layer0
        if zstart == 0:
            self._full_cache_applats[0] = layer0.copy()
        # copies initiales :
        self._parsing_flat_matrice = parse_matstart.copy()
        self._full_flat_matrice = full_matstart.copy()
        # cache matrice (niveau 3 : complet):
        self._full_flat_matrice.set_matrice_cache(3, invariantcache=invcache)
        # Partie 1 :
        i = zstart + 1
        n1 = len(self._limited_zindex_list)
        while i < n1:
            layermat = self._limited_zindex_list[i]
            self._full_cache_applats[i] = self._full_cache_applats[i - 1].copy()
            for c in layermat.get_list_cases():
                self._parsing_flat_matrice.set_case(c)
                self._full_flat_matrice.set_case(c)
                self._full_cache_applats[i].set_case(c)
            i += 1
        # Partie 2 :
        j = i
        n2 = len(self._zindex_list)
        while j < n2:
            layermat = self._zindex_list[j]
            self._full_cache_applats[j] = self._full_cache_applats[j - 1].copy()
            for case in layermat.get_list_cases():
                if case.visible:
                    # Applat complet
                    if case.type_case == LabHelper.CASE_ROBOT:
                        # on ne publie pas les robots éliminés
                        if case.alive:
                            self._full_flat_matrice.set_case(case)
                            self._full_cache_applats[j].set_case(case)
                    else:
                        self._full_flat_matrice.set_case(case)
                        self._full_cache_applats[j].set_case(case)
            j += 1
        self._cache_zindex = n2 - 1
        self._cache_zindex_list = list()

    #-----> Cache par type_case sur l'applat complet
    def _build_fullflat_typecase_cache(self):
        """
        Construit le cache par type_case sur self._full_flat_matrice après sa
        mise à jour
        """
        # structure de données :
        self._fullflat_typecase_cache = dict()
        # familles de cases couramment utilisées :
        familles = [
            LabHelper.FAMILLE_CASES_LIBRES,
            LabHelper.FAMILLE_CASES_DANGERS,
            LabHelper.FAMILLE_CASES_ADVERSAIRES,
            LabHelper.FAMILLE_CASES_BONUS,
            LabHelper.FAMILLE_CASES_MURS,
            LabHelper.FAMILLE_CASES_NO_ACTION,
        ]
        # alimentation :
        for f in familles:
            name = self._get_name_for_typecase_famille(f)
            if name != None:
                # famille
                self._fullflat_typecase_cache[name] = set()
                # types inclus
                for tc in f:
                    tclist = self._full_flat_matrice.get_case_by_type(tc)
                    self._fullflat_typecase_cache[tc] = set(tclist)
                    self._fullflat_typecase_cache[name].update(
                        self._fullflat_typecase_cache[tc]
                    )

    def get_typecase_set(self, typecase):
        """
        Retourne le set de cases associées à typecase dans l'applat complet
        
        Args:
            typecase : famille courante (voir _build_fullflat_typecase_cache) ou type_case unitaire (dans LabHelper.FULL_CASETYPES)
        """
        if not self._flat_matrice_updated:
            self.update_cache()
        rset = None
        keyname = self._get_name_for_typecase_famille(typecase)
        if keyname != None:
            # mot clef associé à une famille de cases
            typecase = keyname
        if typecase in self._fullflat_typecase_cache.keys():
            rset = self._fullflat_typecase_cache[typecase]
        elif typecase in LabHelper.FULL_CASETYPES:
            # création de l'entrée :
            tclist = self._full_flat_matrice.get_case_by_type(typecase)
            self._fullflat_typecase_cache[typecase] = set(tclist)
            rset = self._fullflat_typecase_cache[typecase]
        return rset

    def _get_name_for_typecase_famille(self, famille):
        """
        Retourne une chaine associée à la famille de cases
        """
        name = None
        if famille == LabHelper.FAMILLE_CASES_LIBRES:
            name = LabHelper.TYPE_CASES_LIBRES
        elif famille == LabHelper.FAMILLE_CASES_DANGERS:
            name = LabHelper.TYPE_CASES_DANGERS
        elif famille == LabHelper.FAMILLE_CASES_ADVERSAIRES:
            name = LabHelper.TYPE_CASES_ADVERSAIRES
        elif famille == LabHelper.FAMILLE_CASES_BONUS:
            name = LabHelper.TYPE_CASES_BONUS
        elif famille == LabHelper.FAMILLE_CASES_MURS:
            name = LabHelper.TYPE_CASES_MURS
        elif famille == LabHelper.FAMILLE_CASES_NO_ACTION:
            name = LabHelper.TYPE_CASES_NO_ACTION
        return name

    #-----> Change logs
    def init_level_before_changes(self):
        """
        Initialise les logs fins avant des changements
        """
        # cache d'impacts :
        self._init_impact_cache()
        # chang log :
        self._init_change_log()
        self.init_level_before_step_change()

    def init_level_before_step_change(self):
        """
        Initialise les logs de sous étape de transformation
        """
        # step change log :
        self._init_step_change_log()

    def get_change_log(self):
        """
        Retourne les logs de modifications
        """
        self._change_log["key"] = self._get_change_log_key()
        return self._change_log

    def get_step_change_log(self):
        """
        Retourne les logs de changement d'étape
        """
        return self._step_change_log

    def _init_change_log(self):
        """
        Initialise le suivi des changements dans les différentes couches. 
        Application : gestion fine du cache.
        """
        cl = self._change_log = dict()
        # Liste brute des coords ayant fait l'objet d'un changement
        cl["coords"] = list()
        # détails par typecase:
        for tc in self._layersdict.keys():
            cl[tc] = {"add": list(), "delete": list(), "move": list(), "cleared": False}
        # incrément de version :
        self._change_log_increment += 1
        cl["version"] = self._change_log_increment
        # clef
        cl["key"] = ""

    def _init_step_change_log(self):
        """
        Logs associés à une sous étape de transformation
        """
        self._step_change_log = {
            "coords": list(),
            "cases_added": list(),
            "cases_moved": list(),
            "cases_deleted": list(),
            "cleared_typecases": list(),
        }

    def _clear_change_log(self, typecase):
        """
        Indique que la couche de typecase a eu un clear
        """
        self._change_log[typecase]["cleared"] = True
        cl = self._layersdict[typecase].get_list_cases()
        for c in cl:
            if (c.x, c.y) != (None, None):
                tuppc = (int(c.x), int(c.y))
                if tuppc not in cl["coords"]:
                    cl["coords"].append(tuppc)

    def _register_change_log(self, typechange, case, coords):
        """
        Enregistre un changement suite à une action unitaire
        
        * typechange : "add", "delete", "move"
        * coords : liste de tupples (x, y)
        
        """
        typecase = case.type_case
        for tuppc in coords:
            x, y = tuppc[0], tuppc[1]
            if (x, y) != (None, None):
                tuppcint = (int(x), int(y))
                # change log
                if tuppcint not in self._change_log["coords"]:
                    self._change_log["coords"].append(tuppcint)
                tcl = self._change_log[typecase]
                if tuppcint not in tcl[typechange]:
                    tcl[typechange].append(tuppcint)
                # step change log :
                if tuppcint not in self._step_change_log["coords"]:
                    # on enregistre toutes les coords :
                    self._step_change_log["coords"].append(tuppcint)
                if typechange == "cleared":
                    # on enregistre tous les clears de changelogs
                    if typecase not in self._step_change_log["cleared"]:
                        self._step_change_log["cleared"].append(typecase)
                if typecase not in LabHelper.STEP_CHANGE_LOGS_EXCLUDED:
                    # cases animation omises
                    if typechange == "add":
                        self._step_change_log["cases_added"].append(case)
                    elif (
                        typechange == "delete"
                        and typecase not in LabHelper.LINKED_CASETYPES
                    ):
                        self._step_change_log["cases_deleted"].append(case)
                    elif typechange == "move":
                        self._step_change_log["cases_moved"].append(case)

    def _get_change_log_key(self):
        """
        Génère une clef représentant les changements apportés.
        """
        key = ""
        for z in LabHelper.ZINDEX_LOGS_KEY:
            tc = self._get_typecase(z)
            key += tc[0]
            chl_tc = self._change_log[tc]
            if chl_tc["cleared"]:
                key += "cleared"
            else:
                for action in ["add", "delete", "move"]:
                    lcoords = chl_tc[action]
                    key += action[0] + self._create_key_for_listcoords(lcoords)
        return key

    def _create_key_for_listcoords(self, listcoords):
        """
        Génère une clef en concaténant les nombres associés aux coords
        """
        key = ""
        if len(listcoords) > 0:
            # Trie :
            listcoords = sorted(listcoords, key=itemgetter(0, 1))
            # Transcription :
            for coords in listcoords:
                key += str(self._number_coords(coords))
        return key

    def _number_coords(self, coords):
        """
        Retourne un nombre associé aux coords (x, y)
        """
        w = self.get_dimensions()[0]
        n = coords[0] + coords[1] * w
        return n

    #-----> Utilitaires
    def get_case_sortie(self):
        """
        Retourne la case sortie
        """
        result = None
        if self._case_sortie != None:
            result = self._case_sortie
        else:
            if LabHelper.CASE_SORTIE in self._layersdict.keys():
                result = list(self._layersdict[LabHelper.CASE_SORTIE].get_list_cases())[
                    0
                ]
                self._case_sortie = result
        return result

    def get_sortie_coords(self):
        """
        Retourne les coordonnées de la sortie
        """
        result = (None, None)
        if self._case_sortie != None:
            result = (self._case_sortie.x, self._case_sortie.y)
        else:
            case = self.get_case_sortie()
            if case != None:
                result = (case.x, case.y)
        return result

    def get_distance_between_cases(self, case1, case2):
        """
        Calcul la distance entre deux cases
        """
        d = math.sqrt((case1.x - case2.x) ** 2 + (case1.y - case2.y) ** 2)
        return d

    def get_path_length_between_cases(self, case1, case2):
        """
        Calcul la distance du chemin entre deux cases
        """
        d = int(math.fabs(case1.x - case2.x) + math.fabs(case1.y - case2.y))
        return d

    def get_vector_for_cases(self, case1, case2):
        """
         Retourne un tuple représentant le vecteur allant de c1 à c2
         """
        return (case2.x - case1.x, case2.y - case1.y)

    def scalar_product(self, vect1, vect2):
        """
        Calcul le produit scalaire v1.v2
        """
        return vect1.x * vect2.x + vect1.y + vect2.y

    def get_dirs_for_vector(self, vect):
        """
        Retourne une liste de directions associées au vecteur
        """
        vx, vy = vect[0], vect[1]
        list_dirs = list()
        if vx > 0:
            list_dirs.append(LabHelper.RIGHT)
        if vx < 0:
            list_dirs.append(LabHelper.LEFT)
        if vy > 0:
            list_dirs.append(LabHelper.BOTTOM)
        if vy < 0:
            list_dirs.append(LabHelper.TOP)
        return list_dirs

    #-----> Cache d'impacts
    def _init_impact_cache(self):
        """
        Initialise les dicts de gestion du cache
        """
        # set des cases adjacentes impactées par un danger (non récursif)
        # clef = (x, y, impact), valeur = liste de cases
        self._dgr_adj_impacted = dict()
        # set des cases pouvant être atteintes par un jet de grenade par le robot
        # dans la direction donnée
        # clef = (robot.x, robot.y, robot.uid, direction), valeur = liste de cases
        # rq: robot n'est pas une clef valable, sa position peut changer lors
        # des calculs de recherche de coups
        self._reachable_by_bot_in_dir = dict()
        # dict de toutes les cases impactées de façon récursive par un danger
        # clef = (x, y, impact), valeur = dict d'impacts
        self._dgr_recursive_impacted = dict()
        # dict des dangers entourant une case
        # clef = (x, y), valeur = liste de cases dangers
        self._dgr_arround = dict()

    def _get_impact_cache_object(
        self, cache_type, danger=None, robot=None, direct=None, case=None
    ):
        """
        Recherche en cache d'un résultat de calcul d'impacts
        cache_type : adjacent, recursive, reachable, arround
        """
        result = "not in cache"
        if cache_type == "adjacent":
            k = (int(danger.x), int(danger.y), int(danger.danger_impact))
            d = self._dgr_adj_impacted
        elif cache_type == "recursive":
            k = (int(danger.x), int(danger.y), int(danger.danger_impact))
            d = self._dgr_recursive_impacted
        elif cache_type == "reachable":
            k = (int(robot.x), int(robot.y), robot.uid, direct)
            d = self._reachable_by_bot_in_dir
        elif cache_type == "arround":
            k = (int(case.x), int(case.y))
            d = self._dgr_arround
        if k in d.keys():
            result = d[k]
        return result

    def _set_impact_cache_object(
        self, cache_type, valeur, danger=None, robot=None, direct=None, case=None
    ):
        """
        Mise en cache d'un résultat de calcul d'impacts
        
        * cache_type : adjacent, recursive, reachable
        * valeur : résultat à stocker
        
        """
        if cache_type == "adjacent":
            k = (int(danger.x), int(danger.y), int(danger.danger_impact))
            d = self._dgr_adj_impacted
        elif cache_type == "recursive":
            k = (int(danger.x), int(danger.y), int(danger.danger_impact))
            d = self._dgr_recursive_impacted
        elif cache_type == "reachable":
            k = (int(robot.x), int(robot.y), robot.uid, direct)
            d = self._reachable_by_bot_in_dir
        elif cache_type == "arround":
            k = (int(case.x), int(case.y))
            d = self._dgr_arround
        d[k] = valeur

    #-----> Calcul d'impacts
    def get_minelist_arround_case(self, case):
        """
        Recherche les mines comprises dans la matrice 5*5 centrée sur case
        """
        # cache ?
        cachedlist = self._get_impact_cache_object("arround", case=case)
        if cachedlist != "not in cache":
            return cachedlist
        # coords des cases :
        flatmatrice = self.get_flat_matrice()
        coordset = flatmatrice.get_rectangle_coords(case.x - 2, case.y - 2, 5, 5)
        # Réduction des coordonnées
        realset = flatmatrice.get_coords_set()
        finalset = coordset.intersection(realset)
        # set de cases associées :
        caseset = set()
        if len(finalset) > 0:
            matdict = flatmatrice.get_inner_dict()
            caseset = set([matdict[coord] for coord in finalset])
        # extraction des cases dangers
        dgrlist = [c for c in caseset if c.type_case == LabHelper.CASE_DANGER]
        # mise en cache :
        self._set_impact_cache_object("arround", dgrlist, case=case)
        # retour :
        return dgrlist

    def get_cases_reachable_by_grenade_in_dir(self, robot, direct):
        """
        Retourne le set des cases atteignables par un jet de grenade
        dans la direction donnée.
        """
        # cache ?
        cached_set = self._get_impact_cache_object(
            "reachable", robot=robot, direct=direct
        )
        if cached_set != "not in cache":
            return cached_set
        # calcul initial
        flatmatrice = self.get_flat_matrice()
        rset = set()
        if robot.has_grenade:
            # axe, sens :
            if direct in [LabHelper.LEFT, LabHelper.RIGHT]:
                axis = LabHelper.AXIS_X
            else:
                axis = LabHelper.AXIS_Y
            if direct in [LabHelper.RIGHT, LabHelper.BOTTOM]:
                sens = LabHelper.DIR_POS
            else:
                sens = LabHelper.DIR_NEG
            # dimensions :
            portee = robot.portee_grenade
            puissance = max(robot.get_puissance_list("grenade"))
            dim = portee
            if puissance == 1:
                dim_orth = 1
            elif puissance in range(5, 10):
                dim_orth = 3
            elif puissance >= 13:
                dim_orth = 5
            # rectangle primaire :
            if axis == LabHelper.AXIS_X:
                w, h = dim, dim_orth
                prop, prop_orth = "x", "y"
            else:
                w, h = dim_orth, dim
                prop, prop_orth = "y", "x"
            pt = {"x": None, "y": None}
            if sens == LabHelper.DIR_POS:
                pt[prop] = robot[prop] + 1
            else:
                pt[prop] = robot[prop] - dim
            pt[prop_orth] = robot[prop_orth] - dim_orth // 2
            rset = flatmatrice.get_rectangle_coords(pt["x"], pt["y"], w, h)
            # empreinte supplémentaire :
            if robot.puissance_grenade >= 5:
                gen_dim = dim_orth
                last_pt = {"x": None, "y": None}
                last_pt[prop] = robot[prop] + sens * dim
                last_pt[prop_orth] = robot[prop_orth]
                gen_center_x, gen_center_y = last_pt["x"], last_pt["y"]
                gen_x, gen_y = gen_center_x - gen_dim // 2, gen_center_y - gen_dim // 2
                if puissance in [5, 13]:
                    gen_empreinte = flatmatrice.get_losange_coords
                    gen_args = [gen_center_x, gen_center_y, gen_dim]
                elif puissance in [9, 25]:
                    gen_empreinte = flatmatrice.get_rectangle_coords
                    gen_args = [gen_x, gen_y, gen_dim, gen_dim]
                elif puissance == 17:
                    gen_empreinte = flatmatrice.get_subshape_coords
                    gen_args = [gen_center_x, gen_center_y]
                empreinte_set = gen_empreinte(*gen_args)
                rset = rset.union(empreinte_set)
        # Réduction des coordonnées
        realset = flatmatrice.get_coords_set()
        finalset = rset.intersection(realset)
        # set de cases associées :
        caseset = set()
        if len(finalset) > 0:
            matdict = flatmatrice.get_inner_dict()
            caseset = set([matdict[coord] for coord in finalset])
        # mise en cache :
        self._set_impact_cache_object("reachable", caseset, robot=robot, direct=direct)
        # retour :
        return caseset

    def get_cases_adj_impacted_by_danger(self, casedanger):
        """
        Retourne le set des cases impactées par l'explosion d'un danger
        sans récursivité. 
        La case du danger n'est pas comptée.
        """
        # cache ?
        cached_set = self._get_impact_cache_object("adjacent", danger=casedanger)
        if cached_set != "not in cache":
            return cached_set
        # calcul initial
        caseset = set()
        impact = casedanger.danger_impact
        flatmatrice = self.get_flat_matrice()
        if impact > 1:
            # set de coordonnées :
            gen_empreinte = gen_args = None
            gen_x = gen_y = gen_center_x = gen_center_y = gen_dim = 0
            if impact in range(5, 10):
                gen_dim = 3
            elif impact >= 13:
                gen_dim = 5
            gen_center_x, gen_center_y = casedanger.x, casedanger.y
            gen_x, gen_y = gen_center_x - gen_dim // 2, gen_center_y - gen_dim // 2
            if impact in [5, 13]:
                gen_empreinte = flatmatrice.get_losange_coords
                gen_args = [gen_center_x, gen_center_y, gen_dim]
            elif impact in [9, 25]:
                gen_empreinte = flatmatrice.get_rectangle_coords
                gen_args = [gen_x, gen_y, gen_dim, gen_dim]
            elif impact == 17:
                gen_empreinte = flatmatrice.get_subshape_coords
                gen_args = [gen_center_x, gen_center_y]
            rset = gen_empreinte(*gen_args)
            # Réduction des coordonnées
            realset = flatmatrice.get_coords_set()
            finalset = rset.intersection(realset)
            # set de cases associées :
            caseset = set()
            if len(finalset) > 0:
                matdict = flatmatrice.get_inner_dict()
                caseset = set([matdict[coord] for coord in finalset])
            # retire la case danger au besoin :
            caseset = caseset.difference({casedanger, None})
        # mise en cache :
        self._set_impact_cache_object("adjacent", caseset, danger=casedanger)
        return caseset

    def xlook_for_cases_impacted(self, casedanger, count=0, dictimpact=None):
        """
        Identification récursive des cases impactées par l'activation d'un danger
        
        Retourne un dictionnaire :
        
        - dictimpact["danger_done"] : usage interne
        - dictimp["flat_list"] : liste (set) complète des cases impactées
        - dictimpact[0] : liste (set) de tupples (case, impact) des cases touchées au pas 0
        - ...
        - dictimpact[n] : liste (set) de tupples (case, impact) des cases touchées au pas n
        
        avec n : nombre de pas d'animation.
        
        Rq importante : les données mises en cache ne comprennent pas le danger initial.
        En effet lors des calculs de commandes automatiques, on simule des explosions
        avec des grenades virtuelles. On n'inclue le danger réel qu'au dernier moment.
        """
        # cache ?
        if count == 0:
            cached_dict = self._get_impact_cache_object("recursive", danger=casedanger)
            if cached_dict != "not in cache":
                # copie avec prise en compte de la case danger :
                fulldict = self._complete_recursive_impactdict_with_danger(
                    cached_dict, casedanger
                )
                return fulldict
        c = count
        impact = casedanger.danger_impact
        dictimp = dictimpact
        # init du dict :
        if dictimp == None:
            dictimp = dict()
            dictimp["danger_done"] = set()
            dictimp["flat_list"] = set()
        if c not in dictimp.keys():
            dictimp[c] = set()
        dictimp["danger_done"].add(casedanger)
        dictimp["flat_list"].add(casedanger)
        dictimp[c].add((casedanger, impact))
        # recherche des cases impactées :
        casestouchees = set()
        if casedanger.danger_type == CaseGrenade.DANGER_GRENADE:
            casestouchees = self.get_cases_with_same_coords(casedanger)
        casesadj = self.get_cases_adj_impacted_by_danger(casedanger)
        # ajout des cases adjacentes :
        casessuper = set()
        for case in casesadj:
            casestouchees.add(case)
            cwsm = self.get_cases_with_same_coords(case)
            casessuper = casessuper.union(cwsm)
        # cases superposées :
        casestouchees = casestouchees.union(casessuper)
        # répartition dans les dict en fonction de la distance au danger :
        for case in casestouchees:
            d = math.ceil(self.get_distance_between_cases(case, casedanger))
            # récursivité :
            if type(case) == CaseDanger and case not in dictimp["danger_done"]:
                self.xlook_for_cases_impacted(case, count=c + d, dictimpact=dictimp)
            else:
                if c + d not in dictimp.keys():
                    dictimp[c + d] = set()
                dictimp[c + d].add((case, impact))
                if case not in dictimp["flat_list"]:
                    dictimp["flat_list"].add(case)
        # finalisation :
        resultdict = dictimp
        if count == 0:
            # mise en cache (sans la case danger initiale)
            self._set_impact_cache_object("recursive", dictimp, danger=casedanger)
            # copie avec prise en compte de la case danger :
            resultdict = self._complete_recursive_impactdict_with_danger(
                dictimp, casedanger
            )
        # retour :
        return resultdict

    def _complete_recursive_impactdict_with_danger(self, cacheddict, danger):
        """
        Retourne une copie du dictionnaire généré par xlook_for_cases_impacted
        incluant la case danger
        """
        copydict = dict()
        # copie des set
        for k in cacheddict.keys():
            copydict[k] = cacheddict[k].copy()
        # ajout de la case danger :
        copydict["flat_list"].add(danger)
        copydict[0].add((danger, danger.danger_impact))
        # retour
        return copydict

    #-----> Zones d'action des robots
    def update_bot_action_zones(self, robot, nextgamble=False):
        """
        Interface de mise à jour des zones de mouvements et d'attaque du robot. 
        
        Args:
            nextgamble : si True limite la recherche aux coups à venir (considère 
                la vitesse courante au lieu de la vitesse "absolue")
        """
        if robot.alive:
            # zone de déplacement :
            robot.move_zone = self.get_bot_move_zone(robot, nextgamble=nextgamble)
            # zone d'attaque :
            robot.attack_zone = self.get_bot_attack_zone(robot, nextgamble=nextgamble)

    def get_bot_move_zone(self, robot, nextgamble=False):
        """
        Retourne le set de coords de la sous matrice de forme losange représentant
        le rayon de déplacement du robot.
        
        Args:
            nextgamble : si True limite la recherche aux coups à venir (considère 
                la vitesse courante au lieu de la vitesse "absolue")
        """
        coordset = set()
        flatmatrice = self.get_flat_matrice()
        if nextgamble:
            vit = robot.current_vitesse
        else:
            vit = robot.vitesse
        subm = flatmatrice.get_sublosange(robot.x, robot.y, 2 * vit + 1)
        if subm != None:
            coordset = subm.get_coords_set()
            # on exclue le périmètre
            excludedset = self.get_typecase_set(LabHelper.CASE_MUR_PERIMETRE)
            coordset = coordset.difference(excludedset)
        return coordset

    def get_bot_attack_zone(self, robot, nextgamble=False):
        """
        Retourne le set de coords de la sous matrice représentant les cases
        pouvant être impactées par le robot.
        
        Args:
            nextgamble : si True limite la recherche aux coups à venir (considère 
                la vitesse courante au lieu de la vitesse "absolue")
        """
        coordset = set()
        flatmatrice = self.get_flat_matrice()
        xr, yr = robot.x, robot.y
        directions = [LabHelper.TOP, LabHelper.BOTTOM, LabHelper.LEFT, LabHelper.RIGHT]
        if not robot.has_grenade or robot.puissance_grenade == 0:
            # Sans grenade la zone se résume à la zone de déplacement
            coordset = self.get_bot_move_zone(robot, nextgamble=nextgamble)
        else:
            # Avec grenade :
            if nextgamble:
                vit = robot.current_vitesse
            else:
                vit = robot.vitesse
            portee = robot.portee_grenade
            puissance = max(robot.get_puissance_list("grenade"))
            dim = portee + vit - 1
            if puissance in range(1, 5):
                dim_orth = 1
            elif puissance in range(5, 10):
                dim_orth = 3
            elif puissance >= 13:
                dim_orth = 5
            # zone d'impact centrale :
            central_set = set()
            h_x, h_y = xr - dim, yr - dim_orth // 2
            h_w, h_h = 2 * dim + 1, dim_orth
            main_hrect_set = flatmatrice.get_rectangle_coords(h_x, h_y, h_w, h_h)
            v_x, v_y = xr - dim_orth // 2, yr - dim
            v_w, v_h = dim_orth, 2 * dim + 1
            main_vrect_set = flatmatrice.get_rectangle_coords(v_x, v_y, v_w, v_h)
            central_set = central_set.union(main_hrect_set, main_vrect_set)
            if puissance > 1:
                # empreintes supplémentaires
                for direct in directions:
                    if direct in [LabHelper.LEFT, LabHelper.TOP]:
                        sens = -1
                    else:
                        sens = 1
                    gen_dim = dim_orth
                    if direct in [LabHelper.LEFT, LabHelper.RIGHT]:
                        gen_x = xr + sens * dim
                        gen_center_x = gen_x
                        gen_y = yr - gen_dim // 2
                        gen_center_y = yr
                    else:
                        gen_x = xr - gen_dim // 2
                        gen_center_x = xr
                        gen_y = yr + sens * dim
                        gen_center_y = gen_y
                    if puissance in [5, 13]:
                        gen_empreinte = flatmatrice.get_losange_coords
                        gen_args = [gen_center_x, gen_center_y, gen_dim]
                    elif puissance in [9, 25]:
                        gen_empreinte = flatmatrice.get_rectangle_coords
                        gen_args = [gen_x, gen_y, gen_dim, gen_dim]
                    elif puissance == 17:
                        gen_empreinte = flatmatrice.get_subshape_coords
                        gen_args = [gen_center_x, gen_center_y]
                    empreinte_set = gen_empreinte(*gen_args)
                    central_set = central_set.union(empreinte_set)
            # zone d'impact liée à la vitesse :
            vitesse_set = set()
            if vit > 1:
                i = vit - 1
                while i > 0:
                    v_hrect_set = flatmatrice.get_rectangle_coords(
                        h_x + i, h_y - i, h_w - 2 * i, h_h + 2 * i
                    )
                    v_vrect_set = flatmatrice.get_rectangle_coords(
                        v_x - i, v_y + i, v_w + 2 * i, v_h - 2 * i
                    )
                    vitesse_set = vitesse_set.union(v_hrect_set, v_vrect_set)
                    i -= 1
            # zone d'impact globale :
            coordset = central_set.union(vitesse_set)
        # Réduction des coordonnées
        realset = flatmatrice.get_coords_set()
        coordset = coordset.intersection(realset)
        # on exclue le périmètre
        excludedset = self.get_typecase_set(LabHelper.CASE_MUR_PERIMETRE)
        coordset = coordset.difference(excludedset)
        # retour :
        return coordset

    def get_caseset_for_coordset(self, coordset):
        """
        Retourne le set de cases associé au set de coordonnées
        """
        caseset = set()
        if len(coordset) > 0:
            flatmatrice = self.get_flat_matrice()
            matdict = flatmatrice.get_inner_dict()
            caseset = set([matdict[coord] for coord in coordset])
        return caseset

    def evaluate_bot_attack_proba_for_robot(self, robot, bot):
        """
        Evalue pour les cases de robot.move_zone la probabilité d'attaque
        possible par bot. 
        Rq : approximations rapides et sous évaluées. Méthode destinée à des
        situations désespérées.
        """
        # 1- données
        # dict de retour (key=case, val=proba)
        rdict = dict()
        # zone de mouvement de robot :
        r_move_set = robot.move_zone
        r_move_c_set = self.get_caseset_for_coordset(r_move_set)
        # alimentation de rdict par des probas nulles
        for c in r_move_c_set:
            rdict[c] = 0
        # intersection :
        b_attack_set = bot.attack_zone
        inter_set = b_attack_set.intersection(r_move_set)
        inter_cases_set = self.get_caseset_for_coordset(inter_set)
        # 2- qualification des directions en termes de densité de cases libres
        # exprimant la facilité de bot à se déplacer (approximation)
        # zone de mouvement de bot
        b_move_set = bot.move_zone
        b_move_c_set = self.get_caseset_for_coordset(b_move_set)
        dirdict = dict()
        for direct in LabHelper.LIST_DIRECTIONS:
            caseset = None
            if direct == LabHelper.LEFT:
                caseset = [c for c in b_move_c_set if c.x <= bot.x]
            elif direct == LabHelper.RIGHT:
                caseset = [c for c in b_move_c_set if c.x >= bot.x]
            elif direct == LabHelper.TOP:
                caseset = [c for c in b_move_c_set if c.y <= bot.y]
            elif direct == LabHelper.BOTTOM:
                caseset = [c for c in b_move_c_set if c.y >= bot.y]
            # densité de cases libres dans la direction :
            if len(caseset) > 0:
                cvide = 0
                cdanger = 0
                for c in caseset:
                    if c.type_case in LabHelper.FAMILLE_CASES_LIBRES:
                        cvide += 1
                    elif c.type_case == LabHelper.CASE_DANGER:
                        cdanger += 1
                dvide = cvide / len(caseset)
                ddanger = cdanger / len(caseset)
            else:
                dvide = 0
                ddanger = 0
            dirdict[direct] = {"vide": dvide, "danger": ddanger}
        # 3- évaluation de la probabilité d'attaque pour chaque case de
        # l'intersection :
        dmax = max(1, bot.get_danger_radius() - 1)
        for c in inter_cases_set:
            if c == bot:
                proba = 1
            else:
                # vecteur bot / case
                v = self.get_vector_for_cases(bot, c)
                listdirect = self.get_dirs_for_vector(v)
                # densités moyennes de cases libres et dangers associées aux
                # directions
                dvide = 0
                ddanger = 0
                for direct in listdirect:
                    dvide += dirdict[direct]["vide"]
                    ddanger += dirdict[direct]["danger"]
                dvide /= len(listdirect)
                ddanger /= len(listdirect)
                # distance
                d = self.get_path_length_between_cases(bot, c)
                # proportion de déplacement : à valeur dans [0.5; 1]
                prop = (1 + (dmax - d) / dmax) / 2
                # pseudo probabilité exprimant la facilité d'accès à la case
                if robot.has_grenade:
                    # les dangers vont faciliter l'approche / l'attaque
                    proba = (prop + dvide + ddanger) / 2
                else:
                    proba = (prop + dvide) / 2
                proba = math.ceil(proba * 100) / 100
            rdict[c] = proba
        # retour :
        return rdict


class Matrice:
    """
    Modélise une couche d'un niveau de jeu
    """

    def __init__(self, cachelevel=0, invariantcache=None):
        """
        Constructeur
        
        Args:
            cachelevel: niveau de cache
            invariantcache: cache invariant (coords)
        
        cachelevel à valeur dans :
        
        0. rien (défaut)
        1. liste et set complet de cases
        2. plus cache de lignes, colonnes et submatrices (subshapes) et des 
            coords associées
        3. plus cache invariant (conservation des coords du cache de niveau 2)
        
        """
        # dict principal k=(case.x, case.y), v=case
        self._matrice = dict()
        # ref à une éventuelle Matrice mère
        self._parent_matrice = None
        # propriétés géométriques
        self._width = None
        self._height = None
        self._lefttoppoint = None, None
        self._centerpoint = None, None
        # cache
        # Niveau de mise en cache:
        # 0 : rien (défaut)
        # 1 : liste et set complet de cases
        # 2: + cache de lignes, colonnes et submatrices (subshapes) et des coords associées
        # 3 : + cache invariant (conservation des coords du cache de niveau 2)
        self._cachelevel = 0
        # cache invariant (valeurs = liste de coords)
        self._invariant_cache = invariantcache
        # cache temporaire
        self._temp_cache = None
        # initialisation du cache
        self._init_cache(cachelevel)

    #-----> Cache
    def set_matrice_cache(self, cachelevel, invariantcache=None):
        """
        Activation différée du cache interne avec cachelevel :
        
        0. (rien),
        1. (liste/set des cases, set de leurs coords),
        2. (plus lignes, colonnes, sous matrices)
        3. (plus cache invariant)
        
        """
        self._invariant_cache = invariantcache
        self._init_cache(cachelevel)

    def _init_cache(self, cachelevel):
        """
        Initialise les dicts de gestion du cache temporaire
        
        Args:
            cachelevel : 0, 1, 2 ou 3
        """
        if isinstance(cachelevel, int) and cachelevel in range(1, 4):
            self._cachelevel = cachelevel
        else:
            self._cachelevel = 0
        # destruction du cache temporaire :
        self._temp_cache = {
            "theoric_coords": None,
            "coords": None,
            "case_set": None,
            "case_list": None,
            "line": None,
            "column": None,
            "rectangle_coords": None,
            "losange_coords": None,
            "subshape_coords": None,
            "submatrice": None,
            "subshape": None,
            "sublosange": None,
            "impacted": None,
        }
        # - niveau 1
        if self._cachelevel >= 1:
            # cache de la liste complète de cases
            self._temp_cache["case_list"] = None
            # cache du set complet de cases
            self._temp_cache["case_set"] = None
            # cache du set de coords
            self._temp_cache["coords"] = None
            self._temp_cache["theoric_coords"] = None
        # - niveau 2 :
        if self._cachelevel >= 2:
            # cache de lignes :
            # clef=index de ligne, valeur=ligne (list)
            self._temp_cache["line"] = dict()
            # cache de colonnes :
            # clef=index de colonne, valeur=colonne (list)
            self._temp_cache["column"] = dict()
            # cache de coords de rectangles :
            # clef=(x,y,w,h), valeur = set de coords
            self._temp_cache["rectangle_coords"] = dict()
            # cache de coordonnées de losanges :
            # clef=(xc,yc,dim), valeur = set de coords
            self._temp_cache["losange_coords"] = dict()
            # cache de coords de subshape :
            # clef=(x,y), valeur = set de coords
            self._temp_cache["subshape_coords"] = dict()
            # cache de sous matrices :
            # clef=(x,y,w,h,strictmode), valeur=submatrice
            self._temp_cache["submatrice"] = dict()
            # cache de subshapes :
            # clef=(x,y,shapefactor), valeur=subshape
            self._temp_cache["subshape"] = dict()
            # cache de sous losanges :
            # clef=(xc, yc, dim), valeur=sublosange
            self._temp_cache["sublosange"] = dict()
            # cases impactées par un danger :
            # clef=(x,y,impact), valeur=set de cases
            self._temp_cache["impacted"] = dict()
        # - niveau 3 :
        if self._cachelevel == 3:
            # cache invariant :
            if self._invariant_cache == None:
                self._invariant_cache = {
                    "theoric_coords": None,
                    "coords": None,
                    "line": dict(),
                    "column": dict(),
                    "rectangle_coords": dict(),
                    "losange_coords": dict(),
                    "subshape_coords": dict(),
                    "submatrice": dict(),
                    "subshape": dict(),
                    "sublosange": dict(),
                }
        else:
            self._invariant_cache = None

    def get_invariant_cache(self):
        """
        Retourne les données de cache invariantes fondées sur des listes
        de coordonnées
        """
        return self._invariant_cache

    def _set_cached_object(self, cachedobj, typeobject, **kwargs):
        """
        Met en cache un objet
        
        Args:
            cachedobj : l'objet à mettre en cache
            typeobject (str): line, column, submatrice, subshape, sublosange, case_list, 
                case_set, coords, theoric_coords, rectangle_coords, losange_coords, 
                subshape_coords, impacted 
            **kwargs : paramètres associés à l'objet        
        """
        # filtrage en fonction du niveau de cache
        if self._cachelevel == 0:
            return None
        elif self._cachelevel == 1 and typeobject not in [
            "case_list",
            "case_set",
            "coords",
            "theoric_coords",
        ]:
            return None
        elif self._cachelevel == 2 and typeobject not in [
            "case_list",
            "case_set",
            "coords",
            "theoric_coords",
            "line",
            "column",
            "submatrice",
            "subshape",
            "sublosange",
            "rectangle_coords",
            "losange_coords",
            "subshape_coords",
            "impacted",
        ]:
            return None
        # objets simples
        if typeobject in ["case_list", "case_set", "coords", "theoric_coords"]:
            # cache temporaire
            self._temp_cache[typeobject] = cachedobj
            # cache invariant :
            if self._cachelevel == 3 and typeobject in ["coords", "theoric_coords"]:
                self._invariant_cache[typeobject] = cachedobj
            # fin des traitements
            return
        # objets composés :
        else:
            listargs = list()
            key = None
            value = None
            listcoords = None
            if typeobject == "line":
                listargs = ["y"]
            elif typeobject == "column":
                listargs = ["x"]
            elif typeobject == "submatrice":
                listargs = ["x", "y", "w", "h", "strictmode"]
            elif typeobject == "sublosange":
                listargs = ["xc", "yc", "dim"]
            elif typeobject == "subshape":
                listargs = ["x", "y", "shapefactor"]
            elif typeobject == "rectangle_coords":
                listargs = ["x", "y", "w", "h"]
            elif typeobject == "losange_coords":
                listargs = ["xc", "yc", "dim"]
            elif typeobject == "subshape_coords":
                listargs = ["x", "y"]
            elif typeobject == "impacted":
                listargs = ["x", "y", "impact"]
            # 1- Test de validité :
            valide = cachedobj != None
            for k in listargs:
                if k not in kwargs.keys() or kwargs[k] == None:
                    valide = False
                    break
            # 2- Mise en cache :
            if valide:
                # données
                if typeobject in ["line", "column"]:
                    # liste
                    key = int(kwargs[listargs[0]])
                    value = cachedobj
                    if self._cachelevel == 3:
                        listcoords = set([(c.x, c.y) for c in value])
                else:
                    lk = [int(kwargs[k]) for k in listargs]
                    key = tuple(lk)
                    value = cachedobj
                    if self._cachelevel == 3:
                        if typeobject in ["submatrice", "sublosange", "subshape"]:
                            # matrice
                            listcoords = cachedobj.get_coords_set()
                        elif typeobject in [
                            "rectangle_coords",
                            "losange_coords",
                            "subshape_coords",
                        ]:
                            # sets de coords
                            listcoords = cachedobj
                # cache temporaire :
                self._temp_cache[typeobject][key] = value
                # cache invariant :
                if self._cachelevel == 3 and typeobject in self._invariant_cache.keys():
                    self._invariant_cache[typeobject][key] = listcoords

    def _get_cached_object(self, typeobject, **kwargs):
        """
        Retourne un objet mis en cache ou bien None
        
        Args:
            typeobject (str): line, column, submatrice, subshape, sublosange, case_list, 
                case_set, coords, theoric_coords, rectangle_coords, losange_coords, 
                subshape_coords, impacted 
            **kwargs : paramètres associés à l'objet
        
        """
        # filtrage en fonction du niveau de cache
        if self._cachelevel == 0:
            return None
        elif self._cachelevel == 1 and typeobject not in [
            "case_list",
            "case_set",
            "coords",
            "theoric_coords",
        ]:
            return None
        elif self._cachelevel == 2 and typeobject not in [
            "case_list",
            "case_set",
            "coords",
            "theoric_coords",
            "line",
            "column",
            "submatrice",
            "subshape",
            "sublosange",
            "rectangle_coords",
            "losange_coords",
            "subshape_coords",
            "impacted",
        ]:
            return None
        value = None
        # objets simples :
        if typeobject in ["case_list", "case_set", "coords", "theoric_coords"]:
            # cache temporaire
            value = self._temp_cache[typeobject]
            # cache invariant :
            if (
                value == None
                and self._cachelevel == 3
                and typeobject in ["coords", "theoric_coords"]
            ):
                value = self._invariant_cache[typeobject]
        # objets composés :
        else:
            listargs = list()
            key = None
            value = None
            listcoords = None
            if typeobject == "line":
                listargs = ["y"]
            elif typeobject == "column":
                listargs = ["x"]
            elif typeobject == "submatrice":
                listargs = ["x", "y", "w", "h", "strictmode"]
            elif typeobject == "sublosange":
                listargs = ["xc", "yc", "dim"]
            elif typeobject == "subshape":
                listargs = ["x", "y", "shapefactor"]
            elif typeobject == "rectangle_coords":
                listargs = ["x", "y", "w", "h"]
            elif typeobject == "losange_coords":
                listargs = ["xc", "yc", "dim"]
            elif typeobject == "subshape_coords":
                listargs = ["x", "y"]
            elif typeobject == "impacted":
                listargs = ["x", "y", "impact"]
            # 1- Test de validité :
            valide = True
            for k in listargs:
                if k not in kwargs.keys() or kwargs[k] == None:
                    valide = False
                    break
            # 2- Recherche dans le cache :
            if valide:
                if len(listargs) == 1:
                    key = int(kwargs[listargs[0]])
                else:
                    lk = [int(kwargs[k]) for k in listargs]
                    key = tuple(lk)
                # recherche dans le cache temporaire :
                if key in self._temp_cache[typeobject].keys():
                    value = self._temp_cache[typeobject][key]
                # recherche dans le cache invariant :
                if (
                    self._cachelevel == 3
                    and value == None
                    and typeobject in self._invariant_cache.keys()
                ):
                    if key in self._invariant_cache[typeobject].keys():
                        listcoords = self._invariant_cache[typeobject][key]
                        # reconstitution du cache temporaire :
                        if typeobject in ["line", "column"]:
                            # liste
                            value = [self._matrice[coord] for coord in listcoords]
                            if typeobject == "line":
                                value.sort(key=attrgetter("x"))
                            else:
                                value.sort(key=attrgetter("y"))
                        elif typeobject in ["submatrice", "sublosange", "subshape"]:
                            # matrice
                            cachelevel = 0
                            if self._cachelevel == 3:
                                cachelevel = 1
                            value = Matrice(cachelevel=cachelevel)
                            cachedmatdict = value.get_inner_dict()
                            for coord in listcoords:
                                cachedmatdict[coord] = self._matrice[coord]
                        elif typeobject in [
                            "rectangle_coords",
                            "losange_coords",
                            "subshape_coords",
                        ]:
                            # set de coords
                            value = listcoords
                        self._temp_cache[typeobject][key] = value
        # retour :
        return value

    #-----> Pptés géométriques
    def get_dimensions(self):
        """
        Retourne w, h
        """
        if self._width == None or self._height == None:
            self.compute_dimensions()
        return self._width, self._height

    def get_lefttop_point(self):
        """
        Retourne le point haut gauche
        """
        if self._lefttoppoint == (None, None):
            self.compute_dimensions()
        return self._lefttoppoint

    def get_center(self):
        """
        Retourne les coords (x, y) du point équivalent au centre
        """
        if self._centerpoint == (None, None):
            self.compute_dimensions()
        return self._centerpoint

    def compute_dimensions(self):
        """
        Calcul des dimensions
        """
        w = h = 0
        minx = miny = 0
        xlist = list()
        ylist = list()
        if len(self._matrice) > 0:
            lk = self._matrice.keys()
            for x, y in lk:
                xlist.append(x)
                ylist.append(y)
                w = max(w, x + 1)
                h = max(h, y + 1)
            minx = min(xlist)
            miny = min(ylist)
        self._width = int(w - minx)
        self._height = int(h - miny)
        self._lefttoppoint = int(minx), int(miny)
        self._centerpoint = (
            (self._lefttoppoint[0] + self._width - 1) / 2,
            (self._lefttoppoint[1] + self._height - 1) / 2,
        )

    def get_diagonale_len(self):
        """
        Retourne la dimension de sa diagonale
        """
        wm, hm = self.get_dimensions()
        return math.sqrt(wm ** 2 + hm ** 2)

    #-----> Gestion d'une case
    def get_case(self, x, y):
        """
        Getter de case
        """
        if (x, y) in self._matrice.keys():
            return self._matrice[(x, y)]
        return None

    def set_case(self, case, x=-1, y=-1):
        """
        Setter de case
        """
        xc, yc = x, y
        if (
            case != None
            and LabHelper.REGEXP_INT.match(str(case.x))
            and LabHelper.REGEXP_INT.match(str(case.y))
        ):
            xc, yc = case.x, case.y
        self._matrice[(xc, yc)] = case
        self._on_case_changed(case)

    def move_case(self, case, nextx, nexty):
        """
        Déplace la case aux coordonnées nextx, nexty
        """
        oldx, oldy = (int(case.x), int(case.y))
        del self._matrice[(oldx, oldy)]
        case.x, case.y = nextx, nexty
        self._matrice[(nextx, nexty)] = case
        self._on_case_changed(case)

    def delete_case(self, case):
        """
        Supprime une case
        """
        x, y = case.x, case.y
        if (x, y) in self._matrice.keys():
            del self._matrice[(x, y)]
            self._on_case_changed(case)

    def _on_case_changed(self, case):
        """
        Mise à jour du cache
        """
        if self._cachelevel in range(1, 4):
            if self._cachelevel >= 1:
                self._temp_cache["coords"] = None
                self._temp_cache["case_set"] = None
                self._temp_cache["case_list"] = None
            if self._cachelevel >= 2:
                d1cache = [self._temp_cache["line"], self._temp_cache["column"]]
                d2cache = [
                    self._temp_cache["submatrice"],
                    self._temp_cache["subshape"],
                    self._temp_cache["sublosange"],
                ]
                d3cache = [self._temp_cache["impacted"]]
                for d1c in d1cache:
                    for k, v in d1c.items():
                        if case in v:
                            del d1c[k]
                for d2c in d2cache:
                    for k, v in d2c.items():
                        if case in v.get_set_cases():
                            del d2c[k]
                for d3c in d3cache:
                    for k, v in d3c.items():
                        if case in v:
                            del d3c[k]

    #-----> Gestion globale
    def copy(self):
        """
        Retourne une copie
        """
        newMat = Matrice()
        # copie rapide (sans faire appel à set_case)
        for k, v in self._matrice.items():
            newMat._matrice[k] = v
        return newMat

    def clear(self):
        """
        Efface  toutes les cases de la matrice
        """
        del self._matrice
        self._matrice = dict()
        self._init_cache()

    def get_inner_dict(self):
        """
        Retourne le dict d'enregistrement des cases
        """
        return self._matrice

    def get_signature(self):
        """
        Retourne une chaine constituée des cuid de ses cases
        """
        signature = ""
        linemark = "|"
        h = self.get_dimensions()[1]
        j = 0
        while j < h:
            line = self.get_line(j)
            for c in line:
                signature += c.cuid
            signature += linemark
            j += 1
        return signature

    #-----> Getters de listes, sets, dicts
    def get_list_cases(self):
        """
        Retourne la liste de toutes les cases
        """
        # cache ?
        cachelist = self._get_cached_object("case_list")
        if cachelist != None:
            return cachelist
        # calcul et mise en cache :
        lc = self._compute_cases_cache()[0]
        # retour
        return lc

    def get_set_cases(self):
        """
        Retourne le set de toutes les cases
        """
        # cache ?
        cacheset = self._get_cached_object("case_set")
        if cacheset != None:
            return cacheset
        # calcul et mise en cache :
        sc = self._compute_cases_cache()[1]
        # retour
        return sc

    def _compute_cases_cache(self):
        """
        Met en cache la liste et le set de toutes les cases
        """
        # calcul
        lc = list(self._matrice.values())
        sc = set(lc)
        # mise en cache
        self._set_cached_object(lc, "case_list")
        self._set_cached_object(sc, "case_set")
        # retour
        return lc, sc

    def get_theoric_coords_set(self):
        """
        Retourne le set de toutes les coordonnées possibles de la matrice. 
        Rq : get_coords_set renvoit uniquement les coords utilisées
        """
        # cache ?
        cacheset = self._get_cached_object("theoric_coords")
        if cacheset != None:
            return cacheset
        # calcul et mise en cache :
        x, y = self.get_lefttop_point()
        w, h = self.get_dimensions()
        coordset = self.get_rectangle_coords(x, y, w, h)
        self._set_cached_object(coordset, "theoric_coords")
        # retour
        return coordset

    def get_coords_set(self):
        """
        Retourne le set de coords des cases de la matrice
        """
        # cache ?
        cacheset = self._get_cached_object("coords")
        if cacheset != None:
            return cacheset
        # calcul et mise en cache :
        caseset = self.get_set_cases()
        coordset = set([(c.x, c.y) for c in caseset])
        self._set_cached_object(coordset, "coords")
        # retour
        return coordset

    def get_segment(self, case1, case2):
        """
        Si case1 et case 2 sont sur la même ligne ou la même colonne, retourne la liste
        des cases constituant le segment (triée par coord croissante), ou None.
        """
        x1, y1 = case1.x, case1.y
        x2, y2 = case2.x, case2.y
        liste = None
        if x1 == x2:
            col = self.get_column(x1)
            liste = list()
            ly = [y1, y2]
            ly.sort()
            i = ly[0]
            while i <= ly[1]:
                liste.append(col[i])
                i += 1
            liste.sort(key=attrgetter("y"))
        if y1 == y2:
            ligne = self.get_line(y1)
            liste = list()
            lx = [x1, x2]
            lx.sort()
            i = lx[0]
            while i <= lx[1]:
                liste.append(ligne[i])
                i += 1
            liste.sort(key=attrgetter("x"))
        return liste

    def get_line(self, i):
        """
        Retourne la liste des cases de la ligne i
        """
        # cache
        cachedline = self._get_cached_object("line", y=i)
        if cachedline != None:
            return cachedline
        # calcul
        ligne = list()
        yref = self.get_lefttop_point()[1]
        for v in self._matrice.values():
            if v.y == i + yref:
                ligne.append(v)
        ligne.sort(key=attrgetter("x"))
        # mise en cache
        self._set_cached_object(ligne, "line", y=i)
        # retour
        return ligne

    def get_column(self, j):
        """
        Retourne la liste des cases de la colonne j
        """
        # cache
        cachedcol = self._get_cached_object("column", x=j)
        if cachedcol != None:
            return cachedcol
        # calcul
        col = list()
        xref = self.get_lefttop_point()[0]
        for v in self._matrice.values():
            if v.x == j + xref:
                col.append(v)
        col.sort(key=attrgetter("y"))
        # mise en cache
        self._set_cached_object(col, "column", x=j)
        # retour
        return col

    def get_cases_adjacentes(self, x, y):
        """
        Retourne le dict {"top":, "bottom":, "left":, "right":}
        """
        w, h = self.get_dimensions()
        cl = cr = ct = cb = None
        if 0 < x < w - 1:
            cl = self.get_case(x - 1, y)
            cr = self.get_case(x + 1, y)
        if 0 < y < h - 1:
            ct = self.get_case(x, y - 1)
            cb = self.get_case(x, y + 1)
        return {"left": cl, "right": cr, "top": ct, "bottom": cb}

    def get_cases_impacted_around(self, case, danger_impact):
        """
        Retourne le set des cases entourant case, impactées par un danger de puissance
        danger_impact
        """
        rset = set()
        if danger_impact == None or danger_impact not in [1, 5, 9, 13, 17, 25]:
            return rset
        else:
            # cache
            cachedset = self._get_cached_object(
                "impacted", x=case.x, y=case.y, impact=danger_impact
            )
            if cachedset != None:
                return cachedset
            flatmatrice = self.get_flat_matrice()
            coordset = None
            if danger_impact in range(5, 9):
                coordset = flatmatrice.get_losange_coords(case.x, case.y, 3)
            elif danger_impact in range(9, 13):
                coordset = self.get_rectangle_coords(case.x - 1, case.y - 1, 3, 3)
            elif danger_impact in range(13, 17):
                coordset = flatmatrice.get_losange_coords(case.x, case.y, 5)
            elif danger_impact in range(17, 25):
                coordset = self.get_subshape_coords(case.x, case.y)
            elif danger_impact >= 25:
                coordset = self.get_submatrice(case.x - 2, case.y - 2, 5, 5)
            if coordset != None:
                # réduction aux coordonnées existantes :
                realset = self.get_coords_set()
                finalset = coordset.intersection(realset)
                rset = set([self._matrice[coord] for coord in finalset])
            elif danger_impact == 1:
                rset.add(case)
            # mise en cache
            self._set_cached_object(
                rset, "impacted", x=case.x, y=case.y, impact=danger_impact
            )
            # retour
            return rset

    def get_case_by_type(self, typecase):
        """
        retourne la liste des cases de type typecase
        """
        rl = list()
        for v in self._matrice.values():
            if v.type_case == typecase:
                rl.append(v)
        return rl

    #-----> Référence à une éventuelle matrice mère
    def _get_parent_matrice(self):
        return self._parent_matrice

    def _set_parent_matrice(self, mat):
        if isinstance(mat, Matrice):
            self._parent_matrice = mat

    parent_matrice = property(
        _get_parent_matrice, _set_parent_matrice
    )  #: éventuelle matrice parente

    #-----> Getters de sous matrices
    def get_submatrice(self, x, y, w, h, strictmode=True, autocache=True):
        """
        Retourne une sous matrice
        
        * si strictmode : retourne la sous matrice d'origine x, y et de dims w, h ou None si
          les paramètres sont incohérents avec la géométrie de la matrice
        * sinon : retourne une sous matrice éventuellement tronquée
        
        """
        # cache
        cachedsubmat = self._get_cached_object(
            "submatrice", x=x, y=y, w=w, h=h, strictmode=strictmode
        )
        if cachedsubmat != None:
            return cachedsubmat
        # calcul
        # set de coordonnées générées:
        genset = self.get_rectangle_coords(x, y, w, h)
        # test de validité :
        valide = True
        if strictmode:
            # set de coordonnées maximal :
            maxset = self.get_theoric_coords_set()
            # set de coordonnées possibles :
            redset = genset.intersection(maxset)
            if len(redset) < len(genset):
                valide = False
            else:
                genset = redset
        # création de la sous matrice :
        subm = None
        if valide:
            # sous matrice :
            cachelevel = 0
            if autocache and self._cachelevel == 3:
                cachelevel = 1
            subm = Matrice(cachelevel=cachelevel)
            # réduction aux coordonnées existantes :
            realset = self.get_coords_set()
            finalset = genset.intersection(realset)
            # alimentation rapide :
            subdict = subm.get_inner_dict()
            for coord in finalset:
                subdict[coord] = self._matrice[coord]
            # parent ref :
            subm.parent_matrice = self
        # mise en cache
        self._set_cached_object(
            subm, "submatrice", x=x, y=y, w=w, h=h, strictmode=strictmode
        )
        # retour
        return subm

    def get_sublosange(self, xc, yc, dim):
        """
        Retourne une sous matrice tronquée en forme de losange, centrée en xc, yc
        et de dimension impaire dim.
        """
        # parité :
        if dim % 2 == 0:
            return None
        # cache
        cachedsubmat = self._get_cached_object("sublosange", xc=xc, yc=yc, dim=dim)
        if cachedsubmat != None:
            return cachedsubmat
        # coords théoriques du losange :
        thset = self.get_losange_coords(xc, yc, dim)
        # élimination des coords absurdes
        realset = self.get_coords_set()
        finalset = thset.intersection(realset)
        # création de la sous matrice :
        if len(finalset) > 0:
            # sous matrice :
            cachelevel = 0
            if self._cachelevel == 3:
                cachelevel = 1
            subm = Matrice(cachelevel=cachelevel)
            # copie rapide des cases :
            subdict = subm.get_inner_dict()
            for coord in finalset:
                subdict[coord] = self._matrice[coord]
            # parent ref :
            subm.parent_matrice = self
        # mise en cache
        self._set_cached_object(subm, "sublosange", xc=xc, yc=yc, dim=dim)
        # retour
        return subm

    def get_subshape(self, x, y, shapefactor=17):
        """
        Retourne une sous matrice tronquée de forme non rectangulaire.
        
        * x, y : centre de la forme
        * shapefactor : nombre de cases de la forme (17 : carré crénelé)
        
        Application : zones d'impacts
        """
        if shapefactor != 17:
            return None
        # cache
        cachedsubshape = self._get_cached_object(
            "subshape", x=x, y=y, shapefactor=shapefactor
        )
        if cachedsubshape != None:
            return cachedsubshape
        # calcul
        thset = self.get_subshape_coords(x, y)
        # élimination des coords absurdes
        realset = self.get_coords_set()
        finalset = thset.intersection(realset)
        # création de la sous matrice :
        if len(finalset) > 0:
            # sous matrice :
            cachelevel = 0
            if self._cachelevel == 3:
                cachelevel = 1
            subm = Matrice(cachelevel=cachelevel)
            # copie rapide des cases :
            subdict = subm.get_inner_dict()
            for coord in finalset:
                subdict[coord] = self._matrice[coord]
            # parent ref :
            subm.parent_matrice = self
        # mise en cache
        self._set_cached_object(subm, "subshape", x=x, y=y, shapefactor=shapefactor)
        # retour
        return subm

    #-----> Getters de sets de coordonnées
    def get_rectangle_coords(self, x, y, w, h):
        """
        Retourne les coordonnées des cases de la matrice de point haut gauche
        (x, y) et de dimensions w * h. 
        Rq : set complet, non réduit aux coords théoriques ou existantes
        """
        # cache
        cachedset = self._get_cached_object("rectangle_coords", x=x, y=y, w=w, h=h)
        if cachedset != None:
            return cachedset
        # calcul
        genset = set([coord for coord in self.gen_rectangle_coords(x, y, w, h)])
        # mise en cache
        self._set_cached_object(genset, "rectangle_coords", x=x, y=y, w=w, h=h)
        # retour
        return genset

    def get_losange_coords(self, xc, yc, dim):
        """
        Retourne les coordonnées des cases d'une matrice de forme losange,
        centrée en (xc, yc) et de dimension (impaire) dim. 
        Rq : set complet, non réduit aux coords théoriques ou existantes
        """
        # parité :
        if dim % 2 == 0:
            return set()
        # cache
        cachedset = self._get_cached_object("losange_coords", xc=xc, yc=yc, dim=dim)
        if cachedset != None:
            return cachedset
        # calcul :
        genset = set([coord for coord in self.gen_losange_coords(xc, yc, dim)])
        # mise en cache
        self._set_cached_object(genset, "losange_coords", xc=xc, yc=yc, dim=dim)
        # retour
        return genset

    def get_subshape_coords(self, xc, yc, shapefactor=17):
        """
        Retourne les coords d'une sous matrice 5*5 centrée en xc, yc, tronquée
        symétriquement à 17 cases. 
        Rq : set complet, non réduit aux coords théoriques ou existantes
        """
        if shapefactor != 17:
            return set()
        # cache
        cachedset = self._get_cached_object("subshape_coords", x=xc, y=yc)
        if cachedset != None:
            return cachedset
        # calcul
        genset = set([coord for coord in self.gen_subshape_coords(xc, yc)])
        # mise en cache
        self._set_cached_object(genset, "subshape_coords", x=xc, y=yc)
        # retour
        return genset

    #-----> Générateurs de sets de coordonnées
    def gen_rectangle_coords(self, x, y, w, h):
        """
        Génère les coordonnées des cases de la matrice de point haut gauche
        (x, y) et de dimensions w * h
        """
        for i in range(x, x + w):
            for j in range(y, y + h):
                yield (i, j)

    def gen_losange_coords(self, xc, yc, dim):
        """
        Génère les coordonnées des cases d'une matrice de forme losange,
        centrée en (xc, yc) et de dimension (impaire) dim. 
        Rq : la parité n'est pas vérifiée au niveau du générateur.
        """
        adim = dim // 2
        maxrange = range(xc - adim, xc + adim + 1)
        y0 = yc - adim
        for j in range(0, dim):
            dx = int(math.fabs(j - adim))
            xrange = range(maxrange.start + dx, maxrange.stop - dx)
            for i in xrange:
                yield (i, y0 + j)

    def gen_subshape_coords(self, xc, yc):
        """
        Retourne les coords d'une sous matrice 5*5 centrée en xc, yc, tronquée
        symétriquement à 17 cases
        """
        adim = 2
        maxrange = range(xc - adim, xc + adim + 1)
        y0 = yc - adim
        for j in range(0, 5):
            delta = int(math.fabs(j - adim))
            if delta == 2:
                xrange = range(maxrange.start, maxrange.stop, 2)
            elif delta == 1:
                xrange = range(maxrange.start + 1, maxrange.stop - 1)
            else:
                xrange = maxrange
            for i in xrange:
                yield (i, y0 + j)

    #-----> Particularisation
    def __repr__(self):
        return self._matrice.__repr__()

    def __str__(self):
        x, y = self.get_lefttop_point()
        w, h = self.get_dimensions()
        return "Matrice left={} top={} w={} h={}".format(x, y, w, h)


class AnimatedLayer:
    """
    Modélise une couche d'animation. 
    
    La clef d'identification d'une case ne peut plus être ses coordonnées (elles peuvent 
    varier, se recouvrir entre cases), mais un identifiant unique de case.
    """

    def __init__(self):
        """
        Constructeur
        """
        self._matrice = dict()

    def copy(self):
        """
        Retourne une copie
        """
        newAL = AnimatedLayer()
        # copie rapide (sans faire appel à set_case)
        for k, v in self._matrice.items():
            newAL._matrice[k] = v
        return newAL

    def set_case(self, case):
        """
        Setter de case
        """
        if case != None:
            if isinstance(case, CaseAnimation):
                uid = case.anim_uid
                self._matrice[uid] = case
            elif case.type_case == LabHelper.CASE_DEBUG:
                uid = case.cuid
                self._matrice[uid] = case

    def move_case(self, case, nextx, nexty):
        """
        Déplace la case aux coordonnées nextx, nexty
        """
        case.x, case.y = nextx, nexty

    def delete_case(self, case):
        """
        Supprime une case
        """
        if case != None and isinstance(case, CaseAnimation):
            uid = case.anim_uid
            if uid in self._matrice.keys():
                del self._matrice[uid]

    def clear(self):
        """
        Efface  toutes les cases de la matrice
        """
        self._matrice = dict()

    def get_list_cases(self):
        """
        Retourne la liste de toutes les cases
        """
        return list(self._matrice.values())

    def get_set_cases(self):
        """
        Retourne la liste de toutes les cases
        """
        return set(self._matrice.values())

    def project_layer_on_matrice(self, sortkey):
        """
        Projette la couche sur une matrice. Si deux cases ont les mêmes
        propriétés case.sortkey, celle de valeur la plus élévée sera retenue. 
        Application : projection de cases d'animation, avec sortkey="anim_uid"
        """
        m = Matrice()
        mdict = m.get_inner_dict()
        lc = self.get_list_cases()
        # trie par sortkey croissant :
        lc.sort(key=attrgetter(sortkey))
        for c in lc:
            # copie rapide :
            mdict[(c.x, c.y)] = c
        return m


class Case:
    """
    Modélise une case du Labyrinthe
    """

    # Compteur interne pour la création d'uid de case
    _CUID_COUNT = 0
    # méthodes statiques
    def get_default_dict(cls):
        """
        Méthode statique retournant le dict par défaut attendu par le constructeur
        """
        casedict = dict()
        casedict["x"] = None
        casedict["y"] = None
        casedict["type_case"] = None
        casedict["face"] = None
        casedict["visible"] = True
        return casedict

    get_default_dict = classmethod(get_default_dict)

    def generate_cuid(cls, case):
        """
        Génère un identifiant unique de case. 
        Usage : debug
        """
        char_tc = LabHelper.get_txt_for_role(case.type_case)
        num = str(cls._CUID_COUNT)
        cuid = char_tc + num
        cls._CUID_COUNT += 1
        return cuid

    generate_cuid = classmethod(generate_cuid)
    # méthodes
    def __init__(self, x, y, type_case, face, visible=True):
        """
        Constructeur de la case
        """
        self._x = None
        self._y = None
        self.x = x
        self.y = y
        self.type_case = type_case
        self.face = face
        self.visible = visible
        self.cuid = Case.generate_cuid(self)

    def get_properties_dict(self, full=True):
        """
        Retourne ses paramètres sous forme de dict
        """
        casedict = dict()
        casedict["x"] = self.x
        casedict["y"] = self.y
        casedict["type_case"] = self.type_case
        casedict["face"] = self.face
        casedict["visible"] = self.visible
        return casedict

    # getters / setters de coordonnées
    def _get_x(self):
        return self._x

    def _set_x(self, val):
        self._x = self.parseInt(val)

    x = property(_get_x, _set_x)  #: coord x

    def _get_y(self):
        return self._y

    def _set_y(self, val):
        self._y = self.parseInt(val)

    y = property(_get_y, _set_y)  #: coord y

    def parseBool(self, val):
        """
        Retourne un booléan
        """
        if str(val) == "True":
            return True
        return False

    def parseInt(self, val):
        """
        Retourne un int ou bien None
        """
        if LabHelper.REGEXP_INT.match(str(val)):
            return int(val)
        return None

    def parseFloat(self, val):
        """
        Retourne un Float ou bien None
        """
        if LabHelper.REGEXP_FLOAT.match(str(val)):
            return float(val)
        return None

    def on_case_added(self):
        """
        Appelée lorsque la case est ajoutée à une matrice via le LabLevel
        """
        pass

    def __getitem__(self, prop):
        """
        Rend l'objet "subscriptable"
        """
        return getattr(self, prop)

    def __repr__(self):
        return "Case cuid={} x={} y={} type_case={}".format(
            self.cuid, self.x, self.y, self.type_case
        )

    def __str__(self):
        return "Case cuid={} x={} y={} type_case={} face={} vis={}".format(
            self.cuid, self.x, self.y, self.type_case, self.face, self.visible
        )


class CaseRobot(Case):
    """
    Particularise une case de type robot
    """

    # Données de modélisation statiques :
    # marqueur de joueur humain
    BEHAVIOR_HUMAN = "BEHAVIOR_HUMAN"  #: marque un joueur de type humain
    # comportement des robots automatiques
    BEHAVIOR_WINNER = "BEHAVIOR_WINNER"  #: marque un joueur de type winner
    BEHAVIOR_RANDOM = "BEHAVIOR_RANDOM"  #: marque un joueur de type random
    BEHAVIOR_HUNTER = "BEHAVIOR_HUNTER"  #: marque un joueur de type chasseur
    BEHAVIOR_TOURIST = "BEHAVIOR_TOURIST"  #: marque un joueur de type touriste
    BEHAVIOR_BUILDER = "BEHAVIOR_BUILDER"  #: marque un joueur de type maçon
    BEHAVIOR_SAPPER = "BEHAVIOR_SAPPER"  #: marque un joueur de type mineur
    FAMILLE_BEHAVIOR = [
        BEHAVIOR_WINNER,
        BEHAVIOR_RANDOM,
        BEHAVIOR_HUNTER,
        BEHAVIOR_TOURIST,
        BEHAVIOR_BUILDER,
        BEHAVIOR_SAPPER,
    ]  #: types des joueurs automatiques
    ALL_BEHAVIORS = [
        BEHAVIOR_WINNER,
        BEHAVIOR_RANDOM,
        BEHAVIOR_HUNTER,
        BEHAVIOR_TOURIST,
        BEHAVIOR_BUILDER,
        BEHAVIOR_SAPPER,
        BEHAVIOR_HUMAN,
    ]  #: types exhaustifs
    # représentation par défaut :
    char_repr_BEHAVIOR_HUMAN = "A"  #: caractère d'affichage d'un humain
    char_repr_BEHAVIOR_WINNER = "W"  #: caractère d'affichage d'un winner
    char_repr_BEHAVIOR_RANDOM = "R"  #: caractère d'affichage d'un random
    char_repr_BEHAVIOR_HUNTER = "H"  #: caractère d'affichage d'un chasseur
    char_repr_BEHAVIOR_TOURIST = "T"  #: caractère d'affichage d'un touriste
    char_repr_BEHAVIOR_BUILDER = "B"  #: caractère d'affichage d'un maçon
    char_repr_BEHAVIOR_SAPPER = "S"  #: caractère d'affichage d'un mineur
    # vitesse initiale :
    VITESSE_INITIALE = 1  #: vitesse initiale du joueur"
    # Nombre de cases passées mémorisées au max
    MAX_PASSED_CASES = 10  #: nombre de cases passées mémorisées
    # Nombre de séquences (coups consécutifs) mémorisées :
    MAX_SEQ_COUNT = 4  #: nombre de séquences de coups mémorisées
    # seuils par capacités
    FEATURE_THRESHOLDS = None  #: seuils par capacités
    # seuils génériques
    THRES_MID = 0.5  #: seuil générique moyen
    THRES_HIGH = 0.7  #: seuil générique haut
    # liste des caractéristiques comportementales
    FEATURES = [
        "intelligence",
        "ambition",
        "instinct_survie",
        "curiosite",
        "aggressivite",
        "efficacite",
    ]  #: liste des caractéristiques comportementales
    # stratégies de recherche de bonus :
    STRAT_BONUS_ALL = "bonus_all"  #: stratégie n'importe quel bonus
    STRAT_BONUS_TARGET = "bonus_target"  #: stratégie bonus cohérents avec la cible
    # méthodes statiques
    def init_feature_thresholds(cls):
        """
        Initialise les seuils associés aux caractéristiques des robots.
        Rq : le dict permet de personnaliser les seuils pour chaque
        carcatéristique. En V1 on standardise.
        """
        cls.FEATURE_THRESHOLDS = dict()
        dft = cls.FEATURE_THRESHOLDS
        dft["efficacite"] = {
            "middle": CaseRobot.THRES_MID,
            "high": CaseRobot.THRES_HIGH,
        }
        dft["ambition"] = {"middle": CaseRobot.THRES_MID, "high": CaseRobot.THRES_HIGH}
        dft["instinct_survie"] = {
            "middle": CaseRobot.THRES_MID,
            "high": CaseRobot.THRES_HIGH,
        }
        dft["aggressivite"] = {
            "middle": CaseRobot.THRES_MID,
            "high": CaseRobot.THRES_HIGH,
        }
        dft["curiosite"] = {"middle": CaseRobot.THRES_MID, "high": CaseRobot.THRES_HIGH}
        dft["intelligence"] = {
            "middle": CaseRobot.THRES_MID,
            "high": CaseRobot.THRES_HIGH,
        }

    init_feature_thresholds = classmethod(init_feature_thresholds)

    def get_feature_threshold(cls, feature, level):
        """
        Retourne une valeur entre 0 et 1 pour une feature (efficacite, ...) et
        un level parmi "middle" ou "high"
        """
        val = None
        if feature in cls.FEATURE_THRESHOLDS.keys() and level in ["middle", "high"]:
            val = cls.FEATURE_THRESHOLDS[feature][level]
        return val

    get_feature_threshold = classmethod(get_feature_threshold)

    def get_feature_threshold_dict(cls):
        """
        Retourne le dict de seuils par caractéristiques.
        """
        if CaseRobot.FEATURE_THRESHOLDS == None:
            CaseRobot.init_feature_thresholds()
        return cls.FEATURE_THRESHOLDS

    get_feature_threshold_dict = classmethod(get_feature_threshold_dict)

    def get_default_dict(cls):
        """
        Méthode statique retournant le dict par défaut attendu par le constructeur
        """
        robotdict = Case.get_default_dict()
        robotdict["type_case"] = LabHelper.CASE_ROBOT
        robotdict["alive"] = True
        robotdict["uid"] = None
        robotdict["human"] = None
        robotdict["number"] = None
        robotdict["human_number"] = None
        robotdict["behavior"] = None
        robotdict["vitesse"] = CaseRobot.VITESSE_INITIALE
        robotdict["has_mine"] = False
        robotdict["has_grenade"] = False
        robotdict["puissance_mine"] = 1
        robotdict["puissance_grenade"] = 1
        robotdict["portee_grenade"] = 1
        robotdict["ambition"] = None
        robotdict["instinct_survie"] = None
        robotdict["aggressivite"] = None
        robotdict["curiosite"] = None
        robotdict["efficacite"] = None
        robotdict["intelligence"] = None
        robotdict["color"] = None
        robotdict["order"] = None
        return robotdict

    get_default_dict = classmethod(get_default_dict)

    def configure_behavior(cls, robot):
        """
        Méthode statique particularisant le comportement d'un robot
        V1 : gère le caractère de représentation texte
        """
        # plage de valeurs en fonction des seuils :
        vlow = 0
        vlowmid = math.ceil(CaseRobot.THRES_MID / 2 * 100)
        vmid = math.ceil(CaseRobot.THRES_MID * 100)
        vmidhigh = math.ceil((CaseRobot.THRES_MID + CaseRobot.THRES_HIGH) / 2 * 100)
        vhigh = math.ceil(CaseRobot.THRES_HIGH * 100)
        vhightop = math.ceil((1 + CaseRobot.THRES_HIGH) / 2 * 100)
        vtop = 100
        # en fonction du comportement :
        behavior = robot.behavior
        if behavior == CaseRobot.BEHAVIOR_WINNER:
            robot.efficacite = cr.CustomRandom.randrange(vhigh, vtop) / 100
            robot.ambition = cr.CustomRandom.randrange(vmid, vtop) / 100
            robot.instinct_survie = cr.CustomRandom.randrange(vhigh, vtop) / 100
            robot.aggressivite = cr.CustomRandom.randrange(vmid, vhightop) / 100
            robot.curiosite = cr.CustomRandom.randrange(vlow, vlowmid) / 100
            robot.intelligence = cr.CustomRandom.randrange(vhigh, vtop) / 100
        elif behavior == CaseRobot.BEHAVIOR_RANDOM:
            robot.efficacite = cr.CustomRandom.randrange(vlow, vtop) / 100
            robot.ambition = cr.CustomRandom.randrange(vlow, vlowmid) / 100
            robot.instinct_survie = cr.CustomRandom.randrange(vlow, vtop) / 100
            robot.aggressivite = cr.CustomRandom.randrange(vlow, vtop) / 100
            robot.curiosite = cr.CustomRandom.randrange(vlow, vtop) / 100
            robot.intelligence = cr.CustomRandom.randrange(vlow, vlowmid) / 100
        elif behavior == CaseRobot.BEHAVIOR_HUNTER:
            robot.efficacite = cr.CustomRandom.randrange(vmid, vtop) / 100
            robot.ambition = cr.CustomRandom.randrange(vmid, vtop) / 100
            robot.instinct_survie = cr.CustomRandom.randrange(vlowmid, vtop) / 100
            robot.aggressivite = cr.CustomRandom.randrange(vhigh, vtop) / 100
            robot.curiosite = cr.CustomRandom.randrange(vlow, vlowmid) / 100
            robot.intelligence = cr.CustomRandom.randrange(vmid, vtop) / 100
        elif behavior == CaseRobot.BEHAVIOR_TOURIST:
            robot.efficacite = cr.CustomRandom.randrange(vlow, vmid) / 100
            robot.ambition = cr.CustomRandom.randrange(vlow, vtop) / 100
            robot.instinct_survie = cr.CustomRandom.randrange(vlow, vmid) / 100
            robot.aggressivite = cr.CustomRandom.randrange(vlow, vlowmid) / 100
            robot.curiosite = cr.CustomRandom.randrange(vhightop, vtop) / 100
            robot.intelligence = cr.CustomRandom.randrange(vlow, vlowmid) / 100
        elif behavior == CaseRobot.BEHAVIOR_BUILDER:
            robot.efficacite = cr.CustomRandom.randrange(vlowmid, vhightop) / 100
            robot.ambition = cr.CustomRandom.randrange(vlow, vmidhigh) / 100
            robot.instinct_survie = cr.CustomRandom.randrange(vlowmid, vhigh) / 100
            robot.aggressivite = cr.CustomRandom.randrange(vlow, vmid) / 100
            robot.curiosite = cr.CustomRandom.randrange(vlow, vlowmid) / 100
            robot.intelligence = cr.CustomRandom.randrange(vlow, vmidhigh) / 100
        elif behavior == CaseRobot.BEHAVIOR_SAPPER:
            robot.efficacite = cr.CustomRandom.randrange(vlowmid, vtop) / 100
            robot.ambition = cr.CustomRandom.randrange(vlow, vmidhigh) / 100
            robot.instinct_survie = cr.CustomRandom.randrange(vlowmid, vmidhigh) / 100
            robot.aggressivite = cr.CustomRandom.randrange(vlow, vhightop) / 100
            robot.curiosite = cr.CustomRandom.randrange(vlow, vlowmid) / 100
            robot.intelligence = cr.CustomRandom.randrange(vlow, vlowmid) / 100
        elif behavior == CaseRobot.BEHAVIOR_HUMAN:
            robot.efficacite = vmid / 100
            robot.ambition = vmid / 100
            robot.instinct_survie = vmid / 100
            robot.aggressivite = vmid / 100
            robot.curiosite = vmid / 100
            robot.intelligence = vmid / 100

    configure_behavior = classmethod(configure_behavior)

    def get_features_radar_datas(self):
        """
        Retourne un dict permettant de tracer le graphe radar des
        caractéristiques du robot.
        """
        rdict = dict()
        clsdict = CaseRobot.FEATURE_THRESHOLDS
        for feature in clsdict:
            rdict[feature] = getattr(self, feature)
        return rdict

    def get_char_repr(self, behavior):
        """
        Retourne le char de représentation en fonction du comportement
        """
        if behavior == CaseRobot.BEHAVIOR_HUMAN:
            return CaseRobot.char_repr_BEHAVIOR_HUMAN
        elif behavior == CaseRobot.BEHAVIOR_WINNER:
            return CaseRobot.char_repr_BEHAVIOR_WINNER
        elif behavior == CaseRobot.BEHAVIOR_RANDOM:
            return CaseRobot.char_repr_BEHAVIOR_RANDOM
        elif behavior == CaseRobot.BEHAVIOR_HUNTER:
            return CaseRobot.char_repr_BEHAVIOR_HUNTER
        elif behavior == CaseRobot.BEHAVIOR_TOURIST:
            return CaseRobot.char_repr_BEHAVIOR_TOURIST
        elif behavior == CaseRobot.BEHAVIOR_BUILDER:
            return CaseRobot.char_repr_BEHAVIOR_BUILDER
        elif behavior == CaseRobot.BEHAVIOR_SAPPER:
            return CaseRobot.char_repr_BEHAVIOR_SAPPER

    get_char_repr = classmethod(get_char_repr)
    # méthodes d'instance
    def __init__(self, robotdict):
        """
        Constructeur de la case robot
        """
        # A la première instance crée
        if CaseRobot.FEATURE_THRESHOLDS == None:
            CaseRobot.init_feature_thresholds()
        # Création de l'instance
        Case.__init__(
            self,
            robotdict["x"],
            robotdict["y"],
            robotdict["type_case"],
            robotdict["face"],
            robotdict["visible"],
        )
        self.alive = self.parseBool(robotdict["alive"])
        self.uid = robotdict["uid"]
        self.human = False
        if robotdict["human"] in [True, "True"]:
            self.human = True
        self.number = robotdict["number"]
        self.human_number = robotdict["human_number"]
        if self.human:
            self.behavior = CaseRobot.BEHAVIOR_HUMAN
        else:
            self.behavior = robotdict["behavior"]
        # capacités pouvant être améliorées via les bonus
        self.vitesse = int(robotdict["vitesse"])
        self.has_mine = self.parseBool(robotdict["has_mine"])
        self.has_grenade = self.parseBool(robotdict["has_grenade"])
        self.puissance_mine = int(robotdict["puissance_mine"])
        self.puissance_grenade = int(robotdict["puissance_grenade"])
        self.portee_grenade = int(robotdict["portee_grenade"])
        # mémorisation des propriétés modifiées lors d'un coup
        self._gamble_properties_changes = list()
        # nombre total de coups dans le tour courant:
        self.current_gamble_count = 1
        # numéro du coup en cours
        self.current_gamble_number = 0
        # vitesse réelle à un instant donné
        # (nb de coups restant à jouer dans le tour)
        self._current_vitesse = self.vitesse
        # caractéristiques comportementales
        amb = self.parseFloat(robotdict["ambition"])
        inst_surv = self.parseFloat(robotdict["instinct_survie"])
        agg = self.parseFloat(robotdict["aggressivite"])
        cur = self.parseFloat(robotdict["curiosite"])
        eff = self.parseFloat(robotdict["efficacite"])
        intel = self.parseFloat(robotdict["intelligence"])
        if None in {amb, inst_surv, agg, cur, eff, intel}:
            CaseRobot.configure_behavior(self)
        else:
            self.ambition = amb
            self.instinct_survie = inst_surv
            self.aggressivite = agg
            self.curiosite = cur
            self.efficacite = eff
            self.intelligence = intel
        self.color = robotdict["color"]
        self._order = self.parseInt(robotdict["order"])
        # cibles :
        self.maintargetobject = None
        self.maintargetparams = None
        self.temptargetobjectlist = list()
        self.temptargetobjectdict = dict()
        self.currenttemptarget = None
        # nombre total de coups unitaires joués
        self._totalgamblecount = 0
        # Gamble data set :
        self.current_gdSet = None
        # phase de jeu :
        self._game_phasis = None
        # besoin de bonus ?
        self._need_bonus = False
        # stratégie de recherche de bonus
        self.bonus_strategy = None
        # nombre de bonus gagnés :
        self.earned_bonus = 0
        # cases par lesquelles le robot est passé
        # liste de tupples (coords, gambleid)
        self.passedcase = list()
        # le robot doit il repérer les séquences de cases similaires
        # (outil de détection de bouclages)
        self.detect_sequence_loop = True
        # mémorisation des actions :
        self.passedaction = list()
        # mémorisation des coords associées aux actions MOVE (loop)
        # liste de dicts {"start":, "coords":}
        self._gamble_coords_list = list()
        # à supp
        self.coordsequences = list()
        # nombre de pseudos actions "stay in place" consécutives
        self.no_move_count = 0
        # robots éliminés
        self._bots_killed = list()
        self._has_killed_innocent = False
        self.innocent_killed_count = 0
        self.total_killed_count = 0
        # zones de déplacement, d'attaque (sets de coords):
        self.move_zone = None
        self.attack_zone = None
        # dict de facteurs de dangers :
        self.danger_factor_dict = None
        self.compute_danger_factor_dict()

    def compute_danger_factor_dict(self):
        """
        Calcule le facteur de danger associé à chaque espèce en fonction des
        caractéristiques comportementales du robot.
        
        - 0 : robot inoffensif
        - 1 : robot capable de se défendre
        - 2 : joueur humain au comportement inconnu encore (supposé capable de
          se défendre)
        - 3 : robot pouvant attaquer par opportunité
        - 4 : robot attaquant à coup sûr
        
        Rq : la gestion par dict permet de différencier les facteurs de dangers
        en fonction des espèces (spécisme). En V1 on standardise.        
        """
        # seuils :
        midSUR = CaseRobot.get_feature_threshold("instinct_survie", "middle")
        midAGG = CaseRobot.get_feature_threshold("aggressivite", "middle")
        highAGG = CaseRobot.get_feature_threshold("aggressivite", "high")
        highAMB = CaseRobot.get_feature_threshold("ambition", "high")
        # Par défaut
        defaultfactor = 0
        if self.behavior == CaseRobot.BEHAVIOR_HUNTER:
            # un chasseur est un danger pour toutes les autres espèces
            defaultfactor = 4
        elif self.instinct_survie >= midSUR:
            defaultfactor = 1
        dgrdict = {CaseRobot.BEHAVIOR_HUMAN: defaultfactor}
        for behav in CaseRobot.FAMILLE_BEHAVIOR:
            dgrdict[behav] = defaultfactor
        # Bots :
        if not self.human:
            if self.aggressivite >= highAGG:
                # un psychopathe s'attaque à tout le monde
                for b in dgrdict.keys():
                    dgrdict[b] = 4
            elif midAGG <= self.aggressivite:
                if self.ambition >= highAMB:
                    # un bot suffisament aggressif et très ambitieux
                    # peut sacrifier d'autres bots en terraformant
                    for b in dgrdict.keys():
                        dgrdict[b] = max(3, dgrdict[b])
        # humain
        else:
            # joueur humain :
            if self.innocent_killed_count == 0:
                # le joueur n'a encore tué aucun innocent, facteur de danger
                # inconnu :
                for b in dgrdict.keys():
                    dgrdict[b] = 2
        # les deux :
        if 1 <= self.innocent_killed_count < 2:
            # le joueur a tué un innocent, ça peut être une erreur,
            # facteur de danger possible
            for b in dgrdict.keys():
                dgrdict[b] = max(3, dgrdict[b])
        elif self.innocent_killed_count >= 2:
            # le joueur est considéré comme un psychopathe
            for b in dgrdict.keys():
                dgrdict[b] = 4
        # spécisme des bots :
        if self.behavior == CaseRobot.BEHAVIOR_HUNTER:
            # chasseur inoffensif avec son espèce
            dgrdict[self.behavior] = 0
        # enregistrement :
        self.danger_factor_dict = dgrdict

    def get_danger_factor_for_bot(self, bot, behavior=None):
        """
        Retourne le facteur de danger associé au bot
        """
        # par défaut pour un humain
        b = CaseRobot.BEHAVIOR_HUMAN
        if bot != None:
            b = bot.behavior
        elif behavior in CaseRobot.ALL_BEHAVIORS:
            b = behavior
        if b != None:
            return self.danger_factor_dict[b]
        return None

    def get_apparent_danger_factor_for_bot(self, bot, behavior=None):
        """
        Retourne le facteur de danger apparent associé au bot.
        Utilité : permettre d'afficher la zone de danger des HUNTERS
        en toute circonstance.
        """
        df = self.get_danger_factor_for_bot(bot, behavior=behavior)
        if self.behavior == CaseRobot.BEHAVIOR_HUNTER:
            df = 4
        return df

    def update_dyn_props(self, robotdict):
        """
        Mise à jour des propriétés dynamiques à partir d'un dict
        """
        if "alive" in robotdict.keys():
            self.alive = self.parseBool(robotdict["alive"])
        if "vitesse" in robotdict.keys():
            self.vitesse = int(robotdict["vitesse"])
        if "current_vitesse" in robotdict.keys():
            self.current_vitesse = int(robotdict["current_vitesse"])
        if "current_gamble_count" in robotdict.keys():
            self.current_gamble_count = int(robotdict["current_gamble_count"])
        if "current_gamble_number" in robotdict.keys():
            self.current_gamble_number = int(robotdict["current_gamble_number"])
        if "has_mine" in robotdict.keys():
            self.has_mine = self.parseBool(robotdict["has_mine"])
        if "has_grenade" in robotdict.keys():
            self.has_grenade = self.parseBool(robotdict["has_grenade"])
        if "puissance_mine" in robotdict.keys():
            self.puissance_mine = int(robotdict["puissance_mine"])
        if "puissance_grenade" in robotdict.keys():
            self.puissance_grenade = int(robotdict["puissance_grenade"])
        if "portee_grenade" in robotdict.keys():
            self.portee_grenade = int(robotdict["portee_grenade"])
        if "order" in robotdict.keys():
            self._order = self.parseInt(robotdict["order"])
        if "total_killed_count" in robotdict.keys():
            self.total_killed_count = int(robotdict["total_killed_count"])
        if "innocent_killed_count" in robotdict.keys():
            self.innocent_killed_count = int(robotdict["innocent_killed_count"])
        if "earned_bonus" in robotdict.keys():
            self.earned_bonus = int(robotdict["earned_bonus"])
        # maj facteurs de dangers :
        self.compute_danger_factor_dict()

    def get_properties_dict(self, full=True):
        """
        Retourne ses paramètres sous forme de dict
        """
        if full:
            robotdict = Case.get_properties_dict(self)
            robotdict["alive"] = self.alive
            robotdict["uid"] = self.uid
            robotdict["human"] = self.human
            robotdict["number"] = self.number
            robotdict["human_number"] = self.human_number
            robotdict["behavior"] = self.behavior
            robotdict["vitesse"] = self.vitesse
            robotdict["current_vitesse"] = self.current_vitesse
            robotdict["current_gamble_count"] = self.current_gamble_count
            robotdict["current_gamble_number"] = self.current_gamble_number
            robotdict["has_mine"] = self.has_mine
            robotdict["has_grenade"] = self.has_grenade
            robotdict["puissance_mine"] = self.puissance_mine
            robotdict["puissance_grenade"] = self.puissance_grenade
            robotdict["portee_grenade"] = self.portee_grenade
            robotdict["ambition"] = self.ambition
            robotdict["instinct_survie"] = self.instinct_survie
            robotdict["aggressivite"] = self.aggressivite
            robotdict["curiosite"] = self.curiosite
            robotdict["efficacite"] = self.efficacite
            robotdict["intelligence"] = self.intelligence
            robotdict["color"] = self.color
            robotdict["order"] = self.order
            robotdict["total_killed_count"] = self.total_killed_count
            robotdict["innocent_killed_count"] = self.innocent_killed_count
            robotdict["earned_bonus"] = self.earned_bonus
        else:
            # on se limite aux seules propriétés modifiées durant le coup
            robotdict = None
            if len(self._gamble_properties_changes) > 0:
                robotdict = dict()
                robotdict["uid"] = self.uid
                for name in self._gamble_properties_changes:
                    robotdict[name] = getattr(self, name)
                self._gamble_properties_changes = list()
        return robotdict

    def get_puissance_list(self, weapon):
        """
        Retourne la liste de puissances activées pour l'arme weapon (mine, grenade)
        """
        list_puissance = list()
        if weapon == "mine":
            prop = "puissance_mine"
        elif weapon == "grenade":
            prop = "puissance_grenade"
        if self[prop] in range(1, 5):
            list_puissance = [1]
        elif self[prop] in range(5, 9):
            list_puissance = [1, 5]
        elif self[prop] in range(9, 13):
            list_puissance = [1, 5, 9]
        elif self[prop] in range(13, 17):
            list_puissance = [1, 5, 9, 13]
        elif self[prop] in range(17, 25):
            list_puissance = [1, 5, 9, 13, 17]
        elif self[prop] >= 25:
            list_puissance = [1, 5, 9, 13, 17, 25]
        return list_puissance

    def _get_current_vitesse(self):
        return self._current_vitesse
    
    def _set_current_vitesse(self, val):
        if val != self._current_vitesse:
            self._current_vitesse = val
            self._gamble_properties_changes.append("current_vitesse")
            
    current_vitesse = property(_get_current_vitesse, _set_current_vitesse)  #: vitesse apparente du robot
        
    def register_bots_killed(self, botlist):
        """
        Enregistre les bots éliminés
        """
        for r in botlist:
            if r != self and r not in self._bots_killed:
                self._bots_killed.append(r)
                # r était il innocent?
                dgrfacor = r.get_danger_factor_for_bot(self)
                self.total_killed_count += 1
                self._gamble_properties_changes.append("total_killed_count")
                if dgrfacor <= 2:
                    self._has_killed_innocent = True
                    self.innocent_killed_count += 1
                    self.compute_danger_factor_dict()
                    self._gamble_properties_changes.append("innocent_killed_count")

    def get_bots_killed(self):
        """
        Retourne la liste des bots éliminés
        """
        return self._bots_killed

    def is_a_murderer(self):
        """
        Le robot a t'il tué des innocents?
        """
        return self._has_killed_innocent

    def get_killed_counts(self):
        """
        Retourne le tupple total tués, innocents tués
        """
        return self.total_killed_count, self.innocent_killed_count

    def _get_game_phasis(self):
        return self._game_phasis

    def _set_game_phasis(self, val):
        self._game_phasis = val

    game_phasis = property(_get_game_phasis, _set_game_phasis)  #: phase de jeu actuelle

    def _get_need_bonus(self):
        return self._need_bonus

    def _set_need_bonus(self, val):
        self._need_bonus = val

    need_bonus = property(
        _get_need_bonus, _set_need_bonus
    )  #: devrait prendre un bonus?

    def _get_totalgamblecount(self):
        return self._totalgamblecount

    def _set_totalgamblecount(self, val):
        self._totalgamblecount = val

    totalgamblecount = property(
        _get_totalgamblecount, _set_totalgamblecount
    )  #: nombre de coups consécutifs à jouer

    def _get_order(self):
        return self._order

    def _set_order(self, val):
        self._order = val

    order = property(_get_order, _set_order)  #: ordre du joueur associé

    def get_danger_radius(self):
        """
        Retourne le rayon d'action offensif du robot
        Estimation large pour 5, 13 et 17, exacte pour 1, 9 et 25 (grenade)
        """
        # action kill sur un adjacent
        radius = 1
        # prise en compte des grenades
        if self.has_grenade:
            radius = self.portee_grenade
            if self.puissance_grenade <= 1:
                radius += 0
            elif self.puissance_grenade in range(5, 10):
                radius += 1
            elif self.puissance_grenade >= 13:
                radius += 2
        # prise en compte de la vitesse
        radius += self.vitesse - 1
        return radius

    def get_main_target(self):
        """
        Retourne la cible principale
        """
        return self.maintargetobject

    def set_main_target(self, targetobj, params=None):
        """
        Définit la cible principale
        """
        self.maintargetobject = targetobj
        self.maintargetparams = params

    def get_main_target_params(self):
        """
        Retourne les paramètres optionnels de la cible principale
        """
        return self.maintargetparams

    def get_temp_target(self):
        """
        Retourne la cible actuelle
        """
        return self.currenttemptarget

    def set_temp_target(self, targetobj):
        """
        Définit la nouvelle cible
        """
        self.currenttemptarget = targetobj
        if targetobj != None:
            # clef identifiant l'objet
            k = (targetobj.x, targetobj.y, targetobj.direct, self.x, self.y)
            # enregistrement : mise à jour ou création
            gambleid = self.current_gdSet.gambleid
            if k in self.temptargetobjectdict.keys():
                # nombre de sélection de cette cible pour ces coordonnées du robot
                self.temptargetobjectdict[k]["count"] += 1
                # dernier score obtenu :
                self.temptargetobjectdict[k]["score"] = targetobj.score
                # lors du coup :
                self.temptargetobjectdict[k]["gambleid"] = gambleid
            else:
                self.temptargetobjectdict[k] = {
                    "count": 1,
                    "score": targetobj.score,
                    "gambleid": gambleid,
                }

    def get_prev_temptarget_datas(self, x, y, direct, xrobot=None, yrobot=None):
        """
        Retourne le nombre d'occurences et le dernier score enregistré pour
        une cible de caractéristiques x, y, direct choisie aux coordonnées actuelles
        du robot (si xrobot et yrobot sont indéterminés).
        Par défaut retourne {"count":0, "score":None, "gambleid":None}
        """
        rdata = {"count": 0, "score": 0, "gambleid": None}
        if xrobot == None or yrobot == None:
            xrobot = self.x
            yrobot = self.y
        # recherche de l'enregistrement :
        k = (x, y, direct, xrobot, yrobot)
        if k in self.temptargetobjectdict.keys():
            rdata = self.temptargetobjectdict[k]
        return rdata

    def register_current_gdSet(self, gdSet):
        """
        Enregistre le gdSet courant
        """
        self.current_gdSet = gdSet

    def get_current_gdSet(self):
        """
        Retourne le gdSet courant
        """
        return self.current_gdSet

    def register_action(self, action, gambleid):
        """
        Enregistre la dernière action effectuée
        """
        self.passedaction.append((action, gambleid))

    def get_action_list(self):
        """
        Retourne la liste des actions passées
        """
        rlist = list()
        for t in self.passedaction:
            rlist.append(t[0])
        return rlist

    def get_last_action(self):
        """
        Retourne la dernière action ou None
        """
        lastaction = None
        if len(self.passedaction) > 0:
            lastaction = self.passedaction[-1][0]
        return lastaction

    def get_work_ratio(self):
        """
        Retourne le ratio travail/mouvement sous forme de fraction
        Application sapper et builder
        """
        r = Fraction(0)
        if self.behavior == CaseRobot.BEHAVIOR_SAPPER:
            # Sapper : on module en fonction de l'efficacité
            if self.efficacite < 0.4:
                r = Fraction(1, 4)
            elif 0.4 <= self.efficacite < 0.5:
                r = Fraction(1, 3)
            elif 0.5 <= self.efficacite < 0.6:
                r = Fraction(1, 2)
            elif self.efficacite >= 0.6:
                r = Fraction(1)
        elif self.behavior == CaseRobot.BEHAVIOR_BUILDER:
            # ratio maximal systématique (r>1)
            r = Fraction(2)
        return r

    def register_bonus(self, name, value):
        """
        Enregistre un bonus
        """
        setattr(self, name, value)
        self._gamble_properties_changes.append(name)

    def register_death(self):
        """
        Enregistre son décès
        """
        self.alive = False
        self._gamble_properties_changes.append("alive")

    def register_case(self, case, gambleid):
        """
        Enregistre la dernière case atteinte
        """
        # enregistrement
        coords = int(case.x), int(case.y)
        if gambleid >= 0:
            self._add_gamble_coords_to_current_entry(coords)
        self.passedcase.append((coords, gambleid))
        self._gamble_properties_changes.append("x")
        self._gamble_properties_changes.append("y")
        # effacement progressif du parcours :
        if len(self.passedcase) > CaseRobot.MAX_PASSED_CASES:
            self.passedcase = self.passedcase[-CaseRobot.MAX_PASSED_CASES :]

    def create_gamble_coords_entry(self):
        """
        Crée une entrée dans pour la série de coups à venir
        """
        c = int(self.x), int(self.y)
        entrydict = {"start": c, "coords": [c]}
        self._gamble_coords_list.append(entrydict)
        # effacement progressif des séquences :
        if len(self._gamble_coords_list) > CaseRobot.MAX_SEQ_COUNT:
            self._gamble_coords_list = self._gamble_coords_list[
                -CaseRobot.MAX_SEQ_COUNT :
            ]

    def _add_gamble_coords_to_current_entry(self, coords):
        """
        Ajoute des coorddonnées à la liste crée dans create_gamble_coords_entry.
        """
        lastentry = self._gamble_coords_list[-1]
        lastentry["coords"].append(coords)

    def compute_loop_factor(self, listcoords):
        """
        Retourne un entier caractérisant le risque de bouclage associé 
        à la liste de coordonnées.
        listcoords : liste de tuples (x, y)
        """
        loopfactor = 0
        nbentry = len(self._gamble_coords_list)
        nbc = len(listcoords)
        if nbc > 0 and nbentry > 0:
            # position d'arrivée :
            endpos = listcoords[-1]
            # nombre de séquences précédentes considérées :
            prevseq = CaseRobot.MAX_SEQ_COUNT
            nb = min(prevseq, nbentry)
            # données de ref :
            refstarts = list()
            for i in range(nbentry - 1 - nb, nbentry - 1):
                entry = self._gamble_coords_list[i]
                refstarts.append(entry["start"])
            prevseqcoords = list()
            if nbentry > 1:
                prevseqcoords = self._gamble_coords_list[-2]["coords"]
            # dénombrement :
            startcount = refstarts.count(endpos)
            prevcount = 0
            if len(prevseqcoords) > 0:
                for c in listcoords:
                    prevcount += prevseqcoords.count(c)
            loopfactor = startcount + prevcount
        return loopfactor

    def get_prev_coords(self):  # bug !!
        """
        Retourne les coordonnées de l'avant dernière case par laquelle le robot est passé
        """
        prevcoords = None
        if len(self.passedcase) > 1:
            prevcoords = self.passedcase[-2][0]
        return prevcoords

    def __repr__(self):
        return " CaseRobot uid={} behavior={} x={} y={}".format(
            self.uid, self.behavior, self.x, self.y
        )

    def __str__(self):
        return " CaseRobot uid={} x={} y={} human={} behavior={} face={} vis={}".format(
            self.uid, self.x, self.y, self.human, self.behavior, self.face, self.visible
        )


class CaseDanger(Case):
    """
    Modélise une case danger
    """

    # types de dangers :
    DANGER_MINE = "DANGER_MINE"  #: identifie une case danger (mine)
    # méthodes statiques
    def get_default_dict(cls):
        """
        Méthode statique retournant le dict par défaut attendu par le constructeur
        """
        dangerdict = Case.get_default_dict()
        dangerdict["type_case"] = LabHelper.CASE_DANGER
        dangerdict["face"] = LabHelper.CHAR_REPR_DANGER
        dangerdict["danger_type"] = None
        dangerdict["danger_impact"] = None
        return dangerdict

    get_default_dict = classmethod(get_default_dict)
    # méthodes d'instance
    def __init__(self, dangerdict):
        """
        Constructeur de la case bonus
        """
        Case.__init__(
            self,
            dangerdict["x"],
            dangerdict["y"],
            dangerdict["type_case"],
            dangerdict["face"],
            dangerdict["visible"],
        )
        # spécifique :
        self.danger_type = dangerdict["danger_type"]
        self.danger_impact = self.parseInt(dangerdict["danger_impact"])
        if self.danger_impact <= 9:
            self.face = str(self.danger_impact)
        else:
            self.face = LabHelper.CHAR_REPR_DANGER

    def get_properties_dict(self, full=True):
        """
        Retourne ses paramètres sous forme de dict
        """
        dangerdict = Case.get_properties_dict(self)
        if self.danger_impact <= 9:
            dangerdict["face"] = self.danger_impact
        else:
            dangerdict["face"] = LabHelper.CHAR_REPR_DANGER
        dangerdict["danger_type"] = self.danger_type
        dangerdict["danger_impact"] = self.danger_impact
        return dangerdict

    def get_danger_radius(self):
        """
        Retourne le rayon d'action offensif du danger
        Estimation large pour 5, 13 et 17, exacte pour 1, 9 et 25
        """
        radius = 0
        if self.danger_impact != None:
            if self.danger_impact <= 1:
                radius = 1
            elif self.danger_impact in range(5, 9):
                radius = 2
            elif self.danger_impact >= 13:
                radius = 3
        return radius

    def __str__(self):
        r = super().__str__()
        return r + " danger_type={} danger_impact={}".format(
            self.danger_type, self.danger_impact
        )


class CaseGrenade(CaseDanger):
    """
    Modélise une case grenade
    """

    DANGER_GRENADE = "DANGER_GRENADE"  #: identifie une case grenade
    # méthodes statiques
    def get_default_dict(cls):
        """
        Méthode statique retournant le dict par défaut attendu par le constructeur
        """
        dangerdict = CaseDanger.get_default_dict()
        # subclassement :
        dangerdict["type_case"] = LabHelper.CASE_GRENADE
        dangerdict["face"] = LabHelper.CHAR_REPR_GRENADE
        dangerdict["danger_type"] = CaseGrenade.DANGER_GRENADE
        # spécifique
        dangerdict["x_start"] = None
        dangerdict["y_start"] = None
        return dangerdict

    get_default_dict = classmethod(get_default_dict)
    # méthodes d'instance
    def __init__(self, dangerdict):
        """
        Constructeur de la case bonus
        """
        CaseDanger.__init__(self, dangerdict)
        # spécifique :
        self.x_start = dangerdict["x_start"]
        self.y_start = dangerdict["y_start"]


class CaseAnimation(Case):
    """
    Case temporaire dédiée aux animations
    """

    # types d'animations :
    # déplacement
    ANIM_MOVE = "ANIM_MOVE"  #: animation de mouvement
    # changement d'apparence
    ANIM_FACE = "ANIM_FACE"  #: changement d'apparence
    # Incrémente la génération d'id :
    _NEXT_UID = 0
    # méthodes statiques
    def create_uid(cls):
        """
        Génère un id unique pour une case animation
        """
        uid = cls._NEXT_UID
        cls._NEXT_UID += 1
        return uid

    create_uid = classmethod(create_uid)

    def get_default_dict(cls):
        """
        Méthode statique retournant le dict par défaut attendu par le constructeur
        """
        animdict = Case.get_default_dict()
        # spécifique
        animdict["anim_uid"] = cls.create_uid()
        animdict["type_case"] = LabHelper.CASE_ANIMATION
        # type d'animation
        animdict["type_anim"] = None
        animdict["scenario_anim"] = None
        # impact associé à une explosion
        animdict["impact"] = None
        # nombre de pas d'animation
        animdict["step_count"] = None
        # pas de départ dans l'animation globale
        animdict["start_step"] = 0
        # pas d'animation local :
        animdict["local_step"] = 0
        # liste des apparences successives (ANIM_FACE)
        animdict["face_list"] = None
        # coordonnées initiales (ANIM_MOVE)
        animdict["x_start"] = None
        animdict["y_start"] = None
        # axe de déplacement
        animdict["axe"] = None
        # coordonnées finales (ANIM_MOVE)
        animdict["x_end"] = None
        animdict["y_end"] = None
        return animdict

    get_default_dict = classmethod(get_default_dict)
    # méthodes d'instance
    def __init__(self, animdict):
        """
        Constructeur de la case Animation
        """
        Case.__init__(
            self,
            animdict["x"],
            animdict["y"],
            animdict["type_case"],
            animdict["face"],
            animdict["visible"],
        )
        # spécifique :
        self.anim_uid = animdict["anim_uid"]
        self.type_anim = animdict["type_anim"]
        self.scenario_anim = animdict["scenario_anim"]
        self.step_count = animdict["step_count"]
        self.start_step = animdict["start_step"]
        self.local_step = animdict["local_step"]
        if self.type_anim == CaseAnimation.ANIM_MOVE:
            # déplacement :
            self.x_start = animdict["x_start"]
            self.y_start = animdict["y_start"]
            self.x_end = animdict["x_end"]
            self.y_end = animdict["y_end"]
            self.axe = animdict["axe"]
            self.impact = None
        elif self.type_anim == CaseAnimation.ANIM_FACE:
            # changement d'apparence :
            self.face_list = animdict["face_list"]
            self.impact = animdict["impact"]

    def get_properties_dict(self, full=True):
        """
        Retourne ses paramètres sous forme de dict
        """
        animdict = Case.get_properties_dict(self)
        animdict["anim_uid"] = self.anim_uid
        animdict["type_anim"] = self.type_anim
        animdict["scenario_anim"] = self.scenario_anim
        animdict["step_count"] = self.step_count
        animdict["start_step"] = self.start_step
        animdict["local_step"] = self.local_step
        if self.type_anim == CaseAnimation.ANIM_MOVE:
            animdict["x_start"] = self.x_start
            animdict["y_start"] = self.y_start
            animdict["x_end"] = self.x_end
            animdict["y_end"] = self.y_end
            animdict["axe"] = self.axe
        elif self.type_anim == CaseAnimation.ANIM_FACE:
            animdict["face_list"] = self.face_list
            animdict["impact"] = self.impact
        return animdict

    def apply_animation_step(self, step):
        """
        Applique la transformation associée au pas d'animation global step (0 à n)
        """
        if step < self.start_step:
            self.visible = False
        else:
            self.visible = True
            self.local_step = step - self.start_step
            if self.type_anim == CaseAnimation.ANIM_MOVE:
                if self.local_step <= self.step_count:
                    if self.axe == LabHelper.AXIS_X:
                        xs = self.x_start
                        xe = self.x_end
                        self.x = xs + (xe - xs) / self.step_count * self.local_step
                    else:
                        ys = self.y_start
                        ye = self.y_end
                        self.y = ys + (ye - ys) / self.step_count * self.local_step
            elif self.type_anim == CaseAnimation.ANIM_FACE:
                if self.local_step < self.step_count:
                    self.face = self.face_list[self.local_step]

    def __repr__(self):
        return "CaseAnimation anim_uid={}".format(self.anim_uid)

    def __str__(self):
        r = super().__str__()
        return r + " anim_uid={} start_step={}".format(self.anim_uid, self.start_step)


class CaseBonus(Case):
    """
    Modélise une case bonus
    """

    # types de bonus :
    BONUS_AUGMENTE_VITESSE = "BONUS_AUGMENTE_VITESSE"  #: bonus augmenter la vitesse
    BONUS_MINE = "BONUS_MINE"  #: bonus poser des mines
    BONUS_PUISSANCE_MINE = (
        "BONUS_PUISSANCE_MINE"  
    ) #: bonus augmenter la puissance des mines
    BONUS_GRENADE = "BONUS_GRENADE"  #: bonus lancer des grenades
    BONUS_PUISSANCE_GRENADE = (
        "BONUS_PUISSANCE_GRENADE"  
    ) #: bonus augmenter la puissance des grenades
    BONUS_PORTEE_GRENADE = (
        "BONUS_PORTEE_GRENADE"  
    ) #: bonus augmenter la portée des grenades
    # méthodes statiques
    def get_default_dict(cls):
        """
        Méthode statique retournant le dict par défaut attendu par le constructeur
        """
        bonusdict = Case.get_default_dict()
        bonusdict["type_case"] = LabHelper.CASE_BONUS
        bonusdict["face"] = LabHelper.CHAR_REPR_BONUS
        bonusdict["bonus_type"] = None
        return bonusdict

    get_default_dict = classmethod(get_default_dict)
    # méthodes d'instance
    def __init__(self, bonusdict):
        """
        Constructeur de la case bonus
        """
        Case.__init__(
            self,
            bonusdict["x"],
            bonusdict["y"],
            bonusdict["type_case"],
            bonusdict["face"],
            bonusdict["visible"],
        )
        # spécifique :
        self.bonus_type = bonusdict["bonus_type"]

    def get_properties_dict(self, full=True):
        """
        Retourne ses paramètres sous forme de dict
        """
        bonusdict = Case.get_properties_dict(self)
        bonusdict["bonus_type"] = self.bonus_type
        return bonusdict

    def adapt_bonus_to_robot(self, robot, gameconf, handlebehavior):
        """
        Se configure en fonction des capacités du robot
        gameconf : ref à GameConfiguration s'il est configuré, None sinon
        Rq : un problème d'import circulaire empèche d'importer explicitement
        GameConfiguration.
        """
        bonus_finded = False
        # limites de configuration :
        bonus_policy = {}
        if gameconf != None:
            bonus_policy["vitesse"] = gameconf.get_bonus_policy("vitesse")
            bonus_policy["mine"] = gameconf.get_bonus_policy("mine")
            bonus_policy["grenade"] = gameconf.get_bonus_policy("grenade")
        else:
            # limites max
            bonus_policy["vitesse"] = {"active": True, "increment": 1}
            bonus_policy["mine"] = {
                "active": True,
                "method": "add",
                "increment": 4,
                "max": 25,
            }
            bonus_policy["grenade"] = {
                "active": True,
                "method": "add",
                "increment": 2,
                "max_puissance": 25,
            }
        # capacites du robot :
        capacites = [(robot.vitesse, CaseBonus.BONUS_AUGMENTE_VITESSE)]
        if bonus_policy["mine"]["active"]:
            capacites.append((robot.has_mine, CaseBonus.BONUS_MINE))
        if bonus_policy["grenade"]["active"]:
            capacites.append((robot.has_grenade, CaseBonus.BONUS_GRENADE))
        # augmentation des capacités
        plus_mine = (robot.puissance_mine, CaseBonus.BONUS_PUISSANCE_MINE)
        plus_puissance_grenade = (
            robot.puissance_grenade,
            CaseBonus.BONUS_PUISSANCE_GRENADE,
        )
        plus_portee_grenade = (robot.portee_grenade, CaseBonus.BONUS_PORTEE_GRENADE)
        plus_vitesse = (robot.vitesse, CaseBonus.BONUS_AUGMENTE_VITESSE)
        # ...par défaut :
        puissances = [
            plus_mine,
            plus_puissance_grenade,
            plus_portee_grenade,
            plus_vitesse,
        ]
        # prise en compte du comportement du robot
        if handlebehavior:
            # on oriente le bonus en fonction du comportement
            behavior = robot.behavior
            if behavior in [
                CaseRobot.BEHAVIOR_HUMAN,
                CaseRobot.BEHAVIOR_HUNTER,
                CaseRobot.BEHAVIOR_WINNER,
            ]:
                # on privilégie vitesse et grenade
                vg = [plus_puissance_grenade, plus_portee_grenade, plus_vitesse]
                puissances = vg * 4
                puissances += [plus_mine]
            elif behavior == CaseRobot.BEHAVIOR_SAPPER:
                # on renforce les mines
                puissances = [plus_mine] * 4
                puissances += [
                    plus_puissance_grenade,
                    plus_portee_grenade,
                    plus_vitesse,
                ]
            elif behavior == CaseRobot.BEHAVIOR_TOURIST:
                # on renforce la vitesse
                puissances = [plus_vitesse] * 10
                puissances += [plus_puissance_grenade, plus_portee_grenade, plus_mine]
            else:
                # random et builder: on laisse en standard
                pass
        # on donne de nouveaux pouvoirs
        cr.CustomRandom.shuffle(capacites)
        for cap in capacites:
            if cap[0] == False or str(cap[0]) == "1":
                self.bonus_type = cap[1]
                bonus_finded = True
                break
        # ou on en augmente la puissance
        if not bonus_finded:
            cr.CustomRandom.shuffle(puissances)
            self.bonus_type = puissances[0][1]
            bonus_finded = True
        # application
        bonus_applied = False
        prop_names = None
        prop_values = None
        if bonus_finded:
            if self.bonus_type == CaseBonus.BONUS_AUGMENTE_VITESSE:
                prop_names = ["vitesse"]
                prop_values = [robot.vitesse + bonus_policy["vitesse"]["increment"]]
                bonus_applied = True
            elif (
                bonus_policy["mine"]["active"]
                and self.bonus_type == CaseBonus.BONUS_MINE
            ):
                prop_names = ["has_mine", "puissance_mine"]
                prop_values = [True, 1]
                bonus_applied = True
            elif (
                bonus_policy["grenade"]["active"]
                and self.bonus_type == CaseBonus.BONUS_GRENADE
            ):
                prop_names = ["has_grenade", "puissance_grenade", "portee_grenade"]
                prop_values = [True, 1, 1]
                bonus_applied = True
            elif (
                bonus_policy["mine"]["active"]
                and self.bonus_type == CaseBonus.BONUS_PUISSANCE_MINE
            ):
                if (
                    robot.puissance_mine + bonus_policy["mine"]["increment"]
                    <= bonus_policy["mine"]["max"]
                ):
                    prop_names = ["puissance_mine"]
                    prop_values = [
                        robot.puissance_mine + bonus_policy["mine"]["increment"]
                    ]
                    bonus_applied = True
            elif (
                bonus_policy["grenade"]["active"]
                and self.bonus_type == CaseBonus.BONUS_PUISSANCE_GRENADE
            ):
                if (
                    robot.puissance_grenade + bonus_policy["grenade"]["increment"]
                    <= bonus_policy["grenade"]["max_puissance"]
                ):
                    if (
                        robot.puissance_grenade + bonus_policy["grenade"]["increment"]
                    ) // 2 + 1 <= robot.portee_grenade:
                        prop_names = ["puissance_grenade"]
                        prop_values = [
                            robot.puissance_grenade
                            + bonus_policy["grenade"]["increment"]
                        ]
                        bonus_applied = True
                    else:
                        prop_names = ["portee_grenade"]
                        prop_values = [robot.portee_grenade + 1]
                        bonus_applied = True
            elif (
                bonus_policy["grenade"]["active"]
                and self.bonus_type == CaseBonus.BONUS_PORTEE_GRENADE
            ):
                prop_names = ["portee_grenade"]
                prop_values = [robot.portee_grenade + 1]
                bonus_applied = True
        # Dernière chance :
        if not bonus_applied:
            prop_names = ["vitesse"]
            prop_values = [robot.vitesse + bonus_policy["vitesse"]["increment"]]
            bonus_applied = True
        # Application:
        if bonus_applied:
            n = len(prop_names)
            for i in range(0, n):
                name = prop_names[i]
                value = prop_values[i]
                robot.register_bonus(name, value)
            robot.register_bonus("earned_bonus", robot.earned_bonus + 1)

    def __str__(self):
        r = super().__str__()
        return r + " bonus_type={} ".format(self.bonus_type)
