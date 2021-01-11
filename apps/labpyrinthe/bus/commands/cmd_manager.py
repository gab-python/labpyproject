#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
**CommandManager**, le gestionnaire de commandes du jeu, assurant les deux rôles suivants :

1. Garantit la validité des commandes utilisateurs
2. Pilote les joueurs automatiques

Principes généraux de pilotage des robots:

- les commandes dépendent du type du robot (Chasseur, Winner, ...) et de ses caractéristiques
  propres (intelligence, aggressivité...)
- les robots évoluent au moyen d'une cible principale (la sortie pour un Winner, un adversaire 
  pour un chasseur, ...) et d'une cible temporaire représentant la prochaine étape à atteindre
- le choix d'une commande suit la séquence suivante :

  1. analyse globale de l'environnement (bonus à portée, dangers pouvant impacter le robot, 
     est il en retard...), évaluation de la pertinence des cibles
  2. évaluation des options pouvant constituer la prochaine cible temporaire dans les 4 directions 
     (mesures de densité, calculs de scores)
  3. sélection au besoin d'une nouvelle cible temporaire (prise en compte du coût de parcours
     dans le choix)
  4. priorisation des objectifs en fonction des caractéristiques du robot (mouvement, 
     attaque, défense, travail)
  5. choix de la prochaine commande (ou d'une séquence de coups pour les robots les plus 
     intelligents disposant de plusieurs coups consécutifs)

.. admonition:: Optimisations:

   - cache de très court terme (pour le coup en cours): combinaisons de grenade, chemins
   - cache de court terme (pour la série de coups en cours): objectifs, pseudo actions 
     programmées, probabilité de risque associées aux cases atteignables
   - cache de moyen et long terme: portés par le gestionnaire de carte (LabLevel) et ses 
     applats (Matrices).
   - utilisation de sets plutôt que de listes

"""
# imports :
import math, time
from operator import itemgetter
from operator import attrgetter
import labpyproject.core.random.custom_random as cr
from labpyproject.apps.labpyrinthe.bus.helpers.lab_generator import LabGenerator
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import LabHelper
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import Case
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseRobot
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseDanger
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseGrenade
from labpyproject.apps.labpyrinthe.bus.commands.cmd_helper import CommandHelper
from labpyproject.apps.labpyrinthe.bus.commands.gamble_datas import GambleDataSet
from labpyproject.apps.labpyrinthe.bus.commands.gamble_datas import GambleDataObject
from labpyproject.apps.labpyrinthe.bus.commands.gamble_datas import PseudoActions
from labpyproject.apps.labpyrinthe.bus.commands.targets import TargetObject
from labpyproject.apps.labpyrinthe.bus.commands.targets import TargetPath
from labpyproject.apps.labpyrinthe.bus.commands.targets import TargetPathStep

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["CommandManager"]
# classes :
class CommandManager:
    """
    **Gestionnaire des commandes**
    
    1. validation des commandes entrées par les joueurs
    2. génération des commandes des joueurs automatiques
    
    .. note::
       Prototype fonctionnel. Classe trop lourde (> 6500 lignes), à reconcevoir 
       de façon plus générique dans une version de production.
    
    .. highlight:: none
    Plan du code source : ::
    
        A- Interface publique
        B- Méthodes privées d'analyse et de décision
            B.1- Commande forcée en cas d'échec des algos de décision
            B.2- Initialisations
                B.2.1- Cache de sets
                B.2.2- Initialisations (reconnaissance globale, évaluation des cibles, phase de jeu)
                B.2.3- Initialisations spécifiques
            B.3- Génération des données de choix de commande
            B.4- Evaluation des données de choix de commande
            B.5- Sélection de cible, recherche de chemins
                B.5.1- Cible temporaire
                B.5.2- Interface de recherche de chemins
                B.5.3- Recherche exhaustive de chemins
                B.5.4- Recherche optimisée sur de longues distances
                B.5.5- Approche finale de la cible principale
            B.6- Qualification des options adjacentes
            B.7- Anticipation de coups consécutifs
                B.7.1- Dédiée aux winners et hunters intelligents
                B.7.2- Recherche d'une série de commandes : analyse et décisions
                B.7.3- Méthodes de recherche thématiques
                B.7.4- Schedule tools
                B.7.5- Application de commandes anticipées
            B.8- Recherche du prochain coup
            B.9- Outils communs aux recherches de commande
            B.10- Outils liés au comportement
            B.11- Gestion de lancer de grenade
            B.12- Utilitaires basiques
    .. highlight:: default   
    """

    # phases de jeu
    PHASIS_START = "PHASIS_START"  #: début de partie
    PHASIS_IN_PROGRESS = "PHASIS_IN_PROGRESS"  #: partie en cours
    PHASIS_APPROACH = "PHASIS_APPROACH"  #: approche de la cible
    PHASIS_FINAL = "PHASIS_FINAL"  #: phase finale d'approche
    PHASIS_HUNT = "PHASIS_HUNT"  #: force un chasseur à poursuivre sa cible
    DIST_APPROACH = 5  #: distance à la cible caractérisant la phase finale
    # contexte de sélection des séries de coups
    CTX_OPTIMAL = "CTX_OPTIMAL"  #: contexte de recherche de coups multiples optimal
    CTX_BY_OBJ = "CTX_BY_OBJ"  #: contexte de recherche de coups multiples par objectifs
    CTX_BONUS = "CTX_BONUS"  #: contexte de recherche de coups multiples bonus
    CTX_DESPERATE = (
        "CTX_DESPERATE"  
    ) #: contexte de recherche de coups multiples désespéré
    # objectifs des robots :
    OBJ_ATTACK = "OBJ_ATTACK"  #: marque l'objectif attaque
    OBJ_DEFENSE = "OBJ_DEFENSE"  #: marque l'objectif défense
    OBJ_MOVE = "OBJ_MOVE"  #: marque l'objectif mouvement
    OBJ_WORK = "OBJ_WORK"  #: marque l'objectif travail
    OBJ_RANDOM = "OBJ_RANDOM"  #: marque l'objectif aléatoire
    # types de PseudoActions (série d'actions anticipées)
    PA_OPTIMAL_MOVE = "PA_OPTIMAL_MOVE"  #: pseudoaction de type mouvement
    PA_FREE_EXIT = "PA_FREE_EXIT"  #: pseudoaction de type libérer la sortie
    PA_SAFE_MOVE = "PA_SAFE_MOVE"  #: pseudoaction de type déplacement sans risques
    PA_RISKED_MOVE = "PA_RISKED_MOVE"  #: pseudoaction de type déplacement risqué
    PA_STAY_IN_PLACE = "PA_STAY_IN_PLACE"  #: pseudoaction de type ne pas bouger
    PA_TERRAFORM = "PA_TERRAFORM"  #: pseudoaction de type dégager le chemin
    PA_ATTACK = "PA_ATTACK"  #: pseudoaction de type attaque
    PA_BONUS = "PA_BONUS"  #: pseudoaction de type prise de bonus
    PA_DANGERS = "PA_DANGERS"  #: pseudoaction de type destruction de dangers (pour rebattre les cartes)
    PA_ESCAPE = "PA_ESCAPE"  #: pseudoaction de type fuite
    PA_TYPES = [
        PA_OPTIMAL_MOVE,
        PA_FREE_EXIT,
        PA_SAFE_MOVE,
        PA_RISKED_MOVE,
        PA_STAY_IN_PLACE,
        PA_TERRAFORM,
        PA_ATTACK,
        PA_BONUS,
        PA_DANGERS,
        PA_ESCAPE,
    ]  #: liste des types de pseudoactions supportées
    # méthodes
    def __init__(self):
        """
        Constructeur
        """
        # Niveau (couches de matrices) :
        self._lablevel = None
        # Liste des cases associées aux robots
        self._liste_robots = None
        # Sets remis à jour avant chaque coup :
        self.case_sets_updated = False
        self.alive_bots = None
        self.human_alive = None
        self.winner_alive = None
        self.hunter_alive = None
        self.winner_human_alive = None
        self.winner_human_hunter_alive = None
        self.dangers_set = None
        self.dangers_set_1 = None
        self.dangers_set_plus1 = None
        self.bonus_set = None
        self.play_set = None
        # enregistrement temporaire des blocages de chemins
        self._pathblocklist = None
        # id du coup en cours
        self._currentgambleid = None
        # enregistrement des commandes invalides : k=gambleid, v=cmd
        self._discardedcmddict = dict()

    #-----> A- Interface publique
    def re_initialise(self):
        """
        Ré initialisation avant une nouvelle partie
        """
        # Niveau (couches de matrices) :
        self._lablevel = None
        # Liste des cases associées aux robots
        self._liste_robots = None
        # Sets remis à jour avant chaque coup :
        self.case_sets_updated = False
        self.alive_bots = None
        self.human_alive = None
        self.winner_alive = None
        self.hunter_alive = None
        self.winner_human_alive = None
        self.winner_human_hunter_alive = None
        self.dangers_set = None
        self.dangers_set_1 = None
        self.dangers_set_plus1 = None
        self.bonus_set = None
        self.play_set = None
        # enregistrement temporaire des blocages de chemins
        self._pathblocklist = None
        # id du coup en cours
        self._currentgambleid = None
        # enregistrement des commandes invalides : k=gambleid, v=cmd
        self._discardedcmddict = dict()

    def set_labLevel(self, lablevel):
        """
        Définit ou re définit l'objet LabLevel associé
        """
        self._lablevel = lablevel

    def set_liste_robot(self, listrobot):
        """
        Définit la liste des robots
        """
        self._liste_robots = listrobot

    #-----> Validation / application
    def analyse_cmd_for_robot(self, cmd, robot):
        """
        Analyse une commande
        
        Retourne un tuple avec :
        
        * un boolean indiquant si la commande a apporté un changement
        * le dict généré par CommandHelper.translate_cmd
        * une liste décrivant les conséquences (bonus gagné, danger activé, robot tué, 
          grenade à lancer, case à ajouter)
        * la case visée par le coup        
        """
        dictcmd = None
        action = None
        consequences = list()
        next_case = None
        try:
            dictcmd = CommandHelper.translate_cmd(cmd)
        except ValueError:
            return False, None, consequences, next_case
        else:
            action = dictcmd["action"]
        if action == None:
            return False, None, consequences, next_case
        # cas particuliers :
        if action in [
            LabHelper.ACTION_HELP,
            LabHelper.ACTION_QUIT,
            LabHelper.ACTION_START,
            LabHelper.ACTION_RESET_QUEUE,
        ]:
            # aucune validation à faire :
            return False, dictcmd, consequences, next_case
        # cas général :
        result = False
        direct = dictcmd["direct"]
        x_r = int(robot.x)
        y_r = int(robot.y)
        x_s, y_s = int(x_r), int(y_r)
        flatmatrice = self._lablevel.get_flat_matrice()
        casesadj = flatmatrice.get_cases_adjacentes(x_r, y_r)
        # déplacement :
        pas = dictcmd["pas"]
        if action == LabHelper.ACTION_MOVE:
            pas = 1
            if direct == LabHelper.LEFT:
                next_case = casesadj["left"]
                x_r -= 1
            elif direct == LabHelper.RIGHT:
                next_case = casesadj["right"]
                x_r += 1
            elif direct == LabHelper.TOP:
                next_case = casesadj["top"]
                y_r -= 1
            elif direct == LabHelper.BOTTOM:
                next_case = casesadj["bottom"]
                y_r += 1
            possible = self._possible_todo_ACTION_on_case(next_case, action, robot)
            if possible:
                # déplacement possible
                result = True
                # caractérisation :
                nb_cases = max(math.fabs(x_r - x_s), math.fabs(y_r - y_s))
                consequences.append(
                    {
                        "type": "bot_move",
                        "robot": robot,
                        "case": next_case,
                        "coords1": (x_s, y_s),
                        "coords2": (x_r, y_r),
                        "nb_cases": nb_cases,
                    }
                )
                # cas particuliers :
                if next_case.type_case == LabHelper.CASE_BONUS:
                    consequences.append(
                        {"type": "bonus_win", "robot": robot, "case": next_case}
                    )
                elif next_case.type_case == LabHelper.CASE_DANGER:
                    consequences.append(
                        {"type": "danger_activated", "robot": robot, "case": next_case}
                    )
        elif action == LabHelper.ACTION_GRENADE:
            puissance = dictcmd["puissance"]
            if robot.portee_grenade >= pas and robot.puissance_grenade >= puissance:
                target = self._get_case_for_dir_and_pas(robot, direct, pas)
                if target != None and target.type_case in LabHelper.FAMILLE_GRENADE:
                    result = True
                    gdict = CaseGrenade.get_default_dict()
                    gdict["x"] = target.x
                    gdict["y"] = target.y
                    gdict["danger_impact"] = puissance
                    gdict["x_start"] = robot.x
                    gdict["y_start"] = robot.y
                    caseG = CaseGrenade(gdict)
                    nb_cases = max(math.fabs(target.x - x_s), math.fabs(target.y - y_s))
                    consequences.append(
                        {
                            "type": "launch_grenade",
                            "grenade": caseG,
                            "coords1": (x_s, y_s),
                            "coords2": (target.x, target.y),
                            "nb_cases": nb_cases,
                        }
                    )
        else:
            # case visée
            if direct == LabHelper.LEFT:
                next_case = casesadj["left"]
            elif direct == LabHelper.RIGHT:
                next_case = casesadj["right"]
            elif direct == LabHelper.TOP:
                next_case = casesadj["top"]
            elif direct == LabHelper.BOTTOM:
                next_case = casesadj["bottom"]
            possible = self._possible_todo_ACTION_on_case(next_case, action, robot)
            if possible:
                result = True
                if action == LabHelper.ACTION_CREATE_DOOR:
                    # on modifie le type de la case
                    role = LabHelper.CASE_PORTE
                    face = LabHelper.get_repr_for_role(role)
                    case = Case(next_case.x, next_case.y, role, face)
                    consequences.append({"type": "case_to_add", "case": case})
                    if next_case.type_case == LabHelper.CASE_DANGER:
                        consequences.append(
                            {
                                "type": "danger_activated",
                                "robot": None,
                                "case": next_case,
                            }
                        )
                elif action == LabHelper.ACTION_CREATE_WALL:
                    role = LabHelper.CASE_MUR
                    face = LabHelper.get_repr_for_role(role)
                    case = Case(next_case.x, next_case.y, role, face)
                    consequences.append({"type": "case_to_add", "case": case})
                    if next_case.type_case == LabHelper.CASE_DANGER:
                        consequences.append(
                            {
                                "type": "danger_activated",
                                "robot": None,
                                "case": next_case,
                            }
                        )
                elif action == LabHelper.ACTION_KILL:
                    for robot in self._liste_robots:
                        if (robot.x, robot.y) == (next_case.x, next_case.y):
                            consequences.append(
                                {"type": "robot_killed", "robot": next_case}
                            )
                            break
                elif action == LabHelper.ACTION_MINE:
                    if "puissance" in dictcmd.keys():
                        puissance = dictcmd["puissance"]
                    else:
                        puissance = robot.puissance_mine
                    dictdanger = CaseDanger.get_default_dict()
                    dictdanger["x"] = next_case.x
                    dictdanger["y"] = next_case.y
                    dictdanger["danger_type"] = CaseDanger.DANGER_MINE
                    dictdanger["danger_impact"] = puissance
                    case = CaseDanger(dictdanger)
                    consequences.append({"type": "case_to_add", "case": case})
                    if next_case.type_case == LabHelper.CASE_DANGER:
                        consequences.append(
                            {
                                "type": "danger_activated",
                                "robot": None,
                                "case": next_case,
                            }
                        )
        # mémorisation des cmds invalides :
        if not result:
            self._discard_cmd_for_gambleid(cmd, robot)
        return result, dictcmd, consequences, next_case

    def _discard_cmd_for_gambleid(self, cmd, robot):
        """
        Invalide la cmd passée en paramètre
        """
        k = self._currentgambleid
        d = self._discardedcmddict
        if k not in d.keys():
            d[k] = list()
        l = d[k]
        l.append(cmd)

    def _pre_analyse_cmd_for_robot(self, cmd, robot):
        """
        Vérifie que la commande est ni nulle, ni mémorisée comme invalide.
        """
        valide = True
        if cmd == None:
            valide = False
        else:
            k = self._currentgambleid
            d = self._discardedcmddict
            if k not in d.keys():
                d[k] = list()
            l = d[k]
            valide = cmd not in l
        return valide

    def validate_action_for_robot(
        self, action, robot, nextcase, botskilled, gambleid, gamblenumber, gamblecount
    ):
        """
        Initialisations après application d'une commande
        """
        # enregistrement de l'action :
        robot.totalgamblecount += 1  # inc du nb de coups unitaires joués
        robot.register_action(action, gambleid)
        # ... de la case
        if action == LabHelper.ACTION_MOVE:
            robot.register_case(nextcase, gambleid)
        # ... des bots éliminés
        robot.register_bots_killed(botskilled)
        if gamblenumber == gamblecount:
            # ré init gdSet
            robot.register_current_gdSet(None)
            # ré init vitesse courante
            robot.current_vitesse = robot.vitesse
            # ... et zones :
            self._lablevel.update_bot_action_zones(robot)

    #-----> Initialisation du robot avant un coup
    def init_robot_before_gamble(self, robot, gamblenumber, gamblecount):
        """
        Met à jour la vitesse actuelle du robot ainsi que ses zones de déplacement
        et d'attaque
        """
        robot.current_vitesse = gamblecount - gamblenumber
        robot.current_gamble_count = gamblecount
        robot.current_gamble_number = gamblenumber
        if gamblenumber == 0:
            robot.create_gamble_coords_entry()
        self._lablevel.update_bot_action_zones(robot, nextgamble=True)
        self.case_sets_updated = False

    #-----> Calcul de commande pour Bots
    def compute_cmd_for_autobot(self, robot, gamblenumber, gamblecount, gambleid):
        """
        Définit la cmd à appliquer à un robot automatique suivant son comportement
        
        Args:
            robot
            gamblenumber : numéro du coup (à partir de 1)
            gamblecount : nombre de coups consécutifs du joueur
            gambleid : id unique d'un coup de la partie
        
        Returns:
            cmd
        """
        # 1- Initialisations
        self._currentgambleid = gambleid
        # - maj des listes ré utilisées :
        self._update_usefull_sets()
        # - structure de données
        gdSet = robot.get_current_gdSet()
        gdmemory = None
        if gdSet != None:
            gdmemory = gdSet.get_GD_memory()
        gdSet = GambleDataSet(
            gamblenumber=gamblenumber,
            gamblecount=gamblecount,
            gambleid=gambleid,
            gdmemory=gdmemory,
        )
        robot.register_current_gdSet(gdSet)
        # - initialisation du contexte
        self._init_gamble_context(robot)
        # 2- Recueil de données :
        do_compute = self._need_to_compute_gamble_datas(robot)
        if do_compute:
            # - recueil de données maximal :
            self._get_gamble_datas_for_bot(robot)
            # - calculs de scores :
            self._add_scores_to_gamble_datas(robot)
            # - indique que l'alimentation en données est effectuée :
            gdSet.datas_computed = True
        # 3- Ciblage:
        if robot.game_phasis == CommandManager.PHASIS_FINAL:
            # - le chemin vers la cible est il valable?
            mainTarget = robot.get_main_target()
            if mainTarget != None:
                maintp = mainTarget.targetpath
                dodiscard, newtp = self._update_or_discard_TargetPath(robot, maintp)
                if dodiscard:
                    # recherche du chemin vers la cible principale
                    self._search_final_TargetPath(robot)
                else:
                    # mise à jour du chemin
                    mainTarget.targetpath = newtp
                    if newtp != None:
                        mainTarget.pathcost = newtp.cost
        if do_compute:
            # - redéfinition de la cible temporaire
            self._select_new_temp_target(robot)
        # 4- Classement des options adjacentes
        by_gdSet = do_compute
        self._evaluate_adjacent_cases(robot, by_gdSet)
        # 5- Recherche d'une série de coups?
        do_schedule = self._can_schedule_gambles(robot)
        if do_schedule:
            self._schedule_next_gambles(robot)
        # 6- Choix de la commande à appliquer :
        # - via une pseudo action anticipée ?
        cmd = self._get_cmd_for_next_pseudoaction(robot)
        # - choix de commande à l'instant t :
        if cmd == None:
            cmd = self._search_next_command(robot)
        # 7- ALT / Choix par défaut :
        if cmd == None:
            cmd = self._force_cmd_choice_for_autobot(robot)
        return cmd

    def _pre_check_or_nullify_cmd(self, cmd, robot):
        """
        Vérifie que la commande n'a pas été invalidée auparavant, retourne
        None le cas échéant.
        """
        # pré validation
        valide = self._pre_analyse_cmd_for_robot(cmd, robot)
        if not valide:
            cmd = None
        return cmd

    #-----> B- Méthodes privées d'analyse et de décision
    #-----> B.1- Commande forcée en cas d'échec des algos de décision
    def _force_cmd_choice_for_autobot(self, robot):
        """
        Force le choix d'une commande lorsqu'aucun choix rationnel n'a pu être
        établi.
        """
        gdSet = robot.get_current_gdSet()
        caseadj = gdSet.get_list_case("all_adj")
        # on distingue cases libres, robots et cases dangers :
        # Rq : une case libre peut avoir été exclue car elle expose à un
        # adversaire dangereux
        freelist = [c for c in caseadj if c.type_case in LabHelper.FAMILLE_CASES_LIBRES]
        murlist = [c for c in caseadj if c.type_case == LabHelper.CASE_MUR]
        botlist = [c for c in caseadj if c.type_case == LabHelper.CASE_ROBOT]
        dgrlist = [c for c in caseadj if c.type_case == LabHelper.CASE_DANGER]
        # en fonction de l'instinct de survie :
        cmd = None
        midSUR = CaseRobot.get_feature_threshold("instinct_survie", "middle")
        if cmd == None and len(freelist) > 0:
            # on se déplace sur une case libre :
            for free in freelist:
                cmd = self._evaluate_simple_action(
                    robot,
                    {"action": LabHelper.ACTION_MOVE, "code": ""},
                    free,
                    handlebehavior=False,
                )
                cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                if cmd != None:
                    break
            # on crée une porte:
            if cmd == None and len(murlist) > 0:
                for mur in murlist:
                    cmd = self._evaluate_simple_action(
                        robot,
                        {
                            "action": LabHelper.ACTION_CREATE_DOOR,
                            "code": LabHelper.CHAR_PORTE,
                        },
                        mur,
                    )
                    cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                    if cmd != None:
                        break
        if cmd == None:
            # lancer de grenade?
            cmd = self._random_launch_grenade(robot)
            cmd = self._pre_check_or_nullify_cmd(cmd, robot)
        if (
            cmd == None
            and (robot.instinct_survie > midSUR and len(botlist) > 0)
            or (len(freelist) == 0 and len(dgrlist) == 0)
        ):
            # on élimine un robot au hasard :
            victim = cr.CustomRandom.choice(botlist)
            cmd = self._evaluate_simple_action(
                robot,
                {"action": LabHelper.ACTION_KILL, "code": LabHelper.CHAR_KILL},
                victim,
                handlebehavior=False,
            )
            cmd = self._pre_check_or_nullify_cmd(cmd, robot)
        if cmd == None and len(dgrlist) > 0:
            # on se déplace sur une mine :
            mine = cr.CustomRandom.choice(dgrlist)
            cmd = self._evaluate_simple_action(
                robot,
                {"action": LabHelper.ACTION_MOVE, "code": ""},
                mine,
                handlebehavior=False,
            )
            cmd = self._pre_check_or_nullify_cmd(cmd, robot)
        return cmd

    #-----> B.2- Initialisations
    #-----> B.2.1- Cache de sets
    def _update_usefull_sets(self):
        """
        Recalcul de listes (sets) ré utilisées pendant les calculs
        """
        # 1- Sets de robots
        # robots en activité
        self.alive_bots = set([r for r in self._liste_robots if r.alive])
        # et humains
        self.human_alive = set([r for r in self.alive_bots if r.human])
        # et winners
        self.winner_alive = set(
            [r for r in self.alive_bots if r.behavior == CaseRobot.BEHAVIOR_WINNER]
        )
        # et hunters
        self.hunter_alive = set(
            [r for r in self.alive_bots if r.behavior == CaseRobot.BEHAVIOR_HUNTER]
        )
        # humains et winners
        self.winner_human_alive = set(
            [
                r
                for r in self.alive_bots
                if r.behavior == CaseRobot.BEHAVIOR_WINNER or r.human
            ]
        )
        # les trois
        self.winner_human_hunter_alive = set(
            [
                r
                for r in self.alive_bots
                if r.behavior == CaseRobot.BEHAVIOR_WINNER
                or r.behavior == CaseRobot.BEHAVIOR_HUNTER
                or r.human
            ]
        )
        # 2- Sets de cases :
        # cases dangers :
        self.dangers_set = self._lablevel.get_typecase_set(LabHelper.CASE_DANGER)
        self.dangers_set_1 = set([c for c in self.dangers_set if c.danger_impact == 1])
        self.dangers_set_plus1 = self.dangers_set.difference(self.dangers_set_1)
        # cases bonus :
        self.bonus_set = self._lablevel.get_typecase_set(LabHelper.CASE_BONUS)
        # cases "jouables" (ie hors murs extérieurs)
        flatmatrice = self._lablevel.get_flat_matrice()
        full_set = flatmatrice.get_set_cases()
        murs_ext_set = self._lablevel.get_typecase_set(LabHelper.CASE_MUR_PERIMETRE)
        self.play_set = full_set.difference(murs_ext_set)
        # 3- marqueur
        self.case_sets_updated = True

    #-----> B.2.2- Initialisations (reconnaissance globale, évaluation des cibles, phase de jeu)
    def _init_gamble_context(self, robot):
        """
        Initialise les cibles avant le processus de choix de commande
        """
        # repérage de l'environnement
        self._recognize_area(robot)
        # mise à jour des références :
        self._update_target_ref(robot, robot.get_temp_target())
        self._update_target_ref(robot, robot.get_main_target())
        # cible principale :
        self._define_mainTarget(robot)
        # cible temporaire :
        self._evaluate_temp_target(robot)
        tempTarget = robot.get_temp_target()
        if tempTarget != None and tempTarget.discarded:
            robot.set_temp_target(None)
        # phase de jeu :
        self._update_robot_gamePhasis(robot)
        # winners et hunters : besoin de bonus ?
        self._bot_need_to_earn_bonus(robot)
        # winners : des concurrents sont ils proches de la sortie?
        if robot.behavior == CaseRobot.BEHAVIOR_WINNER:
            self._are_adversaires_in_advance(robot)

    def _recognize_area(self, robot):
        """
        Repère :
        
        * les robots contre lesquels se défendre
        * ceux que l'on peut toucher
        * les cases "safe"
        * les dangers pouvant nous atteindre en cas d'explosion
        * les bonus à portée            
        """
        # paramètres :
        rlist = [r for r in self.alive_bots if r != robot]
        move_zone = self._lablevel.get_caseset_for_coordset(robot.move_zone)
        attack_zone = self._lablevel.get_caseset_for_coordset(robot.attack_zone)
        # analyse :
        rdict = {
            "attaque": list(),
            "defense": list(),
            "safezone": list(),
            "realsafezone": list(),  # cases de safezone hors de portée d'une mine
            "dangers": list(),
            "bonus": list(),
            "attaque_all": list(),
            "defense_all": list(),
            "extendedunsafezone": list(),
            "kill_all": list(),
        }
        # défense et attaque :
        safe_set = move_zone  # cases sûres / coups directs
        ext_unsafe_set = set()  # zone étendue des cases attaquables
        for bot in rlist:
            # attaque :
            if self._may_firstbot_attack_otherbot(robot, bot):
                rdict["attaque_all"].append(bot)
                rdict["kill_all"].append(bot)
                if bot in attack_zone:
                    rdict["attaque"].append(bot)
            # défense :
            if self._may_firstbot_attack_otherbot(bot, robot):
                rdict["defense_all"].append(bot)
                if bot not in rdict["kill_all"]:
                    rdict["kill_all"].append(bot)
                bot_attaque = self._lablevel.get_caseset_for_coordset(bot.attack_zone)
                if robot in bot_attaque:
                    rdict["defense"].append(bot)
                safe_set = safe_set.difference(bot_attaque)
                ext_unsafe_set = ext_unsafe_set.union(bot_attaque)
        # zone safe et realsafezone :
        if len(ext_unsafe_set) > 0 and len(safe_set) > 0:
            # si il y a des adversaires dangereux et des cases à priori sûres
            t_h = CaseRobot.THRES_HIGH
            instinct_survie = robot.instinct_survie
            intelligence = robot.intelligence
            if instinct_survie >= t_h or intelligence >= t_h:
                # on prend en compte l'exposition des cases aux mines
                real_safe_list = list()
                for c in safe_set:
                    if not self._is_case_surrounded_by_mine(c):
                        real_safe_list.append(c)
                rdict["realsafezone"] = real_safe_list
        rdict["safezone"] = list(safe_set)
        rdict["extendedunsafezone"] = list(ext_unsafe_set)
        # trie :
        rdict["defense"].sort(key=itemgetter("aggressivite"), reverse=True)
        rdict["attaque"].sort(key=itemgetter("aggressivite"), reverse=True)
        dfunc = lambda c: self._lablevel.get_distance_between_cases(c, robot)
        rdict["attaque_all"].sort(key=dfunc)
        rdict["defense_all"].sort(key=dfunc)
        # dangers :
        # les dangers dans la sous matrice 5*5 centrée sur robot
        dgr_set = list(self._lablevel.get_minelist_arround_case(robot))
        # sélection des dangers pouvant impacter le robot (sans récursivité) :
        for dgr in dgr_set:
            if self._does_mine_impact_case(dgr, robot):
                rdict["dangers"].append(dgr)
        rdict["dangers"].sort(key=itemgetter("danger_impact"), reverse=True)
        # bonus : à portée
        bonus_set = move_zone.intersection(self.bonus_set)
        rdict["bonus"] = list(bonus_set)
        # enregistrement :
        gdSet = robot.get_current_gdSet()
        gdSet.register_list_case("defense", rdict["defense"])
        gdSet.register_list_case("defense_all", rdict["defense_all"])
        gdSet.register_list_case("attaque", rdict["attaque"])
        gdSet.register_list_case("attaque_all", rdict["attaque_all"])
        gdSet.register_list_case("kill_all", rdict["kill_all"])
        gdSet.register_list_case("safezone", rdict["safezone"])
        gdSet.register_list_case("realsafezone", rdict["realsafezone"])
        gdSet.register_list_case("extendedunsafezone", rdict["extendedunsafezone"])
        gdSet.register_list_case("dangers", rdict["dangers"])
        gdSet.register_list_case("bonus", rdict["bonus"])

    def _update_target_ref(self, robot, target):
        """
        Met à jour les références aux cases des cibles
        """
        if target != None:
            oldcase = target.case
            if oldcase.type_case == LabHelper.CASE_ROBOT:
                target.x = oldcase.x
                target.y = oldcase.y
            else:
                flatmatrice = self._lablevel.get_flat_matrice()
                newcase = flatmatrice.get_case(oldcase.x, oldcase.y)
                target.case = newcase

    def _define_mainTarget(self, robot):
        """
        Affecte une cible principale au robot en fonction de son comportement
        """
        flatmatrice = self._lablevel.get_flat_matrice()
        mainTarget = robot.get_main_target()
        if mainTarget != None:
            maincase = mainTarget.case
            if isinstance(maincase, CaseRobot) and not maincase.alive:
                robot.set_main_target(None)
                mainTarget = None
        case_sortie = self._lablevel.get_case_sortie()
        targetsortie = TargetObject(TargetObject.TARGET_MAIN, case_sortie)
        if robot.behavior == CaseRobot.BEHAVIOR_WINNER:
            # la sortie
            if mainTarget == None:
                robot.set_main_target(targetsortie)
        elif robot.behavior == CaseRobot.BEHAVIOR_HUNTER:
            # un robot à éliminer (huamin ou winner > autres)
            casehunt = self._find_bot_for_hunter(robot)
            if casehunt == None:
                # par défaut on se rapproche de la sortie
                robot.set_main_target(targetsortie)
            else:
                targethunt = TargetObject(TargetObject.TARGET_MAIN, casehunt)
                robot.set_main_target(targethunt)
        elif robot.behavior == CaseRobot.BEHAVIOR_SAPPER:
            # le barycentre d'une zone à faible densité de mines
            # dès la zone atteinte on redéfinit une nouvelle cible
            if mainTarget == None or self._is_bot_on_work_area(robot):
                params = self._find_density_area([LabHelper.CASE_DANGER], True)
                casemain = flatmatrice.get_case(
                    params["center"][0], params["center"][1]
                )
                targetmain = TargetObject(TargetObject.TARGET_MAIN, casemain)
                robot.set_main_target(targetmain, params=params)
        elif robot.behavior == CaseRobot.BEHAVIOR_BUILDER:
            # le barycentre d'une zone à faible densité de murs
            # dès la zone atteinte on redéfinit une nouvelle cible
            if mainTarget == None or self._is_bot_on_work_area(robot):
                params = self._find_density_area([LabHelper.CASE_MUR], True)
                casemain = flatmatrice.get_case(
                    params["center"][0], params["center"][1]
                )
                targetmain = TargetObject(TargetObject.TARGET_MAIN, casemain)
                robot.set_main_target(targetmain, params=params)
        elif robot.behavior in [CaseRobot.BEHAVIOR_TOURIST, CaseRobot.BEHAVIOR_RANDOM]:
            # une case au hasard :
            if mainTarget == None or self._is_bot_on_work_area(robot):
                w, h = flatmatrice.get_dimensions()
                x = cr.CustomRandom.choice(range(1, w - 2))
                y = cr.CustomRandom.choice(range(1, h - 2))
                casemain = flatmatrice.get_case(x, y)
                targetmain = TargetObject(TargetObject.TARGET_MAIN, casemain)
                robot.set_main_target(targetmain)
        # directions vers la cible principale (ou None)
        gdSet = robot.get_current_gdSet()
        gdSet.maintarget_directions = self._get_dirs_to_mainTarget(robot)

    def _evaluate_temp_target(self, robot):
        """
        Evalue la validité de la précédente cible temporaire, mise à jour
        éventuelle du chemin pour y parvenir
        """
        tempTarget = robot.get_temp_target()
        if tempTarget != None:
            dodiscard = False
            case = tempTarget.case
            # cas particuliers
            maintarget = robot.get_main_target()
            if maintarget != None:
                distmain = self._lablevel.get_distance_between_cases(robot, maintarget)
                if distmain < CommandManager.DIST_APPROACH:
                    tempTarget.discarded = True
                    return
            if robot.get_last_action() == LabHelper.ACTION_GRENADE:
                tempTarget.discarded = True
                return
            # 1- cible atteinte ?
            if (case.x, case.y) == (robot.x, robot.y):
                # cible atteinte :
                dodiscard = True
            else:
                # 2- test sur la nature de la cible :
                if not case.type_case in LabHelper.FAMILLE_TARGET:
                    # la cible a changé de nature, on invalide :
                    dodiscard = True
                else:
                    # 3- test du parcours précédent :
                    targetpath = tempTarget.targetpath
                    dodiscard, newpath = self._update_or_discard_TargetPath(
                        robot, targetpath
                    )
                    tempTarget.targetpath = newpath
                    if newpath != None:
                        tempTarget.pathcost = newpath.cost
            # si la cible reste valable, on met à jour la liste de cases :
            # (leur nature a pu changer)
            if not dodiscard:
                prevlistcases = tempTarget.listcases
                prevcoords = [(c.x, c.y) for c in prevlistcases]
                flatmatrice = self._lablevel.get_flat_matrice()
                newlistcases = [flatmatrice.get_case(*coords) for coords in prevcoords]
                tempTarget.listcases = newlistcases
            # validation de la cible temporaire :
            tempTarget.discarded = dodiscard

    def _update_robot_gamePhasis(self, robot):
        """
        Mise à jour de la phase de jeu du robot
        """
        phasis = None
        if robot.behavior == CaseRobot.BEHAVIOR_WINNER:
            phasis = self._update_winner_game_phasis(robot)
        elif robot.behavior == CaseRobot.BEHAVIOR_HUNTER:
            phasis = self._update_hunter_game_phasis(robot)
        else:
            # phase standard par défaut
            phasis = CommandManager.PHASIS_IN_PROGRESS
        # enregistrement
        robot.game_phasis = phasis

    def _is_bot_on_work_area(self, robot):
        """
        Indique si le robot est dans sa zone de travail
        """
        mainparams = robot.get_main_target_params()
        if mainparams == None:
            if robot.behavior in [
                CaseRobot.BEHAVIOR_TOURIST,
                CaseRobot.BEHAVIOR_RANDOM,
            ]:
                # est on proche de la cible ?
                maintarget = robot.get_main_target()
                if maintarget != None:
                    distmain = self._lablevel.get_distance_between_cases(
                        robot, maintarget
                    )
                    if distmain <= 2:
                        return True
                    else:
                        return False
            else:
                return False
        zone = mainparams["submatrice"]
        ltpt = zone.get_lefttop_point()
        ws, hs = zone.get_dimensions()
        x_r, y_r = robot.x, robot.y
        if (ltpt[0] <= x_r <= ltpt[0] + ws) and (ltpt[1] <= y_r <= ltpt[1] + hs):
            return True
        return False

    def _find_density_area(self, listtypecase, lowdensity, w=None, h=None):
        """
        Retourne la zone de plus faible/forte densité en cases de type typecase
        """
        flatmatrice = self._lablevel.get_flat_matrice()
        if w == None or h == None:
            wm, hm = flatmatrice.get_dimensions()
            w, h = wm // 2, hm // 2
        listsm = LabGenerator.sample_submatrices(flatmatrice, w, h)
        listres = list()
        for sm in listsm:
            if sm.get_dimensions() == (w, h):
                dens = LabGenerator.estime_densite(sm, listtypecase)
                listres.append({"submatrice": sm, "densite": dens})
        if lowdensity:
            listres.sort(key=itemgetter("densite"))
        else:
            listres.sort(key=itemgetter("densite"), reverse=True)
        submatrice = listres[0]["submatrice"]
        initial_densite = listres[0]["densite"]
        center = submatrice.get_lefttop_point()
        ws, hs = submatrice.get_dimensions()
        center = center[0] + ws // 2, center[1] + hs // 2
        return {
            "submatrice": submatrice,
            "center": center,
            "initial_densite": initial_densite,
        }

    #-----> B.2.3- Initialisations spécifiques
    def _bot_need_to_earn_bonus(self, robot):
        """
        Indique si le bot devrait obtenir des bonus.
        Retourne un boolean
        """
        behavior = robot.behavior
        do_need = False
        if behavior in [CaseRobot.BEHAVIOR_WINNER, CaseRobot.BEHAVIOR_HUNTER]:
            highQI = CaseRobot.get_feature_threshold("intelligence", "high")
            midEFF = CaseRobot.get_feature_threshold("efficacite", "middle")
            midAMB = CaseRobot.get_feature_threshold("ambition", "middle")
            winhum = [r for r in self.winner_human_alive if r != robot]
            nb_winhum = len(winhum)
            if (
                robot.intelligence > highQI
                or (robot.efficacite + robot.ambition) / 2 >= (midEFF + midAMB) / 2
            ):
                if robot.intelligence > highQI and robot.vitesse < 3:
                    do_need = True
                elif robot.game_phasis == CommandManager.PHASIS_START:
                    do_need = True
                else:
                    listebots = [
                        r for r in self.winner_human_hunter_alive if r != robot
                    ]
                    if len(listebots) > 0:
                        # capacités moyennes et max (humains, winners, hunters)
                        nb_bonus_moy = 0
                        nb_bonus_max = 0
                        vit_moy = 0
                        vit_max = 0
                        for r in listebots:
                            vit_moy += r.vitesse
                            vit_max = max(vit_max, r.vitesse)
                            nb_bonus_moy += r.earned_bonus
                            nb_bonus_max = max(nb_bonus_max, robot.earned_bonus)
                        vit_moy /= len(listebots)
                        nb_bonus_moy /= len(listebots)
                        # comparaison
                        if robot.intelligence > robot.ambition:
                            fact = 0.5
                            op = min
                        else:
                            fact = robot.ambition
                            op = max
                        comp_vitesse = robot.vitesse < op(vit_moy, vit_max * fact)
                        comp_bonus = robot.earned_bonus < op(
                            nb_bonus_moy, nb_bonus_max * fact
                        )
                        do_need = comp_vitesse or comp_bonus
            # si il n'y a plus de winners ou d'humains :
            if nb_winhum == 0:
                do_need = False
        # maj robot
        robot.need_bonus = do_need
        # stratégie de recherche de bonus :
        # Rq : pour un winner, fonction de l'avance des adversaire,
        # paramètre défini dans _are_adversaires_in_advance
        if robot.need_bonus:
            if behavior == CaseRobot.BEHAVIOR_HUNTER:
                # en fonction de la phase de jeu :
                if robot.game_phasis == CommandManager.PHASIS_HUNT:
                    # le robot doit suivre sa cible, on limite la recherche
                    robot.bonus_strategy = CaseRobot.STRAT_BONUS_TARGET
                else:
                    # recherche de bonus tous azimuts
                    robot.bonus_strategy = CaseRobot.STRAT_BONUS_ALL
        else:
            robot.bonus_strategy = None

    #-----> Winner
    def _update_winner_game_phasis(self, robot):
        """
        Met à jour la phase de jeu d'un Winner
        """
        phasis = None
        # données carto
        flatmatrice = self._lablevel.get_flat_matrice()
        diag = flatmatrice.get_diagonale_len()
        case_sortie = self._lablevel.get_case_sortie()
        # nombre total de coups unitaires joués :
        totalgamblecount = robot.totalgamblecount
        # nombre de coups décrivant la phase de début de partie :
        startgamblecount = math.floor(diag * 2 / 6)
        if totalgamblecount < startgamblecount:
            # phase de démarrage
            phasis = CommandManager.PHASIS_START
        else:
            dist_sortie = self._lablevel.get_path_length_between_cases(
                robot, case_sortie
            )
            if dist_sortie <= CommandManager.DIST_APPROACH:
                # phase finale d'approche de la cible
                phasis = CommandManager.PHASIS_FINAL
            elif dist_sortie <= 2 * CommandManager.DIST_APPROACH:
                # phase initiale d'approche de la cible
                phasis = CommandManager.PHASIS_APPROACH
            else:
                # phase standard
                phasis = CommandManager.PHASIS_IN_PROGRESS
        return phasis

    def _are_adversaires_in_advance(self, robot):
        """
        Recherche les winners et humains proches de gagner. Enregistre les
        résultats dans le gdSet du robot.
        """
        # données carto
        case_sortie = self._lablevel.get_case_sortie()
        # adversaires humains ou winners :
        gdSet = robot.get_current_gdSet()
        kill_all = gdSet.get_list_case("kill_all")
        advlist = [r for r in self.winner_human_alive if r != robot and r in kill_all]
        # mesures de proximité, enregistrement des adversaires en phases
        # d'approche et en phase finale et update de leur ppté game_phasis
        adv_in_approach = False
        adv_in_final = False
        approach_list = list()
        final_list = list()
        flatmatrice = self._lablevel.get_flat_matrice()
        mindist = flatmatrice.get_diagonale_len()
        complist = [r for r in self.winner_human_alive if r != robot]
        if complist != None and len(complist) > 0:
            for r in complist:
                drs = self._lablevel.get_path_length_between_cases(r, case_sortie)
                if drs <= CommandManager.DIST_APPROACH and r in advlist:
                    r.game_phasis = CommandManager.PHASIS_FINAL
                    final_list.append(r)
                elif drs <= 2 * CommandManager.DIST_APPROACH and r in advlist:
                    r.game_phasis = CommandManager.PHASIS_APPROACH
                    approach_list.append(r)
                else:
                    r.game_phasis = CommandManager.PHASIS_IN_PROGRESS
                mindist = min(mindist, drs)
        if len(final_list) > 0:
            adv_in_final = True
        if len(approach_list) > 0:
            adv_in_approach = True
        # position du robot
        drs_robot = self._lablevel.get_path_length_between_cases(robot, case_sortie)
        # qualification du retard :
        delta_bot_min = drs_robot - mindist
        if delta_bot_min < 0:
            retard = -1
        elif delta_bot_min == 0:
            retard = 0
        elif delta_bot_min < CommandManager.DIST_APPROACH:
            retard = 1
        elif delta_bot_min < 2 * CommandManager.DIST_APPROACH:
            retard = 2
        else:
            retard = 3
        # stratégie de recherche de bonus :
        strategy = None
        if robot.need_bonus:
            if retard in [-1, 0]:
                # le robot est en avance
                if robot.game_phasis in [
                    CommandManager.PHASIS_APPROACH,
                    CommandManager.PHASIS_FINAL,
                ]:
                    # il est presque arrivé, on suit la cible
                    strategy = CaseRobot.STRAT_BONUS_TARGET
                else:
                    # il peut chercher n'importe quel bonus
                    strategy = CaseRobot.STRAT_BONUS_ALL
            else:
                if adv_in_final or adv_in_approach:
                    # le robot doit suivre sa cible, on limite la recherche
                    strategy = CaseRobot.STRAT_BONUS_TARGET
                elif retard == 1:
                    # le robot n'a pas beaucoup de retard, les adversaires
                    # sont loin de la sortie
                    strategy = CaseRobot.STRAT_BONUS_ALL
                else:
                    # le robot est vraiment en retard
                    strategy = CaseRobot.STRAT_BONUS_TARGET
        robot.bonus_strategy = strategy
        # résultat
        result = {
            "adv_in_final": adv_in_final,
            "adv_in_approach": adv_in_approach,
            "final_list": final_list,
            "approach_list": approach_list,
            "retard": retard,
        }
        # enregistrement dans le gdSet
        gdSet = robot.get_current_gdSet()
        gdSet.set_adversaires_avance(result)

    #-----> Hunter
    def _find_bot_for_hunter(self, robot):
        """
        Définit la cible principale d'un bot chasseur
        De préférence un humain ou un winner.
        """
        huntbot = None
        # robots déja ciblés par d'autres chasseurs
        hlist = [b for b in self.hunter_alive if b != robot]
        targetedset = set()
        for h in hlist:
            maintarget = h.get_main_target()
            if maintarget != None:
                casetarget = maintarget.case
                if casetarget.type_case == LabHelper.CASE_ROBOT:
                    targetedset.add(casetarget)
        # s'ils le sont déja tous, on peut choisir un robot déja ciblé
        diffset = self.winner_human_alive.difference(targetedset)
        if len(self.winner_human_alive) > 0 and len(diffset) == 0:
            targetedset = set()
        # humains et winners :
        hwlist = [b for b in self.winner_human_alive if b not in targetedset]
        if len(hwlist) > 0:
            choicelist = list()
            for b in hwlist:
                df = b.get_danger_factor_for_bot(robot)
                dist = self._lablevel.get_distance_between_cases(robot, b)
                case_sortie = self._lablevel.get_case_sortie()
                dist_sortie = self._lablevel.get_distance_between_cases(case_sortie, b)
                choicelist.append(
                    {"bot": b, "df": df, "dist": dist, "dist_sortie": dist_sortie}
                )
                # trie :
                if len(choicelist) > 0:
                    choicelist.sort(key=itemgetter("dist_sortie", "dist"))
                    huntbot = choicelist[0]["bot"]
        # autres :
        if huntbot == None:
            olist = [
                b
                for b in self.alive_bots
                if b not in self.winner_human_hunter_alive and b not in targetedset
            ]
            if len(olist) == 0:
                # on prend en compte les bots déja ciblés
                olist = [
                    b
                    for b in self.alive_bots
                    if b not in self.winner_human_hunter_alive
                ]
            if len(olist) > 0:
                choicelist = list()
                for b in olist:
                    df = b.get_danger_factor_for_bot(robot)
                    dist = self._lablevel.get_distance_between_cases(robot, b)
                    choicelist.append({"bot": b, "df": df, "dist": dist})
                    # trie par proximité puis facteur de danger desc:
                    if len(choicelist) > 0:
                        choicelist.sort(key=itemgetter("dist"))
                        choicelist.sort(key=itemgetter("df"), reverse=True)
                        huntbot = choicelist[0]["bot"]
        return huntbot

    def _update_hunter_game_phasis(self, robot):
        """
        Met à jour la phase de jeu d'un Winner
        """
        # phase standard par défaut
        phasis = CommandManager.PHASIS_IN_PROGRESS
        # sortie du labyrinthe en cas de victoire :
        case_sortie = self._lablevel.get_case_sortie()
        maintarget = robot.get_main_target()
        if maintarget != None:
            if maintarget.case in self.alive_bots:
                if maintarget.case.game_phasis in [
                    CommandManager.PHASIS_APPROACH,
                    CommandManager.PHASIS_FINAL,
                ]:
                    # chasse forcée
                    phasis = CommandManager.PHASIS_HUNT
            elif maintarget.case == case_sortie:
                # le robot est le dernier joueur
                dist_sortie = self._lablevel.get_distance_between_cases(
                    robot, case_sortie
                )
                if dist_sortie <= CommandManager.DIST_APPROACH:
                    # phase finale d'approche de la sortie
                    phasis = CommandManager.PHASIS_FINAL
        return phasis

    #-----> B.3- Génération des données de choix de commande
    def _need_to_compute_gamble_datas(self, robot):
        """
        Indique si l'on doit recueillir le maximum de données
        """
        do_need = True
        # en fonction de la validité de la cible temporaires
        temptarget = robot.get_temp_target()
        temp_valide = temptarget != None and not temptarget.discarded
        if temp_valide:
            do_need = False
        # cas particulier des winners et hunters en phase finale d'approche
        # de la sortie : approche via le targetpath de maintarget
        if robot.behavior in [CaseRobot.BEHAVIOR_WINNER, CaseRobot.BEHAVIOR_HUNTER]:
            if robot.game_phasis == CommandManager.PHASIS_FINAL:
                do_need = False
        # retour :
        return do_need

    def _get_gamble_datas_for_bot(self, robot):
        """
        Collecte les données permettant de choisir le coup à jouer
        Complète le dictionnaire GambleDataSet gdSet : de mesures (nombre de
        types de cases, nombre de cases immédiatement libres, ...) dans
        les 4 directions :
        
        * gdSet[LabHelper.TOP] : liste d'objets GambleDataObject
        * gdSet[LabHelper.BOTTOM] : liste d'objets GambleDataObject
        * gdSet[LabHelper.LEFT] : liste d'objets GambleDataObject
        * gdSet[LabHelper.RIGHT] : liste d'objets GambleDataObject
        
        """
        # paramètres :
        gdSet = robot.get_current_gdSet()
        maindirs = gdSet.maintarget_directions
        # types de cases à mesurer
        dict_typescases = dict()
        # - dans tous les cas :
        dict_typescases[LabHelper.TYPE_CASES_LIBRES] = LabHelper.FAMILLE_CASES_LIBRES
        # - hors recherche de bonus tous azimuts :
        if robot.bonus_strategy != CaseRobot.STRAT_BONUS_ALL:
            dict_typescases[
                LabHelper.TYPE_CASES_DANGERS
            ] = LabHelper.FAMILLE_CASES_DANGERS
            dict_typescases[
                LabHelper.TYPE_CASES_ADVERSAIRES
            ] = LabHelper.FAMILLE_CASES_ADVERSAIRES
            dict_typescases[LabHelper.TYPE_CASES_BONUS] = LabHelper.FAMILLE_CASES_BONUS
            dict_typescases[LabHelper.TYPE_CASES_MURS] = LabHelper.FAMILLE_CASES_MURS
            dict_typescases[
                LabHelper.TYPE_CASES_NO_ACTION
            ] = LabHelper.FAMILLE_CASES_NO_ACTION
        # création des sous matrices de mesure :
        dict_submat, dictsample = self._get_scan_dict(robot)
        gdSet.largeurX = dictsample["largeurX"]
        gdSet.largeurY = dictsample["largeurY"]
        gdSet.profondeur_max = dictsample["profondeur_max"]
        max_sample_size = gdSet.profondeur_max
        # coords du robot :
        x_r, y_r = int(robot.x), int(robot.y)
        # Recueil de données :
        dict_datas = dict()  # structure intermédiaire
        dict_datas["gdObjects"] = dict()  # objets de mesure finaux
        for direct, (sm, axe, sens) in dict_submat.items():
            # 1- Objets de mesure :
            # - points de mesure :
            if axe == LabHelper.AXIS_X:
                pts = [(x_r + sens, case.y) for case in sm.get_column(0)]
            else:
                pts = [(case.x, y_r + sens) for case in sm.get_line(0)]
            # - dicts de mesure réutilisés
            reuseddict, sample_size = self._get_setsdict_for_axis_and_sens(
                sm, axe, sens
            )
            # - objets de mesure finaux
            for pt in pts:
                gdobj = GambleDataObject(pt[0], pt[1], direct, axe, sens)
                gdSet.add_GDObj(gdobj)
                dict_datas["gdObjects"][pt] = gdobj
            # 2- Collecte principale de données
            # - la direction pointe t'elle vers la cible principale ?
            is_main_direct = True
            if maindirs != None and direct not in maindirs:
                is_main_direct = False
            # - mesures sur l'ensemble des points de la direction :
            dict_datas[direct] = dict()
            # - Dénombrement par type de cases
            for typecase, list_tc in dict_typescases.items():
                dict_datas[direct][typecase] = self._count_typecase_on_set(
                    reuseddict, list_tc
                )
            # - impacts cumulés :
            dict_datas[direct]["impact_cumul"] = self._cumul_typecase_on_set(
                robot, reuseddict, LabHelper.FAMILLE_CASES_DANGERS
            )
            # - En fonction de la stratégie de recherche de bonus :
            if robot.bonus_strategy != None:
                # cumul pondéré des bonus par la distance au robot
                dict_datas[direct][
                    LabHelper.TYPE_CASES_BONUS
                ] = self._cumul_typecase_on_set(
                    robot, reuseddict, LabHelper.FAMILLE_CASES_BONUS
                )
            if robot.bonus_strategy != CaseRobot.STRAT_BONUS_ALL:
                # cases libres & delta de rapprochement / cible principale
                dict_datas[direct][LabHelper.NOMBRE_CASES_LIBRES] = dict()
                dict_datas[direct]["last_free_case"] = dict()
                dict_datas[direct][LabHelper.DELTA_MAIN] = dict()
                for pt in pts:
                    # Nombre de cases immédiatement libres & dernière case libre
                    nbl, last_free = self._compute_free_cases_from_point(
                        pt[0], pt[1], axe, sens
                    )
                    dict_datas[direct][LabHelper.NOMBRE_CASES_LIBRES][pt] = nbl
                    dict_datas[direct]["last_free_case"][pt] = last_free
                    # Delta de rapprochement : un éloignement négatif rapproche de la
                    # cible principale
                    gdo = dict_datas["gdObjects"][pt]
                    delta_main = self._compute_delta_main(robot, gdo)
                    dict_datas[direct][LabHelper.DELTA_MAIN][pt] = delta_main
            # 3- Maj objets de mesure
            defset = attset = None
            for gdobj in gdSet.get_GDObj_list_by_dir(direct):
                # - données déja calculées :
                pt = gdobj.x, gdobj.y
                gdobj.sample_size = sample_size
                gdobj.is_in_maindir = is_main_direct
                gdobj.count_cases_libres = dict_datas[direct][
                    LabHelper.TYPE_CASES_LIBRES
                ][pt]
                gdobj.count_cases_bonus = dict_datas[direct][
                    LabHelper.TYPE_CASES_BONUS
                ][pt]
                gdobj.impact_cumule = dict_datas[direct]["impact_cumul"][pt]
                if robot.bonus_strategy != CaseRobot.STRAT_BONUS_ALL:
                    gdobj.count_cases_dangers = dict_datas[direct][
                        LabHelper.TYPE_CASES_DANGERS
                    ][pt]
                    gdobj.count_cases_adversaires = dict_datas[direct][
                        LabHelper.TYPE_CASES_ADVERSAIRES
                    ][pt]
                    gdobj.count_cases_murs = dict_datas[direct][
                        LabHelper.TYPE_CASES_MURS
                    ][pt]
                    gdobj.count_cases_no_action = dict_datas[direct][
                        LabHelper.TYPE_CASES_NO_ACTION
                    ][pt]
                    gdobj.count_consecutive_libres = dict_datas[direct][
                        LabHelper.NOMBRE_CASES_LIBRES
                    ][pt]
                    gdobj.last_free_case = dict_datas[direct]["last_free_case"][pt]
                    gdobj.delta_main = dict_datas[direct][LabHelper.DELTA_MAIN][pt]
                # - données complémentaires :
                samplelistcases, first_impact = self._get_gdo_sample_list_case(gdobj)
                #   * liste des cases de l'échantillon
                gdobj.listcases = samplelistcases
                #   * premier impact
                gdobj.first_impact = first_impact
                #   * dist au robot
                gdobj.dist_to_bot = self._lablevel.get_distance_between_cases(
                    robot, gdobj
                )
                #   * facteur d'échantillonnage
                gdobj.fact_sample = gdobj.sample_size / max_sample_size
                #   * bots contre lesquels se défendre :
                caseset = set(samplelistcases)
                defset = set(gdSet.get_list_case("defense_all"))
                gdobj.count_bot_defense = len(caseset.intersection(defset))
                #   * bots à attaquer :
                attset = set(gdSet.get_list_case("attaque_all"))
                gdobj.count_bot_attaque = len(caseset.intersection(attset))
            # 4- Direction : valeurs cumulées pondérées par la distance au robot :
            cumuldict = dict()
            matset = sm.get_set_cases()
            # - dans tous les cas :
            bnsset = self._lablevel.get_typecase_set(LabHelper.FAMILLE_CASES_BONUS)
            cumuldict["bonus"] = self._compute_pondered_cumul(robot, matset, bnsset)
            freeset = self._lablevel.get_typecase_set(LabHelper.FAMILLE_CASES_LIBRES)
            cumuldict["libres"] = self._compute_pondered_cumul(robot, matset, freeset)
            # hors recherche de bonus tous azimuts
            if robot.bonus_strategy != CaseRobot.STRAT_BONUS_ALL:
                cumuldict["defense"] = self._compute_pondered_cumul(
                    robot, matset, defset
                )
                cumuldict["attaque"] = self._compute_pondered_cumul(
                    robot, matset, attset
                )
                dgrset = self._lablevel.get_typecase_set(
                    LabHelper.FAMILLE_CASES_DANGERS
                )
                cumuldict["dangers"] = self._compute_pondered_cumul(
                    robot, matset, dgrset
                )
            # enregistrement des cumuls sur la direction :
            gdSet.register_cumul_by_dir(direct, cumuldict)

    def _get_scan_dict(self, robot):
        """
        Retourne le dict contenant les sous matrices de mesures dans les 4 directions 
        ainsi qu'un dictionnaire décrivant les largeurs d'échantillons et la profondeur 
        max.
        """
        dict_submat = {
            LabHelper.TOP: (None, LabHelper.AXIS_Y, LabHelper.DIR_NEG),
            LabHelper.BOTTOM: (None, LabHelper.AXIS_Y, LabHelper.DIR_POS),
            LabHelper.LEFT: (None, LabHelper.AXIS_X, LabHelper.DIR_NEG),
            LabHelper.RIGHT: (None, LabHelper.AXIS_X, LabHelper.DIR_POS),
        }
        # 1- Echantillonage asymétrique (un axe peu avoir 2 profondeurs différentes)
        # largeur, profondeur des échantillons :
        l, p = self._get_sample_size_for_bot(robot)
        # sous matrices d'échantillonnage
        rect = dict()
        rect[LabHelper.TOP] = self._get_scan_submatrice_rectangle(
            robot, LabHelper.AXIS_Y, LabHelper.DIR_NEG, largeur=l, profondeur=p
        )
        rect[LabHelper.BOTTOM] = self._get_scan_submatrice_rectangle(
            robot, LabHelper.AXIS_Y, LabHelper.DIR_POS, largeur=l, profondeur=p
        )
        rect[LabHelper.LEFT] = self._get_scan_submatrice_rectangle(
            robot, LabHelper.AXIS_X, LabHelper.DIR_NEG, largeur=l, profondeur=p
        )
        rect[LabHelper.RIGHT] = self._get_scan_submatrice_rectangle(
            robot, LabHelper.AXIS_X, LabHelper.DIR_POS, largeur=l, profondeur=p
        )
        # 2- Création des sous matrices
        for direct, tupsm in dict_submat.items():
            sm = self._get_scan_submatrice(robot, tupsm[1], tupsm[2], rect[direct])
            dict_submat[direct] = (sm, tupsm[1], tupsm[2])
        # 3- Tailles d'échantillons
        largeurX = largeurY = l
        profondeur_max = 0
        for direct, dictrect in rect.items():
            if direct in [LabHelper.TOP, LabHelper.BOTTOM]:
                lY, pY = dictrect["ws"], dictrect["hs"]
                largeurY = min(largeurY, lY)
                profondeur_max = max(profondeur_max, pY)
            else:
                lX, pX = dictrect["hs"], dictrect["ws"]
                largeurX = min(largeurX, lX)
                profondeur_max = max(profondeur_max, pX)
        # Retour :
        return (
            dict_submat,
            {
                "largeurX": largeurX,
                "largeurY": largeurY,
                "profondeur_max": profondeur_max,
            },
        )

    def _get_scan_submatrice(self, robot, axe, sens, rectdict=None):
        """
        Retourne une sous matrice pour les mesures de densité sur l'axe, selon le sens
        """
        if rectdict == None:
            rectdict = self._get_scan_submatrice_rectangle(robot, axe, sens)
        xmin, ymin, ws, hs = (
            rectdict["xmin"],
            rectdict["ymin"],
            rectdict["ws"],
            rectdict["hs"],
        )
        flatmatrice = self._lablevel.get_flat_matrice()
        sm = flatmatrice.get_submatrice(xmin, ymin, ws, hs)
        return sm

    def _get_scan_submatrice_rectangle(
        self, robot, axe, sens, largeur=None, profondeur=None
    ):
        """
        Retourne le rectangle réel de la sous matrice
        """
        x_r = robot.x
        y_r = robot.y
        flatmatrice = self._lablevel.get_flat_matrice()
        w, h = flatmatrice.get_dimensions()
        if largeur == None:
            largeur = LabHelper.DENSITE_LARGEUR
        if profondeur == None:
            profondeur = LabHelper.DENSITE_PROFONDEUR
        # rectangle de mesure :
        if axe == LabHelper.AXIS_X:
            dx = profondeur
            dy = largeur // 2
            ymin = max(y_r - dy, 0)
            ymax = min(y_r + dy, h - 1)
            if sens == LabHelper.DIR_POS:
                xmin = x_r + 1
                xmax = min(x_r + dx, w - 1)
            else:
                xmin = max(x_r - dx, 0)
                xmax = x_r - 1
        else:
            dx = largeur // 2
            dy = profondeur
            xmin = max(x_r - dx, 0)
            xmax = min(x_r + dx, w - 1)
            if sens == LabHelper.DIR_POS:
                ymin = y_r + 1
                ymax = min(y_r + dy, h - 1)
            else:
                ymin = max(y_r - dy, 0)
                ymax = y_r - 1
        ws = xmax - xmin + 1
        hs = ymax - ymin + 1
        return {"xmin": xmin, "ymin": ymin, "ws": ws, "hs": hs}

    def _get_sample_size_for_bot(self, robot):
        """
        Retourne les dimensions (largeur, profondeur) d'échantillonnage en fonction des
        caractéristiques du robot
        """
        # par défaut :
        l, p = LabHelper.DENSITE_LARGEUR, LabHelper.DENSITE_PROFONDEUR
        # En fonction de l'intelligence :
        intelligence = robot.intelligence
        highQI = CaseRobot.get_feature_threshold("intelligence", "high")
        midQI = CaseRobot.get_feature_threshold("intelligence", "middle")
        if intelligence >= highQI:
            l, p = 7, 9
        elif intelligence >= midQI:
            l, p = 5, 7
        else:
            l, p = 3, 5
        return l, p

    def _count_typecase_on_set(self, dictset, listtypescases):
        """
        Prend pour entrée un dict ayant pour clefs des points de mesure et
        pour valeurs des sets de cases.
        Retourne un dict associant aux clefs le nombre de cases de type compris
        dans listtypescases
        """
        # set de référence :
        refset = self._lablevel.get_typecase_set(listtypescases)
        # mesures :
        dsm = dict()
        for pt, caseset in dictset.items():
            dsm[pt] = len(refset.intersection(caseset))
        return dsm

    def _cumul_typecase_on_set(self, robot, dictset, listtypescases):
        """
        Prend pour entrée un dict ayant pour clefs des points de mesure et
        pour valeurs des sets de cases.
        Retourne un dict associant aux clefsle cumul pondéré par la distance
        au robot des cases de type compris danslisttypescases.
        """
        # set de référence :
        refset = self._lablevel.get_typecase_set(listtypescases)
        # mesures :
        dsm = dict()
        for pt, caseset in dictset.items():
            dsm[pt] = self._compute_pondered_cumul(robot, caseset, refset)
        return dsm

    def _get_setsdict_for_axis_and_sens(self, matrice, axe, sens):
        """
        Retourne un dict ayant pour
        
        * clefs : un point de mesure (x, y)
        * valeur : un set de cases correspondant à une ligne ou une colonne
          de la matrice          
        """
        xmin, ymin = matrice.get_lefttop_point()
        w, h = matrice.get_dimensions()
        xmax, ymax = xmin + w - 1, ymin + h - 1
        x_r = y_r = None
        dsm = dict()
        if axe == LabHelper.AXIS_X:
            if sens == LabHelper.DIR_POS:
                x_r = xmin
            else:
                x_r = xmax
            w = xmax - xmin + 1
            h = 1
            ly = [y for y in range(ymin, ymax + 1)]
            dy = ymin
            for y in ly:
                line = matrice.get_line(y - dy)
                dsm[(x_r, y)] = set(line)
        else:
            if sens == LabHelper.DIR_POS:
                y_r = ymin
            else:
                y_r = ymax
            w = 1
            h = ymax - ymin + 1
            lx = [x for x in range(xmin, xmax + 1)]
            dx = xmin
            for x in lx:
                col = matrice.get_column(x - dx)
                dsm[(x, y_r)] = set(col)
        sample_size = max(w, h)
        return dsm, sample_size

    def _compute_free_cases_from_point(self, x, y, axe, sens, samplesize=None):
        """
        Calcule le nombre de cases libres consécutives à partir du point sur
        l'axe axe, dans le sens sens
        samplesize : limite le calcul à un nombre de cases donné
        """
        nbl = 0
        last_free = None
        flatmatrice = self._lablevel.get_flat_matrice()
        case = flatmatrice.get_case(x, y)
        listcases = None
        if axe == LabHelper.AXIS_X:
            listcases = flatmatrice.get_line(y)
            listcases = sorted(listcases, key=attrgetter(LabHelper.AXIS_X))
            if sens == LabHelper.DIR_POS:
                listcases = listcases[x:]
            else:
                listcases = listcases[: x + 1]
                listcases = sorted(
                    listcases, key=attrgetter(LabHelper.AXIS_X), reverse=True
                )
        else:
            listcases = flatmatrice.get_column(x)
            listcases = sorted(listcases, key=attrgetter(LabHelper.AXIS_Y))
            if sens == LabHelper.DIR_POS:
                listcases = listcases[y:]
            else:
                listcases = listcases[: y + 1]
                listcases = sorted(
                    listcases, key=attrgetter(LabHelper.AXIS_Y), reverse=True
                )
        if samplesize != None:
            n = len(listcases)
            s = min(samplesize, n)
            listcases = listcases[0:s]
        for case in listcases:
            if case.type_case in LabHelper.FAMILLE_CASES_LIBRES:
                nbl += 1
                last_free = case
            else:
                break
        return nbl, last_free

    def _compute_pondered_cumul(self, robot, mesuredset, refset):
        """
        Calcul le cumul pondéré par la distance au robot des cases comprises
        dans les deux sets passés en paramètres.
        refset : set de référence à croiser avec mesuredset
        """
        # interssection :
        interset = refset.intersection(mesuredset)
        # cumul pondéré par la distance :
        pondval = 0
        for c in interset:
            # plus la case est éloignée, moins elle a de poids
            d = self._lablevel.get_distance_between_cases(robot, c)
            val = 1
            if c.type_case == LabHelper.CASE_DANGER:
                val = math.sqrt(c.danger_impact)
            pondval += val / d
        return pondval

    def _compute_delta_main(self, robot, gdo):
        """
        Calcul le facteur d'éloignement par rapport à la cible principale
        d'un GambleDataObject
        """
        delta_main = 0
        gdSet = robot.get_current_gdSet()
        maindirs = gdSet.maintarget_directions
        mainTarget = robot.get_main_target()
        if mainTarget != None:
            # distance à la cible principale
            dist_bot_main = self._lablevel.get_distance_between_cases(robot, mainTarget)
            delta_orth = 0
            delta_dist = 0
            # delta de rapprochement sur l'axe orthogonal :
            orth_sign = -1
            axe = gdo.axe
            if axe == LabHelper.AXIS_X:
                if LabHelper.TOP in maindirs:
                    orth_sign = 1
                delta_orth = orth_sign * (gdo.y - robot.y)
            else:
                if LabHelper.LEFT in maindirs:
                    orth_sign = 1
                delta_orth = orth_sign * (gdo.x - robot.x)
            # delta en distance / cible principale :
            dist_gdo_main = self._lablevel.get_distance_between_cases(gdo, mainTarget)
            delta_dist = dist_gdo_main - dist_bot_main
            # somme :
            delta_main = delta_orth + delta_dist
        return delta_main

    def _get_gdo_sample_list_case(self, gdo):
        """
        Retourne la liste de cases échantillonnées pour gdo, ainsi que la
        valeur de first impact
        """
        flatmatrice = self._lablevel.get_flat_matrice()
        case = flatmatrice.get_case(gdo.x, gdo.y)
        fulllistcases = self._get_next_cases_in_dir(case, gdo.direct)
        sample_size = gdo.sample_size
        samplelistcases = fulllistcases[:sample_size]
        first_impact = 0
        if case.type_case in LabHelper.FAMILLE_CASES_DANGERS:
            first_impact = case.danger_impact
        return samplelistcases, first_impact

    #-----> B.4- Evaluation des données de choix de commande
    def _add_scores_to_gamble_datas(self, robot):
        """
        Note les options présentes dans le GambleDataSet gdSet pour les 4 directions
        """
        gdSet = robot.get_current_gdSet()
        # méthode de scoring propre au robot :
        gdo_score_method = dir_score_method = None
        if robot.bonus_strategy != None:
            dir_score_method = self._bonus_direction_score_method
            gdo_score_method = self._bonus_score_method
        else:
            dir_score_method = self._default_direction_score_method
            gdo_score_method = self._default_score_method
        # distance à la cible :
        flatmatrice = self._lablevel.get_flat_matrice()
        diag = flatmatrice.get_diagonale_len()
        mainTarget = robot.get_main_target()
        dist_ref = diag
        if mainTarget != None:
            dist_ref = self._lablevel.get_distance_between_cases(robot, mainTarget)
        # évaluations :
        for direct in LabHelper.LIST_DIRECTIONS:
            listegdo = gdSet.get_GDObj_list_by_dir(direct)
            # score de la direction :
            dir_score_method(robot, direct)
            # évaluations individuelles :
            for gdo in listegdo:
                # avance :
                if robot.bonus_strategy != CaseRobot.STRAT_BONUS_ALL:
                    self._compute_GDObj_avance(gdo, dist_ref)
                # score :
                gdo_score_method(robot, gdo)

    def _default_direction_score_method(self, robot, direct):
        """
        Calcul le score d'une direction à partir des valeurs cumulées pondérées
        par la distance au robot.
        """
        gdSet = robot.get_current_gdSet()
        # paramètres propres au robot :
        ambition = robot.ambition
        instinct_survie = robot.instinct_survie
        aggressivite = robot.aggressivite
        curiosite = robot.curiosite
        efficacite = robot.efficacite
        intelligence = robot.intelligence
        # valeurs cumulées dans la direction, pondérées par la distance au robot
        cumuldict = gdSet.get_cumul_by_dir(direct)
        val_defense = cumuldict["defense"]
        val_attaque = cumuldict["attaque"]
        val_dangers = cumuldict["dangers"]
        val_bonus = cumuldict["bonus"]
        val_libres = cumuldict["libres"]
        # scores par paramètres :
        score_mvt = efficacite * val_libres
        score_dangers = -instinct_survie * val_dangers
        score_defense = -instinct_survie * val_defense
        score_attaque = aggressivite * val_attaque
        score_ambition = ambition * (val_bonus + val_libres)
        score_curiosite = curiosite * (val_bonus + val_defense + val_attaque)
        score_intelligence = intelligence * (val_bonus + val_libres - val_defense)
        # score global
        score = (
            score_mvt
            + score_dangers
            + score_defense
            + score_attaque
            + score_ambition
            + score_curiosite
            + score_intelligence
        )
        # enregistrement dans le dict associé :
        cumuldict["score"] = score

    def _bonus_direction_score_method(self, robot, direct):
        """
        Calcul le score d'une direction à partir des valeurs cumulées pondérées
        par la distance au robot.
        """
        gdSet = robot.get_current_gdSet()
        # paramètres propres au robot :
        ambition = robot.ambition
        efficacite = robot.efficacite
        intelligence = robot.intelligence
        # valeurs cumulées dans la direction, pondérées par la distance au robot
        cumuldict = gdSet.get_cumul_by_dir(direct)
        val_bonus = cumuldict["bonus"]
        val_libres = cumuldict["libres"]
        # scores par paramètres :
        score_mvt = efficacite * val_libres
        score_bonus = (ambition + efficacite + intelligence) * val_bonus
        # score global
        score = score_mvt + score_bonus ** 2
        # enregistrement dans le dict associé :
        cumuldict["score"] = score

    def _compute_GDObj_avance(self, gdo, dist_ref):
        """
        Calcul de l'avance associée à un objet GambleDataObject.
        """
        # paramètres de la case évaluée
        c_libres = gdo.count_cases_libres
        c_no_action = gdo.count_cases_no_action
        nb_libre = gdo.count_consecutive_libres
        delta_main = gdo.delta_main
        # calcul de l'avance associée
        ouverture = nb_libre + c_libres - c_no_action
        eloignement = delta_main
        avance = ouverture - eloignement
        # enregistrement
        gdo.avance = avance

    def _default_score_method(self, robot, gdo):
        """
        Calcul de score par défaut d'un objet GambleDataObject.
        """
        # paramètres propres au robot :
        ambition = robot.ambition
        instinct_survie = robot.instinct_survie
        aggressivite = robot.aggressivite
        curiosite = robot.curiosite
        efficacite = robot.efficacite
        intelligence = robot.intelligence
        # paramètres de la case évaluée
        c_adversaires = gdo.count_cases_adversaires
        c_defense = gdo.count_bot_defense
        c_attaque = gdo.count_bot_attaque
        c_bonus = gdo.count_cases_bonus
        c_libres = gdo.count_cases_libres
        first_impact = gdo.first_impact
        impact_cumule = gdo.impact_cumule
        avance = gdo.avance
        # scores par paramètres :
        score_mvt = efficacite * avance
        score_dangers = -instinct_survie * (first_impact + math.sqrt(impact_cumule))
        score_defense = -instinct_survie * c_defense
        score_attaque = aggressivite * c_attaque
        score_ambition = ambition * (avance + c_bonus)
        score_curiosite = curiosite * (c_bonus + c_adversaires)
        score_intelligence = intelligence * (c_bonus + c_libres - c_defense)
        # score global
        score = (
            score_mvt
            + score_dangers
            + score_defense
            + score_attaque
            + score_ambition
            + score_curiosite
            + score_intelligence
        )
        # enregistrements :
        gdo.score = math.ceil(score * 100) / 100

    def _bonus_score_method(self, robot, gdo):
        """
        Calcul de score privilégiant les bonus.
        """
        # paramètres propres au robot :
        ambition = robot.ambition
        instinct_survie = robot.instinct_survie
        efficacite = robot.efficacite
        intelligence = robot.intelligence
        # paramètres de la case évaluée
        c_bonus = gdo.count_cases_bonus
        first_impact = gdo.first_impact
        impact_cumule = gdo.impact_cumule
        avance = gdo.avance
        # scores limités à certains paramètres :
        score_dangers = -instinct_survie * (math.sqrt(first_impact) + impact_cumule)
        score_bonus = (ambition + efficacite + intelligence) * (1 + c_bonus) ** 2
        # score global :
        score = score_bonus + score_dangers
        # en fonction de la stratégie de recherche de bonus
        if robot.bonus_strategy != CaseRobot.STRAT_BONUS_ALL:
            score_mvt = efficacite * avance
            score += score_mvt
        # enregistrements :
        gdo.score = math.ceil(score * 100) / 100

    #-----> B.5- Sélection de cible, recherche de chemins
    #-----> B.5.1- Cible temporaire
    def _select_new_temp_target(self, robot):
        """
        Analyse les données, détermine la cible temporaire et le chemin pour y parvenir.
        """
        gdSet = robot.get_current_gdSet()
        flatmatrice = self._lablevel.get_flat_matrice()
        # Séparation des options en fonction des directions
        # - prioritaires:
        bestdirs = self._select_best_directions(robot)
        priorgdolist = list()
        for direct in bestdirs:
            priorgdolist += gdSet.get_GDObj_list_by_dir(direct)
        # - autres
        otherdirs = [d for d in LabHelper.LIST_DIRECTIONS if d not in bestdirs]
        othergdolist = list()
        for direct in otherdirs:
            othergdolist += gdSet.get_GDObj_list_by_dir(direct)
        # Clefs de trie :
        descsortkey = attrgetter("score")  # par défaut
        ascsortkey = None
        if robot.behavior == CaseRobot.BEHAVIOR_BUILDER:
            ascsortkey = attrgetter("count_cases_murs")
        elif robot.behavior == CaseRobot.BEHAVIOR_SAPPER:
            ascsortkey = attrgetter("count_cases_dangers")
        else:
            midSUR = CaseRobot.get_feature_threshold("instinct_survie", "middle")
            if robot.need_bonus:
                descsortkey = attrgetter("score", "count_cases_bonus")
            elif robot.instinct_survie > midSUR:
                ascsortkey = attrgetter("count_bot_defense", "count_cases_dangers")
        # Recherche de la meilleure option :
        bestopt, bestopt_dir, finaleopt = None, None, None
        # 1- Recherche dans les directions principales :
        if priorgdolist != None:
            # trie des options
            if ascsortkey:
                priorgdolist.sort(key=ascsortkey, reverse=False)
            if descsortkey:
                priorgdolist.sort(key=descsortkey, reverse=True)
            for gdo in priorgdolist:
                selected = self._select_GambleDataObject(robot, gdo)
                if selected:
                    bestopt_dir = gdo
                    break
        # 2- Recherche dans les autres directions :
        if bestopt_dir == None:
            if ascsortkey:
                othergdolist.sort(key=ascsortkey, reverse=False)
            if descsortkey:
                othergdolist.sort(key=descsortkey, reverse=True)
            for gdo in othergdolist:
                selected = self._select_GambleDataObject(robot, gdo)
                if selected:
                    bestopt = gdo
                    break
        # 3- Choix de l'option finale :
        if bestopt_dir != None:
            finaleopt = bestopt_dir
        elif bestopt != None:
            finaleopt = bestopt
        # Affectation de la nouvelle cible temporaire :
        if finaleopt != None:
            # point d'entrée de la cible
            target_case = flatmatrice.get_case(finaleopt.x, finaleopt.y)
            newtarget = TargetObject(
                TargetObject.TARGET_TEMP,
                target_case,
                finaleopt.direct,
                finaleopt.axe,
                finaleopt.sens,
                finaleopt.score,
            )
            newtarget.targetpath = finaleopt.targetpath
            newtarget.pathcost = finaleopt.pathcost
            # dernière case libre
            last_free_case = finaleopt.last_free_case
            newtarget.last_free_case = last_free_case
            # liste des cases associées
            newtarget.listcases = finaleopt.listcases
            # affectation
            robot.set_temp_target(newtarget)
            gdSet.finaleoption = finaleopt

    def _select_best_directions(self, robot):
        """
        Sélectionne les meilleures directions de recherche de cible.
        """
        gdSet = robot.get_current_gdSet()
        listdirect = list()
        # directions vers la cible principale
        maindirs = gdSet.maintarget_directions
        choose_main = True
        # Cas particulier : recherche de bonus tous azimuts ou absence de
        # cible principale
        if robot.bonus_strategy == CaseRobot.STRAT_BONUS_ALL or maindirs == None:
            choose_main = False
        # cas standard : directions principales
        if choose_main:
            listdirect += maindirs
        else:
            # Sélection via le score des directions
            # Calcul du score de ref (50% du max)
            refscore = maxscore = 0
            for direct in LabHelper.LIST_DIRECTIONS:
                cumuldict = gdSet.get_cumul_by_dir(direct)
                score = cumuldict["score"]
                maxscore = max(score, maxscore)
            refscore = maxscore * 0.5
            # Sélection des directions les plus performantes
            for direct in LabHelper.LIST_DIRECTIONS:
                cumuldict = gdSet.get_cumul_by_dir(direct)
                score = cumuldict["score"]
                if direct not in listdirect and score >= refscore:
                    listdirect.append(direct)
        return listdirect

    def _select_GambleDataObject(self, robot, gdo):
        """
        Peut on retenir gdo comme future cible temporaire?
        """
        selected = False
        # Evaluation de l'accessibilité
        flatmatrice = self._lablevel.get_flat_matrice()
        case = flatmatrice.get_case(gdo.x, gdo.y)
        if case.type_case not in LabHelper.FAMILLE_NO_TARGET:
            # Accessibilité ?
            gdo.targetpath = self._search_TargetPath(robot, gdo)[0]
            if gdo.targetpath != None:
                gdo.pathcost = gdo.targetpath.cost
                # cible accessible on peut la sélectionner
                selected = True
        # retour :
        return selected

    #-----> B.5.2- Interface de recherche de chemins
    def _search_TargetPath(self, robot, baseObj, ecomode=True):
        """
        Recherche le meilleur chemin allant du robot à la case associée au baseObj
        
        * baseObj : un objet GambleDataObject, TargetObject ou Case
        * ecomode : limite la charge de calcul en limitant la recherche de
          combinaisons de lancers de grenade aux jets directs
          
        """
        # enregistrement temporaire des dangers bloquants
        self._pathblocklist = list()
        # en fonction de l'objet passé en paramètre
        case = self._get_case_for_baseObj(baseObj)
        if case == None:
            return None, self._pathblocklist.copy()
        # coordonnées :
        xr, yr = robot.x, robot.y
        xt, yt = case.x, case.y
        # cache ?
        key = (xr, yr, xt, yt, ecomode)
        gdSet = robot.get_current_gdSet()
        cachedresult = gdSet.get_TargetPath_in_cache(key)
        if cachedresult != "not in cache":
            return cachedresult
        # enregistrement temporaire des dangers bloquants
        self._pathblocklist = list()
        # Recherche : en fonction de la longueur du chemin
        finalpath = None
        pathlength = self._lablevel.get_path_length_between_cases(robot, case)
        if pathlength <= 4:
            # recherche exhaustive :
            finalpath = self._search_short_TargetPath(robot, case, ecomode=ecomode)
        else:
            # recherche optimisée
            finalpath = self._search_long_TargetPath(robot, case, ecomode=ecomode)
        # mise en cache :
        result = finalpath, self._pathblocklist.copy()
        gdSet.cache_TargetPath(key, result)
        # retour
        return result

    def _get_case_for_baseObj(self, baseObj):
        """
        Recherche la case associée à l'objet
        baseObj : un objet GambleDataObject, TargetObject ou Case
        """
        flatmatrice = self._lablevel.get_flat_matrice()
        # en fonction de l'objet passé en paramètre
        case = None
        if type(baseObj) is GambleDataObject:
            case = flatmatrice.get_case(baseObj.x, baseObj.y)
        elif type(baseObj) is TargetObject:
            case = baseObj.case
        elif isinstance(baseObj, Case):
            case = baseObj
        return case

    def _update_or_discard_TargetPath(self, robot, tp):
        """
        Retourne un boolean indiquant si le chemin est encore valable et le
        chemin mis à jour ou None
        Si c'est le cas, les étape du chemin sont mises à jour.
        """
        if tp == None:
            return True, None
        dodiscard = False
        newpath = None
        flatmatrice = self._lablevel.get_flat_matrice()
        oldsteplist = tp.get_steps_list()
        # coûts de parcours
        oldcost = 0
        newcost = 0
        oldsteplist.reverse()
        botinpath = False
        newtpslist = list()
        for oldstep in oldsteplist:
            oldcase = oldstep.case
            newcase = flatmatrice.get_case(oldstep.x, oldstep.y)
            newtps = TargetPathStep(newcase)
            newtpslist.append(newtps)
            if newcase == robot:
                botinpath = True
                break
            oldcost += self._compute_case_cost(robot, oldcase)
            newcost += self._compute_case_cost(robot, newcase)
        oldsteplist.reverse()
        if newcost > oldcost or not botinpath:
            # le coût de parcours augmente ou le bot est sorti du chemin
            dodiscard = True
        else:
            # cible conservée, mise à jour du parcours:
            newtpslist.reverse()
            newpath = TargetPath(steplist=newtpslist)
            newpath.cost = newcost
        return dodiscard, newpath

    #-----> B.5.3- Recherche exhaustive de chemins
    def _search_short_TargetPath(self, robot, case, ecomode=True):
        """
        Recherche exhaustive du meilleur chemin allant du robot à la case
        """
        # coordonnées :
        xr, yr = robot.x, robot.y
        xt, yt = case.x, case.y
        # cache ?
        key = (xr, yr, xt, yt, ecomode)
        gdSet = robot.get_current_gdSet()
        cachedresult = gdSet.get_TargetPath_in_cache(key)
        if cachedresult != "not in cache":
            cachedpath = cachedresult[0]
            return cachedpath
        flatmatrice = self._lablevel.get_flat_matrice()
        # sous matrice :
        xmin = min(xr, xt)
        ymin = min(yr, yt)
        w = int(math.fabs(xr - xt) + 1)
        h = int(math.fabs(yr - yt) + 1)
        sm = flatmatrice.get_submatrice(xmin, ymin, w, h)
        # directions de parcours :
        maindir = self._get_dir_for_case(robot, case)
        if maindir in [LabHelper.LEFT, LabHelper.RIGHT]:
            dirs = [maindir, LabHelper.TOP, LabHelper.BOTTOM]
        else:
            dirs = [maindir, LabHelper.LEFT, LabHelper.RIGHT]
        # Arbre de parcours :
        pathtree = {"case": robot, "parent": None, "pathlist": list()}
        self._xlook_for_steps(robot, pathtree, sm, dirs, ecomode=ecomode)
        # TargetPath associés :
        listtargetpath = list()
        # cas particulier des simulations, le robot n'est pas forcément la
        # première case
        firstcase = flatmatrice.get_case(robot.x, robot.y)
        inittgtpath = TargetPath([TargetPathStep(firstcase)])
        listtargetpath = self._xcreate_TargetPaths(
            listtargetpath, pathtree, inittgtpath
        )
        # sélection des chemins complets :
        completelist = list()
        for tp in listtargetpath:
            lasttps = tp.get_last_step()
            if lasttps.case == case:
                completelist.append(tp)
        # évaluations :
        finalpath = None
        if len(completelist) > 0:
            for tp in completelist:
                for tps in tp.get_steps_list():
                    tp.cost += self._compute_case_cost(robot, tps.case)
                tp.cost -= 2  # robot compté pour 2
            # trie par coût croissant :
            completelist.sort(key=attrgetter("cost"))
            finalpath = completelist[0]
        # mise en cache :
        result = finalpath, self._pathblocklist.copy()
        gdSet.cache_TargetPath(key, result)
        # retour
        return finalpath

    def _compute_case_cost(self, robot, case):
        """
        Calcul du coût de parcours d'une case
        """
        cost = 0
        tc = case.type_case
        if tc in LabHelper.FAMILLE_CASES_BONUS:
            cost -= int(robot.need_bonus)
        elif tc in LabHelper.FAMILLE_CASES_LIBRES:
            cost += 1
        elif tc == LabHelper.CASE_DANGER:
            cost += case.danger_impact + 1
        else:
            cost += 2
        return cost

    def _xcreate_TargetPaths(self, listtargetpath, pathtree, tgtpath):
        """
        Génère les objets TargetPath à partir de l'arbre de parcours
        """
        pathlist = pathtree["pathlist"]
        if pathlist != None:
            for ptree in pathlist:
                case = ptree["case"]
                tps = TargetPathStep(case)
                tp = tgtpath.copy()
                tp.add_pathstep(tps)
                listtargetpath.append(tp)
                # récursivité :
                self._xcreate_TargetPaths(listtargetpath, ptree, tp)
        return listtargetpath

    def _xlook_for_steps(
        self, robot, pathtree, submat, dirs, xcoords=list(), ecomode=True
    ):
        """
        Recherche récursive de l'arbre de parcours
        """
        case = pathtree["case"]
        parent = pathtree["parent"]
        newxcoords = [coord for coord in xcoords]
        if parent != None:
            xp, yp = int(parent.x), int(parent.y)
            newxcoords.append((xp, yp))
        x, y = case.x, case.y
        for direct in dirs:
            xs, ys = None, None
            if direct == LabHelper.TOP:
                xs, ys = x, int(y - 1)
            elif direct == LabHelper.BOTTOM:
                xs, ys = x, int(y + 1)
            elif direct == LabHelper.LEFT:
                xs, ys = int(x - 1), y
            elif direct == LabHelper.RIGHT:
                xs, ys = int(x + 1), y
            childcase = submat.get_case(xs, ys)
            if childcase != None and (xs, ys) not in newxcoords:
                if self._valide_path_step(childcase, robot, ecomode=ecomode):
                    childpathtree = {
                        "case": childcase,
                        "parent": case,
                        "pathlist": list(),
                    }
                    pathtree["pathlist"].append(childpathtree)
                    # récursivité :
                    self._xlook_for_steps(
                        robot, childpathtree, submat, dirs, xcoords=newxcoords
                    )

    def _valide_path_step(self, case, robot, ecomode=True):
        """
        Indique si la case peut constituer une étape de chemin
        """
        valide = False
        gdSet = robot.get_current_gdSet()
        if case.type_case in LabHelper.FAMILLE_TARGET:
            valide = True
        elif case.type_case == LabHelper.CASE_ROBOT:
            kill_all = gdSet.get_list_case("kill_all")
            if case in kill_all:
                d = self._lablevel.get_distance_between_cases(robot, case)
                if d == 1:
                    # action kill possible
                    valide = True
                elif robot.has_grenade:
                    # recherche de combinaisons de lancers de grenade
                    # (directes par défaut - ecomode=True)
                    params = self._get_params_for_grenade(
                        robot, case, directonly=ecomode
                    )
                    if params != None:
                        valide = True
        elif case.type_case == LabHelper.CASE_DANGER:
            if robot.has_grenade:
                if case.danger_impact == 1:
                    valide = True
                else:
                    # en fonction de la distance :
                    d = self._lablevel.get_distance_between_cases(robot, case)
                    dgr_radius = case.get_danger_radius()
                    if dgr_radius >= d:
                        # optimisation : on écarte l'étape, même si le rayon réel
                        # peut être inférieur (cas des impacts = 5, 13, 17, en
                        # fonction de l'angle du vecteur robot / danger)
                        valide = False
                    else:
                        # recherche de combinaisons de lancers de grenade
                        # (directes par défaut - ecomode=True)
                        params = self._get_params_for_grenade(
                            robot, case, directonly=ecomode
                        )
                        if params != None:
                            valide = True
        if not valide:
            # enregistrement temporaire du blocage
            if case.type_case == LabHelper.CASE_DANGER:
                self._pathblocklist.append(case)
        return valide

    #-----> B.5.4- Recherche optimisée sur de longues distances
    def _search_long_TargetPath(
        self, robot, case, ecomode=True, subtargetpath=None, excludedpoints=None
    ):
        """
        Version optimisée de _search_TargetPath pour des parcours longs.
        Résultat non assuré : le déplacement du robot le long des sous chemins
        est simulé. Pour l'un de ces sous chemins, l'étape de validation peut
        considérer que le robot est trop près d'un danger alors qu'il a la
        possibilité de terraformer bien en amont.
        """
        targetpath = None
        valide = False
        # mémorisation des coords initiales du robot :
        xref, yref = int(robot.x), int(robot.y)
        # liste des TargetPath à concaténer, points à exclure des échantillons
        if subtargetpath == None:
            # démarrage du process de recherche
            subtargetpath = list()
            excludedpoints = list()
        # case constituant le départ du nouveau sous chemin
        if len(subtargetpath) == 0:
            prevcase = robot
        else:
            # reprise du process de recherche après un échec
            lastsubtp = subtargetpath[-1]
            lasttps = lastsubtp.get_last_step()
            prevcase = lasttps.case
        # recherche...
        while prevcase != None and prevcase != case:
            valide = False
            # meilleur sous chemin trouvé par recherche rapide
            sub_tp, samplecount = self._fast_search_next_step(
                robot, case, ecomode=ecomode, excludedpoints=excludedpoints
            )
            if sub_tp != None:
                laststep = sub_tp.get_last_step()
                if laststep != None:
                    valide = True
                    # incrément
                    prevcase = laststep.case
                    robot.x, robot.y = prevcase.x, prevcase.y
                    subtargetpath.append(sub_tp)
            if not valide:
                # Retour en arrière ?
                if len(subtargetpath) > 0 and samplecount > 0:
                    # d'autres échantillons existent :
                    # - on élimine le sous chemin menant à un échec :
                    delsubtp = subtargetpath.pop()
                    # - on ajoute les coordonnées de l'échantillon à exclure
                    excludedtps = delsubtp.get_last_step()
                    excludedcase = excludedtps.case
                    excludedpoints.append((excludedcase.x, excludedcase.y))
                    # - rétablissement des coordonnées du robot:
                    robot.x, robot.y = xref, yref
                    # - on relance la recherche
                    return self._search_long_TargetPath(
                        robot,
                        case,
                        ecomode=ecomode,
                        subtargetpath=subtargetpath,
                        excludedpoints=excludedpoints,
                    )
                else:
                    # recherche définitivement en échec
                    break
        # Concaténation des sous parcours:
        if valide:
            targetpath = TargetPath()
            prevcoords = []
            defstepslist = list()
            for subtp in subtargetpath:
                substeps = subtp.get_steps_list()
                subcoords = subtp.get_coords_list()
                # élimination des redondances
                if len(prevcoords) > 0:
                    prevcoords.reverse()
                    i = -1
                    if prevcoords[0] == subcoords[0]:
                        lp = len(prevcoords)
                        ls = len(subcoords)
                        n = min(lp, ls)
                        i = 0
                        for k in range(1, n):
                            if prevcoords[k] == subcoords[k]:
                                i += 1
                            else:
                                break
                    if i >= 0:
                        # nettoyage du nouveau sous parcours
                        substeps = substeps[i + 1 :]
                        subcoords = subcoords[i + 1 :]
                    if i >= 1:
                        # nettoyage de la liste finale d'étape
                        defstepslist.reverse()
                        defstepslist = defstepslist[i:]
                        defstepslist.reverse()
                # alimentation de la liste finale
                for tps in substeps:
                    defstepslist.append(tps)
                # incrément :
                prevcoords = subcoords
            # constitution du parcours final :
            targetpath = TargetPath(steplist=defstepslist)
            for tps in defstepslist:
                targetpath.cost += self._compute_case_cost(robot, tps.case)
            targetpath.cost -= 2  # robot compté pour 2
        # rétablissement des coordonnées du robot:
        robot.x, robot.y = xref, yref
        # retour
        return targetpath

    def _fast_search_next_step(self, robot, case, ecomode=True, excludedpoints=list()):
        """
        Recherche rapide d'un chemin entre la position actuelle du robot et la
        case.
        Retourne :
        
        * un TargetPath ou None
        * le nombre d'échantillons testés, 0 par défaut (si recherche de path
          déléguée à _search_short_TargetPath)
        
        """
        targetpath = None
        samplecount = 0
        # constantes d'optimisation
        ptbyline = 3
        dlength = 4
        # en fonction de la distance restant à parcourir :
        pathlength = self._lablevel.get_path_length_between_cases(robot, case)
        if pathlength <= 4:
            targetpath = self._search_short_TargetPath(robot, case, ecomode=ecomode)
        else:
            xr, yr = robot.x, robot.y
            xt, yt = case.x, case.y
            # recherche d'échantillons
            flatmatrice = self._lablevel.get_flat_matrice()
            vector = self._lablevel.get_vector_for_cases(robot, case)
            samples = {"x": None, "y": None, "xy": None}
            if vector[0] != 0:
                # échantillons sur x :
                sens = 1
                if vector[0] < 0:
                    sens = -1
                samples["x"] = self._get_path_samples_on_axis(
                    robot, "x", sens, ptbyline, dlength, excludedpoints=excludedpoints
                )
            if vector[1] != 0:
                # échantillons sur y :
                sens = 1
                if vector[1] < 0:
                    sens = -1
                samples["y"] = self._get_path_samples_on_axis(
                    robot, "y", sens, ptbyline, dlength, excludedpoints=excludedpoints
                )
            if vector[0] * vector[1] != 0:
                # échantillons sur xy :
                # sous matrice :
                xmin = min(xr, xt)
                ymin = min(yr, yt)
                w = int(math.fabs(xr - xt) + 1)
                h = int(math.fabs(yr - yt) + 1)
                sm = flatmatrice.get_submatrice(xmin, ymin, w, h, strictmode=False)
                smcases = sm.get_list_cases()
                samples["xy"] = list()
                for c in smcases:
                    if not (c.x, c.y) in excludedpoints:
                        d = self._lablevel.get_path_length_between_cases(robot, c)
                        if d == dlength:
                            cost = self._compute_case_cost(robot, c)
                            samples["xy"].append({"case": c, "cost": cost})
            # sélection des meilleurs échantillons pour x, y et xy
            bestsamples = list()
            for linesearch in samples.keys():
                linesamples = samples[linesearch]
                if linesamples != None and len(linesamples) > 0:
                    linesamples.sort(key=itemgetter("cost"))
                    bestforline = linesamples[0]
                    bestsamples.append(bestforline)
                    samplecount += len(linesamples)
            # calcul des targetpath pour les meilleurs échantillons :
            finalsamples = list()
            dref = self._lablevel.get_path_length_between_cases(robot, case)
            for sampledict in bestsamples:
                c = sampledict["case"]
                dc = self._lablevel.get_path_length_between_cases(c, case)
                if dc < dref:
                    # évite de diverger de la cible :
                    tp = self._search_short_TargetPath(robot, c, ecomode=ecomode)
                    if tp != None:
                        sampledict["tp"] = tp
                        # cost / 2 limite l'attraction des bonus
                        sampledict["finalcost"] = tp.cost / 2 + dc
                        finalsamples.append(sampledict)
            # trie des chemins évalués
            if len(finalsamples) > 0:
                finalsamples.sort(key=itemgetter("finalcost"))
                targetpath = finalsamples[0]["tp"]
            else:
                # on est suffisament proche de la cible :
                targetpath = self._search_short_TargetPath(robot, case, ecomode=ecomode)
        # retour :
        return targetpath, samplecount

    def _get_path_samples_on_axis(
        self, robot, axis, sens, count, delta, excludedpoints=list()
    ):
        """
        Collecte des échantillons pour la recherche rapide de path
        sur l'axe "x" ou "y"
        Retourne une liste de dicts {"case":, "cost";}
        """
        xr, yr = robot.x, robot.y
        flatmatrice = self._lablevel.get_flat_matrice()
        coords = list()
        samples = list()
        # recherche de points dans la zone jouable
        if axis == "x":
            dy = count // 2
            yrange = range(yr - dy, yr + dy + 1)
            for y in yrange:
                i = 0
                done = False
                while not done:
                    dx = sens * (delta - i)
                    if dx == 0:
                        break
                    x = xr + dx
                    c = flatmatrice.get_case(x, y)
                    if (
                        c == None
                        or c not in self.play_set
                        or (c.x, c.y) in excludedpoints
                    ):
                        i += 1
                    else:
                        coords.append((x, y))
                        done = True
        else:
            dx = count // 2
            xrange = range(xr - dx, xr + dx + 1)
            for x in xrange:
                i = 0
                done = False
                while not done:
                    dy = sens * (delta - i)
                    if dy == 0:
                        break
                    y = yr + dy
                    c = flatmatrice.get_case(x, y)
                    if (
                        c == None
                        or c not in self.play_set
                        or (c.x, c.y) in excludedpoints
                    ):
                        i += 1
                    else:
                        coords.append((x, y))
                        done = True
        # constitution de l'échantillon
        for (x, y) in coords:
            c = flatmatrice.get_case(x, y)
            if c != None:
                cost = self._compute_case_cost(robot, c)
                samples.append({"case": c, "cost": cost})
        return samples

    #-----> B.5.5- Approche finale de la cible principale
    def _search_final_TargetPath(self, robot):
        """
        Recherche le chemin final vers la cible principale.
        """
        result = False
        mainTarget = robot.get_main_target()
        if mainTarget != None:
            robot.set_temp_target(None)
            targetpath = self._search_TargetPath(robot, mainTarget)[0]
            if targetpath != None:
                mainTarget.targetpath = targetpath
                mainTarget.pathcost = targetpath.cost
                result = True
            else:
                mainTarget.targetpath = None
        return result

    #-----> B.6- Qualification des options adjacentes
    def _evaluate_adjacent_cases(self, robot, by_gdSet):
        """
        Retourne les cases adjacentes triées par pertinence
        """
        gdSet = robot.get_current_gdSet()
        flatmatrice = self._lablevel.get_flat_matrice()
        # Options adjacentes :
        optionsadj = dict()
        if by_gdSet:
            # via les données collectées
            gdolist = gdSet.get_full_GDObj_list()
            gdolist.sort(key=attrgetter("dist_to_bot"))
            for opt in gdolist:
                if opt.dist_to_bot == 1:
                    optionsadj[opt.direct] = opt
                else:
                    break
        else:
            # on crée des objets de mesures temporaires
            adjdict = flatmatrice.get_cases_adjacentes(robot.x, robot.y)
            for direct, case in adjdict.items():
                if case != None:
                    gdobj = GambleDataObject(case.x, case.y, direct, None, None)
                    optionsadj[direct] = gdobj
        # enregistrement des cases adjacentes :
        adjlist = list()
        for direct in optionsadj:
            gdo = optionsadj[direct]
            cadj = flatmatrice.get_case(gdo.x, gdo.y)
            adjlist.append(cadj)
        gdSet.register_list_case("all_adj", adjlist)
        # en fonction de la cible temporaire :
        firstchoice = list()
        firstlist = list()
        tempTarget = robot.get_temp_target()
        mainTarget = robot.get_main_target()
        if tempTarget != None:
            tpslist = tempTarget.targetpath.get_steps_list()
            nextcase = tpslist[1].case
            firstlist.append(nextcase)
        elif mainTarget != None:
            if mainTarget.targetpath != None:
                tpslist = mainTarget.targetpath.get_steps_list()
                nextcase = tpslist[1].case
                firstlist.append(nextcase)
            else:
                vecteur = self._lablevel.get_vector_for_cases(robot, mainTarget)
                if vecteur[0] >= 0:
                    firstchoice.append(optionsadj[LabHelper.RIGHT])
                if vecteur[0] <= 0:
                    firstchoice.append(optionsadj[LabHelper.LEFT])
                if vecteur[1] >= 0:
                    firstchoice.append(optionsadj[LabHelper.BOTTOM])
                if vecteur[1] <= 0:
                    firstchoice.append(optionsadj[LabHelper.TOP])
                for gdo in firstchoice:
                    case = flatmatrice.get_case(gdo.x, gdo.y)
                    firstlist.append(case)
        gdSet.register_list_case("first_adj", firstlist)
        # bonus adjacents :
        listbonus = gdSet.get_list_case("bonus")
        if len(listbonus) > 0:
            bonusadj = list()
            listbonus.sort(
                key=lambda case: self._lablevel.get_distance_between_cases(case, robot)
            )
            for case in listbonus:
                if self._lablevel.get_distance_between_cases(case, robot) == 1:
                    bonusadj.append(case)
                else:
                    break
            if len(bonusadj) > 0:
                gdSet.register_list_case("bonus_adj", bonusadj)
        # options adjacentes ignorées :
        secondchoice = list()
        for direct, gdo in optionsadj.items():
            if gdo not in firstchoice:
                secondchoice.append(gdo)
        secondchoice.sort(key=attrgetter("score"), reverse=True)
        otherlist = list()
        for gdobj in secondchoice:
            case = flatmatrice.get_case(gdobj.x, gdobj.y)
            if case not in firstlist:
                otherlist.append(case)
        gdSet.register_list_case("other_adj", otherlist)
        # incluse dans safe zone :
        safezonelist = gdSet.get_list_case("safezone")
        safelist = [c for c in adjlist if c in safezonelist]
        gdSet.register_list_case("safe_adj", safelist)

    #-----> B.7- Anticipation de coups consécutifs
    #-----> B.7.1- Dédiée aux winners et hunters intelligents
    def _can_schedule_gambles(self, robot):
        """
        Indique si le robot peut prévoir plusieurs coups.
        """
        gdSet = robot.get_current_gdSet()
        # hunters et winners uniquement
        cond0 = robot.behavior in [CaseRobot.BEHAVIOR_HUNTER, CaseRobot.BEHAVIOR_WINNER]
        # si aucune pseudo action n'est définie
        cond1 = not gdSet.has_next_pseudoaction()
        # en fontion de son intelligence :
        cond2 = robot.intelligence >= CaseRobot.get_feature_threshold(
            "intelligence", "middle"
        )
        # en fonction du nombre de coups restants :
        cond3 = True  # gdSet.gamblecount - gdSet.gamblenumber + 1 > 1
        # validité des actions prévues :
        cond4 = True
        if not cond1:
            cond4 = not self._get_pseudoactionlist_validity(robot)
        # retour
        if cond0 and cond1 and cond2 and cond3 and cond4:
            return True
        return False

    def _get_pseudoactionlist_validity(self, robot):
        """
        Vérifie qu'un danger bloquant ne soit pas apparu dans le parcours.
        """
        valide = False
        flatmatrice = self._lablevel.get_flat_matrice()
        gdSet = robot.get_current_gdSet()
        palist = None
        paobj = gdSet.get_pseudoactions()
        if paobj != None:
            palist = paobj.get_pseudoaction_list()
        if palist != None:
            valide = True
            for pa in palist:
                typepa = pa["type"]
                if typepa == "goto":
                    x, y = pa["coords"]
                    tc = pa["type_case"]
                    actcase = flatmatrice.get_case(x, y)
                    if actcase.type_case == LabHelper.CASE_DANGER:
                        # nouveau danger ?
                        if tc != LabHelper.CASE_DANGER:
                            # quel rayon, quelle distance
                            actradius = actcase.get_danger_radius()
                            d = self._lablevel.get_distance_between_cases(
                                robot, actcase
                            )
                            if d < actradius:
                                # on invalide les actions programmées
                                valide = False
                                gdSet.register_pseudoactions(None)
                                break
        return valide

    #-----> B.7.2- Recherche d'une série de commandes : analyse et décisions
    def _schedule_next_gambles(self, robot):
        """
        Méthode principale d'anticipation de plusieurs coups.
        """
        # paramètres
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        # 1- Initialisation de la recherche :
        if gdSet.gamblenumber == 1:
            # priorisation des objectifs :
            self._define_scheduled_ordered_objectifs(robot)
        gsearch.maxactions = gdSet.gamblecount - gdSet.gamblenumber + 1
        # identification des possibilités
        self._define_scheduled_possibilities(robot)
        # 2- Actions optimales
        finded, paObj = self._analyse_optimal_actions(robot)
        # 3- Actions selon les objectifs
        if not finded:
            finded, paObj = self._analyse_actions_by_objectifs(robot)
        # 4- Récupération de bonus :
        if not finded:
            finded, paObj = self._search_scheduled_bonus(robot)
        # 5- Revue des actions évaluées :
        if not finded and len(gsearch.paObjlist) > 0:
            # peut on se contenter d'une action de pertinence moyenne?
            paolist = [pao for pao in gsearch.paObjlist if pao.relevantfactor > 0]
            if len(paolist) > 0:
                paolist.sort(key=attrgetter("score"), reverse=True)
                paObj = paolist[0]
                finded = True
        # 6- Actions désespérées si aucun objectif n'a pu être atteint
        if not finded:
            finded, paObj = self._analyse_desperate_actions(robot)
        # 7- Meileur score :
        if len(gsearch.paObjlist) > 0:
            gsearch.paObjlist.sort(
                key=attrgetter("relevantfactor", "score"), reverse=True
            )
            paObj = gsearch.paObjlist[0]
            finded = True
        # 8- Enregistrement de la pseudos action trouvée :
        if finded:
            gdSet.register_pseudoactions(paObj)
            if paObj.name == CommandManager.PA_STAY_IN_PLACE:
                # incrément du nombre de pa no move :
                robot.no_move_count += 1
            else:
                robot.no_move_count = 0

    def _define_scheduled_ordered_objectifs(self, robot):
        """
        Définit la liste des objectifs triés par priorité en fonction du robot.
        """
        objectifs = list()
        # - caractéristiques du robot
        gdSet = robot.get_current_gdSet()
        behavior = robot.behavior
        ambition = robot.ambition
        instinct_survie = robot.instinct_survie
        aggressivite = robot.aggressivite
        intelligence = robot.intelligence
        # - seuils :
        midSUR = CaseRobot.get_feature_threshold("instinct_survie", "middle")
        highSUR = CaseRobot.get_feature_threshold("instinct_survie", "high")
        midAGG = CaseRobot.get_feature_threshold("aggressivite", "middle")
        highAGG = CaseRobot.get_feature_threshold("aggressivite", "high")
        # - priorités
        if aggressivite < midAGG:
            # robot non aggressif
            if instinct_survie < midSUR:
                objectifs = [CommandManager.OBJ_MOVE]
            else:
                if instinct_survie >= highSUR:
                    objectifs = [CommandManager.OBJ_DEFENSE, CommandManager.OBJ_MOVE]
                else:
                    objectifs = [CommandManager.OBJ_MOVE, CommandManager.OBJ_DEFENSE]
        elif aggressivite >= highAGG:
            # robot hyper aggressif
            if instinct_survie < midSUR:
                objectifs = [CommandManager.OBJ_ATTACK, CommandManager.OBJ_MOVE]
            else:
                if instinct_survie >= highSUR:
                    objectifs = [
                        CommandManager.OBJ_ATTACK,
                        CommandManager.OBJ_DEFENSE,
                        CommandManager.OBJ_MOVE,
                    ]
                else:
                    objectifs = [
                        CommandManager.OBJ_ATTACK,
                        CommandManager.OBJ_MOVE,
                        CommandManager.OBJ_DEFENSE,
                    ]
        else:
            # cas intermédiaire
            cond1 = False
            # - cas particulier des winners
            if behavior == CaseRobot.BEHAVIOR_WINNER:
                advdict = gdSet.get_adversaires_avance()
                if advdict["adv_in_final"] or advdict["adv_in_approach"]:
                    # des adversaires peuvent gagner !
                    cond1 = True
            # - cas particulier des hunters
            if behavior == CaseRobot.BEHAVIOR_HUNTER:
                maintarget = robot.get_main_target()
                if maintarget != None and maintarget.case in gdSet.get_list_case(
                    "attaque"
                ):
                    # Priorité à l'attaque
                    cond1 = True
            # - cas général de priorité à l'attaque
            cond2 = (aggressivite + ambition) / 2 > (intelligence + instinct_survie) / 2
            if cond1 or cond2:
                objectifs = [CommandManager.OBJ_ATTACK, CommandManager.OBJ_MOVE]
                if instinct_survie >= midSUR:
                    objectifs.append(CommandManager.OBJ_DEFENSE)
            else:
                if instinct_survie < midSUR:
                    objectifs = [CommandManager.OBJ_MOVE, CommandManager.OBJ_ATTACK]
                else:
                    if instinct_survie >= highSUR:
                        objectifs = [
                            CommandManager.OBJ_DEFENSE,
                            CommandManager.OBJ_MOVE,
                            CommandManager.OBJ_ATTACK,
                        ]
                    else:
                        objectifs = [
                            CommandManager.OBJ_MOVE,
                            CommandManager.OBJ_DEFENSE,
                            CommandManager.OBJ_ATTACK,
                        ]
        # enregistrement
        gsearch = gdSet.gamblesearch
        gsearch.objectifs = objectifs

    def _define_scheduled_possibilities(self, robot):
        """
        Analyse les possibilités de mouvement, attaque et défense
        """
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        # 1- Cas général
        # - déplacement sécurisé
        safezone = gdSet.get_list_case("safezone")
        gsearch.safe_move_possible = len(safezone) > 0
        # - action défensive requise
        gsearch.list_defense = gdSet.get_list_case("defense")
        gsearch.defense_needed = len(gsearch.list_defense) > 0
        # - attaque directe possible :
        listatt = None
        behavior = robot.behavior
        if behavior == CaseRobot.BEHAVIOR_WINNER:
            # cas particulier d'un winner :
            dictadv = gdSet.get_adversaires_avance()
            list1 = list()
            list2 = list()
            if dictadv["adv_in_final"]:
                list1 = dictadv["final_list"]
            elif dictadv["adv_in_approach"]:
                list2 = dictadv["approach_list"]
            list1.extend(list2)
            if len(list1) > 0:
                listatt = list1
        if listatt == None:
            listatt = gdSet.get_list_case("attaque")
        gsearch.list_attaque = listatt
        gsearch.attaque_possible = len(gsearch.list_attaque) > 0
        # 2- Pour un robot intelligent :
        intelligence = robot.intelligence
        highQI = CaseRobot.get_feature_threshold("intelligence", "high")
        objectifs = gsearch.objectifs
        if intelligence >= highQI:
            # attaque indirecte ?
            if (
                objectifs[0] == CommandManager.OBJ_ATTACK
                and not gsearch.attaque_possible
            ):
                att_all = gdSet.get_list_case("attaque_all")
                if len(att_all) > 0:
                    gsearch.list_attaque = att_all
                    gsearch.attaque_possible = True
            # défense indirecte ?
            if (
                objectifs[0] == CommandManager.OBJ_DEFENSE
                and not gsearch.defense_needed
            ):
                def_all = gdSet.get_list_case("defense_all")
                if len(def_all) > 0:
                    gsearch.list_defense = def_all
                    gsearch.defense_needed = True

    def _analyse_optimal_actions(self, robot):
        """
        Analyse la possibilité de réaliser des actions optimales
        """
        finded = False
        paObj = None
        relevantfactor = 0
        # paramètres
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        # 1- analyse des possibilités
        # 1.1- attaque optimale ?
        if (
            gsearch.objectifs[0] == CommandManager.OBJ_ATTACK
            and gsearch.attaque_possible
        ):
            # on recherche une pseudo action offensive pertinente :
            finded, paObj = self._batch_search_scheduled_attaque(
                robot,
                gsearch.list_attaque,
                searchctx=CommandManager.CTX_OPTIMAL,
                relevantonly=True,
            )
            if paObj != None:
                relevantfactor = paObj.relevantfactor
            gsearch.attaque_tried = True
        # 1.2- mouvement optimal ?
        if gsearch.safe_move_possible and relevantfactor < 2:
            # - libérer la sortie en phase finale
            if robot.game_phasis == CommandManager.PHASIS_FINAL:
                # Le chemin vers la sortie est il défini?
                maintarget = robot.get_main_target()
                case_sortie = self._lablevel.get_case_sortie()
                if maintarget.case == case_sortie and maintarget.targetpath == None:
                    # un ou plusieurs dangers bloquants sont à éliminer
                    finded, paObj = self._search_scheduled_free_sortie(robot)
                    gsearch.free_sortie_tried = True
            # - suivre le chemin vers la cible :
            if not finded:
                finded, paObj = self._search_scheduled_optimal_move(robot)
                gsearch.optimal_move_tried = True
            # - garder la position si elle est sûre :
            if not finded:
                finded, paObj = self._search_scheduled_keep_position(robot)
            if finded:
                # on enregistre le résultat pour comparaison ultérieure
                paObj.searchctx = CommandManager.CTX_OPTIMAL
                gsearch.paObjlist.append(paObj)
                # la PseudoActions est elle pertinente?
                relevantfactor = self._valide_paObj_relevance(robot, paObj)
        # 2- décision
        if finded and relevantfactor < 2:
            # l'action n'est pas d'une pertinence optimale
            # liste des bots / securestop=False
            stoptargets = paObj.stoptargets
            if stoptargets != None and len(stoptargets) > 0:
                # trie des dangers identifiés :
                targetsdictlist = list()
                for b in stoptargets:
                    d = self._lablevel.get_distance_between_cases(robot, b)
                    targetsdictlist.append({"b": b, "d": d})
                targetsdictlist.sort(key=itemgetter("d"))
                defbots = [bdict["b"] for bdict in targetsdictlist]
                # on passe "defense" en obj prioritaire
                if CommandManager.OBJ_DEFENSE in gsearch.objectifs:
                    gsearch.objectifs.remove(CommandManager.OBJ_DEFENSE)
                gsearch.objectifs.insert(0, CommandManager.OBJ_DEFENSE)
                # on met à jour listdef et defense_needed
                gsearch.list_defense = defbots
                gsearch.defense_needed = True
            # on invalide le résultat
            finded = False
        return finded, paObj

    def _analyse_actions_by_objectifs(self, robot):
        """
        Recherche une action suivant la priorité des objectifs
        """
        finded = False
        paObj = None
        # paramètres
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        aggressivite = robot.aggressivite
        midAGG = CaseRobot.get_feature_threshold("aggressivite", "middle")
        # analyse
        for objectif in gsearch.objectifs:
            if not finded:
                if (
                    objectif == CommandManager.OBJ_MOVE
                    and not gsearch.safe_move_tried
                    and gsearch.safe_move_possible
                ):
                    # safe move?
                    finded, paObj = self._search_scheduled_safe_move(robot)
                    gsearch.safe_move_tried = True
                    if finded:
                        # on mémorise l'action
                        paObj.searchctx = CommandManager.CTX_BY_OBJ
                        gsearch.paObjlist.append(paObj)
                        # pertinence :
                        relevantfactor = self._valide_paObj_relevance(robot, paObj)
                        if relevantfactor < 2:
                            # on poursuit la recherche
                            finded = False
                elif (
                    objectif == CommandManager.OBJ_DEFENSE
                    and not gsearch.defense_tried
                    and gsearch.defense_needed
                ):
                    # defense?
                    # - par attaque
                    if not finded and aggressivite >= midAGG:
                        # on recherche une pseudo action offensive pertinente :
                        finded, paObj = self._batch_search_scheduled_attaque(
                            robot,
                            gsearch.list_defense,
                            searchctx=CommandManager.CTX_BY_OBJ,
                            relevantonly=True,
                        )
                    # - par safe move
                    if (
                        not finded
                        and not gsearch.safe_move_tried
                        and gsearch.safe_move_possible
                    ):
                        finded, paObj = self._search_scheduled_safe_move(robot)
                        gsearch.safe_move_tried = True
                        if finded:
                            # on mémorise l'action
                            paObj.searchctx = CommandManager.CTX_BY_OBJ
                            gsearch.paObjlist.append(paObj)
                            # pertinence :
                            relevantfactor = self._valide_paObj_relevance(robot, paObj)
                            if relevantfactor < 2:
                                # on poursuit la recherche
                                finded = False
                    # solutions de défense traitées
                    gsearch.defense_tried = True
                elif (
                    objectif == CommandManager.OBJ_ATTACK
                    and not gsearch.attaque_tried
                    and gsearch.attaque_possible
                ):
                    # attaque?
                    # on recherche une pseudo action offensive pertinente :
                    finded, paObj = self._batch_search_scheduled_attaque(
                        robot,
                        gsearch.list_attaque,
                        searchctx=CommandManager.CTX_BY_OBJ,
                        relevantonly=True,
                    )
                    gsearch.attaque_tried = True
            else:
                break
        return finded, paObj

    def _analyse_desperate_actions(self, robot):
        """
        Sélectionne une action désespérée
        """
        finded = False
        paObj = None
        # paramètres
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        # analyse
        listact = ["dangers", "risk", "escape"]
        # cr.CustomRandom.shuffle(listact)
        for act in listact:
            if act == "dangers":
                # - rebattre les cartes en explosant des mines
                finded, paObj = self._search_scheduled_dangers(robot)
            elif act == "risk":
                # - tenter un déplacement risqué
                finded, paObj = self._search_scheduled_risked_move(robot)
            elif act == "escape":
                # - fuite désespérée
                finded, paObj = self._search_scheduled_desperate_escape(robot)
            if finded:
                break
        if finded:
            # infos minimales (arrêt sécurisé?)
            paObj.searchctx = CommandManager.CTX_DESPERATE
            self._complete_paObj_with_secure_infos(robot, paObj)
            gsearch.paObjlist.append(paObj)
            self._valide_paObj_relevance(robot, paObj)
        return finded, paObj

    #-----> B.7.3- Méthodes de recherche thématiques
    def _search_scheduled_optimal_move(self, robot):
        """
        Analyse le parcours du targetpath associé à TempTarget (si définie), ou
        MainTarget.
        Retourne un objet PseudoActions si la cible et le chemin existent, ou
        None.
        """
        finded = False
        paObj = None
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        maxactions = gsearch.maxactions
        # 1- Sélection d'un nombre de cases égal au nombre de coups à jouer
        # dans le chemin vers la cible, ou les cases suivantes :
        listcases = self._get_optimal_listcases_for_move(robot)
        if listcases != None:
            # 2- Analyse du nombre de coups nécessaires et des besoins de
            # terraformage :
            listdictcases = list()
            delcases = list()
            extendedunsafezone = gdSet.get_list_case("extendedunsafezone")
            for c in listcases:
                nbg = self._get_case_pathcost_for_robot(c, robot)
                if nbg == None:
                    # robot inattaquable
                    break
                else:
                    if nbg == 2:
                        delcases.append(c)
                    safe = c not in extendedunsafezone
                    tc = c.type_case
                    cdict = {
                        "case": c,
                        "tc": tc,
                        "nbg": nbg,
                        "safe": safe,
                        "terraformed": False,
                    }
                    listdictcases.append(cdict)
            # besoin de terraformer?
            needterraform = False
            terrares = None
            if len(delcases) > 0:
                needterraform = True
                params = self._get_params_for_grenade_and_listcases(robot, delcases)
                if params != None:
                    exist = params["finded"]
                    if exist:
                        if params["bestfirst"] != None:
                            terrares = params["bestfirst"]
                        else:
                            terrares = params["bestres"]
            # 3- Réduction de la liste
            # rq : supprimer des dangers peut en faire apparaitre d'autres
            totalnbg = 0
            isexact = not needterraform
            finaldictlist = list()
            if isexact:
                finaldictlist = listdictcases
                totalnbg = len(finaldictlist)
            else:
                if terrares == None:
                    # pas de solution de terraformage initiale, on s'appuye sur
                    # les nombres de coups théoriques
                    for cdict in listdictcases:
                        c = cdict["case"]
                        nbg = cdict["nbg"]
                        if totalnbg + nbg <= maxactions:
                            totalnbg += nbg
                            finaldictlist.append(cdict)
                        else:
                            break
                else:
                    # terraformage au premier coup : on optimise le nombre de
                    # coups prévus (mais pas forcément exact)
                    terraset = terrares["setmatch"]
                    totalnbg += 1
                    for cdict in listdictcases:
                        c = cdict["case"]
                        nbg = cdict["nbg"]
                        if c in terraset:
                            # hypothèse favorable : un danger n'apparaitra pas
                            nbg = 1
                            cdict["terraformed"] = True
                        if totalnbg + nbg <= maxactions:
                            totalnbg += nbg
                            finaldictlist.append(cdict)
                        else:
                            break
            # élimination des cases non sûres en fin de liste :
            reddictlist = list()
            finaldictlist.reverse()
            hassafe = False
            for cdict in finaldictlist:
                safe = cdict["safe"]
                if safe:
                    hassafe = True
                if hassafe:
                    reddictlist.append(cdict)
                    c = cdict["case"]
                else:
                    # mise à jour du nombre de coups estimés
                    if cdict["terraformed"]:
                        totalnbg -= 1
                    else:
                        totalnbg -= cdict["nbg"]
            reddictlist.reverse()
            # 4- Création de l'objet pseudo actions :
            if len(reddictlist) > 0:
                finded = True
                palist = list()
                killedbots = None
                # terraformage initial
                if terrares != None:
                    comb = terrares["combinaison"]
                    terraset = terrares["setmatch"]
                    killedbots = [c for c in terraset if c in self.alive_bots]
                    cmd = self._get_cmd_from_grenade_combinaison(robot, comb)
                    terrapa = {"type": "grenade", "cmd": cmd}
                    palist.append(terrapa)
                # déplacement :
                for cdict in reddictlist:
                    c = cdict["case"]
                    mpa = self._format_move_pseudoaction_for_case(c)
                    palist.append(mpa)
                # objet PseudoActions :
                paObj = PseudoActions(palist, totalnbg)
                paObj.killedbots = killedbots
                paObj.exactpath = isexact
                paObj.name = CommandManager.PA_OPTIMAL_MOVE
                # infos minimales (arrêt sécurisé?)
                self._complete_paObj_with_secure_infos(robot, paObj)
        return finded, paObj

    def _search_scheduled_free_sortie(self, robot):
        """
        Recherche une série de coups permettant de libérer la sortie de
        dangers empéchant la recherche d'un chemin.
        """
        finded = False
        paObj = None
        # liste des dgrs triés par dist croissante à la sortie
        case_sortie = self._lablevel.get_case_sortie()
        # les dangers identifiés lors de la recherche de chemin
        blockingdgr = self._search_TargetPath(robot, case_sortie)[1]
        if len(blockingdgr) == 0:
            # tous les dangers environnants la sortie
            blockingdgr = self._do_dangers_block_sortie(robot)
        if len(blockingdgr) > 0:
            for dgr in blockingdgr:
                finded, paObj = self._search_scheduled_attaque(robot, targetcase=dgr)
                if finded:
                    paObj.name = CommandManager.PA_FREE_EXIT
                    # infos minimales (arrêt sécurisé?)
                    self._complete_paObj_with_secure_infos(robot, paObj)
                    break
        return finded, paObj

    def _search_scheduled_keep_position(self, robot):
        """
        Recherche si la position actuelle est sûre.
        """
        finded = False
        paObj = None
        # évite des actions no move infinies :
        if robot.no_move_count > 1:
            return finded, paObj
        # la position actuelle du robot est-elle sûre?
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        maxactions = gsearch.maxactions
        safezone = gdSet.get_list_case("safezone")
        if robot in safezone:
            palist = [{"type": "nomove"}]
            paObj = PseudoActions(palist, maxactions)
            self._complete_paObj_with_secure_infos(robot, paObj)
            paObj.name = CommandManager.PA_STAY_IN_PLACE
            finded = True
        return finded, paObj

    def _search_scheduled_safe_move(self, robot, wait_at_end=False):
        """
        Recherche d'un parcours menant à une case comprise dans la safe zone, si
        possible dans la direction de TempTarget ou MainTarget.
        wait_at_end : complète au besoin la liste de pseudos actions avec
        des actions nomove
        """
        gdSet = robot.get_current_gdSet()
        # liste des cases sûres
        # - hors portée de mine ou attaque directe
        realsafezone = gdSet.get_list_case("realsafezone")
        finded, paObj = self._search_scheduled_move_in_list(
            robot, realsafezone, wait_at_end=wait_at_end
        )
        # - hors attaque directe
        if not finded:
            safezone = gdSet.get_list_case("safezone")
            redsafe = [c for c in safezone if c not in realsafezone]
            finded, paObj = self._search_scheduled_move_in_list(
                robot, redsafe, wait_at_end=wait_at_end
            )
        if finded:
            # infos minimales (arrêt sécurisé?)
            self._complete_paObj_with_secure_infos(robot, paObj)
        if finded:
            paObj.name = CommandManager.PA_SAFE_MOVE
        return finded, paObj

    def _search_scheduled_risked_move(self, robot, risklevel=1, wait_at_end=False):
        """
        Recherche d'un parcours risqué si possible dans la direction de
        TempTarget ou MainTarget.
        
        * risklevel : entier décrivant le niveau de risque accepté
        
          * 1 : cases de move_zone telles que la proba max
            d'attaque soit inférieure à 55%
          * autres : toute case de proba minimale
            
        * wait_at_end : complète au besoin la liste de pseudos actions avec
          des actions nomove
        
        Rq : méthode "désespérée", faisant appel à des pseudos probas sous
        évaluées
        """
        # 1- Probabilités d'attaque par case de move_zone :
        listprob = self._get_attack_probas_for_move_zone(robot)
        # proba max en fonction du niveau de risque
        pmax = 1
        if risklevel == 1:
            pmax = 0.55
        # sélection des cases
        clist = list()
        for cdict in listprob:
            if cdict["proba"] <= pmax:
                clist.append(cdict["case"])
            else:
                break
        # 2- Recherche de chemin
        finded, paObj = self._search_scheduled_move_in_list(
            robot, clist, wait_at_end=wait_at_end
        )
        if finded:
            paObj.name = CommandManager.PA_RISKED_MOVE
            # infos minimales (arrêt sécurisé?)
            self._complete_paObj_with_secure_infos(robot, paObj)
        return finded, paObj

    def _search_scheduled_move_in_list(self, robot, listcases, wait_at_end=False):
        """
        Recherche d'un parcours menant à une case comprise dans listcases, si
        possible dans la direction de TempTarget ou MainTarget.
        wait_at_end : complète au besoin la liste de pseudos actions avec
        des actions nomove
        """
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        maxactions = gsearch.maxactions
        finded = False
        paObj = None
        if len(listcases) > 0:
            # liste de dicts {"case":, "dist":, "bonus":,  "inpath":, "indirect":}
            # distantes de maxactions au max
            predictlist = self._preselect_cases_for_safe_move(robot, listcases)
            # choix de la meilleure liste de recherche :
            searchdictlist = None
            pathdictlist = [cdict for cdict in predictlist if cdict["inpath"] == 1]
            if len(pathdictlist) > 0:
                # rester dans le path
                searchdictlist = pathdictlist
            if searchdictlist == None:
                dirdictlist = [cdict for cdict in predictlist if cdict["indirect"] == 1]
                if len(dirdictlist) > 0:
                    # rester dans les directions de la cible principale
                    searchdictlist = dirdictlist
            if searchdictlist == None:
                # par défaut la liste entière
                searchdictlist = predictlist
            # trie :
            if robot.need_bonus:
                searchdictlist.sort(key=itemgetter("bonus", "dist"), reverse=True)
            else:
                searchdictlist.sort(key=itemgetter("dist", "bonus"), reverse=True)
            # évaluations :
            for searchdict in searchdictlist:
                c = searchdict["case"]
                tp = self._search_TargetPath(robot, c)[0]
                if tp != None:
                    # un chemin existe, est il assez court?
                    nbgamble = self._get_gamble_count_for_TargetPath(robot, tp)
                    if nbgamble != None and nbgamble <= maxactions:
                        # parcours trouvé :
                        pseudoactionlist = self._get_pseudoactionlist_for_TargetPath(tp)
                        if wait_at_end and nbgamble < maxactions:
                            # pseudo action sans mouvement jusqu'à la fin
                            # du tour (non dénombrée, nbgamble n'étant pas
                            # forcément exact)
                            pseudoaction = {"type": "nomove"}
                            pseudoactionlist.append(pseudoaction)
                            nbgamble = maxactions
                        # Objet PseudoActions
                        paObj = PseudoActions(pseudoactionlist, nbgamble)
                        finded = True
                        break
        # retour :
        return finded, paObj

    def _batch_search_scheduled_attaque(
        self, robot, botslist, searchctx=None, relevantonly=False
    ):
        """
        Recherche dans la liste une combinaison de coups offensifs.
        
        * botslist : liste de robots à attaquer
        * searchctx : contexte de recherche
        * relevantonly (bool) : si True poursuit la recherche jusqu'à trouver
          une pseudo action pertinente (relevantfactor=2).
          
        """
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        finded = False
        paObj = None
        # on exclut les robots déja traités
        filterdef = [b for b in botslist if not gsearch.kill_search_already_done(b)]
        for b in filterdef:
            finded, paObj = self._search_scheduled_attaque(robot, targetcase=b)
            if finded:
                # on mémorise l'action
                paObj.searchctx = searchctx
                gsearch.paObjlist.append(paObj)
                # pertinence :
                relevantfactor = self._valide_paObj_relevance(robot, paObj)
                if relevantfactor < 2 and relevantonly:
                    # on poursuit la recherche
                    finded = False
                    paObj = None
                else:
                    break
        return finded, paObj

    def _search_scheduled_attaque(self, robot, targetcase=None, pathsearch=True):
        """
        Recherche d'une série de coups offensifs
        Retourne un boolean indiquant si une solution a été trouvée et une liste
        de pseudos actions ou None
        """
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        maxactions = gsearch.maxactions
        finded = False
        paObj = None
        # cible de l'attaque
        attcase = targetcase
        if attcase == None:
            listatt = gsearch.list_attaque
            if len(listatt) > 0:
                attcase = listatt[0]
            if attcase == None:
                return finded, paObj
        # liste des bots éliminés :
        killedbots = None
        # 1- Attaque directe
        directcmd = None
        typeaction = None
        if robot.has_grenade:
            recursive = False
            highQI = CaseRobot.get_feature_threshold("intelligence", "high")
            if robot.intelligence >= highQI:
                recursive = True
            typeaction = "grenade"
            directcmd = self._evaluate_complex_action(
                robot, LabHelper.ACTION_GRENADE, attcase, recursive=recursive
            )
        elif (
            self._lablevel.get_distance_between_cases(robot, attcase) == 1
            and attcase.type_case == LabHelper.CASE_ROBOT
        ):
            typeaction = "kill"
            actdict = {"action": LabHelper.ACTION_KILL, "code": LabHelper.CHAR_KILL}
            directcmd = self._evaluate_simple_action(robot, actdict, attcase)
        directcmd = self._pre_check_or_nullify_cmd(directcmd, robot)
        if directcmd != None:
            pseudoaction = {"type": typeaction, "cmd": directcmd}
            pseudoactionlist = [pseudoaction]
            # bots impactés :
            if robot.has_grenade:
                params = self._get_params_for_grenade(
                    robot, attcase, recursive=recursive
                )
                defcomb = params["default"]
                cases_impactees = defcomb["cases_impactees"]
                killedbots = [c for c in cases_impactees if c in self.alive_bots]
            elif attcase.type_case == LabHelper.CASE_ROBOT:
                killedbots = [attcase]
            # Objet PseudoActions
            paObj = PseudoActions(pseudoactionlist, 1)
            paObj.killedbots = killedbots
            finded = True
        # 2- Mouvement puis attaque
        if not finded and pathsearch:
            move_zone = self._lablevel.get_caseset_for_coordset(robot.move_zone)
            dlist = list()
            # mémorisation coords robot
            refx, refy = int(robot.x), int(robot.y)
            # cas particulier ou cas général ?
            test_dgr = attcase.type_case == LabHelper.CASE_DANGER
            cond_back = test_dgr and attcase.get_danger_radius() >= self._lablevel.get_distance_between_cases(
                robot, attcase
            )
            # 2.1- Cas général
            if not cond_back:
                # attcase n'est pas un danger ou la distance robot-attcase est
                # supérieure au rayon d'action du danger, on avance.
                # - distance limite pour la sélection de cases
                dra = self._lablevel.get_path_length_between_cases(robot, attcase)
                if not robot.has_grenade:
                    dlimit = 1
                else:
                    dlimit = (robot.get_danger_radius() - robot.vitesse + 1) * 1.5
                # - cases accessibles en direction de la cible
                for c in move_zone:
                    dr = self._lablevel.get_path_length_between_cases(c, robot)
                    # on garde une action offensive
                    if 0 < math.ceil(dr) < maxactions:
                        d = self._lablevel.get_path_length_between_cases(c, attcase)
                        # on se limite :
                        # - aux cases dirigées vers la cible : d < dra
                        # - telles que dist case / attcase <= 1 sans grenade
                        # - ou dist case / attcase <= dlimit si grenade
                        #   pour limiter les calculs récurifs
                        if d <= min(dra, dlimit):
                            vector = self._lablevel.get_vector_for_cases(robot, c)
                            cost = self._compute_case_cost(robot, c)
                            dlist.append(
                                {
                                    "case": c,
                                    "dist": d,
                                    "disr_robot": dr,
                                    "vx": vector[0],
                                    "vy": vector[1],
                                    "cost": cost,
                                }
                            )
            # 2.2- Cas particulier
            elif robot.has_grenade:
                # attcase est un danger trop proche du robot, il faut reculer.
                # rq : nécessite un lancer de grenade.
                dmin = self._lablevel.get_distance_between_cases(robot, attcase)
                dlimit = (robot.get_danger_radius() - robot.vitesse + 1) * 1.5
                for c in move_zone:
                    dr = self._lablevel.get_path_length_between_cases(c, robot)
                    # on garde une action offensive
                    if 0 < math.ceil(dr) < maxactions:
                        d = self._lablevel.get_distance_between_cases(c, attcase)
                        # on se limite aux cases qui éloignent le robot de la
                        # cible tout en restant dans dlimit
                        if dmin < d <= dlimit:
                            vector = self._lablevel.get_vector_for_cases(robot, c)
                            cost = self._compute_case_cost(robot, c)
                            dlist.append(
                                {
                                    "case": c,
                                    "dist": d,
                                    "disr_robot": dr,
                                    "vx": vector[0],
                                    "vy": vector[1],
                                    "cost": cost,
                                }
                            )
            # - tentative de réduction de la liste de recherche...
            searchlist1 = list()
            searchlist2 = list()
            if len(dlist) > 5:
                # ... à partir d'un certain nombre d'options
                xlist = [cd for cd in dlist if cd["vy"] == 0]
                ylist = [cd for cd in dlist if cd["vx"] == 0]
                rlist = [cd for cd in dlist if cd["vx"] * cd["vy"] != 0]
                # en fonction du vecteur robot -> cible
                vectra = self._lablevel.get_vector_for_cases(robot, attcase)
                cond_hori = vectra[1] == 0 or (
                    vectra[0] != 0 and math.fabs(vectra[1] / vectra[0]) < 0.16
                )
                cond_vert = vectra[0] == 0 or math.fabs(vectra[1] / vectra[0]) > 6
                cond_oblique = not cond_hori and not cond_vert
                if cond_oblique:
                    # vecteur oblique (pas de réduction évidente)
                    if math.fabs(vectra[0]) > math.fabs(vectra[1]):
                        # on privilégie y
                        searchlist1 = ylist
                    else:
                        # sinon x
                        searchlist1 = xlist
                    # on complète avec les autres éléments de dlist
                    searchlist2 = [cd for cd in dlist if cd not in searchlist1]
                elif cond_hori:
                    # vecteur horizontal (réduction)
                    searchlist1 = xlist
                    searchlist2 = [cd for cd in rlist if math.fabs(cd["vy"]) < 3]
                elif cond_vert:
                    # vecteur vertical (réduction)
                    searchlist1 = ylist
                    searchlist2 = [cd for cd in rlist if math.fabs(cd["vx"]) < 3]
            else:
                searchlist1 = dlist
            # - tries :
            searchlist1.sort(key=itemgetter("disr_robot", "cost"))
            searchlist2.sort(key=itemgetter("disr_robot", "cost"))
            # concaténation
            finalsearchlist = searchlist1
            finalsearchlist.extend(searchlist2)
            # limitation des recherches :
            nbmax = min(len(finalsearchlist), math.floor(15 * robot.intelligence))
            finalsearchlist = finalsearchlist[0:nbmax]
            # - recherche d'une case permettant d'attaquer :
            finalTargetPath = attaquepa = nbgamble = None
            for cdict in finalsearchlist:
                c = cdict["case"]
                # rétablissement des coordonnées
                robot.x, robot.y = refx, refy
                # position de tir satisfaisante?
                (
                    finded,
                    finalTargetPath,
                    attaquepa,
                    killedbots,
                    nbgamble,
                ) = self._evaluate_scheduled_shoot_position(
                    robot, c, attcase, maxactions
                )
                if finded:
                    # on a trouvé une solution
                    break
            # rétablissement des coordonnées
            robot.x, robot.y = refx, refy
            # Création de la liste finale de pseudos actions :
            if finded:
                pseudoactionlist = self._get_pseudoactionlist_for_TargetPath(
                    finalTargetPath
                )
                pseudoactionlist.append(attaquepa)
                # Objet PseudoActions
                paObj = PseudoActions(pseudoactionlist, nbgamble + 1)
                paObj.killedbots = killedbots
        # mémorisation de la recherche offensive
        if attcase.type_case == LabHelper.CASE_ROBOT:
            gsearch.register_kill_search(attcase)
        # retour :
        if finded:
            paObj.name = CommandManager.PA_ATTACK
            # infos minimales (arrêt sécurisé?)
            self._complete_paObj_with_secure_infos(robot, paObj)
        return finded, paObj

    def _search_scheduled_bonus(self, robot):
        """
        En cas de bloquage, vise à amasser le plus de bonus.
        """
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        maxactions = gsearch.maxactions
        finded = False
        paObj = None
        # les bonus à partée
        listbonus = gdSet.get_list_case("bonus")
        if len(listbonus) == 0:
            return False, None
        # distance au robot
        bonusdictlist = list()
        for b in listbonus:
            d = self._lablevel.get_path_length_between_cases(robot, b)
            bonusdictlist.append({"case": b, "dist": d, "distprev": 0})
        # trie par proximité au robot
        bonusdictlist.sort(key=itemgetter("dist"))
        # mesure des inter distances
        proxdictlist = list()
        if len(bonusdictlist) > 1:
            prevb = robot
            for bdict in bonusdictlist:
                # mesure des inter distances
                b = bdict["case"]
                d = self._lablevel.get_path_length_between_cases(prevb, b)
                bdict["distprev"] = d
                prevb = b
            proxdictlist = [bd for bd in bonusdictlist if bd["distprev"] <= 2]
            if len(proxdictlist) > 0:
                proxdictlist.sort(key=itemgetter("distprev", "dist"))
        # mémorisation coords robot
        refx, refy = int(robot.x), int(robot.y)
        # recherche de parcours :
        dictlist = bonusdictlist
        if len(proxdictlist) >= 2:
            dictlist = proxdictlist
        tplist = list()
        prevcase = robot
        gcount = 0
        for bdict in dictlist:
            b = bdict["case"]
            robot.x, robot.y = prevcase.x, prevcase.y
            tp = self._search_TargetPath(robot, b)[0]
            if tp != None:
                # la case peut être atteinte...
                nbgamble = self._get_gamble_count_for_TargetPath(robot, tp)
                if nbgamble != None:
                    if gcount + nbgamble <= maxactions:
                        tplist.append(tp)
                        gcount += nbgamble
                        prevcase = b
                    else:
                        break
        # création de la liste de pseudos actions
        if len(tplist) > 0:
            finded = True
            # concaténation des paths :
            defstepslist = list()
            lastcase = None
            for subtp in tplist:
                substeps = subtp.get_steps_list()
                for tps in substeps:
                    if tps.case != lastcase:
                        defstepslist.append(tps)
                        lastcase = tps.case
            targetpath = TargetPath(steplist=defstepslist)
            # création des p.a.
            pseudoactionlist = self._get_pseudoactionlist_for_TargetPath(targetpath)
            # Objet PseudoActions
            paObj = PseudoActions(pseudoactionlist, gcount)
        # rétablissement des coordonnées
        robot.x, robot.y = refx, refy
        # retour
        if finded:
            # on mémorise l'action
            paObj.name = CommandManager.PA_BONUS
            paObj.searchctx = CommandManager.CTX_BONUS
            gsearch.paObjlist.append(paObj)
            # infos minimales (arrêt sécurisé?)
            self._complete_paObj_with_secure_infos(robot, paObj)
            # pertinence :
            relevantfactor = self._valide_paObj_relevance(robot, paObj)
            if relevantfactor < 2:
                # on poursuit la recherche
                finded = False
        self.bonus_tried = True
        return finded, paObj

    def _search_scheduled_dangers(self, robot):
        """
        Méthode de défense alternative : faire exploser un maximum de mines
        pour rebattre les cartes.
        """
        gdSet = robot.get_current_gdSet()
        finded = False
        paObj = None
        # recherche des mines dans la zone d'attaque
        setatt = set(gdSet.get_list_case("attaque"))
        setdgr = self.dangers_set_plus1
        proxdgr = list(setatt.intersection(setdgr))
        # Trie
        proxdgr.sort(key=attrgetter("danger_impact"), reverse=True)
        # recherche
        for dgr in proxdgr:
            if dgr.danger_impact < 9:
                break
            finded, paObj = self._search_scheduled_attaque(robot, targetcase=dgr)
            if finded:
                paObj.name = CommandManager.PA_DANGERS
                # infos minimales (arrêt sécurisé?)
                self._complete_paObj_with_secure_infos(robot, paObj)
                break
        return finded, paObj

    def _search_scheduled_desperate_escape(self, robot):
        """
        Recherche d'une fuite désespérée
        Retourne un boolean indiquant si une solution a été trouvée et une liste
        de pseudos actions ou None
        """
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        maxactions = gsearch.maxactions
        finded = False
        paObj = None
        pseudoactionlist = None
        midQI = CaseRobot.get_feature_threshold("intelligence", "middle")
        # le bot à priori le plus dangereux :
        defbot = None
        listdef = gsearch.list_defense
        if len(listdef) > 0:
            defbot = listdef[0]
        if defbot == None:
            return finded, pseudoactionlist
        # On s'éloigne de defbot (en posant mine ou mur si intelligence < moyenne)
        # case la plus éloignée de defbot
        move_zone = self._lablevel.get_caseset_for_coordset(robot.move_zone)
        dlist = list()
        for c in move_zone:
            d = self._lablevel.get_distance_between_cases(c, defbot)
            dlist.append({"case": c, "dist": d})
        dlist.sort(key=itemgetter("dist"), reverse=True)
        # recherche de chemin :
        farcase, tp = None, None
        for cdict in dlist:
            c = cdict["case"]
            tp = self._search_TargetPath(robot, c)[0]
            if tp != None:
                farcase = c
                break
        if farcase != None:
            nbgamble = 0
            pseudoactionlist = list()
            tpslist = tp.get_steps_list()[1:]
            for tps in tpslist:
                case = tps.case
                cost = self._get_case_pathcost_for_robot(case, robot)
                # conditions d'arrêt
                if cost == None or nbgamble >= maxactions:
                    break
                nbgamble += cost
                # mouvement :
                x, y = int(case.x), int(case.y)
                tc = case.type_case
                dgr_impact = 0
                if tc == LabHelper.CASE_DANGER:
                    dgr_impact = case.danger_impact
                pseudoaction = {
                    "type": "goto",
                    "coords": (x, y),
                    "type_case": tc,
                    "danger_impact": dgr_impact,
                }
                pseudoactionlist.append(pseudoaction)
                # mur ou mine
                if robot.intelligence < midQI:
                    if nbgamble < maxactions:
                        if robot.has_mine:
                            pseudoaction = {"type": "minemax"}
                        else:
                            pseudoaction = {"type": "wall"}
                        pseudoactionlist.append(pseudoaction)
                        nbgamble += 1
            if nbgamble > 0:
                # Objet PseudoActions
                paObj = PseudoActions(pseudoactionlist, nbgamble)
                paObj.name = CommandManager.PA_ESCAPE
                # infos minimales (arrêt sécurisé?)
                self._complete_paObj_with_secure_infos(robot, paObj)
                finded = True
        # retour :
        return finded, paObj

    #-----> B.7.4- Schedule tools
    def _valide_paObj_relevance(self, robot, paObj):
        """
        Calcul le facteur de pertinence de la PseudoActions
        """
        relevantfactor = 0
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        # 1- Pertinence globale
        # la case d'arrivée est elle sûre?
        securestop = paObj.securestop
        # une case sûre pourra elle être rejointe ensuite?
        secureissue = paObj.secureissue
        # nombre d'actions supplémentaires
        supactions = gsearch.maxactions - paObj.gamblecount
        # fin sur une action nomove?
        lastpa = paObj.get_last_pseudoaction()
        endnomove = lastpa["type"] == "nomove"
        # évaluation de la pertinence de l'action :
        if securestop and supactions == 0:
            if endnomove:
                # pertinence moyenne
                relevantfactor = 1
            else:
                # pertinence max
                relevantfactor = 2
        elif secureissue and supactions > 0:
            if supactions >= 2:
                # pertinence max
                relevantfactor = 2
            else:
                # pertinence moyenne
                relevantfactor = 1
        # prise en compte minimale des risques de bouclage
        lcoords = paObj.get_path_in_pseudoaction_list()
        paObj.loop_factor = robot.compute_loop_factor(lcoords)
        if paObj.loop_factor > 0 and relevantfactor == 2:
            # on rétrograde sauf pour la libération de la sortie
            if paObj.name != CommandManager.PA_FREE_EXIT:
                relevantfactor = 1
            else:
                paObj.loop_factor = 0
        # cas particulier de la recherche de bonus (lancée si aucune action
        # optimale ou par objectif n'a atteint la pertinence de 2)
        if paObj.name == CommandManager.PA_BONUS:
            if securestop and paObj.bonuscount > 0:
                relevantfactor = 2
                paObj.loop_factor = 0
        # enregistrement
        paObj.relevantfactor = relevantfactor
        # 2- Score :
        sco_avance = paObj.deltamainpathlen
        sco_bonus = paObj.bonuscount * (1 + int(robot.need_bonus)) ** 2
        sco_defense = paObj.defensecount * (1 + int(gsearch.defense_needed)) ** 2
        sco_attaque = paObj.attaquecount
        sco_loop = -paObj.loop_factor
        # enregistrement
        paObj.score = sco_avance + sco_bonus + sco_defense + sco_attaque + sco_loop
        # enregistrement et retour :
        paObj.relevantfactor = relevantfactor
        return relevantfactor

    def _complete_paObj_with_secure_infos(self, robot, paObj):
        """
        Renseigne les propriétés suivantes d'un objet PseudoActions :
        
        * securestop : la case d'arrivée est elle sûre?
        * stoptargets : liste des bots / securestop=False
        * secureissue : une case sûre pourra elle être rejointe ensuite?
        * bonuscount : nombre de bonus dans le path
        * defensecount : nombre de bots contre lesquels se défendre éliminés
        * attaquecount : nombre de bots à attaquer éliminer
        
        """
        securestop = False
        stoptargets = list()
        case_sortie = self._lablevel.get_case_sortie()
        flatmatrice = self._lablevel.get_flat_matrice()
        # définition de la sûreté des zones :
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        botdefcount = 0  # bots contre lesquels se défendre touchés
        botattcount = 0  # bots à attaquer touchés
        if paObj.killedbots != None:
            # des bots vont être éliminés pendant l'action, on doit re définir
            # les zones
            defall = gdSet.get_list_case("defense_all")
            defreal = [b for b in defall if b not in paObj.killedbots]
            move_zone = self._lablevel.get_caseset_for_coordset(robot.move_zone)
            safe_set = move_zone  # cases sûres / coups directs
            ext_unsafe_set = set()  # zone étendue des cases attaquables
            for b in defreal:
                b_att = self._lablevel.get_caseset_for_coordset(b.attack_zone)
                safe_set = safe_set.difference(b_att)
                ext_unsafe_set = ext_unsafe_set.union(b_att)
            safezone = list(safe_set)
            extendedunsafezone = list(ext_unsafe_set)
            # dénombrement des bots touchés :
            killset = set(paObj.killedbots)
            defset = set()
            if gsearch.list_defense != None:
                defset = set(gsearch.list_defense)
            botdefcount = len(killset.intersection(defset))
            attset = set()
            if gsearch.list_attaque != None:
                attset = set(gsearch.list_attaque)
            botattcount = len(killset.intersection(attset))
        else:
            # pas de bots éliminés, on utilise les listes complètes
            extendedunsafezone = gdSet.get_list_case("extendedunsafezone")
            safezone = gdSet.get_list_case("safezone")
        # 1- Case d'arrivée de la série d'actions
        # dernière case atteinte :
        coordspath = paObj.get_path_in_pseudoaction_list()
        lastcase = None
        if len(coordspath) >= 1:
            x, y = coordspath[-1]
            lastcase = flatmatrice.get_case(x, y)
        else:
            lastcase = robot
        # est elle dans la zone non sûre?
        if lastcase == case_sortie:
            securestop = True
        elif lastcase not in extendedunsafezone:
            securestop = True
        else:
            deftargets = self._get_defense_targets_for_case(robot, lastcase)
            if paObj.killedbots != None:
                # on retire les bots qui vont être éliminés
                stoptargets = [b for b in deftargets if b not in paObj.killedbots]
            else:
                stoptargets = deftargets
        # distance du chemin vers la cible principale
        mainTarget = robot.get_main_target()
        deltamainpathlen = 0
        if mainTarget != None:
            maincase = mainTarget.case
            mainpathlen = self._lablevel.get_path_length_between_cases(
                lastcase, maincase
            )
            botpathlen = self._lablevel.get_path_length_between_cases(robot, maincase)
            deltamainpathlen = botpathlen - mainpathlen
        # 2- Possibilité de rejoindre une case sûre ensuite?
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        maxactions = gsearch.maxactions
        supactions = maxactions - paObj.gamblecount
        secureissue = False
        if lastcase == case_sortie:
            secureissue = True
        elif supactions > 0:
            # 2.1- Trajet initial à rebourd sur?
            if lastcase not in [None, robot]:
                # si lastcase est sure et que le trajet robot->lastcase est
                # réalisable en supactions coups maximum, on a trouvé une
                # solution de repli possible
                if lastcase in safezone:
                    # reconstitution du targetpath :
                    stepslist = list()
                    for coords in coordspath:
                        c = flatmatrice.get_case(*coords)
                        tps = TargetPathStep(c)
                        stepslist.append(tps)
                    backtp = TargetPath(steplist=stepslist)
                    backcount = self._get_gamble_count_for_TargetPath(robot, backtp)
                    if backcount != None and backcount <= supactions:
                        secureissue = True
            # 2.2- Recherche d'autres cases sures
            if not secureissue:
                # coordonnées du robot :
                refx, refy = int(robot.x), int(robot.y)
                robot.x, robot.y = lastcase.x, lastcase.y
                # une case sûre pourra elle être atteinte?
                limitedsafe = list()
                for c in safezone:
                    d = self._lablevel.get_path_length_between_cases(robot, c)
                    if d <= supactions:
                        limitedsafe.append({"case": c, "dist": d})
                limitedsafe.sort(key=itemgetter("dist"))
                # recherche restreinte aux cases accessibles
                restrictsafe = [cdict["case"] for cdict in limitedsafe]
                for c in restrictsafe:
                    tp = self._search_TargetPath(robot, c)[0]
                    if tp != None:
                        # la première possibilité suffit
                        secureissue = True
                        break
                # rétablissement des coords :
                robot.x, robot.y = refx, refy
        # 3- Dénombrement des bonus :
        listcoords = paObj.get_path_in_pseudoaction_list()
        listcases = [flatmatrice.get_case(x, y) for (x, y) in listcoords]
        listbonus = [c for c in listcases if c.type_case == LabHelper.CASE_BONUS]
        nbbonus = len(listbonus)
        # 4- Mise à jour de l'objet
        paObj.securestop = securestop
        paObj.stoptargets = stoptargets
        paObj.secureissue = secureissue
        paObj.bonuscount = nbbonus
        paObj.defensecount = botdefcount
        paObj.attaquecount = botattcount
        paObj.deltamainpathlen = deltamainpathlen

    def _get_attack_probas_for_move_zone(self, robot):
        """
        Retourne une liste de dicts {"case", "proba":}, triée par proba desc
        des cases de la zone de déplacement du robot avec proba une pseudo
        probabilité d'attaque associée à une case.
        Rq : ces pseudos probas sont aussi approximatives que sous évaluées,
        elles permettent néanmoins d'essayer de minimiser les risques lorsqu'il
        n'y a pas de zone sûre.
        """
        gdSet = robot.get_current_gdSet()
        # 1- Cache ?
        cachedlist = gdSet.get_list_case("prob_dicts")
        if cachedlist != None:
            return cachedlist
        # 2- Calcul des probabilités d'attaque par case de move_zone :
        # - init avec probas nulles
        probdict = dict()
        move_zone = self._lablevel.get_caseset_for_coordset(robot.move_zone)
        for c in move_zone:
            probdict[c] = {"case": c, "proba": 0}
        # - proba max d'attaque par case sur l'ensemble des bots contre lesquels
        # se défendre
        listdef = gdSet.get_list_case("defense_all")
        for b in listdef:
            bprobdict = self._lablevel.evaluate_bot_attack_proba_for_robot(robot, b)
            for c, p in bprobdict.items():
                casedict = probdict[c]
                oldp = casedict["proba"]
                casedict["proba"] = max(p, oldp)
        # - extraction et trie de la liste de dicts {"case":, "proba":}
        listprob = [dv for dv in probdict.values()]
        listprob.sort(key=itemgetter("proba"))
        # - mise en cache
        gdSet.register_list_case("prob_dicts", listprob)
        # retour
        return listprob

    def _evaluate_scheduled_shoot_position(self, robot, case, target, maxactions):
        """
        Evalue si la case peut être une bonne position de tir sur target
        pour le robot disposant de maxactions possibles
        """
        finded = False
        finalTargetPath = None
        attaquepaobj = None
        attaquepa = None
        killedbots = None
        nbgamble = None
        # targetpath :
        tp = self._search_TargetPath(robot, case)[0]
        if tp != None:
            # la case peut être atteinte...
            nbgamble = self._get_gamble_count_for_TargetPath(robot, tp)
            if nbgamble != None and nbgamble < maxactions:
                # ... assez rapidement
                # déplacement du robot à la position de la case
                robot.x, robot.y = case.x, case.y
                # attaque directe :
                finded, attaquepaobj = self._search_scheduled_attaque(
                    robot, targetcase=target, pathsearch=False
                )
                if finded:
                    # on a trouvé une solution
                    attaquepa = attaquepaobj.get_next_pseudoaction()
                    killedbots = attaquepaobj.killedbots
                    finalTargetPath = tp
        # retour
        return finded, finalTargetPath, attaquepa, killedbots, nbgamble

    def _preselect_cases_for_safe_move(self, robot, listcase, dmax=None):
        """
        Retourne une liste de cases de listcase cohérente avec les cibles,
        ou la liste complète par défaut.
        """
        if dmax == None:
            dmax = 100
        # directions ou paths à privilégier?
        targetpathlist = self._get_optimal_listcases_for_move(robot)
        refdirs = None
        maintarget = robot.get_main_target()
        if maintarget != None:
            refdirs = self._get_dirs_to_mainTarget(robot)
        # pré sélection :
        choicedictlist = list()
        preselectlist = list()
        # dans le path
        if targetpathlist != None:
            for c in listcase:
                if c in targetpathlist:
                    dist = math.ceil(
                        self._lablevel.get_distance_between_cases(robot, c)
                    )
                    if dist <= dmax:
                        bonus = int(c in self.bonus_set)
                        choicedict = {
                            "case": c,
                            "dist": dist,
                            "bonus": bonus,
                            "inpath": 1,
                            "indirect": 1,
                        }
                        choicedictlist.append(choicedict)
                    preselectlist.append(c)
        # dans les directions de ref
        if refdirs != None:
            for c in listcase:
                direct = self._get_dir_for_case(robot, c)
                if direct in refdirs and c not in preselectlist:
                    dist = math.ceil(
                        self._lablevel.get_distance_between_cases(robot, c)
                    )
                    if dist <= dmax:
                        bonus = int(c in self.bonus_set)
                        choicedict = {
                            "case": c,
                            "dist": dist,
                            "bonus": bonus,
                            "inpath": 0,
                            "indirect": 1,
                        }
                        choicedictlist.append(choicedict)
                    preselectlist.append(c)
        # liste finale :
        finalchoicedictlist = None
        if len(preselectlist) > 0:
            finalchoicedictlist = choicedictlist
        else:
            finalchoicedictlist = list()
        for c in listcase:
            if c not in preselectlist:
                dist = math.ceil(self._lablevel.get_distance_between_cases(robot, c))
                if dist <= dmax:
                    bonus = int(c in self.bonus_set)
                    choicedict = {
                        "case": c,
                        "dist": dist,
                        "bonus": bonus,
                        "inpath": 0,
                        "indirect": 0,
                    }
                    finalchoicedictlist.append(choicedict)
        return finalchoicedictlist

    def _get_optimal_listcases_for_move(self, robot):
        """
        Retourne une liste de maxactions éléments comprenant :
        
        * les cases du path de Target Temp augmentées de la liste des cases
          suivant la cible
        * les cases du path de la cible principale sinon
        * None par défaut
        
        """
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        maxactions = gsearch.maxactions
        # liste des cases qui devraient constituer la suite du chemin
        listcases = self._get_nextcases_in_path(robot)
        # on tronque listcases pour avoir au max maxactions éléments
        if listcases != None and len(listcases) > maxactions:
            listcases = listcases[:maxactions]
        # retour:
        return listcases

    def _get_nextcases_in_path(self, robot):
        """
        Recherche quelle seront les prochaines cases dans le path des cibles
        """
        listcases = None
        # recherche dans les paths des cibles
        targettp = None
        tempTarget = robot.get_temp_target()
        targettype = None
        if tempTarget != None:
            targettp = tempTarget.targetpath
            targettype = tempTarget.typetarget
        else:
            maintarget = robot.get_main_target()
            if maintarget != None:
                targettp = maintarget.targetpath
                targettype = maintarget.typetarget
        if targettp != None:
            # dans les cases suivant la cible
            targetsteplist = targettp.get_steps_list()
            listcases = [tps.case for tps in targetsteplist]
            listcases = listcases[1:]  # première case = robot
            if targettype == TargetObject.TARGET_TEMP:
                # dans le cas d'une cible principale le chemin complet est déja
                # défini. Dans le cas d'une cible temporaire, le chemin va se
                # poursuivre (à priori) dans les cases suivant la cible.
                targetlistcases = tempTarget.listcases[1:]
                listcases.extend(targetlistcases)
        return listcases

    def _get_gamble_count_for_TargetPath(self, robot, targetpath):
        """
        Compte le nombre de coups nécessaire pour atteindre la dernière case
        du targetpath
        """
        nbgamble = None
        if targetpath != None and len(targetpath.get_steps_list()) > 1:
            tpslist = targetpath.get_steps_list()[1:]
            nbgamble = 0
            for tps in tpslist:
                case = tps.case
                cost = self._get_case_pathcost_for_robot(case, robot)
                if cost == None:
                    return None
                nbgamble += cost
        return nbgamble

    def _get_case_pathcost_for_robot(self, case, robot):
        """
        Retourne le coût pour accéder à la case
        """
        cost = None
        if case.type_case in LabHelper.FAMILLE_CASES_LIBRES:
            cost = 1
        elif robot.has_grenade:
            if case.type_case == LabHelper.CASE_ROBOT:
                # peut on l'éliminer?
                gdSet = robot.get_current_gdSet()
                att_all = gdSet.get_list_case("attaque_all")
                def_all = gdSet.get_list_case("defense_all")
                if case in att_all or case in def_all:
                    cost = 2
            else:
                # case danger : suppression théorique possible
                cost = 2
        return cost

    def _get_pseudoactionlist_for_TargetPath(self, targetpath):
        """
        Convertit le TargetPath en liste de pseudos actions de mouvement
        Rq : la validité de targetpath a été vérifiée au préalable
        """
        pseudoactionlist = list()
        tpslist = targetpath.get_steps_list()[1:]
        for tp in tpslist:
            case = tp.case
            pseudoaction = self._format_move_pseudoaction_for_case(case)
            pseudoactionlist.append(pseudoaction)
        return pseudoactionlist

    def _format_move_pseudoaction_for_case(self, case):
        """
        Génère la pseudo action de déplacement sur la case
        """
        tc = case.type_case
        dgr_impact = 0
        if tc == LabHelper.CASE_DANGER:
            dgr_impact = case.danger_impact
        x, y = int(case.x), int(case.y)
        # pseudo action de déplacement
        pseudoaction = {
            "type": "goto",
            "coords": (x, y),
            "type_case": tc,
            "danger_impact": dgr_impact,
        }
        return pseudoaction

    def _get_defense_targets_for_case(self, robot, case):
        """
        Retrouve dans les bots contre lesquels se défendre, ceux qui menacent
        directement case.
        """
        gdSet = robot.get_current_gdSet()
        def_all = gdSet.get_list_case("defense_all")
        targets = list()
        for b in def_all:
            bot_attaque = self._lablevel.get_caseset_for_coordset(b.attack_zone)
            if case in bot_attaque:
                targets.append(b)
        return targets

    #-----> B.7.5- Application de commandes anticipées
    def _get_cmd_for_next_pseudoaction(self, robot):
        """
        Traduit la prochaine pseudoaction en commande si elle existe ou
        retourne None
        """
        cmd = None
        gdSet = robot.get_current_gdSet()
        flatmatrice = self._lablevel.get_flat_matrice()
        firstadj = gdSet.get_list_case("first_adj")
        bonusadj = gdSet.get_list_case("bonus_adj")
        if bonusadj == None:
            bonusadj = list()
        alladj = gdSet.get_list_case("all_adj")
        safezone = gdSet.get_list_case("safezone")
        nextpa = None
        paobj = gdSet.get_pseudoactions()
        if paobj != None:
            nextpa = paobj.get_next_pseudoaction()
        removepa = False
        if nextpa != None:
            # profondeur de recherche
            fullsearch = False
            recursive = False
            highQI = CaseRobot.get_feature_threshold("intelligence", "high")
            if robot.intelligence >= highQI:
                recursive = True
                if robot.need_bonus:
                    # recherche de toutes les combinaisons de terraformage pour
                    # limiter la destruction de bonus
                    fullsearch = True
            typepa = nextpa["type"]
            if typepa in ["grenade", "kill"]:
                # attaque, cmd déja générée et pré validée
                cmd = nextpa["cmd"]
                removepa = True
            elif typepa in ["goto"]:
                # mouvement :
                # liste des coordonnées du path à suivre :
                listcoords = paobj.get_path_in_pseudoaction_list()
                listcases = [flatmatrice.get_case(x, y) for (x, y) in listcoords]
                # ménage à faire ?
                dellist = list()
                for c in listcases:
                    if c.type_case in [LabHelper.CASE_DANGER, LabHelper.CASE_MUR]:
                        dellist.append(c)
                if len(dellist) > 0:
                    cmd = self._search_cmd_in_terraform_list(
                        robot, dellist, recursive=recursive, fullsearch=fullsearch
                    )
                    cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                if cmd == None:
                    x, y = nextpa["coords"]
                    case = flatmatrice.get_case(x, y)
                    actiondict = None
                    doremove = False
                    if case.type_case in LabHelper.FAMILLE_CASES_LIBRES:
                        actiondict = {"action": LabHelper.ACTION_MOVE, "code": ""}
                        doremove = True
                    elif case.type_case == LabHelper.CASE_MUR:
                        actiondict = {
                            "action": LabHelper.ACTION_CREATE_DOOR,
                            "code": LabHelper.CHAR_PORTE,
                        }
                    # Rq : inutile de vérifier que l'action est sûre si l'on
                    # transite par une case hors safezone (handlebehavior=False)
                    if actiondict != None:
                        cmd = self._evaluate_simple_action(
                            robot, actiondict, case, handlebehavior=False
                        )
                        cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                    if cmd != None:
                        removepa = doremove
            elif typepa == "nomove":
                # actions à priori statiques
                sup_gdcount = gdSet.gamblecount - gdSet.gamblenumber
                if sup_gdcount == 0:
                    # dernière action du tour, un mouvement sur et pertinent
                    # est il possible?
                    moveset = set(bonusadj).union(set(firstadj))
                    safeset = moveset.intersection(set(safezone))
                    listcases = [
                        c for c in safeset if c in LabHelper.FAMILLE_CASES_LIBRES
                    ]
                    if len(listcases) > 0:
                        actiondict = {"action": LabHelper.ACTION_MOVE, "code": ""}
                        cmd = self._evaluate_simple_action(
                            robot, actiondict, listcases[0], handlebehavior=True
                        )
                        cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                if cmd == None:
                    # ménage anticipé?
                    listcases = self._get_nextcases_in_path(robot)
                    if listcases != None:
                        dellist = list()
                        for c in listcases:
                            if c.type_case in [
                                LabHelper.CASE_DANGER,
                                LabHelper.CASE_MUR,
                            ]:
                                dellist.append(c)
                        if len(dellist) > 0:
                            cmd = self._search_cmd_in_terraform_list(
                                robot,
                                dellist,
                                recursive=recursive,
                                fullsearch=fullsearch,
                            )
                            cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                            if cmd != None and sup_gdcount == 0:
                                # on modifie le type de l'objet :
                                # cf identification des actions stay in place
                                # répétées.
                                paobj.name = CommandManager.PA_TERRAFORM
                                # on ré initialise le compteur de ces actions
                                robot.no_move_count = 0
                if cmd == None:
                    # moins utile : porte, mur
                    for actiontype in ["door", "wall"]:
                        if actiontype == "door":
                            searchlist = alladj
                        else:
                            searchlist = [c for c in alladj if c not in firstadj]
                        cmd = self._search_cmd_by_action_in_list(
                            robot, searchlist, actiontype
                        )
                        cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                        if cmd != None:
                            break
            elif typepa in ["minemax", "wall"]:
                # mine, mur :
                searchlist = [c for c in alladj if c not in firstadj]
                cmd = self._search_cmd_by_action_in_list(robot, searchlist, typepa)
                cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                if cmd != None:
                    removepa = True
            # dépilement de la pseudo action?
            if removepa:
                paobj.remove_pseudoaction_from_list(nextpa)
        return cmd

    def _search_cmd_by_action_in_list(self, robot, listcase, actiontype):
        """
        Recherche dans la liste de cases la première pouvant faire l'objet
        de l'action actiontype
        """
        cmd = None
        # familles de cases adaptées :
        famille = None
        if actiontype == "minemax":
            famille = LabHelper.FAMILLE_MINE
        elif actiontype == "wall":
            famille = LabHelper.FAMILLE_BUILD_WALL
        elif actiontype == "door":
            famille = LabHelper.FAMILLE_BUILD_DOOR
        if famille != None:
            # recherche de la première case adaptée
            actioncase = None
            for c in listcase:
                if c.type_case in famille:
                    actioncase = c
                    break
            # si la case existe :
            if actioncase != None:
                actiondict = None
                if actiontype == "minemax":
                    actiondict = {
                        "action": LabHelper.ACTION_MINE,
                        "code": LabHelper.CHAR_MINE,
                    }
                elif actiontype == "wall":
                    actiondict = {
                        "action": LabHelper.ACTION_CREATE_WALL,
                        "code": LabHelper.CHAR_MUR,
                    }
                elif actiontype == "door":
                    actiondict = {
                        "action": LabHelper.ACTION_CREATE_DOOR,
                        "code": LabHelper.CHAR_PORTE,
                    }
                if actiondict != None:
                    cmd = self._evaluate_simple_action(robot, actiondict, actioncase)
        return cmd

    #-----> B.8- Recherche du prochain coup
    def _search_next_command(self, robot):
        """
        Choisit une commande une fois la cible temporaire mise à jour et les données évaluées
        """
        # seuils
        midAGG = CaseRobot.get_feature_threshold("aggressivite", "middle")
        # Objectifs généraux et actions associées (valuées en termes de violence)
        objectifs = dict()
        objectifs[CommandManager.OBJ_MOVE] = [
            {"action": LabHelper.ACTION_MOVE, "code": "", "violence": 0},
            {
                "action": LabHelper.ACTION_CREATE_DOOR,
                "code": LabHelper.CHAR_PORTE,
                "violence": 0,
            },
        ]
        objectifs[CommandManager.OBJ_DEFENSE] = [
            {
                "action": LabHelper.ACTION_GRENADE,
                "code": LabHelper.CHAR_GRENADE,
                "violence": 3,
            },
            {
                "action": LabHelper.ACTION_MINE,
                "code": LabHelper.CHAR_MINE,
                "violence": 1,
            },
            {
                "action": LabHelper.ACTION_KILL,
                "code": LabHelper.CHAR_KILL,
                "violence": 2,
            },
            {"action": LabHelper.ACTION_MOVE, "code": "", "violence": 0},
            {
                "action": LabHelper.ACTION_CREATE_WALL,
                "code": LabHelper.CHAR_MUR,
                "violence": 0,
            },
        ]
        objectifs[CommandManager.OBJ_ATTACK] = [
            {
                "action": LabHelper.ACTION_GRENADE,
                "code": LabHelper.CHAR_GRENADE,
                "violence": 3,
            },
            {
                "action": LabHelper.ACTION_KILL,
                "code": LabHelper.CHAR_KILL,
                "violence": 2,
            },
        ]
        # 1- Priorisation des objectifs :
        orderedobjectifs = self._define_direct_ordered_objectifs(robot)
        # 2- Traduction des objectifs en actions :
        bot_objectif = list()
        for motclef in orderedobjectifs:
            if motclef == CommandManager.OBJ_MOVE:
                mouv_list = objectifs[CommandManager.OBJ_MOVE]
                bot_objectif.append((CommandManager.OBJ_MOVE, mouv_list))
            elif motclef == CommandManager.OBJ_ATTACK:
                att_list = sorted(
                    objectifs[CommandManager.OBJ_ATTACK],
                    key=itemgetter("violence"),
                    reverse=robot.aggressivite >= midAGG,
                )
                bot_objectif.append((CommandManager.OBJ_ATTACK, att_list))
            elif motclef == CommandManager.OBJ_DEFENSE:
                def_list = sorted(
                    objectifs[CommandManager.OBJ_DEFENSE],
                    key=itemgetter("violence"),
                    reverse=robot.aggressivite >= midAGG,
                )
                bot_objectif.append((CommandManager.OBJ_DEFENSE, def_list))
            elif motclef == CommandManager.OBJ_WORK:
                if robot.behavior == CaseRobot.BEHAVIOR_SAPPER:
                    # travail = pose de mine
                    bot_objectif.append(
                        (
                            CommandManager.OBJ_WORK,
                            [
                                {
                                    "action": LabHelper.ACTION_MINE,
                                    "code": LabHelper.CHAR_MINE,
                                    "violence": 1,
                                }
                            ],
                        )
                    )
                elif robot.behavior == CaseRobot.BEHAVIOR_BUILDER:
                    # travail = construction de mur
                    bot_objectif.append(
                        (
                            CommandManager.OBJ_WORK,
                            [
                                {
                                    "action": LabHelper.ACTION_CREATE_WALL,
                                    "code": LabHelper.CHAR_MUR,
                                    "violence": 0,
                                }
                            ],
                        )
                    )
            elif motclef == CommandManager.OBJ_RANDOM:
                # hasard = mur, porte, mine, grenade
                list_rand = [
                    {
                        "action": LabHelper.ACTION_CREATE_WALL,
                        "code": LabHelper.CHAR_MUR,
                    },
                    {
                        "action": LabHelper.ACTION_CREATE_DOOR,
                        "code": LabHelper.CHAR_PORTE,
                    },
                    {"action": LabHelper.ACTION_MINE, "code": LabHelper.CHAR_MINE},
                    {
                        "action": LabHelper.ACTION_GRENADE,
                        "code": LabHelper.CHAR_GRENADE,
                    },
                ]
                cr.CustomRandom.shuffle(list_rand)
                bot_objectif.append((CommandManager.OBJ_RANDOM, list_rand))
        # 3- Recherche de commande :
        cmd = None
        for item in bot_objectif:
            objectif, actionlist = item[0], item[1]
            if objectif == CommandManager.OBJ_ATTACK and cmd == None:
                cmd = self._search_next_command_attack(robot, actionlist)
            elif objectif == CommandManager.OBJ_DEFENSE and cmd == None:
                cmd = self._search_next_command_defense(robot, actionlist)
            elif objectif == CommandManager.OBJ_MOVE and cmd == None:
                cmd = self._search_next_command_move(robot, actionlist)
            elif objectif == CommandManager.OBJ_WORK and cmd == None:
                cmd = self._search_next_command_work(robot, actionlist)
            elif objectif == CommandManager.OBJ_RANDOM and cmd == None:
                cmd = self._search_next_command_random(robot, actionlist)
            if cmd != None:
                break
        # retour :
        return cmd

    def _define_direct_ordered_objectifs(self, robot):
        """
        Retourne une liste d'objectifs priorisés pour le prochain coup à jouer.
        Méthode dédiée à tous les comportements.
        """
        orderedobjectifs = list()
        # paramètres
        gdSet = robot.get_current_gdSet()
        listdefense = gdSet.get_list_case("defense")
        # caractéristiques du robot
        behavior = robot.behavior
        instinct_survie = robot.instinct_survie
        aggressivite = robot.aggressivite
        ambition = robot.ambition
        intelligence = robot.intelligence
        # seuils
        midSUR = CaseRobot.get_feature_threshold("instinct_survie", "middle")
        highSUR = CaseRobot.get_feature_threshold("instinct_survie", "high")
        midAGG = CaseRobot.get_feature_threshold("aggressivite", "middle")
        highAGG = CaseRobot.get_feature_threshold("aggressivite", "high")
        # 1- auto défense :
        if len(listdefense) > 0 and (
            instinct_survie >= highSUR
            or (
                instinct_survie >= midSUR
                and (instinct_survie + intelligence) > (aggressivite + ambition)
            )
        ):
            orderedobjectifs.append(CommandManager.OBJ_DEFENSE)
        # 2- en fonction du comportement :
        if behavior == CaseRobot.BEHAVIOR_WINNER:
            advdict = gdSet.get_adversaires_avance()
            if advdict["adv_in_final"] or advdict["adv_in_approach"]:
                # des adversaires peuvent gagner !
                orderedobjectifs.append(CommandManager.OBJ_ATTACK)
                orderedobjectifs.append(CommandManager.OBJ_MOVE)
            else:
                # Priorité au mouvement
                orderedobjectifs.append(CommandManager.OBJ_MOVE)
        elif behavior == CaseRobot.BEHAVIOR_HUNTER:
            maintarget = robot.get_main_target()
            cond_att = aggressivite >= highAGG
            if (
                maintarget != None and maintarget.case in gdSet.get_list_case("attaque")
            ) or cond_att:
                # Priorité à l'attaque
                orderedobjectifs.append(CommandManager.OBJ_ATTACK)
                orderedobjectifs.append(CommandManager.OBJ_MOVE)
            else:
                # Priorité au mouvement
                orderedobjectifs.append(CommandManager.OBJ_MOVE)
                orderedobjectifs.append(CommandManager.OBJ_ATTACK)
        elif robot.behavior in [CaseRobot.BEHAVIOR_SAPPER, CaseRobot.BEHAVIOR_BUILDER]:
            # mouvement et "travail" alternés:
            if behavior == CaseRobot.BEHAVIOR_SAPPER:
                work_action = LabHelper.ACTION_MINE
            else:
                work_action = LabHelper.ACTION_CREATE_WALL
            # en fonction du ratio :
            nextaction = "move"
            wmratio = robot.get_work_ratio()  # fraction travail/mouvement
            if wmratio > 1:
                # travail dès que possible (sauf dans le targetpath)
                listothers = gdSet.get_list_case("other_adj")
                if listothers == None:
                    listothers = list()
                freeadj = [
                    c for c in listothers if c.type_case in LabHelper.FAMILLE_BUILD_WALL
                ]
                if len(freeadj) > 0:
                    nextaction = "work"
            else:
                # en fonction des dernières actions effectuées :
                actionlist = robot.get_action_list()
                wmratio_num = wmratio.numerator
                wmratio_den = wmratio.denominator
                if len(actionlist) < wmratio_den:
                    # par alternance au début
                    lastaction = None
                    if len(actionlist) > 0:
                        lastaction = actionlist[len(actionlist) - 1]
                    if lastaction == LabHelper.ACTION_MOVE:
                        nextaction = "work"
                else:
                    # par ratio ensuite
                    lastactions = actionlist[-wmratio_den:]
                    lastwork = [a for a in lastactions if a == work_action]
                    nbwork = len(lastwork)
                    if nbwork < wmratio_num:
                        nextaction = "work"
            # priorisation
            if nextaction == "work":
                orderedobjectifs.append(CommandManager.OBJ_WORK)
                orderedobjectifs.append(CommandManager.OBJ_MOVE)
            else:
                orderedobjectifs.append(CommandManager.OBJ_MOVE)
                orderedobjectifs.append(CommandManager.OBJ_WORK)
        elif robot.behavior == CaseRobot.BEHAVIOR_TOURIST:
            # Mouvement seul :
            orderedobjectifs = [CommandManager.OBJ_MOVE]
        elif robot.behavior == CaseRobot.BEHAVIOR_RANDOM:
            # random
            orderedobjectifs.append(CommandManager.OBJ_MOVE)
            orderedobjectifs.append(CommandManager.OBJ_RANDOM)
        # 3- objectif oublié?
        if behavior != CaseRobot.BEHAVIOR_TOURIST:
            if (
                CommandManager.OBJ_ATTACK not in orderedobjectifs
                and aggressivite >= midAGG
            ):
                orderedobjectifs.append(CommandManager.OBJ_ATTACK)
            if (
                CommandManager.OBJ_DEFENSE not in orderedobjectifs
                and instinct_survie >= midSUR
                and len(listdefense) > 0
            ):
                orderedobjectifs.append(CommandManager.OBJ_DEFENSE)
        if behavior == CaseRobot.BEHAVIOR_RANDOM:
            cr.CustomRandom.shuffle(orderedobjectifs)
        # retour
        return orderedobjectifs

    def _search_next_command_attack(self, robot, actionlist):
        """
        Evalue les possibilités immédiates d'attaque
        """
        cmd = None
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        # cibles de l'attaque
        listbots = None
        # profondeur de recherche
        recursive = False
        highQI = CaseRobot.get_feature_threshold("intelligence", "high")
        if robot.intelligence >= highQI:
            recursive = True
        # cas particuliers :
        if robot.behavior == CaseRobot.BEHAVIOR_WINNER:
            # des adversaires en avance?
            dictadv = gdSet.get_adversaires_avance()
            listadv = list()
            if dictadv["adv_in_final"]:
                listadv.extend(dictadv["final_list"])
            if dictadv["adv_in_approach"]:
                listadv.extend(dictadv["approach_list"])
            if len(listadv) > 0:
                listbots = listadv
        elif robot.behavior == CaseRobot.BEHAVIOR_HUNTER:
            maintarget = robot.get_main_target()
            if maintarget != None:
                if maintarget.case in gdSet.get_list_case("attaque"):
                    listbots = [maintarget.case]
        # par défaut :
        if listbots == None:
            listbots = gdSet.get_list_case("attaque")
        # filtrage des coups déja analysés :
        filteratt = [b for b in listbots if not gsearch.kill_search_already_done(b)]
        # Recherche de commandes :
        if len(filteratt) > 0:
            for actdict in actionlist:
                for bot in filteratt:
                    if actdict["action"] == LabHelper.ACTION_GRENADE:
                        # cas complexe : grenade
                        cmd = self._evaluate_complex_action(
                            robot, LabHelper.ACTION_GRENADE, bot, recursive=recursive
                        )
                        cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                        # mémorisation de la recherche
                        gsearch.register_kill_search(bot)
                        if cmd != None:
                            break
                    else:
                        # cas général simple (kill)
                        cmd = self._evaluate_simple_action(robot, actdict, bot)
                        cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                        if cmd != None:
                            break
                if cmd != None:
                    break
        return cmd

    def _search_next_command_defense(self, robot, actionlist):
        """
        Evalue les possibilités immédiates de défense
        """
        cmd = None
        gdSet = robot.get_current_gdSet()
        gsearch = gdSet.gamblesearch
        # profondeur de recherche
        recursive = False
        highQI = CaseRobot.get_feature_threshold("intelligence", "high")
        if robot.intelligence >= highQI:
            recursive = True
        # 1- robots
        listbots = gdSet.get_list_case("defense")
        # filtrage des coups déja analysés :
        filterdef = [b for b in listbots if not gsearch.kill_search_already_done(b)]
        if len(filterdef) > 0:
            for actdict in actionlist:
                for bot in filterdef:
                    if actdict["action"] == LabHelper.ACTION_GRENADE:
                        # cas complexe : grenade
                        cmd = self._evaluate_complex_action(
                            robot, LabHelper.ACTION_GRENADE, bot, recursive=recursive
                        )
                        cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                        # mémorisation de la recherche
                        gsearch.register_kill_search(bot)
                        if cmd != None:
                            break
                    else:
                        # cas général simple (kill, move, mine...)
                        cmd = self._evaluate_simple_action(robot, actdict, bot)
                        cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                        if cmd != None:
                            break
                if cmd != None:
                    break
        # 2- dangers
        listdgrs = gdSet.get_list_case("dangers")
        if len(listdgrs) > 0 and cmd == None:
            for actdict in actionlist:
                for case in listdgrs:
                    if actdict["action"] == LabHelper.ACTION_GRENADE:
                        cmd = self._evaluate_complex_action(
                            robot, LabHelper.ACTION_GRENADE, case, recursive=recursive
                        )
                        cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                        if cmd != None:
                            break
                    else:
                        cmd = self._evaluate_simple_action(robot, actdict, case)
                        cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                        if cmd != None:
                            break
                if cmd != None:
                    break
        return cmd

    def _search_next_command_work(self, robot, actionlist):
        """
        Evalue les possibilités de réaliser des commandes particulières hors contexe
        de défense, attaque, mouvement : pour les sappers, builders et random
        """
        cmd = None
        # afin de ne pas bloquer sa progression, on effectue le travail de
        # préférence sur la dernière case passée ou sur les "other_adj":
        listadj = list()
        prevcoords = robot.get_prev_coords()
        prevupdated = None
        if prevcoords != None:
            x, y = prevcoords[0], prevcoords[1]
            flatmatrice = self._lablevel.get_flat_matrice()
            prevupdated = flatmatrice.get_case(x, y)
            listadj.append(prevupdated)
        gdSet = robot.get_current_gdSet()
        listothers = gdSet.get_list_case("other_adj")
        if listothers != None:
            listadj.extend(listothers)
        for case in listadj:
            for actdict in actionlist:
                cmd = self._evaluate_simple_action(robot, actdict, case)
                cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                if cmd != None:
                    break
            if cmd != None:
                break
        return cmd

    def _search_next_command_move(self, robot, actionlist):
        """
        Evalue les opportunités de mouvement
        """
        cmd = None
        gdSet = robot.get_current_gdSet()
        # Les listes contenant les 4 options adjacentes
        firstlist = gdSet.get_list_case("first_adj")
        bonuslist = gdSet.get_list_case("bonus_adj")
        otherlist = gdSet.get_list_case("other_adj")
        # 1- Cas particulier d'un bonus à prendre :
        case = ""
        if robot.need_bonus:
            case = "need_bonus"
            case_bonus = None
            if firstlist != None:
                for c in firstlist:
                    if c.type_case == LabHelper.CASE_BONUS:
                        case_bonus = c
                        break
            if case_bonus == None and bonuslist != None:
                case_bonus = bonuslist[0]
            if case_bonus != None:
                actdict = {"action": LabHelper.ACTION_MOVE, "code": "", "violence": 0}
                cmd = self._evaluate_simple_action(robot, actdict, case_bonus)
                cmd = self._pre_check_or_nullify_cmd(cmd, robot)
        # 2- Cas général :
        # doit on faire le ménage?
        if cmd == None:
            case = "terraform"
            cmd = self._terraform_to_move(robot)
            cmd = self._pre_check_or_nullify_cmd(cmd, robot)
        # recherche dans la liste principale, les bonus puis la liste secondaire :
        if firstlist != None and cmd == None:
            case = "firstlist"
            # peut on bouger sur une des cases prioritaires?
            for case in firstlist:
                for actdict in actionlist:
                    cmd = self._evaluate_simple_action(robot, actdict, case)
                    cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                    if cmd != None:
                        break
                if cmd != None:
                    break
            # peut-on faire le ménage?
            if cmd == None and robot.has_grenade:
                for case in firstlist:
                    if type(case) == CaseDanger and case.danger_impact <= 1:
                        cmd = self._evaluate_complex_action(
                            robot, LabHelper.ACTION_GRENADE, case
                        )
                        cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                        if cmd != None:
                            break
        if bonuslist != None and cmd == None:
            case = "bonuslist"
            for case in bonuslist:
                actdict = {"action": LabHelper.ACTION_MOVE, "code": ""}
                cmd = self._evaluate_simple_action(robot, actdict, case)
                cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                if cmd != None:
                    break
        if otherlist != None and cmd == None:
            case = "otherlist"
            for case in otherlist:
                for actdict in actionlist:
                    if actdict["action"] == LabHelper.ACTION_GRENADE:
                        cmd = self._evaluate_complex_action(
                            robot, LabHelper.ACTION_GRENADE, case
                        )
                        cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                        if cmd != None:
                            break
                    else:
                        cmd = self._evaluate_simple_action(robot, actdict, case)
                        cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                        if cmd != None:
                            break
                if cmd != None:
                    break
        # retour
        if cmd == None:
            case = "None"
        return cmd

    def _search_next_command_random(self, robot, actionlist):
        """
        Commande aléatoire
        """
        cmd = None
        gdSet = robot.get_current_gdSet()
        listadj = gdSet.get_list_case("all_adj")
        # recherche :
        for actdict in actionlist:
            action = actdict["action"]
            if action == LabHelper.ACTION_GRENADE:
                cmd = self._random_launch_grenade(robot)
                cmd = self._pre_check_or_nullify_cmd(cmd, robot)
            else:
                for case in listadj:
                    cmd = self._evaluate_simple_action(robot, actdict, case)
                    cmd = self._pre_check_or_nullify_cmd(cmd, robot)
                    if cmd != None:
                        break
            if cmd != None:
                break
        # retour :
        return cmd

    #-----> B.9- Outils communs aux recherches de commande
    def _terraform_to_move(self, robot):
        """
        Etudie l'opportunité de faire le ménage avant de bouger
        Retour : cmd ou None
        """
        # Condition préalable :
        midEFF = CaseRobot.get_feature_threshold("efficacite", "middle")
        if robot.efficacite < midEFF:
            return None
        # profondeur de recherche
        fullsearch = False
        recursive = False
        highQI = CaseRobot.get_feature_threshold("intelligence", "high")
        if robot.intelligence >= highQI:
            recursive = True
            if robot.need_bonus:
                # recherche de toutes les combinaisons de terraformage pour
                # limiter la destruction de bonus
                fullsearch = True
        # Traitement
        cmd = None
        # 1- Cas particulier de l'approche de la sortie :
        if robot.behavior in [
            CaseRobot.BEHAVIOR_WINNER,
            CaseRobot.BEHAVIOR_HUNTER,
        ] and robot.game_phasis in [
            CommandManager.PHASIS_APPROACH,
            CommandManager.PHASIS_FINAL,
        ]:
            # Des dangers bloquent ils la sortie ?
            dgrnearsortie = self._do_dangers_block_sortie(robot)
            if len(dgrnearsortie) > 0:
                # recherche poussée :
                cmd = self._search_cmd_in_terraform_list(
                    robot,
                    dgrnearsortie,
                    recursive=recursive,
                    fullsearch=fullsearch,
                    fardangeronly=True,
                )
        # 2- Recherche dans le targetpath :
        worktarget = None
        temptarget = robot.get_temp_target()
        mainTarget = robot.get_main_target()
        if temptarget != None:
            worktarget = temptarget
        elif mainTarget != None:
            worktarget = mainTarget
        if cmd == None and worktarget != None:
            targetpath = worktarget.targetpath
            if targetpath != None:
                ontheline = (
                    worktarget.axe == LabHelper.AXIS_X and robot.y == worktarget.y
                ) or (worktarget.axe == LabHelper.AXIS_Y and robot.x == worktarget.x)
                if not ontheline:
                    # nettoyage du chemin vers la cible
                    stepslist = worktarget.targetpath.get_steps_list()
                    pathlist = [
                        tps.case
                        for tps in stepslist
                        if tps.case != robot
                        and tps.case.type_case
                        in [LabHelper.CASE_MUR, LabHelper.CASE_DANGER]
                    ]
                    if len(pathlist) > 0:
                        cmd = self._search_cmd_in_terraform_list(
                            robot, pathlist, recursive=recursive, fullsearch=fullsearch
                        )
        # 3- Recherche dans la direction de la cible si elle est principale
        if cmd == None:
            maindirs = self._get_dirs_to_mainTarget(robot)
            if worktarget != None and worktarget.direct in maindirs:
                direct = worktarget.direct
                nextcases = self._get_next_cases_in_dir(robot, direct)
                directlist = [
                    c for c in nextcases if c.type_case == LabHelper.CASE_DANGER
                ]
                if len(directlist) > 0:
                    cmd = self._search_cmd_in_terraform_list(
                        robot,
                        directlist,
                        recursive=recursive,
                        fullsearch=fullsearch,
                        fardangeronly=True,
                    )
        # Retour :
        return cmd

    def _search_cmd_in_terraform_list(
        self,
        robot,
        listcases,
        fardangeronly=False,
        recursive=False,
        safemode=True,
        fullsearch=False,
        allowcollatdamage=False,
        directonly=False,
    ):

        """
        Recherche des cases murs ou dangers à éliminer en priorité dans
        la liste.
        
        * listcases : liste de cases mur ou danger
        * recursive : recherche l'intégralité des combinaisons (récursion comprise)
        * safemode : respect ou non de l'instinct de survie du robot
        * fullsearch : recherche l'ensemble des combinaisons simples (non récursives par défaut)
        * allowcollatdamage : similaire à safemode, pour surcharger l'empathie
          du bot et permettre des dégâts collatéraux
        * directonly : limite la recherche aux coups directs
        
        Retourne une cmd ou None
        """
        cmd = None
        botradius = robot.get_danger_radius()
        maxdist = 8 * robot.efficacite  # distance maxi considérée
        # Liste de dicts {"case":, "distance":, "impact":}
        dictlist = list()
        for c in listcases:
            d = self._lablevel.get_distance_between_cases(robot, c)
            i = 0
            if c.type_case == LabHelper.CASE_DANGER:
                i = c.get_danger_radius()
            if d <= min(botradius, maxdist):
                dictlist.append({"case": c, "distance": d, "impact": i})
        dictlist.sort(key=itemgetter("distance"))
        # 1- Cases proches ralentissant le robot :
        nearfactor = 3
        if not fardangeronly:
            neardictlist = [
                cdict for cdict in dictlist if cdict["distance"] <= nearfactor
            ]
            if len(neardictlist) == 1:
                # recherche rapide :
                cible = neardictlist[0]["case"]
                cmd = self._evaluate_complex_action(
                    robot,
                    LabHelper.ACTION_GRENADE,
                    cible,
                    recursive=recursive,
                    safemode=safemode,
                    fullsearch=fullsearch,
                    allowcollatdamage=allowcollatdamage,
                    directonly=directonly,
                )
            elif len(neardictlist) > 1:
                # recherche plus poussée :
                # directions associées :
                listdirect = list()
                for cdict in neardictlist:
                    direct = self._get_dir_for_case(robot, cdict["case"])
                    if direct not in listdirect:
                        listdirect.append(direct)
                # évaluation des directions :
                evaldirectlist = list()
                for direct in listdirect:
                    # toutes les cases pouvant être atteintes (certaines combinaisons
                    # associées peuvent être fatales au robot)
                    casesimpactees = self._lablevel.get_cases_reachable_by_grenade_in_dir(
                        robot, direct
                    )
                    nb = 0
                    for cdict in neardictlist:
                        if cdict["case"] in casesimpactees:
                            nb += 1
                    evaldirectlist.append({"direct": direct, "count": nb})
                # choix de la meilleure direction :
                evaldirectlist.sort(key=itemgetter("count"), reverse=True)
                bestdirect = evaldirectlist[0]["direct"]
                # choix d'une cible (distance = moitié du rayon d'action du robot)
                pas = botradius // 2
                cible = None
                while pas > 0:
                    cible = self._get_case_for_dir_and_pas(robot, bestdirect, pas)
                    if cible == None:
                        pas -= 1
                    else:
                        break
                if cible != None:
                    cmd = self._evaluate_complex_action(
                        robot,
                        LabHelper.ACTION_GRENADE,
                        cible,
                        recursive=recursive,
                        safemode=safemode,
                        fullsearch=fullsearch,
                        allowcollatdamage=allowcollatdamage,
                        directonly=directonly,
                    )
                    # la commande a t'elle du sens?
                    params = self._get_params_for_grenade(robot, cible)
                    if params != None:
                        casesimpactees = params["default"]["cases_impactees"]
                        nb = 0
                        for cdict in neardictlist:
                            if cdict["case"] in casesimpactees:
                                nb += 1
                        if nb == 0:
                            cmd = None
        # 2- Dangers éloignés pouvant libérer de l'espace pour les coups prochains :
        if cmd == None or fardangeronly:
            dgrdictlist = list()
            for cdict in dictlist:
                if cdict["distance"] > nearfactor and cdict["impact"] > 1:
                    dgrdictlist.append(cdict)
            if len(dgrdictlist) > 0:
                # on commence par le danger le plus puissant :
                dgrdictlist.sort(key=itemgetter("impact"))
                for dgrdict in dgrdictlist:
                    cible = dgrdict["case"]
                    cmd = self._evaluate_complex_action(
                        robot,
                        LabHelper.ACTION_GRENADE,
                        cible,
                        recursive=recursive,
                        safemode=safemode,
                        fullsearch=fullsearch,
                        allowcollatdamage=allowcollatdamage,
                        directonly=directonly,
                    )
                    if cmd != None:
                        break
        # Retour :
        return cmd

    def _do_dangers_block_sortie(self, robot):
        """
        Retourne la liste des cases dangers à proximité de la sortie, triées
        par distance croissante à la sortie
        critère : distance <= CommandManager.DIST_APPROACH
        """
        # données carto
        case_sortie = self._lablevel.get_case_sortie()
        dist_bot_sortie = self._lablevel.get_distance_between_cases(robot, case_sortie)
        list_dgrs = self.dangers_set_plus1
        # réduction de la liste :
        dfunc = lambda c: self._lablevel.get_distance_between_cases(c, case_sortie)
        fulllist = [(dgr, dfunc(dgr)) for dgr in list_dgrs]
        dist_max = min(dist_bot_sortie, CommandManager.DIST_APPROACH)
        redlist = [t for t in fulllist if t[1] < dist_max]
        redlist.sort(key=itemgetter(1))
        result = [t[0] for t in redlist]
        return result

    def _evaluate_simple_action(self, robot, actiondict, case, handlebehavior=True):
        """
        Retourne la commande si l'action est possible et conforme au comportement
        du robot (si handlebehavior=True), None sinon.
        Prend en charge toutes les actions sur des cases adjacentes.
        """
        cmd = None
        possible = self._possible_todo_ACTION_on_case(case, actiondict["action"], robot)
        conform = True
        if handlebehavior and possible:
            conform = self._simple_action_conform_to_behavior(
                robot, case, actiondict["action"]
            )
        if possible and conform:
            action = actiondict["code"]
            direction = self._get_dir_cmd_for_case(robot, case)
            if action != None and direction != None:
                cmd = action + direction
            if actiondict["action"] == LabHelper.ACTION_MINE:
                puissance = self._get_puissance_mine_for_bot(robot)
                cmd += str(puissance)
        return cmd

    def _get_puissance_mine_for_bot(self, robot):
        """
        Retourne une puissance de mine
        """
        puissance = None
        list_puissance = robot.get_puissance_list("mine")
        midAGG = CaseRobot.get_feature_threshold("aggressivite", "middle")
        midEFF = CaseRobot.get_feature_threshold("efficacite", "middle")
        cond_puissance = robot.aggressivite >= midAGG or robot.efficacite >= midEFF
        if cond_puissance:
            # max
            puissance = max(list_puissance)
        else:
            # aléatoire
            puissance = cr.CustomRandom.choice(list_puissance)
        return puissance

    def _evaluate_complex_action(
        self,
        robot,
        action,
        case,
        recursive=False,
        safemode=True,
        fullsearch=False,
        allowcollatdamage=False,
        directonly=False,
    ):
        """
        Retourne la commande si l'action est possible et conforme au comportement du robot,
        None sinon.
        
        * recursive : recherche l'intégralité des combinaisons (récursion comprise)
        * safemode : respect ou non de l'instinct de survie du robot
        * fullsearch : recherche l'ensemble des combinaisons simples (non récursives par défaut)
        * allowcollatdamage : similaire à safemode, pour surcharger l'empathie
          du bot et permettre des dégâts collatéraux
        * directonly : limite la recherche aux coups directs
        
        Prend en charge des actions complexes (ACTION_GRENADE à ce jour)
        """
        if action != LabHelper.ACTION_GRENADE:
            return None
        cmd = None
        params = self._get_params_for_grenade(
            robot,
            case,
            recursive=recursive,
            safemode=safemode,
            fullsearch=fullsearch,
            allowcollatdamage=allowcollatdamage,
            directonly=directonly,
        )
        if params != None:
            defaultcomb = params["default"]
            cmd = self._get_cmd_from_grenade_combinaison(robot, defaultcomb)
        return cmd

    def _get_cmd_from_grenade_combinaison(self, robot, combinaison):
        """
        Retoune une cmd formatée à partir de combinaison, dict de la forme
        {"cible":, "portee":, "puissance":}
        """
        cmd = None
        action = LabHelper.CHAR_GRENADE
        direction = self._get_dir_cmd_for_case(robot, combinaison["cible"])
        try:
            cmd = (
                action
                + direction
                + str(combinaison["portee"])
                + "-"
                + str(combinaison["puissance"])
            )
        except Exception as e:
            raise (e)
        return cmd

    def _simple_action_conform_to_behavior(
        self, robot, case, action, danger_impact=None
    ):
        """
        Indique si l'action est cohérente avec le comportement du robot
        actionargs = {"action":, "case":, "danger_impact":}
        Ne prend en charge que les actions simples, pour les jets de grenade
        la conformité est vérifiée dans les méthodes dédiées.
        """
        gdSet = robot.get_current_gdSet()
        drc = self._lablevel.get_distance_between_cases(robot, case)
        # l'action est-elle fatale, conforme?
        dodie = False
        maydie = False
        conform = True
        if action in [
            LabHelper.ACTION_MOVE,
            LabHelper.ACTION_CREATE_WALL,
            LabHelper.ACTION_CREATE_DOOR,
        ]:
            if type(case) == CaseDanger:
                dodie = True
            if action == LabHelper.ACTION_MOVE:
                safelist = gdSet.get_list_case("safe_adj")
                if case not in safelist:
                    maydie = True
        elif action == LabHelper.ACTION_KILL:
            if case.type_case == CaseRobot:
                kill_all = gdSet.get_list_case("kill_all")
                if not case in kill_all:
                    conform = False
        elif action == LabHelper.ACTION_MINE:
            if danger_impact == None:
                danger_impact = self._get_puissance_mine_for_bot(robot)
            if type(case) == CaseDanger:
                radius_case = case.get_danger_radius()
                if radius_case > drc or danger_impact > drc:
                    dodie = True
        # en fonction du comportement:
        midSUR = CaseRobot.get_feature_threshold("instinct_survie", "middle")
        highSUR = CaseRobot.get_feature_threshold("instinct_survie", "high")
        if robot.instinct_survie >= midSUR and dodie:
            conform = False
        elif robot.instinct_survie >= highSUR and maydie:
            conform = False
        return conform

    def _random_launch_grenade(self, robot):
        """
        Lancer de gernade au hasard (cohérent avec le facteur de danger du robot)
        """
        if not robot.has_grenade:
            return None
        # paramètres
        list_portee = list(range(1, robot.portee_grenade + 1))
        cr.CustomRandom.shuffle(list_portee)
        list_puissance = robot.get_puissance_list("grenade").copy()
        cr.CustomRandom.shuffle(list_puissance)
        directions = LabHelper.LIST_DIRECTIONS.copy()
        cr.CustomRandom.shuffle(directions)
        finded = False
        cmd = None
        # recherche :
        for direct in directions:
            for portee in list_portee:
                for puissance in list_puissance:
                    # combinaison :
                    cible = self._get_case_for_dir_and_pas(robot, direct, portee)
                    if cible != None and cible.type_case in LabHelper.FAMILLE_GRENADE:
                        comb = {
                            "cible": cible,
                            "portee": portee,
                            "puissance": puissance,
                        }
                        valide = self._complete_and_valide_grenade_combinaison(
                            robot, cible, comb
                        )
                        if valide:
                            listchardir = [
                                LabHelper.CHAR_TOP,
                                LabHelper.CHAR_BOTTOM,
                                LabHelper.CHAR_LEFT,
                                LabHelper.CHAR_RIGHT,
                            ]
                            listdir = [
                                LabHelper.TOP,
                                LabHelper.BOTTOM,
                                LabHelper.LEFT,
                                LabHelper.RIGHT,
                            ]
                            indice = listdir.index(direct)
                            chardir = listchardir[indice]
                            cmd = (
                                LabHelper.CHAR_TXT_GRENADE
                                + chardir
                                + str(portee)
                                + "-"
                                + str(puissance)
                            )
                            finded = True
                            break
                if finded:
                    break
            if finded:
                break
        # retour
        return cmd

    #-----> B.10- Outils liés au comportement
    def _may_firstbot_attack_otherbot(self, firstbot, otherbot):
        """
        Analyse si firstbot peut attaquer otherbot.
        """
        possible = False
        # 1- attaque :
        # facteur de danger associé à firstbot
        fb_dgrfactor = firstbot.get_danger_factor_for_bot(otherbot)
        if fb_dgrfactor == 4:
            # psychopathe : danger certain
            possible = True
        elif fb_dgrfactor == 3:
            # danger possible :
            # - cas d'un winner aggressif et ambitieux / adversaire en avance
            # - cas d'un bot aggressif et efficace qui peut terraformer
            possible = True
        # 2- défense:
        midSUR = CaseRobot.get_feature_threshold("instinct_survie", "middle")
        highSUR = CaseRobot.get_feature_threshold("instinct_survie", "high")
        # facteur de danger associé à otherbot
        ob_dgrfactor = otherbot.get_danger_factor_for_bot(firstbot)
        # """
        if ob_dgrfactor == 4 and firstbot.instinct_survie >= midSUR:
            # niveau de défense minimal
            possible = True
        elif ob_dgrfactor == 3 and firstbot.instinct_survie >= highSUR:
            # niveau de défense avancé
            possible = True
        # """
        if ob_dgrfactor >= 3 and fb_dgrfactor >= 1:
            possible = True
        # retour
        return possible

    def _possible_todo_ACTION_on_case(self, case, action, robot):
        """
        Indique si une case peut faire l'objet d'une action de la part de l'éventuel robot
        Rq : LabHelper.ACTION_GRENADE non prise en charge par cette méthode
        """
        cond = True
        possible = False
        if action == LabHelper.ACTION_MOVE:
            famille = LabHelper.FAMILLE_MOVE
        elif action == LabHelper.ACTION_CREATE_DOOR:
            famille = LabHelper.FAMILLE_BUILD_DOOR
        elif action == LabHelper.ACTION_CREATE_WALL:
            famille = LabHelper.FAMILLE_BUILD_WALL
        elif action == LabHelper.ACTION_KILL:
            famille = LabHelper.FAMILLE_KILL
            cond = self._lablevel.get_distance_between_cases(robot, case) == 1
        elif action == LabHelper.ACTION_MINE:
            famille = LabHelper.FAMILLE_MINE
            cond = robot.has_mine and robot.puissance_mine > 0
        if cond and case.type_case in famille:
            possible = True
        # cas particuliers :
        if robot.behavior == CaseRobot.BEHAVIOR_HUNTER:
            if not self.case_sets_updated:
                # cas particulier d'un client
                self._update_usefull_sets()
            case_sortie = self._lablevel.get_case_sortie()
            other_alive = self.alive_bots.difference(self.hunter_alive)
            if case == case_sortie and len(other_alive) > 0:
                # tant qu'il y a du monde à éliminer
                possible = False
        # retour
        return possible

    #-----> B.11- Gestion de lancer de grenade
    def _get_params_for_grenade(
        self,
        robot,
        case,
        recursive=False,
        safemode=True,
        fullsearch=False,
        allowcollatdamage=False,
        directonly=False,
    ):
        """
        Recherche la meilleure combinaison de lancer de grenade pour atteindre
        case depuis la position actuelle du robot.
           
        * recursive : recherche l'intégralité des combinaisons (récursion comprise)
        * safemode : respect ou non de l'instinct de survie du robot
        * fullsearch : recherche l'ensemble des combinaisons simples (non récursives par défaut)
        * allowcollatdamage : similaire à safemode, pour surcharger l'empathie
          du bot et permettre des dégâts collatéraux
        * directonly : limite la recherche aux coups directs
        
        Retourne :
        
        * le dict {"finded":, "default":, "combinaisons":} permettant au
          robot de détruire la case par un lancer de grenade. default est la
          solution à priori adapée au robot, combinaisons comprend la liste
          des combinaisons possibles pour un choix particulier.
        * None si c'est impossible
        
        """
        if not (robot.has_grenade and robot.puissance_grenade > 0):
            return None
        if case == robot:
            return None
        # Recherche en cache ou calcul des combinaisons possibles et
        # des paramètres adaptés au robot
        params = self._search_grenade_combinaisons(
            robot,
            case,
            recursive=recursive,
            safemode=safemode,
            fullsearch=fullsearch,
            allowcollatdamage=allowcollatdamage,
            directonly=directonly,
        )
        if not params["finded"]:
            params = None
        return params

    def _get_params_for_grenade_and_listcases(
        self,
        robot,
        listcases,
        recursive=True,
        safemode=True,
        fullsearch=True,
        allowcollatdamage=False,
        directonly=False,
    ):
        """
        Tente de trouver une combinaison permettant d'atteindre le maximum de
        cases de listcases.
        Méthode de terraformage de haut niveau.
        Retourne :
        
        * le dict {"finded":, "bestres":, "bestfirst":} avec
        
            * finded : un boolean indiquant si une solution parfaite existe
            * bestres : la meilleure solution trouvée au format
              {"case":, "combinaison":, "setmatch":, "nb":}
            * bestfirst : la meilleure solution trouvée comprenant la
              première case de listcases au même format ou None
            
        * ou None
            
        """
        if not robot.has_grenade or len(listcases) == 0:
            return None
        params = None
        # cache ?
        gdSet = robot.get_current_gdSet()
        listcases.sort(key=attrgetter("x", "y"))
        casescoords = [str(c.x) + "," + str(c.y) for c in listcases]
        keycoords = "-".join(casescoords)
        k = (
            robot.x,
            robot.y,
            keycoords,
            recursive,
            safemode,
            fullsearch,
            allowcollatdamage,
            directonly,
        )
        cached_params = gdSet.get_params_grenade_in_cache(k)
        if cached_params != None:
            # recherche déja effectuée
            if cached_params["finded"]:
                # résultat trouvé
                params = cached_params
        else:
            # Liste de dicts de résultats
            resdictlist = list()
            setcases = set(listcases)
            # recherche case à case
            finded = False
            for c in listcases:
                if c != robot:
                    params = self._search_grenade_combinaisons(
                        robot,
                        c,
                        recursive=recursive,
                        safemode=safemode,
                        fullsearch=fullsearch,
                        allowcollatdamage=allowcollatdamage,
                        directonly=directonly,
                    )
                    if params["finded"]:
                        combinaisons = params["combinaisons"]
                        # analyse des combinaisons :
                        for comb in combinaisons:
                            set_impacted = set(comb["cases_impactees"])
                            set_match = set_impacted.intersection(setcases)
                            if len(set_match) > 0:
                                res = {
                                    "case": c,
                                    "combinaison": comb,
                                    "setmatch": set_match,
                                    "nb": len(set_match),
                                }
                                if len(set_match) == len(setcases):
                                    # solution parfaite trouvée
                                    resdictlist = [res]
                                    finded = True
                                    break
                                else:
                                    resdictlist.append(res)
                    if finded:
                        break
            # Meilleur résultat
            bestres = bestfirst = None
            if len(resdictlist) > 0:
                # trie par nombre de matchs
                resdictlist.sort(key=itemgetter("nb"), reverse=True)
                bestres = resdictlist[0]
                # meilleur résultat comprenant la première case de la liste
                firstc = listcases[0]
                for resdict in resdictlist:
                    setmatch = resdict["setmatch"]
                    if firstc in setmatch:
                        bestfirst = resdict
                        break
            params = {"finded": finded, "bestres": bestres, "bestfirst": bestfirst}
            # mise en cache :
            gdSet.cache_params_grenade(k, params)
        return params

    def _search_grenade_combinaisons(
        self,
        robot,
        case,
        recursive=False,
        safemode=True,
        fullsearch=False,
        allowcollatdamage=False,
        directonly=False,
    ):
        """
        Recherche l'ensemble des combinaisons de lancé de grenade.
        Crée ou complète l'objet GambleDataSet du robot pour mettre en cache
        les principaux résultats.
        Retourne le dict :
        {"finded":, "default":, "combinaisons":}
        
        avec combinaisons une liste de dicts
        {"cible":, "realportee":, "puissance":,"cases_impactees":,
        "destruction":, "dangers":, "bonus":, "robots":, "murs":} valides
        
        """
        # cache ?
        gdSet = robot.get_current_gdSet()
        if gdSet == None:
            # permet la mise en cache des données
            robot.register_current_gdSet(GambleDataSet())
        k = (
            robot.x,
            robot.y,
            case.x,
            case.y,
            recursive,
            safemode,
            fullsearch,
            allowcollatdamage,
            directonly,
        )
        params = gdSet.get_params_grenade_in_cache(k)
        if params == None:
            # Recherche :
            combinaisons = list()
            result_finded = False
            # Condition de trie par puissance : à revoir
            midAGG = CaseRobot.get_feature_threshold("aggressivite", "middle")
            midEFF = CaseRobot.get_feature_threshold("efficacite", "middle")
            cond_puissance = robot.aggressivite >= midAGG or robot.efficacite >= midEFF
            # 1- Recherche de combinaisons par lancer direct :
            # récupération d'une liste de dicts {"cible":, "portee":, "puissance":}
            directlist = self._direct_grenade_parameters_search(
                robot, case, safemode=safemode, fullsearch=fullsearch
            )
            if directlist != None:
                # Trie en fonction du comportement :
                if cond_puissance:
                    directlist.sort(key=itemgetter("puissance"), reverse=True)
                else:
                    directlist.sort(key=itemgetter("puissance"))
                # Validation des combinaisons, complétion des dicts avec les clefs
                # cases_impactees, destruction, dangers, bonus, robots, murs
                for cdict in directlist:
                    valide = self._complete_and_valide_grenade_combinaison(
                        robot,
                        case,
                        cdict,
                        safemode=safemode,
                        allowcollatdamage=allowcollatdamage,
                        directonly=directonly,
                    )
                    if valide:
                        combinaisons.append(cdict)
                        result_finded = True
                        if not fullsearch:
                            break
            # 2- Recherche de combinaisons "par la bande"
            # optimisation : on vérifie que la recherche indirecte a du sens
            # La case est elle dans la zone d'impact d'une mine?
            keepsearching = self._is_case_surrounded_by_mine(case)
            # poursuite éventuelle de la recherche
            if (keepsearching and not result_finded) or (fullsearch and not directonly):
                nondirectlist = self._nondirect_grenade_parameters_search(
                    robot,
                    case,
                    recursive=recursive,
                    safemode=safemode,
                    fullsearch=fullsearch,
                )
                if nondirectlist != None:
                    # Trie en fonction du comportement :
                    if cond_puissance:
                        nondirectlist.sort(key=itemgetter("puissance"), reverse=True)
                    else:
                        nondirectlist.sort(key=itemgetter("puissance"))
                    # Validation des combinaisons, complétion des dicts avec les clefs
                    # cases_impactees, destruction, dangers, bonus, robots, murs
                    for cdict in nondirectlist:
                        valide = self._complete_and_valide_grenade_combinaison(
                            robot,
                            case,
                            cdict,
                            safemode=safemode,
                            allowcollatdamage=allowcollatdamage,
                            directonly=directonly,
                        )
                        if valide:
                            combinaisons.append(cdict)
                            result_finded = True
                            if not fullsearch:
                                break
            # sélection de l'option la plus adaptée
            params = self._select_grenade_parameters(
                robot,
                case,
                combinaisons,
                recursive=recursive,
                safemode=safemode,
                fullsearch=fullsearch,
                allowcollatdamage=allowcollatdamage,
                directonly=directonly,
            )
            # mise en cache :
            gdSet.cache_params_grenade(k, params)
        # retour :
        return params

    def _select_grenade_parameters(
        self,
        robot,
        case,
        combinaisons,
        recursive=False,
        safemode=True,
        fullsearch=False,
        allowcollatdamage=False,
        directonly=False,
    ):
        """
        Recherche les paramètres de commande les plus adaptés au robot.
        combinaisons liste générée par _search_grenade_combinaisons.
        toutes les combinaisons ont été validées au préalable.
        """
        # Analyse :
        params = None
        if len(combinaisons) == 0:
            params = {"finded": False}
        else:
            # solutions par défaut
            midAGG = CaseRobot.get_feature_threshold("aggressivite", "middle")
            midEFF = CaseRobot.get_feature_threshold("efficacite", "middle")
            if robot.need_bonus:
                # on minimise la destruction de bonus
                combinaisons.sort(key=itemgetter("bonus"))
            if robot.aggressivite >= midAGG or robot.efficacite >= midEFF:
                # destruction décroissante
                combinaisons.sort(key=itemgetter("destruction"), reverse=True)
            elif robot.behavior == CaseRobot.BEHAVIOR_RANDOM:
                # au hasard
                cr.CustomRandom.shuffle(combinaisons)
            else:
                # destruction croissante
                combinaisons.sort(key=itemgetter("destruction"))
            # Données :
            params = {
                "finded": True,
                "default": combinaisons[0],
                "combinaisons": combinaisons,
            }
        return params

    def _direct_grenade_parameters_search(
        self, robot, case, safemode=True, fullsearch=True
    ):
        """
        Recherche d'un coup direct : la grenade touche directement la case.
        
        * safemode : respect ou non de l'instinct de survie du robot
        * fullsearch : recherche ou non toutes les combinaisons possibles
        
        Rq : les conséquences (cases impactées) ne sont pas calculées.
        Retourne une liste de dicts {"cible":, "portee":, "puissance":}
        """
        combinaisons = list()
        # cadre géométrique :
        vecteur = self._lablevel.get_vector_for_cases(robot, case)
        dx, dy = math.fabs(vecteur[0]), math.fabs(vecteur[1])
        D = int(max(dx, dy))
        d = int(min(dx, dy))
        # params : portée et puissance
        list_portee = list(range(1, robot.portee_grenade + 1))
        portee_max = list_portee[-1]
        list_puissance = robot.get_puissance_list("grenade")
        # trie en fonction du comportement du robot et de son besoin de bonus :
        if not robot.need_bonus:
            midAGG = CaseRobot.get_feature_threshold("aggressivite", "middle")
            midEFF = CaseRobot.get_feature_threshold("efficacite", "middle")
            if robot.aggressivite >= midAGG or robot.efficacite >= midEFF:
                list_puissance.sort(reverse=True)
        # Recherche  :
        if not (d > 2 or D > portee_max + 2):
            # Rq : cas impossibles sachant que puissance_max <= 25
            # liste de recherche de cible (sens robot vers case):
            liste = self._get_segment_for_grenade_search(robot, case)
            portee_max = int(min(portee_max, len(liste)))
            famille = LabHelper.FAMILLE_GRENADE
            # recherche des combinaisons :
            result_finded = False
            for puissance in list_puissance:
                plist = None
                # rayon d'action induit par la puissance :
                power_radius = 0
                if puissance >= 5:
                    power_radius = 1
                if puissance >= 13:
                    power_radius = 2
                # recherche des portées en fonction de la puissance
                if d == 0:
                    if puissance == 1 and D <= portee_max:
                        plist = [D]
                    elif puissance in [5, 9]:
                        plist = [i for i in range(D - 1, D + 2) if 0 <= i <= portee_max]
                    elif puissance >= 13:
                        plist = [i for i in range(D - 2, D + 3) if 0 <= i <= portee_max]
                elif d == 1:
                    if puissance == 5 and D <= portee_max:
                        plist = [D]
                    elif puissance in [9, 13, 17]:
                        plist = [i for i in range(D - 1, D + 2) if 0 <= i <= portee_max]
                    elif puissance == 25:
                        plist = [i for i in range(D - 2, D + 3) if 0 <= i <= portee_max]
                elif d == 2:
                    if puissance == 13 and D <= portee_max:
                        plist = [D]
                    elif puissance == 17:
                        plist = [
                            i
                            for i in range(D - 2, D + 3)
                            if 0 <= i <= portee_max and (D - i + 1) % 2 == 1
                        ]
                    elif puissance == 25:
                        plist = [i for i in range(D - 2, D + 3) if 0 <= i <= portee_max]
                # alimentation
                if plist != None:
                    for p in plist:
                        if p <= len(liste):
                            cible = liste[p - 1]
                            valide = True
                            if safemode:
                                # exclus les tirs immédiatement suicidaires
                                # attention : les impacts en cascade ne sont pas
                                # recherchés ici.
                                radius = p - power_radius
                                if radius <= 0:
                                    valide = False
                            if valide and cible.type_case in famille:
                                combinaisons.append(
                                    {
                                        "cible": cible,
                                        "portee": p,
                                        "puissance": puissance,
                                    }
                                )
                                result_finded = True
                            if result_finded and not fullsearch:
                                break
                if result_finded and not fullsearch:
                    break
        # retour :
        if len(combinaisons) == 0:
            combinaisons = None
        return combinaisons

    def _nondirect_grenade_parameters_search(
        self, robot, case, recursive=False, safemode=True, fullsearch=False
    ):
        """
        Recherche d'un coup "par la bande" : peut on atteindre la case en
        visant une case danger avoisinnante?
        
        * recursive : recherche récursive, faux par défaut
        * safemode : respect ou non de l'instinct de survie du robot
        * fullsearch : recherche ou non toutes les combinaisons possibles
        
        """
        # cadre géométrique :
        vecteur = self._lablevel.get_vector_for_cases(robot, case)
        vx, vy = vecteur[0], vecteur[1]
        if math.fabs(vx) > math.fabs(vy):
            main_sens = vx / math.fabs(vx)
            if main_sens > 0:
                main_dir = LabHelper.RIGHT
            else:
                main_dir = LabHelper.LEFT
            if vy < 0:
                second_dirs = [LabHelper.TOP]
            elif vy > 0:
                second_dirs = [LabHelper.BOTTOM]
            else:
                second_dirs = [LabHelper.TOP, LabHelper.BOTTOM]
        else:
            main_sens = vy / math.fabs(vy)
            if main_sens > 0:
                main_dir = LabHelper.BOTTOM
            else:
                main_dir = LabHelper.TOP
            if vx < 0:
                second_dirs = [LabHelper.LEFT]
            elif vx > 0:
                second_dirs = [LabHelper.RIGHT]
            else:
                second_dirs = [LabHelper.LEFT, LabHelper.RIGHT]
        # combinaisons :
        combinaisons = list()
        # recherche dans la direction principale :
        # rq : liste_main est un set
        liste_main = self._lablevel.get_cases_reachable_by_grenade_in_dir(
            robot, main_dir
        )
        main_comb = self._does_liste_may_impact_case(
            robot, case, liste_main, recursive, safemode, fullsearch
        )
        if main_comb != None:
            combinaisons.extend(main_comb)
        # recherche dans les directions secondaires :
        if len(combinaisons) == 0 or fullsearch:
            liste_second = set()
            for direct in second_dirs:
                # rq : l est un set
                l = self._lablevel.get_cases_reachable_by_grenade_in_dir(robot, direct)
                if l != None:
                    liste_second = liste_second.union(l)
            second_comb = self._does_liste_may_impact_case(
                robot, case, liste_second, recursive, safemode, fullsearch
            )
            if second_comb != None:
                combinaisons.extend(second_comb)
        # retour :
        if len(combinaisons) == 0:
            combinaisons = None
        return combinaisons

    def _is_case_surrounded_by_mine(self, case):
        """
        Vérifie si une case est dans la zone d'impact d'une ou plusieurs mines.
        """
        maybeimpacted = False
        # les mines comprises dans la sous matrice 5*5 centrée sur case :
        minelist = self._lablevel.get_minelist_arround_case(case)
        minelist.sort(key=attrgetter("danger_impact"), reverse=True)
        # recherche d'impact non récursive :
        for dgr in minelist:
            maybeimpacted = self._does_mine_impact_case(dgr, case)
            if maybeimpacted or dgr.danger_impact == 1:
                # on s'arrête au premier résultat positif (ou lorsque l'impact
                # est trop faible)
                break
        return maybeimpacted

    def _does_liste_may_impact_case(
        self, robot, case, listecases, recursive, safemode, fullsearch
    ):
        """
        Recherche la ou les combinaisons consistant à impacter la case par
        l'explosion d'un danger contenu dans la liste (le set), via un jet de
        grenade par le robot.
        """
        combinaisons = list()
        liste_dgr = self._extract_and_sort_dangers_for_case(listecases, case)
        if liste_dgr != None:
            result_finded = False
            for dgr in liste_dgr:
                done = self._does_mine_impact_case(dgr, case, recursive=recursive)
                if done:
                    # _direct_grenade_parameters_search ne vérifiant pas l'ensemble
                    # des cases impactées de façon récursive, le coup peut être
                    # fatal "par rebond". A ce stade la première solution qui
                    # fonctionne suffit (d'où fullsearch=False).
                    comb_for_dgr = self._direct_grenade_parameters_search(
                        robot, dgr, safemode=safemode, fullsearch=False
                    )
                    if comb_for_dgr != None:
                        combinaisons.extend(comb_for_dgr)
                        result_finded = True
                    if result_finded and not fullsearch:
                        break
        # retour :
        if len(combinaisons) == 0:
            combinaisons = None
        return combinaisons

    def _extract_and_sort_dangers_for_case(self, listecases, case):
        """
        Extrait de la liste toutes les cases dangers, opère un trie par
        proximité à la cases et puissance décroissantes
        """
        if listecases == None:
            return None
        # 1- filtrage des cases dangers :
        filterset = self._extract_dangers_for_case(listecases, case)
        # 2- création de la liste de dict, trie
        liste_dgr = None
        liste_dgr_dict = [{"case": c} for c in filterset]
        if liste_dgr_dict != None:
            for cd in liste_dgr_dict:
                c = cd["case"]
                cd["impact"] = c.danger_impact
                cd["dist"] = self._lablevel.get_distance_between_cases(c, case)
            liste_dgr_dict.sort(key=itemgetter("dist"))
            liste_dgr_dict.sort(key=itemgetter("impact"), reverse=True)
            liste_dgr = [d["case"] for d in liste_dgr_dict]
        return liste_dgr

    def _extract_dangers_for_case(self, listecases, case):
        """
        Retourne le set de cases dangers (impact > 1) contenues dans listecases,
        différentes de case.
        """
        if listecases == None:
            return None
        fullset = set(listecases)
        # réduction aux cases dangers
        filterset = fullset.intersection(self.dangers_set)
        # puis aux dangers d'impacts > 1, sans la case
        filterset = filterset.difference(self.dangers_set_1, {case})
        return filterset

    def _does_mine_impact_case(self, mine, case, recursive=False):
        """
        Est-ce que l'explosion de la mine impacte la case?
        
        1/2 : Initialisation
        
        * recursive : recherche récursive, faux par défaut
        
        """
        # set de mémorisation des dangers traités :
        donelist = set()
        # méthode récursive :
        return self._xdoes_mine_impact_case(mine, case, donelist, recursive=recursive)

    def _xdoes_mine_impact_case(self, mine, case, donelist, recursive=False):
        """
        Est-ce que l'explosion de la mine impacte la case?
        
        2/2 : Méthode récursive.
        
        * donelist : liste (set) des dangers déja traités
        * recursive : recherche récursive, faux par défaut
        
        """
        result = False
        donelist.add(mine)
        # set de cases impactées :
        cases_impactees = self._lablevel.get_cases_adj_impacted_by_danger(mine)
        if len(cases_impactees) > 0:
            if case in cases_impactees:
                result = True
            elif recursive:
                set_dgr = self._extract_dangers_for_case(cases_impactees, case)
                if set_dgr != None:
                    newdgr = set_dgr.difference(donelist)
                    for c in newdgr:
                        result = self._xdoes_mine_impact_case(
                            c, case, donelist, recursive=recursive
                        )
                        if result:
                            break
        return result

    def _get_segment_for_grenade_search(self, robot, case):
        """
        Retourne la liste de cases de la cible vers le robot (exclus), s'approchant
        le plus du vecteur formé par robot & case
        """
        flatmatrice = self._lablevel.get_flat_matrice()
        vecteur = self._lablevel.get_vector_for_cases(robot, case)
        if vecteur[0] == 0 or vecteur[1] == 0:
            segment = flatmatrice.get_segment(robot, case)
        else:
            if math.fabs(vecteur[0]) > math.fabs(vecteur[1]):
                extremite = flatmatrice.get_case(case.x, robot.y)
            else:
                extremite = flatmatrice.get_case(robot.x, case.y)
            segment = flatmatrice.get_segment(robot, extremite)
        liste = list()
        n = len(segment)
        firstcase = segment[0]
        # le robot a pu être déplacé virtuellement sans mise à jour de la
        # flatmatrice, le test robot == segment[0] n'est donc pas sûr
        if (firstcase.x, firstcase.y) == (robot.x, robot.y):
            liste = segment[1:n]
        else:
            liste = segment[0 : n - 1]
            liste.reverse()
        return liste

    def _complete_and_valide_grenade_combinaison(
        self,
        robot,
        case,
        combinaison,
        safemode=True,
        allowcollatdamage=False,
        directonly=False,
    ):
        """
        Valide la combinaison, la complète en cas de validité.
        Retourne un boolean indiquant si la combinaison atteint la case ciblée
        et est cohérente avec le robot et les paramètres passés
        """
        gdSet = robot.get_current_gdSet()
        # cache ?
        cible = combinaison["cible"]
        portee = combinaison["portee"]
        puissance = combinaison["puissance"]
        k = (
            robot.x,
            robot.y,
            cible.x,
            cible.y,
            portee,
            puissance,
            safemode,
            allowcollatdamage,
            directonly,
        )
        valide, cases_impactees, combstats = gdSet.get_combinaison_grenade_in_cache(k)
        if (valide, cases_impactees, combstats) == (None, None, None):
            # calcul initial
            dangerdict = CaseGrenade.get_default_dict()
            dangerdict["danger_impact"] = puissance
            dangerdict["x"] = cible.x
            dangerdict["y"] = cible.y
            virtualgrenade = CaseGrenade(dangerdict)
            dictimpact = self._lablevel.xlook_for_cases_impacted(virtualgrenade)
            # validité de la combinaison
            cases_impactees = dictimpact["flat_list"]
            # en projectif les coords du robot peuvent être virtuelles, le test
            # is_bot_impacted = robot in cases_impactees n'est donc pas suffisant
            coords_impactees = set([(c.x, c.y) for c in cases_impactees])
            is_bot_impacted = (robot.x, robot.y) in coords_impactees
            others_bot_impacted = [
                c
                for c in cases_impactees
                if c.type_case == LabHelper.CASE_ROBOT and c != robot and c.alive
            ]
            valide = case in cases_impactees
            midSUR = CaseRobot.get_feature_threshold("instinct_survie", "middle")
            if safemode and robot.instinct_survie >= midSUR and is_bot_impacted:
                valide = False
            if not allowcollatdamage and len(others_bot_impacted) > 0:
                kill_all = gdSet.get_list_case("kill_all")
                for b in others_bot_impacted:
                    if b not in kill_all:
                        valide = False
                        break
            # données complémentaires :
            destruction = 0
            dangers = 0
            bonus = 0
            robots = 0
            murs = 0
            if valide:
                for c in cases_impactees:
                    if c.type_case == LabHelper.CASE_DANGER:
                        dangers += c.danger_impact
                    elif c.type_case == LabHelper.CASE_BONUS:
                        bonus += 1
                    elif c.type_case == LabHelper.CASE_ROBOT:
                        robots += 1
                    elif c.type_case == LabHelper.CASE_MUR:
                        murs += 1
            destruction = dangers + robots + murs
            combstats = {
                "destruction": destruction,
                "dangers": dangers,
                "bonus": bonus,
                "robots": robots,
                "murs": murs,
            }
            if destruction == 0:
                valide = False
            # mise en cache dans le gdSet
            v = (valide, cases_impactees, combstats)
            gdSet.cache_combinaison_grenade(k, v)
        # on complète la combinaison :
        combinaison["cases_impactees"] = cases_impactees
        combinaison["destruction"] = combstats["destruction"]
        combinaison["dangers"] = combstats["dangers"]
        combinaison["bonus"] = combstats["bonus"]
        combinaison["robots"] = combstats["robots"]
        combinaison["murs"] = combstats["murs"]
        # retour :
        return valide

    def _get_params_for_grenade_cmd(self, robot, cmd):
        """
        Retourne les paramètres associés à une commande formatée (ex gn2-5)
        """
        dictcmd = None
        params = None
        try:
            dictcmd = CommandHelper.translate_cmd(cmd)
        except:
            pass
        if dictcmd != None:
            pas = dictcmd["pas"]
            direct = dictcmd["direct"]
            cible = self._get_case_for_dir_and_pas(robot, direct, pas)
            if cible != None:
                params = self._get_params_for_grenade(robot, cible)
        return params

    #-----> B.12- Utilitaires basiques
    def _get_dir_for_axe_and_sens(self, axe, sens):
        """
        Utilitaire : traduit axe+sens en dir
        """
        if axe == LabHelper.AXIS_X:
            if sens == LabHelper.DIR_POS:
                return LabHelper.RIGHT
            else:
                return LabHelper.LEFT
        else:
            if sens == LabHelper.DIR_POS:
                return LabHelper.BOTTOM
            else:
                return LabHelper.TOP

    def _get_next_cases_in_dir(self, case, direct):
        """
        Retourne la liste des cases suivantes dans la direction direct
        """
        flatmatrice = self._lablevel.get_flat_matrice()
        w, h = flatmatrice.get_dimensions()
        listcases = list()
        x, y = case.x, case.y
        if direct == LabHelper.LEFT:
            while x >= 0:
                listcases.append(flatmatrice.get_case(x, y))
                x -= 1
        elif direct == LabHelper.RIGHT:
            while x < w:
                listcases.append(flatmatrice.get_case(x, y))
                x += 1
        elif direct == LabHelper.TOP:
            while y >= 0:
                listcases.append(flatmatrice.get_case(x, y))
                y -= 1
        elif direct == LabHelper.BOTTOM:
            while y < h:
                listcases.append(flatmatrice.get_case(x, y))
                y += 1
        return listcases

    def _get_dir_cmd_for_case(self, robot, case):
        """
        Indique quelle direction de commande correspond à la case
        """
        direction = None
        vecteur = self._lablevel.get_vector_for_cases(robot, case)
        if vecteur[0] == 0:
            if vecteur[1] > 0:
                direction = LabHelper.CHAR_BOTTOM
            if vecteur[1] < 0:
                direction = LabHelper.CHAR_TOP
        elif vecteur[1] == 0:
            if vecteur[0] > 0:
                direction = LabHelper.CHAR_RIGHT
            if vecteur[0] < 0:
                direction = LabHelper.CHAR_LEFT
        else:
            if math.fabs(vecteur[0]) > math.fabs(vecteur[1]):
                if vecteur[0] > 0:
                    direction = LabHelper.CHAR_RIGHT
                if vecteur[0] < 0:
                    direction = LabHelper.CHAR_LEFT
            else:
                if vecteur[1] > 0:
                    direction = LabHelper.CHAR_BOTTOM
                if vecteur[1] < 0:
                    direction = LabHelper.CHAR_TOP
        return direction

    def _get_dir_for_case(self, robot, case):
        """
        Indique quelle direction correspond à la case
        """
        direction = None
        vecteur = self._lablevel.get_vector_for_cases(robot, case)
        if vecteur[0] == 0:
            if vecteur[1] > 0:
                direction = LabHelper.BOTTOM
            if vecteur[1] < 0:
                direction = LabHelper.TOP
        elif vecteur[1] == 0:
            if vecteur[0] > 0:
                direction = LabHelper.RIGHT
            if vecteur[0] < 0:
                direction = LabHelper.LEFT
        else:
            if math.fabs(vecteur[0]) > math.fabs(vecteur[1]):
                if vecteur[0] > 0:
                    direction = LabHelper.RIGHT
                if vecteur[0] < 0:
                    direction = LabHelper.LEFT
            else:
                if vecteur[1] > 0:
                    direction = LabHelper.BOTTOM
                if vecteur[1] < 0:
                    direction = LabHelper.TOP
        return direction

    def _get_case_for_dir_and_pas(self, robot, direct, pas):
        """
        Retourne la case associée aux paramètres
        """
        if direct == LabHelper.LEFT:
            axis = LabHelper.AXIS_X
            sens = LabHelper.DIR_NEG
        elif direct == LabHelper.RIGHT:
            axis = LabHelper.AXIS_X
            sens = LabHelper.DIR_POS
        elif direct == LabHelper.TOP:
            axis = LabHelper.AXIS_Y
            sens = LabHelper.DIR_NEG
        elif direct == LabHelper.BOTTOM:
            axis = LabHelper.AXIS_Y
            sens = LabHelper.DIR_POS
        x, y = x_r, y_r = robot.x, robot.y
        if axis == LabHelper.AXIS_X:
            x = x_r + pas * sens
        else:
            y = y_r + pas * sens
        flatmatrice = self._lablevel.get_flat_matrice()
        return flatmatrice.get_case(x, y)

    def _get_dirs_to_mainTarget(self, robot):
        """
        Retourne les directions robot -> cible principale ou None
        """
        mainTarget = robot.get_main_target()
        if mainTarget == None:
            return None
        else:
            list_dirs = list()
            vecteur = self._lablevel.get_vector_for_cases(robot, mainTarget)
            if vecteur[0] > 0:
                list_dirs.append(LabHelper.RIGHT)
            if vecteur[0] < 0:
                list_dirs.append(LabHelper.LEFT)
            if vecteur[1] > 0:
                list_dirs.append(LabHelper.BOTTOM)
            if vecteur[1] < 0:
                list_dirs.append(LabHelper.TOP)
            return list_dirs
