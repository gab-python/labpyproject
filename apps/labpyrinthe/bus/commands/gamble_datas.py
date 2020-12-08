#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Données utilisées pour la définition de coups

* GambleDataSet : dataset utilisé pour le calcul de coups automatiques
* GambleDataObject : modélise une case pouvant constituer la cible d'un coup
* GambleSearch : contexte de définition d'un coup
* PseudoActions :  modélise une liste de pseudos-actions (série de coups anticipés)

"""
# imports :
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import LabHelper

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["GambleDataSet", "GambleDataObject", "PseudoActions", "GambleSearch"]
# classes :
class GambleDataSet:
    """
    Conteneur des données utilisées pour le calcul automatique d'un coup à jouer
    """

    # variables statiques
    FILTER_LT = "FILTER_LT"  #: filtre <
    # méthodes statiques
    def get_filterdict(cls, filter_type, attr, val):
        """
        Retourne un filtre de liste (sous forme de dict)
        """
        if filter_type == cls.FILTER_LT:
            return {"filtre": cls.filter_property_lt, "attr": attr, "value": val}
        else:
            return None

    get_filterdict = classmethod(get_filterdict)

    def filter_property_lt(cls, gdo, attr, val):
        """
        Pour filtrer une liste de GambleDataObject en sélectionnat ceux dont l'attribut 
        prop est inférieur à val
        """
        if hasattr(gdo, attr):
            if gdo[attr] < val:
                return True
        return False

    filter_property_lt = classmethod(filter_property_lt)
    # méthodes d'instance
    def __init__(
        self, gamblenumber=None, gamblecount=None, gambleid=None, gdmemory=None
    ):
        """
        Constructeur
        
        Args:
            gamblenumber : numéro du coup (à partir de 1)
            gamblecount : nombre de coups consécutifs du joueur
            gambleid : id unique d'un coup de la partie
            gdmemory : cache de court terme
        """
        # numéro du coup (indice >= 1)
        self.gamblenumber = gamblenumber
        # nombre consécutifs de coups
        self.gamblecount = gamblecount
        # id du coup dans la partie
        self.gambleid = gambleid
        # données internes
        self._innerdict = dict()
        # listes de GambleDataObject par directions :
        self._innerdict[LabHelper.TOP] = list()
        self._innerdict[LabHelper.BOTTOM] = list()
        self._innerdict[LabHelper.LEFT] = list()
        self._innerdict[LabHelper.RIGHT] = list()
        self._innerdict["all_dirs"] = list()
        # listes de cases environnantes :
        self._innerdict[
            "defense_all"
        ] = None  # tous les robots contre lesquels se défendre
        self._innerdict[
            "defense"
        ] = None  # les robots contre lesquels se défendre dans la zone d'action
        self._innerdict["attaque_all"] = None  # tous les robots que l'on peut attaquer
        self._innerdict[
            "attaque"
        ] = None  # ceux que l'on peut toucher dans la zone d'action
        self._innerdict[
            "safezone"
        ] = None  # cases dans la zone de déplacement hors d'atteinte directe d'adversaire
        self._innerdict[
            "realsafezone"
        ] = None  # cases de safezone hors de portée d'une mine
        self._innerdict[
            "extendedunsafezone"
        ] = None  # toutes les cases de la carte pouvant faire l'objet d'attaque directe
        self._innerdict[
            "dangers"
        ] = None  # les dangers pouvant nous atteindre en cas d'explosion
        self._innerdict[
            "bonus"
        ] = None  # les bonus à portée (en fonction de la vitesse)
        self._innerdict["kill_all"] = None  # defense_all + attaque_all
        # listes de cases pour le choix final :
        self._innerdict["all_adj"] = None
        self._innerdict["first_adj"] = None
        self._innerdict["bonus_adj"] = None
        self._innerdict["other_adj"] = None
        self._innerdict["safe_adj"] = None
        # liste de dicts {"case":, "proba":} décrivant le risque d'attaque par
        # case de robot.move_zone
        self._innerdict["prob_dicts"] = None
        # cumuls pondérés (/distance au robot des cases) par directions :
        # dicts du type :  {"defense":, "attaque":, "dangers":, "bonus":, "libres":, "score":}
        self._innerdict["cumul"] = {
            LabHelper.TOP: None,
            LabHelper.BOTTOM: None,
            LabHelper.LEFT: None,
            LabHelper.RIGHT: None,
        }
        # sample size  :
        self.largeurX = 0
        self.largeurY = 0
        self.profondeur_max = 0
        # directions vers l'éventuelle cible principale
        self.maintarget_directions = None
        # option finale
        self.finaleoption = None
        # cache de commandes grenade
        self._grenadedict = dict()
        self._grenadecombdict = dict()
        # cache de TargetPath
        self._targetpathdict = dict()
        # avance des adversaires (pour winner) :
        self._winner_adv_avance = {
            "adv_in_final": False,
            "adv_in_approach": False,
            "final_list": None,
            "approach_list": None,
            "retard": None,
        }
        # état de l'alimentation en données :
        self.datas_computed = False
        # prochaines actions pré définies (si vitesse > 1)
        self._pseudoactionsobj = None
        # contexte de la recherche de coup
        self._gamblesearch = GambleSearch()
        # données mémorisées :
        if gdmemory != None:
            self.set_GD_memory(gdmemory)

    #-----> Données à conserver lors de coups multiples
    def get_GD_memory(self):
        """
        Retourne un dict regroupant les données réutilisables lors de coups
        multiples
        """
        gddict = dict()
        # pseudo actions
        gddict["pseudoactions"] = self.get_pseudoactions()
        # objectifs :
        gddict["objectifs"] = self.gamblesearch.objectifs
        # probas d'attaque sur move zone
        gddict["prob_dicts"] = self._innerdict["prob_dicts"]
        return gddict

    def set_GD_memory(self, gddict):
        """
        Enregistre les données de coups multiples à mémoriser
        """
        # pseudo actions
        paobj = gddict["pseudoactions"]
        self.register_pseudoactions(paobj)
        # objectifs :
        self.gamblesearch.objectifs = gddict["objectifs"]
        # probas d'attaque sur move zone
        self._innerdict["prob_dicts"] = gddict["prob_dicts"]

    #-----> Objet GambleSearch
    def _get_gamblesearch(self):
        """Contexte du coup."""
        return self._gamblesearch

    def _set_gamblesearch(self, val):
        self._gamblesearch = val

    gamblesearch = property(_get_gamblesearch, _set_gamblesearch)

    #-----> Winners : classement / sortie
    def set_adversaires_avance(self, resultdict):
        """
        Enregistre le dict décrivant l'avancée des adversaires d'un winner.
        
        Args:
            resultdict (dict):{"adv_in_final":bool, "adv_in_approach":bool,
                "final_list":final_ist, "approach_list":, "retard":}
        """
        self._winner_adv_avance = resultdict

    def get_adversaires_avance(self):
        """
        Retourne le dict décrivant l'avancée des adversaires d'un winner.
        """
        return self._winner_adv_avance

    #-----> Gestion des pseudos actions (coups anticipés)
    def register_pseudoactions(self, paObj):
        """
        Enregistre un objet PseudoActions modélisant une série d'actions
        "schédulées".
        """
        self._pseudoactionsobj = paObj

    def get_pseudoactions(self):
        """
        Retourne l'objet PseudoActions enregistré
        """
        return self._pseudoactionsobj

    def has_next_pseudoaction(self):
        """
        Indique si une ou plusieurs pseudo actions sont prévues
        """
        haspa = False
        if self._pseudoactionsobj != None:
            haspa = self._pseudoactionsobj.get_pseudoactions_count() > 0
        return haspa

    #-----> Options pour le choix de cible temporaire
    def add_GDObj(self, gdobj):
        """
        Ajoute un objet GambleDataObject dans la liste associée à sa direction
        """
        direct = gdobj.direct
        if direct != None:
            self._innerdict[direct].append(gdobj)
            self._innerdict["all_dirs"].append(gdobj)

    def get_GDObj_list_by_dir(self, direct, filterdict=None):
        """
        Retourne la liste des GambleDataObject associée à une direction
        """
        if direct in LabHelper.LIST_DIRECTIONS:
            liste = self._innerdict[direct]
            if filterdict == None:
                return liste
            else:
                fct_filtre = filterdict["filtre"]
                attr = filterdict["attr"]
                val = filterdict["value"]
                rlist = list()
                for gdo in liste:
                    if fct_filtre(gdo, attr, val):
                        rlist.append(gdo)
                return rlist
        return None

    def get_full_GDObj_list(self, filterdict=None):
        """
        Retourne la liste de tous les objets GambleDataObject
        """
        liste = self._innerdict["all_dirs"]
        if filterdict == None:
            return liste
        else:
            fct_filtre = filterdict["filtre"]
            attr = filterdict["attr"]
            val = filterdict["value"]
            rlist = list()
            for gdo in liste:
                if fct_filtre(gdo, attr, val):
                    rlist.append(gdo)
            return rlist

    #-----> Gestion des listes générées lors de la reconnaissance de
    # l'environnement
    def register_list_case(self, key, liste):
        """
        Enregistre une liste de cases (environnantes, choix final)
        """
        if key in [
            "defense",
            "attaque",
            "safezone",
            "realsafezone",
            "dangers",
            "bonus",
            "all_adj",
            "first_adj",
            "bonus_adj",
            "other_adj",
            "safe_adj",
            "defense_all",
            "attaque_all",
            "prob_dicts",
            "extendedunsafezone",
            "kill_all",
        ]:
            self._innerdict[key] = liste

    def get_list_case(self, key):
        """
        Retourne une liste de cases (environnantes, choix final)
        """
        if key in [
            "defense",
            "attaque",
            "safezone",
            "realsafezone",
            "dangers",
            "bonus",
            "all_adj",
            "first_adj",
            "bonus_adj",
            "other_adj",
            "safe_adj",
            "defense_all",
            "attaque_all",
            "prob_dicts",
            "extendedunsafezone",
            "kill_all",
        ]:
            return self._innerdict[key]
        return None

    def register_cumul_by_dir(self, direct, dictval):
        """
        Enregistre un dict de cumul de mesures pour une direction
        """
        if direct in LabHelper.LIST_DIRECTIONS:
            self._innerdict["cumul"][direct] = dictval

    def get_cumul_by_dir(self, direct):
        """
        Retourne un dict de cumul de mesures pour une direction
        """
        if direct in LabHelper.LIST_DIRECTIONS:
            return self._innerdict["cumul"][direct]

    #-----> Cache de chemins
    def get_TargetPath_in_cache(self, key):
        """
        Recherche de TargetPath dans le cache.
        
        Retourne :
        
        * le meilleur chemin en cache et une liste vide
        * ou None et une liste de dangers bloquants
        
        """
        if key in self._targetpathdict.keys():
            return self._targetpathdict[key]
        return "not in cache"

    def cache_TargetPath(self, key, result):
        """
        Mise en cache de TargetPath.
        
        Met en cache :
        
        * un objet TargetPath et une liste vide
        * ou None et une liste de dangers bloquants
            
        pour la clef key : (xrobot, yrobot, xtarget, ytarget, ecomode)
        """
        self._targetpathdict[key] = result

    #-----> Cache de lancers de grenade
    def get_params_grenade_in_cache(self, key):
        """
        Retourne des params de lancer de grenade en cache
        """
        if key in self._grenadedict.keys():
            return self._grenadedict[key]
        return None

    def cache_params_grenade(self, key, params):
        """
        Met en cache des params de lancer de grenade valides

        - pour une case :
        
          - key: (robot.x, robot.y, case.x, case.y, recursive, safemode,
            fullsearch, allowcollatdamage, directonly)        
          - valeur: le dict {"finded":, "default":, "combinaisons":} ou None 
            par défaut
        
        - OU pour une liste de cases :

          - key: (robot.x, robot.y, keycoords, recursive, safemode,
            fullsearch, allowcollatdamage, directonly)              
          - valeur:  le dict {"finded", "bestres":} ou None par défaut
            
        """
        self._grenadedict[key] = params

    def get_combinaison_grenade_in_cache(self, key):
        """
        Recherche de cache de paramètres de lancer de grenade
        
        Args:
            key : (robot.x, robot.y, cible.x, cible.y, portee, puissance, safemode, 
                allowcollatdamage, directonly)
        
        Valeur retournée, un tuple :
        
        * valide, cases_impactees, combstats (dict)
        * None, None, None, par défaut
        """
        if key in self._grenadecombdict.keys():
            return self._grenadecombdict[key]
        return (None, None, None)

    def cache_combinaison_grenade(self, key, value):
        """
        Met en cache une combinaison (cible, portee, puissance) sa validité,
        sa liste de cases impactées et les stats par type de cases
        """
        self._grenadecombdict[key] = value


class GambleDataObject:
    """
    Données associée à une case pouvant constituer une cible lors du calcul
    automatique de coups à jouer
    """

    def __init__(self, x, y, direct, axe, sens):
        """
        Constructeur
        """
        self.x = x
        self.y = y
        self.direct = direct
        self.axe = axe
        self.sens = sens
        # données mises à jour ultérieurement :
        # dénombrement
        self.count_cases_libres = None
        self.last_free_case = None
        self.count_cases_dangers = None
        self.count_cases_adversaires = None
        self.count_cases_bonus = None
        self.count_cases_murs = None
        self.count_cases_no_action = None
        self.count_consecutive_libres = None
        # robots (attaque, défense)
        self.count_bot_attaque = 0
        self.count_bot_defense = 0
        # distances
        self.dist_to_bot = None
        self.delta_main = None
        # facteur d'échantillonnage
        self.sample_size = 0
        self.fact_sample = 0
        # liste de cases
        self.listcases = None
        # score
        self.avance = 0
        self.score = 0
        # accessibilité de la cible
        self.targetpath = None
        self.pathcost = 0
        # dans une direction de l'éventuelle cible principale
        self.is_in_maindir = True
        # paramètres liés aux mines
        self.impact_cumule = 0
        self.first_impact = 0
        # prise en compte
        self.discarded = False

    def __getitem__(self, prop):
        """
        Rend l'objet "subscriptable"
        """
        return getattr(self, prop)

    def serialize(self):
        return ""

    def __repr__(self):
        return "\nGDObj direct={} x={} y={} score={} pathcost={}  avance={}  discarded={} last_free_case={}".format(
            self.direct,
            self.x,
            self.y,
            self.score,
            self.pathcost,
            self.avance,
            self.discarded,
            self.last_free_case,
        )


class PseudoActions:
    """
    Objet modélisant une liste de pseudos actions définies par les méthodes de
    "schedule" de CmdManager.
    """

    def __init__(self, pseudoactionlist, gamblecount, name=None):
        """
        Constructeur
        
        Args:
            pseudoactionlist : list de pseudos actions
            gamblecount : nombre de coups maximums nécessaires pour effectuer les actions          
        """
        self._palist = pseudoactionlist
        # nombre de coups total
        self.gamblecount = gamblecount
        # nombre de coups utiles
        self.relevantgamblecount = 0  # à intégrer
        # identifiants
        self.searchctx = None
        self.name = name
        # le chemin est il exact ?
        # rq : le besoin de terraformer induit une incertitude (cf dangers
        # ajoutés aléatoirement)
        self.exactpath = False
        # la case d'arrivée est elle sûre?
        self.securestop = False
        # liste des bots / securestop=False
        self.stoptargets = None
        # une case sûre pourra elle être rejointe ensuite?
        self.secureissue = False
        # liste des bots éliminés durant l'action
        self.killedbots = None
        # nombre de bonus associés
        self.bonuscount = 0
        # nombre de bots contre lesquels se défendre éliminés
        self.defensecount = 0
        # nombre de bots à attaquer éliminés
        self.attaquecount = 0
        # delta entre longueur du path robot/mainTarget et longueur du path
        # dernière case atteinte/mainTarget
        self.deltamainpathlen = 0
        # facteur de pertinence 2>1>0
        self.relevantfactor = 0
        # score additionnel :
        self.score = 0
        # facteur de bouclage
        self.loop_factor = 0

    def get_next_pseudoaction(self):
        """
        Retourne la prochaine action enregistrée (sans dépilement) ou None
        """
        action = None
        if len(self._palist) > 0:
            action = self._palist[0]
        return action

    def get_last_pseudoaction(self):
        """
        Retourne la dernière action enregistrée (sans dépilement) ou None
        """
        action = None
        if len(self._palist) > 0:
            action = self._palist[-1]
        return action

    def get_path_in_pseudoaction_list(self):
        """
        Retourne la liste de coordonnées des actions de type "goto" présentes
        en début de liste. On ajoute l'éventuelle action terraform en fin de
        liste.
        """
        coords = list()
        if len(self._palist) > 0:
            for pa in self._palist:
                if pa["type"] in ["goto", "terraform"]:
                    coords.append(pa["coords"])
                else:
                    break
        return coords

    def add_pseudoaction_to_list(self, pa):
        """
        Ajoute une pseudo action en fin de liste
        """
        self._palist.append(pa)

    def remove_pseudoaction_from_list(self, pa):
        """
        La pseudo action a été traitée
        """
        if pa in self._palist:
            self._palist.remove(pa)

    def get_pseudoactions_count(self):
        """
        Retourne le nombre d'actions enregistrées
        """
        return len(self._palist)

    def get_pseudoaction_list(self):
        """
        Retourne une copie de la liste des pseudos actions
        """
        return self._palist

    def __repr__(self):
        return "paObj : name={} searchctx={} securestop={} secureissue={} gamblecount={} bonuscount={} relevantfactor={} score={}".format(
            self.name,
            self.searchctx,
            self.securestop,
            self.secureissue,
            self.gamblecount,
            self.bonuscount,
            self.relevantfactor,
            self.score,
        )


class GambleSearch:
    """
    Contexte de définition d'un coup.
    """

    def __init__(self):
        """
        Constructeur
        """
        # nombre d'actions maxi
        self.maxactions = 0
        # liste d'objectifs priorisés
        self.objectifs = None
        # possibilités :
        # - de déplacement sécurisé
        self.safe_move_possible = False
        # - d'attaque
        self.attaque_possible = False
        self.list_attaque = None
        # - nécessité de se défendre
        self.defense_needed = False
        self.list_defense = None
        # objectifs traités
        self.free_sortie_tried = False
        self.optimal_move_tried = False
        self.safe_move_tried = False
        self.defense_tried = False
        self.attaque_tried = False
        self.bonus_tried = False
        # mémorisation des adversaires ayant fait l'objet d'une recherche
        # offensive (pour attaque ou défense)
        self._kill_search_done = list()
        # liste des objets PseudoActions concurrents
        self.paObjlist = list()

    #-----> Mémorisation des recherches d'attaque
    def register_kill_search(self, robot):
        """
        Mémorise que le robot a été évalué pour une action offensive
        """
        self._kill_search_done.append(robot)

    def kill_search_already_done(self, robot):
        """
        Indique si une recherche offensive a déja été effectuée pour le robot
        """
        return robot in self._kill_search_done
