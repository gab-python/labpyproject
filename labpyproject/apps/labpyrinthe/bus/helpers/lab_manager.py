#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
**LabManager** : manager intermédiaire utilisé par composition par le GameManager.

Utilise par composition les managers suivants :

- LabParser
- LabLevel
- CommandManager

Fait appel aux helpers statiques :

- LabGenerator
- LabHelper

"""
# imports :
import math
import time
from operator import itemgetter, attrgetter
import labpyproject.core.random.custom_random as cr
from labpyproject.apps.labpyrinthe.bus.helpers.lab_generator import LabGenerator
from labpyproject.apps.labpyrinthe.bus.helpers.game_configuration import (
    GameConfiguration,
)
from labpyproject.apps.labpyrinthe.bus.helpers.lab_parser import LabParser
from labpyproject.apps.labpyrinthe.bus.commands.cmd_manager import CommandManager
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import LabHelper
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import Matrice
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import Case
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseRobot
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseDanger
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseBonus
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseAnimation

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["LabManager"]
# classes :
class LabManager:
    """
    **Gestionnaire de labyrinthe**
    """

    def __init__(self, gameMngr):
        """
        Constructeur
        
        Args:
            gameMngr (GameManager)
        """
        # manager de jeu :
        self.gameMngr = gameMngr
        # Parseur / générateur :
        self._labParser = LabParser()
        # Gestionnaire de commandes
        self._cmdMngr = CommandManager()
        # Dict de placement des robots
        self._place_bots_dict = None
        # Echantillons pour la distribution initiale des Xtras
        self._initial_samples = None
        # Niveau (couches de matrices) :
        self._lablevel = None
        # Liste des cases associées aux robots
        self._liste_robots = None

    def re_initialise(self):
        """
        Ré initialisation avant une nouvelle partie
        """
        # managers :
        self._labParser.re_initialise()
        self._cmdMngr.re_initialise()
        # Propriétés :
        self._place_bots_dict = None
        self._initial_samples = None
        self._lablevel = None
        self._liste_robots = None
        self._add_bonus = False
        self._add_danger = False

    #-----> A- Création aléatoire de carte
    def create_random_carte(
        self, fullrandom=True, width=30, height=20, propvide=0.55, propporte=0.05
    ):
        """
        Crée aléatoirement une carte texte. 
        Retourne une liste de lignes (comme le fait cio.load_text_file)
        """
        # Délégation à une méthode statique du générateur
        return LabGenerator.create_random_carte(
            fullrandom, width, height, propvide, propporte
        )

    def _define_bots_places(self):
        """
        Après création de la carte de base (murs, vide, portes), repère les cases
        vides pour le placement des robots.
        """
        self._place_bots_dict = dict()
        # params
        flatmatrice = self._lablevel.get_flat_matrice()
        w, h = flatmatrice.get_dimensions()
        cases_vides = self._lablevel.get_typecase_set(LabHelper.CASE_VIDE)
        case_sortie = self._lablevel.get_case_sortie()
        behaviorcount = GameConfiguration.get_behaviors_count()
        nb_winners = behaviorcount[CaseRobot.BEHAVIOR_WINNER]
        nb_hunters = behaviorcount[CaseRobot.BEHAVIOR_HUNTER]
        interdist = GameConfiguration.get_initial_bots_inter_distance()
        # traitements
        placelist = list()
        # distance à la sortie
        for c in cases_vides:
            d = self._lablevel.get_path_length_between_cases(c, case_sortie)
            placelist.append(
                {"case": c, "ds": d, "x": c.x, "y": c.y, "selected": False, "bot": None}
            )
        # dénombrement :
        placedict = dict()
        maxds = 0
        for cdict in placelist:
            ds = cdict["ds"]
            maxds = max(maxds, ds)
            if ds in placedict.keys():
                placedict[ds] += 1
            else:
                placedict[ds] = 1
        for i in range(0, maxds):
            if i not in placedict.keys():
                placedict[i] = 0
        # partage en fonction des bots :
        maxlenpath = w + h - 4
        # - winners, humans : loin de la sortie
        whlimit = math.ceil(maxlenpath * 0.7)
        whind = whlimit
        whcount = placedict[whind]
        whplace = [cdict for cdict in placelist if cdict["ds"] == whind]
        while whcount < nb_winners * 10 and whind < maxds:
            whind += 1
            whcount += placedict[whind]
            whplace.extend([cdict for cdict in placelist if cdict["ds"] == whind])
        whplace.sort(key=itemgetter("x", "y"))
        # sélection de cases espacées de interdist
        lastdict = whplace[0]
        lastdict["selected"] = True
        whfinal = [lastdict]
        whfinalcaseset = set([lastdict["case"]])
        for cdict in whplace[1:]:
            lastcase = lastdict["case"]
            case = cdict["case"]
            d = self._lablevel.get_distance_between_cases(lastcase, case)
            if d >= interdist:
                sm = flatmatrice.get_sublosange(case.x, case.y, interdist * 2 - 1)
                smset = sm.get_set_cases()
                if len(smset.intersection(whfinalcaseset)) == 0:
                    # la case est à bonne distance des cases déja sélectionnées
                    cdict["selected"] = True
                    whfinal.append(cdict)
                    whfinalcaseset.add(case)
                    lastdict = cdict
        whfinal.sort(key=itemgetter("ds"))
        whalt = [cdict for cdict in whplace if not cdict["selected"]]
        whalt.sort(key=itemgetter("ds"))
        self._place_bots_dict["winhum_1"] = whfinal
        self._place_bots_dict["winhum_2"] = whalt
        # - hunters : près de la sortie
        ds_hunt = math.floor(whlimit / 4)
        hplace = [cdict for cdict in placelist if cdict["ds"] <= ds_hunt]
        hcount = len(hplace)
        while hcount < nb_hunters and hcount < maxds:
            ds_hunt += 1
            hplace.extend([cdict for cdict in placelist if cdict["ds"] == ds_hunt])
            hcount = len(hplace)
        cr.CustomRandom.shuffle(hplace)
        self._place_bots_dict["hunters"] = hplace
        # - autres : entre les deux
        moy_ds = math.floor((whlimit + ds_hunt) / 2)
        ro = range(moy_ds - 3, moy_ds + 4)
        oplace = [cdict for cdict in placelist if cdict["ds"] in ro]
        cr.CustomRandom.shuffle(oplace)
        self._place_bots_dict["others"] = oplace
        # - alternatives
        r1 = range(ds_hunt + 1, moy_ds - 3)
        r2 = range(moy_ds + 4, whlimit)
        aplace = [
            cdict for cdict in placelist if cdict["ds"] in r1 or cdict["ds"] in r2
        ]
        cr.CustomRandom.shuffle(aplace)
        self._place_bots_dict["alt"] = aplace

    def define_initial_samples(self):
        """
        Définit les sous matrices de cases vides dédiées à la ditribution initiale
        des XTras (bonus, mines). Génère de 4 à 16 sous matrices.
        """
        # Nouvelle matrice de cases vides :
        flatmatrice = self._lablevel.get_flat_matrice()
        cases_vides = self._lablevel.get_typecase_set(LabHelper.CASE_VIDE)
        matvide = Matrice()
        for c in cases_vides:
            matvide.set_case(c)
        # Dimensions des sous matrices (/ nombre entre 4 et 16)
        wfm, hfm = flatmatrice.get_dimensions()
        w, h = wfm - 2, hfm - 2  # on ignore le périmètre
        ws, hs = 0, 0  # dims des sous matrices
        rdim = range(2, 10)
        # sur x
        for dim in rdim:
            fx = w // dim
            if 2 <= fx <= 4:
                ws = dim
                break
        rx = w % ws
        listw = [ws] * (fx - 1)
        listw.append(ws + rx)  # dernière colonne éventuellement plus large
        # sur y
        for dim in rdim:
            fy = h // dim
            if 2 <= fy <= 4:
                hs = dim
                break
        ry = h % hs
        listh = [hs] * (fy - 1)
        listh.append(hs + ry)  # resp dernière ligne éventuellement plus haute
        # génération des sous matrices :
        listsm = list()
        x = 1
        for wsm in listw:
            y = 1
            for hsm in listh:
                sm = matvide.get_submatrice(x, y, wsm, hsm, True)
                if sm != None:
                    lsm = len(sm.get_list_cases())
                    if lsm > 0:
                        listsm.append(sm)
                y += hsm
            x += wsm
        # liste de dicts :
        case_sortie = self._lablevel.get_case_sortie()
        rdictlist = list()
        for sm in listsm:
            x, y = sm.get_lefttop_point()
            w, h = sm.get_dimensions()
            listevide = sm.get_case_by_type(LabHelper.CASE_VIDE)
            nbvide = len(listevide)
            center = sm.get_center()
            case_center = Case(center[0], center[1], None, "")
            dist_sortie = self._lablevel.get_distance_between_cases(
                case_sortie, case_center
            )
            dict_sm = {
                "listecases": listevide,
                "nb": nbvide,
                "dist_cs": dist_sortie,
                "x": x,
                "y": y,
                "nb_bots": 0,
                "nb_bonus": 0,
                "nb_danger": 0,
                "allow_danger": True,
            }
            rdictlist.append(dict_sm)
        # doit-on éviter de poser des mines à côté de la sortie?
        niveau = GameConfiguration.get_difficulty()
        if niveau != 3:
            rdictlist.sort(key=itemgetter("dist_cs"))
            # pas de mine dans la sous matrice la plus proche de la sortie
            rdictlist[0]["allow_danger"] = False
        self._initial_samples = rdictlist

    def _trace_samples_after_distribution(self):
        """
        debug
        """
        for dsm in self._initial_samples:
            x = dsm["x"]
            y = dsm["y"]
            nbv = dsm["nb"]
            nbbots = dsm["nb_bots"]
            nbbonus = dsm["nb_bonus"]
            nbdanger = dsm["nb_danger"]
            print(
                "sm : x=",
                x,
                " y=",
                y,
                " vide=",
                nbv,
                " bots=",
                nbbots,
                " bonus=",
                nbbonus,
                " dangers=",
                nbdanger,
            )

    def _define_simple_sample(self):
        """
        Génération d'un seul échantillon de cases vides pour la distribution d'XTras en 
        cours de partie.
        """
        cases_vides = self._lablevel.get_typecase_set(LabHelper.CASE_VIDE)
        # doit-on éviter de poser des mines à côté de la sortie?
        niveau = GameConfiguration.get_difficulty()
        if niveau not in [4, 5]:
            # on filtre :
            filtreliste = list()
            case_sortie = self._lablevel.get_case_sortie()
            ecart = 3
            for cv in cases_vides:
                if self._lablevel.get_distance_between_cases(case_sortie, cv) > ecart:
                    filtreliste.append(cv)
            cases_vides = filtreliste
        nbvide = len(cases_vides)
        dict_sm = {
            "listecases": cases_vides,
            "nb": nbvide,
            "dist_cs": 0,
            "nb_bonus": 0,
            "nb_danger": 0,
            "allow_danger": True,
        }
        return [dict_sm]

    def random_distribute_XTras(self, initialpub=False):
        """
        Distribution aléatoire des bonus et dangers
        
        Args:
            initialpub: indique s'il s'agit de la publication initiale
        """
        bonuslist = list()
        dangerlist = list()
        if initialpub:
            # publication initiale
            listdictsm = self._initial_samples
            bonuslist = self._random_distribute_bonus(listdictsm)
            dangerlist = self._random_distribute_dangers(listdictsm)
        else:
            # mise à jour en cours de partie
            if (
                GameConfiguration.ensure_bonus_density()
                or GameConfiguration.ensure_danger_density()
            ):
                # on génère un unique échantillon (complet) de cases vides
                listdictsm = self._define_simple_sample()
                if GameConfiguration.ensure_bonus_density():
                    bonuslist = self._random_distribute_bonus(listdictsm)
                    self._add_bonus = False
                if GameConfiguration.ensure_danger_density():
                    dangerlist = self._random_distribute_dangers(listdictsm)
                    self._add_danger = False
        return bonuslist, dangerlist

    def _random_distribute_bonus(self, listdictsm=None):
        """
        Distribution aléatoire de cases bonus
        
        Args:
            listdictsm: liste de dicts similaire à ce que génère _define_initial_samples(), 
                à minima avec un seul dict représentant la matrice complète des cases vides
        """
        # liste des cases crées :
        rlist = list()
        # échantillons
        if listdictsm == None:
            # on génère un unique échantillon (complet) de cases vides
            listdictsm = self._define_simple_sample()
        nbsamples = len(listdictsm)
        if nbsamples == 0:
            return rlist
        nbvides = 0
        for dict_sm in listdictsm:
            nbvides += dict_sm["nb"]
        # densité
        if GameConfiguration.is_game_configured():
            dens_bonus = GameConfiguration.get_initial_density("bonus")
        else:
            dens_bonus = LabHelper.BONUS_DENSITE
        # nombre de cases à ajouter
        flatmatrice = self._lablevel.get_flat_matrice()
        w, h = flatmatrice.get_dimensions()
        nb_bonus = math.ceil(dens_bonus * w * h)
        cases_bonus = self._lablevel.get_typecase_set(LabHelper.CASE_BONUS)
        delta = nb_bonus - len(cases_bonus)
        if delta > nbvides:
            delta = nbvides
        elif delta == 0:
            return rlist
        # nombre de cases à ajouter par échantillon :
        nbbysample = delta // nbsamples
        rest = delta % nbsamples
        restdone = True
        # trie aléatoire de la liste (évite que la dernière sous matrice soit plus alimentée)
        cr.CustomRandom.shuffle(listdictsm)
        # ajouts :
        for dict_sm in listdictsm:
            nb = 0
            if rest > 0:
                restdone = False
            while nb < nbbysample or restdone == False:
                # extraction d'une case vide
                listecases = dict_sm["listecases"]
                if len(listecases) == 0:
                    break
                casevide = cr.CustomRandom.choice(listecases)
                listecases.remove(casevide)
                dict_sm["nb"] -= 1
                dict_sm["nb_bonus"] += 1
                # création d'une case bonus
                dictbonus = CaseBonus.get_default_dict()
                dictbonus["x"] = casevide.x
                dictbonus["y"] = casevide.y
                bonus = CaseBonus(dictbonus)
                self._lablevel.set_case(bonus)
                rlist.append(bonus)
                nb += 1
                delta -= 1
                if nb > nbbysample:
                    restdone = True
                    rest -= 1
                if delta == 0:
                    break
            if delta == 0:
                break
        return rlist

    def _random_distribute_dangers(self, listdictsm=None):
        """
        Distribution aléatoire de cases dangers.
        
        Args:
            listdictsm : liste de dicts similaire à ce que génère _define_initial_samples(), 
                à minima avec un seul dict représentant la matrice complète des cases vides
        """
        # liste des cases crées :
        rlist = list()
        # échantillons
        if listdictsm == None:
            # on génère un unique échantillon (complet) de cases vides
            listdictsm = self._define_simple_sample()
        nbsamples = len(listdictsm)
        if nbsamples == 0:
            return rlist
        nbvides = 0
        for dict_sm in listdictsm:
            nbvides += dict_sm["nb"]
        # densité et impacts
        impacts = [1, 5, 9, 13, 17, 25]
        if GameConfiguration.is_game_configured():
            dens_danger = GameConfiguration.get_initial_density("danger")
            max_impact = GameConfiguration.get_danger_max_power()
        else:
            dens_danger = LabHelper.DANGER_DENSITE
            max_impact = cr.CustomRandom.choice(impacts)
        listimpact = [x for x in impacts if x <= max_impact]
        # nombre de cases à ajouter
        flatmatrice = self._lablevel.get_flat_matrice()
        w, h = flatmatrice.get_dimensions()
        nb_danger = math.ceil(dens_danger * w * h)
        cases_danger = self._lablevel.get_typecase_set(LabHelper.CASE_DANGER)
        delta = nb_danger - len(cases_danger)
        if delta > nbvides:
            delta = nbvides
        elif delta == 0:
            return rlist
        # nombre de cases à ajouter par échantillon :
        nbbysample = delta // nbsamples
        rest = delta % nbsamples
        restdone = True
        # trie aléatoire de la liste (évite que la dernière sous matrice soit plus alimentée)
        cr.CustomRandom.shuffle(listdictsm)
        # ajouts :
        for dict_sm in listdictsm:
            if dict_sm["allow_danger"]:
                nb = 0
                if rest > 0:
                    restdone = False
                while nb < nbbysample or restdone == False:
                    # extraction d'une case vide
                    listecases = dict_sm["listecases"]
                    if len(listecases) == 0:
                        break
                    casevide = cr.CustomRandom.choice(listecases)
                    listecases.remove(casevide)
                    dict_sm["nb"] -= 1
                    dict_sm["nb_danger"] += 1
                    # création d'une case danger
                    dictdanger = CaseDanger.get_default_dict()
                    dictdanger["x"] = casevide.x
                    dictdanger["y"] = casevide.y
                    dictdanger["danger_type"] = CaseDanger.DANGER_MINE
                    dictdanger["danger_impact"] = cr.CustomRandom.choice(listimpact)
                    danger = CaseDanger(dictdanger)
                    self._lablevel.set_case(danger)
                    rlist.append(danger)
                    nb += 1
                    delta -= 1
                    if nb > nbbysample:
                        restdone = True
                        rest -= 1
                    if delta == 0:
                        break
            if delta == 0:
                break
        return rlist

    def publish_players(self, playerlist):
        """
        Positionne les robots pré enregistrés après chargement de la carte.
        """
        # repérage des cases :
        if self._place_bots_dict == None:
            self._define_bots_places()
        # publication :
        for player in playerlist:
            if not player.published:
                robot = player.get_robot()
                if robot != None:
                    self._random_place_robot(robot)
                    self._lablevel.set_case(robot)
                    player.published = True

    def _random_place_robot(self, robot):
        """
        Positionne aléatoirement le robot associé à un joueur (choix orienté).
        """
        # en fonction du robot :
        behavior = robot.behavior
        iswinhum = False
        dictlist = None
        if robot.human or behavior == CaseRobot.BEHAVIOR_WINNER:
            dictlist = self._place_bots_dict["winhum_1"]
            iswinhum = True
        elif behavior == CaseRobot.BEHAVIOR_HUNTER:
            dictlist = self._place_bots_dict["hunters"]
        else:
            dictlist = self._place_bots_dict["others"]
        altdictlist = self._place_bots_dict["alt"]
        # choix d'une case
        freedictlist = [cdict for cdict in dictlist if cdict["bot"] == None]
        if len(freedictlist) == 0:
            if iswinhum:
                altdictlist = self._place_bots_dict["winhum_2"]
            freedictlist = [cdict for cdict in altdictlist if cdict["bot"] == None]
        casedict = cr.CustomRandom.choice(freedictlist)
        # positionnement :
        casevide = casedict["case"]
        casedict["bot"] = robot
        robot.x = casevide.x
        robot.y = casevide.y
        # Enregistrement coords initiales
        robot.register_case(robot, -1)
        # initialisation des zones du robot :
        self._lablevel.update_bot_action_zones(robot)

    #-----> B- Données : exports et parsing
    def parse_labyrinthe(self, kwargs):
        """
        Parse la carte textuelle et crée les cases robots, bonus, dangers.
        """
        # Délégation au parseur
        self._lablevel, parse_liste_robots = self._labParser.parse_labyrinthe(kwargs)
        # le master crée la liste de robots
        if not self.gameMngr.is_master():
            self._liste_robots = parse_liste_robots
            # pour un spectateur connecté en cours de partie :
            self.sort_bots_by_order()
        # paramétrage du cmdMngr :
        self._sync_commandMngr()

    def _sync_commandMngr(self):
        """
        Met à jour les pointeurs du commande manager
        """
        # paramétrage du cmdMngr :
        self._cmdMngr.set_labLevel(self._lablevel)
        self._cmdMngr.set_liste_robot(self._liste_robots)

    def get_parsedicts_for_listcases(self, listcase):
        """
        Retourne un dict à parser pour une liste de cases (master).
        """
        # Délégation au parseur
        return self._labParser.get_parsedicts_for_listcases(listcase)

    def update_bots_or_XTras(self, kwargs):
        """
        Ajoute des cases robots, ou bonus et dangers crées par le master (slave).
        """
        if not self.gameMngr.is_master():
            # Délégation au parseur
            self._liste_robots = self._labParser.update_bots_or_XTras(kwargs)
            # paramétrage du cmdMngr :
            self._sync_commandMngr()

    def rebuild_labyrinthe(self, kwargs):
        """
        En cas de désynchronisation en mode slave, on reparse intégralement
        les données (slave).
        """
        if not self.gameMngr.is_master():
            # soit un parsing initial:
            self.parse_labyrinthe(kwargs)

    def get_repr_view(self, matrice=None):
        """
        Retourne la représentation texte du labyrinthe pour affichage.
        """
        # Délégation au parseur
        return self._labParser.get_repr_view(matrice)

    def get_flatmatrice(self):
        """
        Retourne l'applat de matrices pour affichage.
        """
        return self._lablevel.get_flat_matrice()

    def get_graph_matrices(self):
        """
        Retourne toutes les données d'affichages destinées à une GUI graphique
        pour une publication complète de la carte.
        """
        dictmat = dict()
        # couche de base (sauf robots, grenade, animation, target, debug)
        dictmat["mat_base"] = self._lablevel.get_flat_matrice(guidedicated=True)
        # dangers :
        dictmat["mat_dangers"] = self._lablevel.get_layer(LabHelper.CASE_DANGER)
        # bonus :
        dictmat["mat_bonus"] = self._lablevel.get_layer(LabHelper.CASE_BONUS)
        # robots :
        dictmat["mat_robots"] = self._lablevel.get_layer(LabHelper.CASE_ROBOT)
        # grenade :
        dictmat["mat_grenade"] = self._lablevel.get_layer(LabHelper.CASE_GRENADE)
        # animations :
        dictmat["animlay_animation"] = self._lablevel.get_layer(
            LabHelper.CASE_ANIMATION
        )
        # debug :
        dictmat["animlay_debug"] = self._lablevel.get_layer(LabHelper.CASE_DEBUG)
        # target :
        dictmat["mat_target"] = self._lablevel.get_layer(LabHelper.CASE_TARGET)
        return dictmat

    def get_diff_graph_datas(self):
        """
        Retourne uniquement les changements graphiques apportés depuis le dernier
        appel à self.init_step_changelogs.
        """
        dictdatas = dict()
        # logs fins des cases ajoutées/modifiées ou détruites hors cases animation
        step_chlogs = self._lablevel.get_step_change_log()
        step_coords = step_chlogs["coords"]
        # cases ajoutées ou modifiées (liste) :
        dictdatas["cases_added"] = step_chlogs["cases_added"]
        # cases supprimées (liste) :
        dictdatas["cases_deleted"] = step_chlogs["cases_deleted"]
        # cases déplacées (liste) :
        dictdatas["cases_moved"] = step_chlogs["cases_moved"]
        # clear de couches (liste) :
        dictdatas["cleared_typecases"] = step_chlogs["cleared_typecases"]
        # matrice d'animation (projection) :
        anim_mat = self._lablevel.get_animation_matrice()
        cases_anim = list()
        # on filtre avec les coords de l'étape :
        anim_lc = anim_mat.get_list_cases()
        for c in anim_lc:
            tuppcint = (int(c.x), int(c.y))
            if tuppcint in step_coords:
                cases_anim.append(c)
        dictdatas["cases_anim"] = cases_anim
        return dictdatas

    def get_dimensions(self):
        """
        Retourne w, h
        """
        return self._lablevel.get_dimensions()

    def get_parsing_datas(self):
        """
        Retourne un dictionnaire à sérialiser comprenant toutes les données nécessaires 
        au parsing.
        """
        # Délégation au parseur
        return self._labParser.get_parsing_datas()

    def get_bots_datas(self, full=True):
        """
        Retourne un dictionnaire à sérialiser comprenant toutes les données relatives 
        aux robots.
        """
        # Délégation au parseur
        return self._labParser.get_bots_datas(full=full)

    #-----> C- Gestion des coups
    #-----> C.1- Changelogs (synchro)
    def init_changelogs(self):
        """
        Ré initialise les logs du LabLevel.
        """
        if self._lablevel:
            self._lablevel.init_level_before_changes()

    def get_changelogs_key(self):
        """
        Retourne la clef caractérisant les changements apportés au LabLevel.
        """
        chlogs = self._lablevel.get_change_log()
        return chlogs["key"]

    def init_step_changelogs(self):
        """
        Ré initiazlise les logs d'étape.
        """
        if self._lablevel:
            self._lablevel.init_level_before_step_change()

    #-----> C.2- Commandes
    def compute_cmd_for_autobot(self, uid, gamblenumber, gamblecount, gambleid):
        """
        Définit la cmd à appliquer à un robot automatique suivant son comportement
        
        * uid : id unique du robot
        * gamblenumber : numéro du coup (à partir de 1)
        * gamblecount : nombre de coups consécutifs du joueur
        
        Retour : cmd
        """
        robot = self.get_robot_by_uid(uid)
        # Délégation au manager de commande :
        return self._cmdMngr.compute_cmd_for_autobot(
            robot, gamblenumber, gamblecount, gambleid
        )

    def analyse_cmd_for_robot(self, cmd, uid):
        """
        Analyse une commande pour le robot d'id uid
        
        Retourne un tupple avec :
        
        * un boolean indiquant si la commande a apporté un changement
        * le dict généré par CommandHelper.translate_cmd
        * une liste décrivant les conséquences (bonus gagné, danger activé, robot tué, 
          grenade à lancer,
          case à ajouter)
        * la case visée par l'action
                
        """
        # Si la partie a été ré initialisée :
        if self._lablevel == None:
            return False, None, None, None
        # robot
        robot = self.get_robot_by_uid(uid)
        # Analyse de la commande :
        result, dictcmd, consequences, next_case = self._cmdMngr.analyse_cmd_for_robot(
            cmd, robot
        )
        return result, dictcmd, consequences, next_case

    def on_cmd_for_robot_done(
        self, dictcmd, robot, next_case, botskilled, gambleid, gamblenumber, gamblecount
    ):
        """
        Post traitement après qu'une commande ait été appliquée.
        """
        action = dictcmd["action"]
        self._cmdMngr.validate_action_for_robot(
            action, robot, next_case, botskilled, gambleid, gamblenumber, gamblecount
        )

    #-----> C.3- Gestion des cases
    def add_case(self, case):
        """
        Ajoute une case au LabLevel
        """
        self._lablevel.set_case(case)

    def move_case(self, case, x, y):
        """
        Déplace une case du LabLevel
        """
        self._lablevel.move_case(case, x, y)

    def remove_case(self, case):
        """
        Supprime une case du Lablevl
        """
        self._lablevel.delete_case(case)

    #-----> C.4- Utilitaires
    def init_robot_before_gamble(self, uid, gamblenumber, gamblecount):
        """
        Met à jour la vitesse actuelle du robot ainsi que ses zones de déplacement
        et d'attaque
        """
        robot = self.get_robot_by_uid(uid)
        # Délégation au manager de commande :
        self._cmdMngr.init_robot_before_gamble(robot, gamblenumber, gamblecount)

    def need_to_complete_XTras_after_gamble(self):
        """
        Indique si l'on doit compléter les bonus et dangers
        """
        if (GameConfiguration.ensure_bonus_density() and self._add_bonus) or (
            GameConfiguration.ensure_danger_density() and self._add_danger
        ):
            return True
        return False

    def on_bonus_win(self, casebonus):
        """
        Appelée lorsque le robot d'uid passe sur une case bonus
        """
        # suppression de la case :
        self._lablevel.delete_case(casebonus)
        # marque la disparition d'un bonus :
        self._add_bonus = True

    def get_explosion_scenario(self, uid, casedanger):
        """
        Appelée lorsqu'une case danger est déclenchée
        """
        # dict des cases impactées :
        dictimpact = self._lablevel.xlook_for_cases_impacted(casedanger)
        # position du robot :
        if uid != None:
            robot = self.get_robot_by_uid(uid)
            robot.x, robot.y = casedanger.x, casedanger.y
            dictimpact[0].add((robot, casedanger.danger_impact))
        # scénario d'animation :
        scenariodict = self._create_animation_scenario(
            LabHelper.ANIMATION_SCENARIO["EXPLOSION"], dictimpact
        )
        # retour :
        return scenariodict

    def explosion_callback(self, dictscenario):
        """
        Callback de fin d'explosion (animée ou non)
        
        Args:
            dictscenario : dict généré par self._create_animation_scenario
        """
        # Suppression des cases d'animation :
        self._lablevel.clear(LabHelper.CASE_ANIMATION)
        self._lablevel.clear(LabHelper.CASE_DEBUG)
        # marque la disparition d'un danger :
        self._add_danger = True

    def on_robot_killed(self, uid, delete=False):
        """
        Appelée lorsqu'un robot est éliminé
        """
        robot = self.get_robot_by_uid(uid)
        if robot != None:
            robot.register_death()
            if delete:
                # usage : déconnection d'un joueur avant
                # démarrage de la partie
                # modèle : pour les vues graphiques
                self._lablevel.delete_case(robot)
                # parser :
                self._labParser.delete_robot(robot)
                # paramétrage du cmdMngr :
                self._sync_commandMngr()
            self._lablevel.discard_cache(LabHelper.CASE_ROBOT)
            self._lablevel.mark_case_as_modified(robot)

    #-----> C.5- Animation
    def _create_animation_scenario(self, scenariotype, dictdatas):
        """
        Crée les données nécessaires à la lecture d'une animation
        
        * scenarios types : une entrée du dict LabHelper.ANIMATION_SCENARIO
        * dictdatas : dict de données
        
        Rqs : 
        
        * si "EXPLOSION" : dict généré par self._lablevel.xlook_for_cases_impacted(casedanger)
        * les cases animation crées sont initialement à visible=False
        
        """
        if not isinstance(dictdatas, dict):
            return None
        scenario_anim = None
        if scenariotype == LabHelper.ANIMATION_SCENARIO["EXPLOSION"]:
            # Explosion(s) : animation de type CaseAnimation.ANIM_FACE
            scenario_anim = dict()
            scenario_anim["type_anim"] = CaseAnimation.ANIM_FACE
            scenario_anim["cases_animation"] = dict()
            scenario_anim["cases_a_effacer"] = dict()
            scenario_anim["flat_del_list"] = dictdatas["flat_list"]
            # Alimentation du scénario :
            face_list = LabHelper.ANIMATION_EXPLOSION_FACES
            local_step_count = len(face_list)
            i = 0
            while i in dictdatas.keys():
                if len(dictdatas[i]) != 0:
                    scenario_anim["step_count"] = i
                    # Création des cases animation :
                    scenario_anim["cases_animation"][i] = list()
                    scenario_anim["cases_a_effacer"][i] = list()
                    for c, impact in dictdatas[i]:
                        # c = case touchée par l'explosion à l'étape i
                        # impact : impact du danger ayant impacté c
                        if c.type_case not in LabHelper.FAMILLE_CASES_NO_ANIMATION:
                            animdict = CaseAnimation.get_default_dict()
                            animdict["visible"] = False
                            animdict["type_anim"] = CaseAnimation.ANIM_FACE
                            animdict["scenario_anim"] = LabHelper.ANIMATION_SCENARIO[
                                "EXPLOSION"
                            ]
                            animdict["step_count"] = local_step_count
                            animdict["start_step"] = i
                            animdict["x"] = c.x
                            animdict["y"] = c.y
                            animdict["face"] = face_list[0]
                            animdict["face_list"] = face_list
                            animdict["impact"] = impact
                            caseA = CaseAnimation(animdict)
                            scenario_anim["cases_animation"][i].append(caseA)
                            scenario_anim["cases_a_effacer"][i].append(c)
                i += 1
            # Finalisation du scénario :
            scenario_anim["prevtime"] = time.perf_counter()
            scenario_anim["current_step"] = 0
            scenario_anim["step_count"] += local_step_count
        return scenario_anim

    def handle_animation_step(self, scenariodict, current_step):
        """
        Effectue les traitement d'une étape d'animation. 
        Retourne la liste des robots éliminés.
        """
        type_anim = scenariodict["type_anim"]
        botkilled = list()
        if type_anim == CaseAnimation.ANIM_FACE:
            casesAdict = scenariodict["cases_animation"]
            j = 0
            # sélection des cases à afficher :
            filterdict = dict()
            while j <= current_step:
                if j in casesAdict.keys():
                    for cA in casesAdict[j]:
                        k = (int(cA.x), int(cA.y))
                        if k in filterdict.keys():
                            rcA = filterdict[k]
                            if cA.start_step > rcA.start_step:
                                filterdict[k] = cA
                        else:
                            filterdict[k] = cA
                else:
                    break
                j += 1
            for cA in filterdict.values():
                cA.apply_animation_step(current_step)
                self._lablevel.set_case(cA)
            # effacement :
            deldict = scenariodict["cases_a_effacer"]
            if current_step in deldict.keys():
                dellist = deldict[current_step]
                botkilled = self._clean_animation_step(dellist)
            # debug :
            # self._create_debug_layer(dellist, scenariodict["flat_del_list"])
        return botkilled

    def _create_debug_layer(self, steplist, fullist):
        """
        Debug : affichage des cases à supprimer à l'étape et au total
        """
        # clear :
        self._lablevel.clear(LabHelper.CASE_DEBUG)
        # full :
        for c in fullist:
            if (c.x, c.y) != (None, None):
                dc = Case(c.x, c.y, LabHelper.CASE_DEBUG, "1")
                self._lablevel.set_case(dc)
        # step :
        for c in steplist:
            if (c.x, c.y) != (None, None):
                dc = Case(c.x, c.y, LabHelper.CASE_DEBUG, "2")
                self._lablevel.set_case(dc)

    def _clean_animation_step(self, dlist):
        """
        Efface les cases à supprimer lors d'un pas d'animation
        dlist : liste des cases à effacer
        """
        botkilled = list()
        if dlist != None and len(dlist) > 0:
            for case in dlist:
                if case.type_case == LabHelper.CASE_ROBOT:
                    if case.alive:
                        botkilled.append(case)
                if case.type_case == LabHelper.CASE_BONUS:
                    self._add_bonus = True
                if case.type_case == LabHelper.CASE_DANGER:
                    self._add_danger = True
                if case.type_case not in LabHelper.FAMILLE_CASES_UNDELETABLE:
                    casevide = Case(
                        case.x, case.y, LabHelper.CASE_VIDE, LabHelper.CHAR_REPR_VIDE
                    )
                    self._lablevel.set_case(casevide)
                    self._lablevel.delete_case(case)
        return botkilled

    #-----> D- Robots
    def update_robotlist(self, rlist):
        """
        En contexte master les robots n'ont pas été identifiés au parsing, on met à 
        jour la liste avant de démarrer la partie.
        """
        self._liste_robots = rlist
        self._cmdMngr.set_liste_robot(self._liste_robots)

    def sort_bots_by_order(self):
        """
        Trie de la liste des bots par order croissant.
        """
        if self._liste_robots != None:
            try:
                self._liste_robots.sort(key=attrgetter("order"))
            except TypeError:
                # ordres indéfinis encore (order=None)
                pass

    def get_robotlist(self):
        """
        Retourne la liste des robots.
        """
        return self._liste_robots

    def register_robot(self, dictrobot):
        """
        Ajoute un robot à la liste.
        
        Args:
            dictrobot : dict généré par robot.get_properties_dict()
        """
        # case :
        case = CaseRobot(dictrobot)
        if GameConfiguration.is_game_configured():
            case.vitesse = GameConfiguration.get_initial_powers("vitesse")
            case.has_mine = GameConfiguration.get_initial_powers("has_mine")
            case.puissance_mine = GameConfiguration.get_initial_powers("puissance_mine")
            case.has_grenade = GameConfiguration.get_initial_powers("has_grenade")
            case.puissance_grenade = GameConfiguration.get_initial_powers(
                "puissance_grenade"
            )
            case.portee_grenade = GameConfiguration.get_initial_powers("portee_grenade")
            if not case.human:
                case.aggressivite = min(
                    case.aggressivite, GameConfiguration.get_max_aggressivite()
                )
                case.efficacite = min(
                    case.efficacite, GameConfiguration.get_max_efficacite()
                )
        else:
            impacts = [1, 5, 9, 13, 17, 25]
            case.vitesse = 1
            case.has_mine = True
            case.puissance_mine = cr.CustomRandom.choice(impacts)
            case.has_grenade = True
            case.puissance_grenade = cr.CustomRandom.choice(impacts)
            case.portee_grenade = cr.CustomRandom.randrange(1, 5)
        # liste :
        if self._liste_robots == None or len(self._liste_robots) == 0:
            self._liste_robots = list()
        self._liste_robots.append(case)
        # retour :
        return case

    def get_robot_by_uid(self, uid):
        """
        Retourne la case associée au robot d'identifiant uid ou None
        """
        result = None
        if self._liste_robots != None and len(self._liste_robots) > 0:
            for robot in self._liste_robots:
                if robot.uid == uid:
                    result = robot
                    break
        return result

    def has_robot_won(self, uid):
        """
        Indique par un boolean si le robot d'id uid a gagné
        """
        robot = self.get_robot_by_uid(uid)
        if robot != None:
            xs, ys = self._lablevel.get_sortie_coords()
            if robot.x == xs and robot.y == ys:
                return True
        return False

    def is_partie_ended(self):
        """
        Indique s'il reste des bots susceptibles de gagner la partie, à savoir 
        un joueur humain, un winner ou un chasseur.
        """
        ended = True
        restrited_b = [
            CaseRobot.BEHAVIOR_WINNER,
            CaseRobot.BEHAVIOR_HUNTER,
            CaseRobot.BEHAVIOR_HUMAN,
        ]
        for r in self._liste_robots:
            if r.alive and r.behavior in restrited_b:
                ended = False
                break
        return ended
            