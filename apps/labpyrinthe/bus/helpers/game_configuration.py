#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GameConfiguration : configurateur statique de partie
"""
# imports :
import math
import labpyproject.core.random.custom_random as cr
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import LabHelper
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseRobot

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["GameConfiguration"]
# classes :
class GameConfiguration:
    """
    Classe statique définissant les paramètres de configuration d'une partie
    """

    # Difficulté de la partie :
    _DIFFICULTY = None
    # Types de robots pouvant participer
    _BOT_BEHAVIOR_ACCEPTED = []
    # Valeurs comportementales max :
    _BOT_MAX_AGGRESSIVITE = 0
    _BOT_MAX_EFFICACITE = 0
    # Dimensions de la carte :
    # à minima 7x7 (/ échantillonages), non vérifié
    _W_RANGE = []
    _H_RANGE = []
    # Densités :
    _DENSITY = {
        "vide": None,
        "porte": None,
        "bots": None,
        "danger": None,
        "bonus": None,
    }
    # proportions des types de robots :
    _WINNER_PROP = 0
    _HUNTER_PROP = 0
    # liste de comportements des bots :
    _BEHAVIOR_LIST = None
    # dénombrement winners, hunters, autres :
    _BEHAVIOR_COUNT_DICT = None
    # distance initiale inter-bots :
    _BOTS_INTER_DIST = 2
    # Pouvoirs initiaux des robots
    _BOTS_INITIAL_POWERS = {
        "has_mine": False,
        "puissance_mine": 0,
        "has_grenade": False,
        "puissance_grenade": 0,
        "portee_grenade": 0,
        "vitesse": 1,
    }
    # Dangers
    _DANGER_MAX_POWER = 0
    _ENSURE_DANGER_DENSITY = False
    # Bonus pouvant être appliqués
    _ENSURE_BONUS_DENSITY = False
    _BONUS_POLICY = {"vitesse": None, "mine": None, "grenade": None}
    # Méthodes statiques
    #-----> Initialisation
    def set_difficulty(cls, val):
        """
        Définit la difficulté de la partie
        val : un entier entre 1 et 3
        """
        if (type(val) == int or LabHelper.REGEXP_INT.match(val)) and int(val) in range(
            1, 4
        ):
            cls._DIFFICULTY = val
            cls._configureGame()

    set_difficulty = classmethod(set_difficulty)

    def re_initialise(cls):
        """
        Re initialise la classe avant la définition d'une nouvelle partie
        """
        cls._DIFFICULTY = None

    re_initialise = classmethod(re_initialise)

    def _configureGame(cls):
        """
        Définit les paramètres statiques en fonction du niveau de difficulté
        """
        # Par défaut au niveau 1
        # Bots : pas de sapper
        cls._BOT_BEHAVIOR_ACCEPTED = [
            CaseRobot.BEHAVIOR_TOURIST,
            CaseRobot.BEHAVIOR_WINNER,
            CaseRobot.BEHAVIOR_BUILDER,
            CaseRobot.BEHAVIOR_RANDOM,
            CaseRobot.BEHAVIOR_HUNTER,
        ]
        cls._BOT_MAX_AGGRESSIVITE = 1  # à mod
        cls._BOT_MAX_EFFICACITE = 1  # à mod
        cls._WINNER_PROP = cr.CustomRandom.randrange(10, 20) / 100
        cls._HUNTER_PROP = cr.CustomRandom.randrange(10, 20) / 100
        cls._BOTS_INITIAL_POWERS = {
            "has_mine": False,
            "puissance_mine": 0,
            "has_grenade": False,
            "puissance_grenade": 0,
            "portee_grenade": 0,
            "vitesse": 1,
        }
        cls._BOTS_INTER_DIST = 2
        # Carte :
        cls._W_RANGE = cr.CustomRandom.randrange(10, 16)
        cls._H_RANGE = cr.CustomRandom.randrange(10, 16)
        cls._DENSITY = {
            "vide": cr.CustomRandom.randrange(60, 71) / 100,
            "porte": cr.CustomRandom.randrange(2, 5) / 100,
            "bots": cr.CustomRandom.randrange(30, 40) / 1000,
            "danger": cr.CustomRandom.randrange(2, 4) / 100,
            "bonus": cr.CustomRandom.randrange(3, 8) / 100,
        }
        # Mines :
        cls._DANGER_MAX_POWER = 1
        cls._ENSURE_DANGER_DENSITY = True
        # Bonus :
        cls._ENSURE_BONUS_DENSITY = True
        cls._BONUS_POLICY["vitesse"] = {"active": True, "increment": 1}
        cls._BONUS_POLICY["mine"] = {"active": False}
        cls._BONUS_POLICY["grenade"] = {"active": False}
        if cls._DIFFICULTY >= 2:
            # niveau 2 :
            # Bots : tous
            cls._BOT_BEHAVIOR_ACCEPTED = [
                CaseRobot.BEHAVIOR_TOURIST,
                CaseRobot.BEHAVIOR_WINNER,
                CaseRobot.BEHAVIOR_BUILDER,
                CaseRobot.BEHAVIOR_RANDOM,
                CaseRobot.BEHAVIOR_SAPPER,
                CaseRobot.BEHAVIOR_HUNTER,
            ]
            cls._WINNER_PROP = cr.CustomRandom.randrange(15, 30) / 100
            cls._HUNTER_PROP = cr.CustomRandom.randrange(15, 30) / 100
            cls._BOTS_INITIAL_POWERS = {
                "has_mine": True,
                "puissance_mine": 5,
                "has_grenade": True,
                "puissance_grenade": 1,
                "portee_grenade": 1,
                "vitesse": 1,
            }
            cls._BOTS_INTER_DIST = 2
            # Carte :
            cls._W_RANGE = cr.CustomRandom.randrange(12, 20)
            cls._H_RANGE = cr.CustomRandom.randrange(12, 20)
            cls._DENSITY["vide"] = cr.CustomRandom.randrange(50, 61) / 100
            cls._DENSITY["porte"] = cr.CustomRandom.randrange(1, 5) / 100
            cls._DENSITY["bots"] = cr.CustomRandom.randrange(20, 30) / 1000
            cls._DENSITY["danger"] = cr.CustomRandom.randrange(4, 9) / 100
            cls._DENSITY["bonus"] = cr.CustomRandom.randrange(4, 9) / 100
            # Mines :
            cls._DANGER_MAX_POWER = 9
            cls._ENSURE_DANGER_DENSITY = True
            # Bonus :
            cls._BONUS_POLICY["mine"] = {
                "active": True,
                "method": "add",
                "increment": 1,
                "max": 9,
            }
            cls._BONUS_POLICY["grenade"] = {
                "active": True,
                "method": "add",
                "increment": 1,
                "max_puissance": 5,
            }
        if cls._DIFFICULTY >= 3:
            # niveau 3 :
            # Bots :
            cls._BOTS_INITIAL_POWERS = {
                "has_mine": True,
                "puissance_mine": 9,
                "has_grenade": True,
                "puissance_grenade": 5,
                "portee_grenade": 2,
                "vitesse": 1,
            }
            cls._BOTS_INTER_DIST = 4
            # Carte :
            cls._W_RANGE = cr.CustomRandom.randrange(17, 26)
            cls._H_RANGE = cr.CustomRandom.randrange(17, 26)
            cls._DENSITY["vide"] = cr.CustomRandom.randrange(45, 61) / 100
            cls._DENSITY["porte"] = cr.CustomRandom.randrange(1, 4) / 100
            cls._DENSITY["bots"] = cr.CustomRandom.randrange(20, 30) / 1000
            cls._DENSITY["danger"] = cr.CustomRandom.randrange(7, 10) / 100
            cls._DENSITY["bonus"] = cr.CustomRandom.randrange(7, 10) / 100
            # Mines :
            cls._DANGER_MAX_POWER = 25
            # Bonus :
            cls._BONUS_POLICY["mine"] = {
                "active": True,
                "method": "add",
                "increment": 4,
                "max": 25,
            }
            cls._BONUS_POLICY["grenade"] = {
                "active": True,
                "method": "add",
                "increment": 2,
                "max_puissance": 25,
            }
        # définition des comportements :
        cls._BEHAVIOR_LIST = cls._define_bots_behaviors_list()

    _configureGame = classmethod(_configureGame)

    def _define_bots_behaviors_list(cls):
        """
        Définit la liste de comportements à appliquer aux bots
        Retourne une liste de comportements
        """
        listbehav = list()
        # 1- nombre de bots à créer et liste de comportements possibles :
        nbbots = cls.get_bots_number()
        # winners :
        propwinner = cls.get_bot_proportion(CaseRobot.BEHAVIOR_WINNER)
        nbwinners = math.ceil(nbbots * propwinner)
        # hunters :
        prophunters = cls.get_bot_proportion(CaseRobot.BEHAVIOR_HUNTER)
        nbhunters = math.ceil(nbbots * prophunters)
        # autres :
        nbothers = nbbots - nbwinners - nbhunters
        # comportements acceptés
        if nbbots < 1:
            return listbehav
        if cls.is_game_configured():
            listcomp = cls.get_behaviors()
        else:
            listcomp = CaseRobot.FAMILLE_BEHAVIOR
        otherscomp = [
            comp
            for comp in listcomp
            if comp not in [CaseRobot.BEHAVIOR_WINNER, CaseRobot.BEHAVIOR_HUNTER]
        ]
        nbotherscomp = len(otherscomp)
        # 2- choix :
        # winners :
        if nbwinners > 0:
            listbehav.extend([CaseRobot.BEHAVIOR_WINNER] * nbwinners)
        # hunters :
        if nbhunters > 0:
            listbehav.extend([CaseRobot.BEHAVIOR_HUNTER] * nbhunters)
        # autres :
        if nbothers > 0:
            d = nbothers // nbotherscomp
            r = nbothers % nbotherscomp
            if d == 0:
                i = 0
                while i < nbothers:
                    listbehav.append(otherscomp[i])
                    i += 1
            else:
                i = 0
                while i < d:
                    for comp in otherscomp:
                        listbehav.append(comp)
                    i += 1
                if r > 0:
                    j = 0
                    while j < r:
                        comp = cr.CustomRandom.choice(otherscomp)
                        listbehav.append(comp)
                        j += 1
        # mémo dénombrement :
        cls._BEHAVIOR_COUNT_DICT = dict()
        cls._BEHAVIOR_COUNT_DICT[CaseRobot.BEHAVIOR_WINNER] = nbwinners
        cls._BEHAVIOR_COUNT_DICT[CaseRobot.BEHAVIOR_HUNTER] = nbhunters
        cls._BEHAVIOR_COUNT_DICT["others"] = nbotherscomp
        # mélange et retour :
        cr.CustomRandom.shuffle(listbehav)
        return listbehav

    _define_bots_behaviors_list = classmethod(_define_bots_behaviors_list)

    #-----> Getters
    def get_game_repr(cls):
        """
        Retourne des infos textuelles à propos de la configuration
        """
        msg = "Jeu non configuré"
        if cls._DIFFICULTY != None:
            msg = "Niveau : " + str(cls._DIFFICULTY) + " ("
            msg += "w=" + str(cls._W_RANGE) + ", h=" + str(cls._H_RANGE) + ")"
        return msg

    get_game_repr = classmethod(get_game_repr)

    def get_difficulty(cls):
        """
        Retourne le niveau courant
        """
        return cls._DIFFICULTY

    get_difficulty = classmethod(get_difficulty)

    def is_game_configured(cls):
        """
        Indique si la classe a été configurée
        """
        if cls._DIFFICULTY != None:
            return True
        return False

    is_game_configured = classmethod(is_game_configured)

    def get_behaviors_list(cls):
        """
        Retourne la liste des comportements sélectionnés
        """
        return cls._BEHAVIOR_LIST

    get_behaviors_list = classmethod(get_behaviors_list)

    def get_behaviors_count(cls):
        """
        Retourne le dict de dénombrement winners, hunters, autres
        """
        return cls._BEHAVIOR_COUNT_DICT

    get_behaviors_count = classmethod(get_behaviors_count)

    def get_behaviors(cls):
        """
        Retourne les comportements de robots associés au niveau
        """
        return cls._BOT_BEHAVIOR_ACCEPTED

    get_behaviors = classmethod(get_behaviors)

    def get_initial_bots_inter_distance(cls):
        """
        Retourne la distance initiale entre bots
        """
        return cls._BOTS_INTER_DIST

    get_initial_bots_inter_distance = classmethod(get_initial_bots_inter_distance)

    def get_bots_number(cls):
        """
        Retourne le nombre de bots à ajouter
        """
        dens = cls.get_initial_density("bots")
        num = min(math.ceil(cls._W_RANGE * cls._H_RANGE * dens), 15)
        return num

    get_bots_number = classmethod(get_bots_number)

    def get_bot_proportion(cls, behavior):
        """
        Retourne la proportion de winners, hunters ou autres.
        """
        if behavior == CaseRobot.BEHAVIOR_WINNER:
            return cls._WINNER_PROP
        elif behavior == CaseRobot.BEHAVIOR_HUNTER:
            return cls._HUNTER_PROP
        else:
            return 1 - cls._WINNER_PROP - cls._HUNTER_PROP

    get_bot_proportion = classmethod(get_bot_proportion)

    def get_max_aggressivite(cls):
        """
        Retourne l'aggressivité max d'un robot
        """
        return cls._BOT_MAX_AGGRESSIVITE

    get_max_aggressivite = classmethod(get_max_aggressivite)

    def get_max_efficacite(cls):
        """
        Retourne l'efficacité max d'un robot
        """
        return cls._BOT_MAX_EFFICACITE

    get_max_efficacite = classmethod(get_max_efficacite)

    def get_initial_powers(cls, powertype):
        """
        Retourne les pouvoirs initiaux d'un robot
        """
        if powertype in [
            "has_mine",
            "puissance_mine",
            "has_grenade",
            "puissance_grenade",
            "portee_grenade",
            "vitesse",
        ]:
            return cls._BOTS_INITIAL_POWERS[powertype]
        return None

    get_initial_powers = classmethod(get_initial_powers)

    def get_carte_dimensions(cls):
        """
        Retourne w, h
        """
        return cls._W_RANGE, cls._H_RANGE

    get_carte_dimensions = classmethod(get_carte_dimensions)

    def get_initial_density(cls, typeobj):
        """
        Retourne la densité initiale pour typeobj dans ["vide", "porte", "bots", 
        "danger", "bonus"]
        """
        if typeobj in ["vide", "porte", "bots", "danger", "bonus"]:
            return cls._DENSITY[typeobj]
        else:
            return None

    get_initial_density = classmethod(get_initial_density)

    def get_danger_max_power(cls):
        """
        Retourne l'impact max d'une mine
        """
        return cls._DANGER_MAX_POWER

    get_danger_max_power = classmethod(get_danger_max_power)

    def ensure_danger_density(cls):
        """
        Indique si la densité de danger doit être maintenue
        """
        return cls._ENSURE_DANGER_DENSITY

    ensure_danger_density = classmethod(ensure_danger_density)

    def get_bonus_policy(cls, bonustype):
        """
        Retourne un dict de paramétrage pour bonustype dans ["vitesse", "mine", 
        "grenade"]
        """
        if bonustype in ["vitesse", "mine", "grenade"]:
            return cls._BONUS_POLICY[bonustype]
        else:
            return None

    get_bonus_policy = classmethod(get_bonus_policy)

    def ensure_bonus_density(cls):
        """
        Indique si la densité de danger doit être maintenue
        """
        return cls._ENSURE_BONUS_DENSITY

    ensure_bonus_density = classmethod(ensure_bonus_density)
