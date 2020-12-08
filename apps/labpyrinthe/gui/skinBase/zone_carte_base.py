#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Carte (labyrinthe) : logique applicative.
Implémentation générique de ZoneCarteBase.

Remarque : le recyclage d'items a été testé et abandonné, n'apportant pas (Pygame) ou
très peu (Tkinter) de gains de performances au prix d'un surplus de tests dans les algos.

"""
# imports :
import math
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import LabHelper
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractZoneCarte

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ZoneCarteBase", "ItemObjectBase"]
# classes :
class ZoneCarteBase(AbstractZoneCarte):
    """
    Zone carte (labyrinthe), équivalent graphique du LabLevel.
    """

    # params statiques :
    # noms des couches associées aux "formes vectos" (pouvant être instanciées
    # sous forme d'image)
    SHAPE_BG = "SHAPE_BG" #: couche de formes vectorielles
    SHAPE_MASK = "SHAPE_MASK" #: couche de formes vectorielles
    SHAPE_HIGHLIGHT_ROBOT = "SHAPE_HIGHLIGHT_ROBOT" #: couche de formes vectorielles
    # nom de la couche associée aux zones robots (représentant la zone d'influence
    # d'un robot)
    IMAGE_ZONE_ROBOT = "IMAGE_ZONE_ROBOT" #: couche dédiée aux zones d'action des robots
    # couche de base des cases
    BASE_CASE_LAYER = "BASE_CASE_LAYER" #: couche de base des cases
    # types de cases de la couche de base
    BASE_LAYER_TYPECASES = None #: types des cases de la couche de base
    # méthodes
    def __init__(self, Mngr, skin, ItemObjectClass, **kwargs):
        """
        Constructeur
        
        Args:
            ItemObjectClass : implémentation dédiée de ItemObjectBase
            kwargs : logperf (bool: indique si l'on mesure les perfs d'affichage), 
                max_casesize (int: par défaut 40)
        
        """
        # ZonePartie :
        self.Mngr = Mngr
        # GUI :
        self.guiMngr = None
        # Skin :
        self.skin = skin
        # couleurs :
        self._init_colors()
        #  implémentation dédiée de ItemObjectBase :
        self.ItemObjectClass = ItemObjectClass
        if "max_casesize" in kwargs and isinstance(kwargs["max_casesize"], int):
            self.max_casesize = kwargs["max_casesize"]
        else:
            self.max_casesize = 40
        # Données de publication :
        self.carte_published = False
        self.lastcontentdict = None
        self.carte_dimensions_initialized = False
        self.carte_dimensions = (None, None)
        self.carte_repere = (None, None)
        self.casesize = (None, None)
        self.highlighted_bot = None
        # Structure interne :
        self.layersdict = None
        self.casetype_datas = None
        self.layers_by_dict = None
        self.layers_of_shapes = None
        self.zindexslist = None
        self._init_virtual_layers()

    def register_GUI(self, guiMngr):
        """
        Enregistre la ref à la GUI
        """
        self.guiMngr = guiMngr

    def _init_colors(self):
        """
        Couleurs portées par le skin :
        """
        self.color_bg_lab = self.skin.get_color("carte", "bg_lab")

    def re_initialise(self):
        """
        Ré initialise l'objet
        """
        # efface la carte :
        self.clear_all()
        # dict d'associations case/items
        self.init_layersdict()
        # Données de publication :
        self.carte_published = False
        self.lastcontentdict = None
        self.carte_dimensions_initialized = False
        self.carte_dimensions = (None, None)
        self.carte_repere = (None, None)
        self.casesize = (None, None)
        self.highlighted_bot = None

    #-----> Initialisation des couches
    def _init_virtual_layers(self):
        """
        Initialise les différentes couches virtuelles
        """
        # dimensions de la carte :
        self.carte_dimensions_initialized = False
        # structure des couches virtuelles :
        # types de cases constituant la couche de base
        ZoneCarteBase.BASE_LAYER_TYPECASES = [
            LabHelper.CASE_MUR_PERIMETRE,
            LabHelper.CASE_SORTIE,
            LabHelper.CASE_VIDE,
            LabHelper.CASE_PORTE,
            LabHelper.CASE_MUR,
        ]
        # z indexs et noms des couches:
        self.zindexslist = [
            {"z": 0, "typecontent": "shape", "name": ZoneCarteBase.SHAPE_BG},
            {"z": 1, "typecontent": "image", "name": ZoneCarteBase.BASE_CASE_LAYER},
            {"z": 2, "typecontent": "image", "name": LabHelper.CASE_DANGER},
            {"z": 3, "typecontent": "image", "name": LabHelper.CASE_BONUS},
            {"z": 4, "typecontent": "image", "name": ZoneCarteBase.IMAGE_ZONE_ROBOT},
            {
                "z": 5,
                "typecontent": "shape",
                "name": ZoneCarteBase.SHAPE_HIGHLIGHT_ROBOT,
            },
            {"z": 6, "typecontent": "image", "name": LabHelper.CASE_ROBOT},
            {"z": 7, "typecontent": "image", "name": LabHelper.CASE_GRENADE},
            {"z": 8, "typecontent": "image", "name": LabHelper.CASE_ANIMATION},
            {"z": 9, "typecontent": "image", "name": LabHelper.CASE_TARGET},
            {"z": 10, "typecontent": "image", "name": LabHelper.CASE_DEBUG},
            {"z": 11, "typecontent": "shape", "name": ZoneCarteBase.SHAPE_MASK},
        ]
        # dicts d'association cases/items :
        self.layers_of_shapes = [
            ZoneCarteBase.SHAPE_BG,
            ZoneCarteBase.SHAPE_HIGHLIGHT_ROBOT,
            ZoneCarteBase.SHAPE_MASK,
        ]
        self.layers_by_dict = [
            ZoneCarteBase.BASE_CASE_LAYER,
            LabHelper.CASE_DANGER,
            LabHelper.CASE_BONUS,
            ZoneCarteBase.IMAGE_ZONE_ROBOT,
            LabHelper.CASE_ROBOT,
            LabHelper.CASE_GRENADE,
            LabHelper.CASE_ANIMATION,
            LabHelper.CASE_TARGET,
        ]
        self.layersdict = dict()
        self.init_layersdict(firstinit=True)
        # références rapides type de case / layername et zindex
        self.casetype_datas = dict()
        self.init_casetype_datas()
        # activation des couches :
        for dictlayer in self.zindexslist:
            name = dictlayer["name"]
            z = dictlayer["z"]
            self.active_single_layer(name, z)
        # Formes :
        self.draw_shapes()

    def init_layersdict(self, firstinit=False):
        """
        Ré initialise le dict d'association cases / items
        """
        for dictlay in self.zindexslist:
            # références aux items
            layername = dictlay["name"]
            if layername in self.layers_by_dict:
                # association par clefs :
                self.layersdict[layername] = dict()
            elif layername not in self.layers_of_shapes or firstinit:
                # liste (sera peu utilisé)
                self.layersdict[layername] = list()

    def init_casetype_datas(self):
        """
        Références rapides type de case / layername et zindex
        """
        for dictlay in self.zindexslist:
            if dictlay["typecontent"] == "image":
                z = dictlay["z"]
                name = dictlay["name"]
                if name == ZoneCarteBase.BASE_CASE_LAYER:
                    for tc in ZoneCarteBase.BASE_LAYER_TYPECASES:
                        self.casetype_datas[tc] = {"z": z, "name": name}
                else:
                    self.casetype_datas[name] = {"z": z, "name": name}

    def active_single_layer(self, layername, z):
        """
        Post initialisation d'une couche :
        
        * pour activer la couche de façon permanente (pygame)
        * pour insérer un marqueur de gestion des zindexs (tkinter)
        
        """
        # à subclasser

    #-----> Dimensions
    def get_canvas_dimensions(self):
        """
        Retourne les dimensions de l'objet graphique implémentant ZoneCarteBase
        """
        # à subclasser

    def init_carte_dimensions(self, w, h):
        """
        Initialise les dimensions de la carte au premier affichage
        """
        cw, ch = self.get_canvas_dimensions()
        self.carte_dimensions = (w, h)
        self.carte_dimensions_initialized = True
        # taille des cases :
        self.casesize = self.compute_caze_size(cw, ch)
        # ref x,y :
        self.carte_repere = self.compute_delta_coords(cw, ch)
        # callback
        self.on_carte_geometry_updated()

    def compute_caze_size(self, cw, ch):
        """
        Retourne la taille des cases si le canvas mesure cw*ch
        """
        w, h = self.carte_dimensions
        if (w, h) != (None, None):
            wfactor = cw // w
            hfactor = ch // h
            dim = min(wfactor, hfactor)
            if dim < self.max_casesize:
                casesize = (dim, dim)
            else:
                casesize = (self.max_casesize, self.max_casesize)
            return casesize
        return (None, None)

    def compute_delta_coords(self, cw, ch):
        """
        Calcul les décallages dx, dy à appliquer aux cases pour les centrer
        si le canvas mesure cw*ch
        """
        w, h = self.carte_dimensions
        x = math.ceil((cw - w * self.casesize[0]) / 2)
        y = math.ceil((ch - h * self.casesize[1]) / 2)
        return (x, y)

    #-----> Resize tools
    def clean_before_resize(self):
        """
        Ré-initialisations avant re-publication suite à un resize.
        """
        self.carte_dimensions_initialized = False

    def update_carte_geometry(self, w, h):
        """
        Méthode de resize de la carte. 
        Recalcul de la taille des cases et du repère de positionnement,
        déclenche au besoin les callbacks de modification des dimensions et du
        positionnement des cases. 
        
        Args:
            (w, h) : surface alouée à la carte
        """
        if self.carte_published:
            if not self.carte_dimensions_initialized:
                dochange = False
                listitems = self.get_all_items()
                # taille des cases :
                prev_size = None, None
                if self.casesize != (None, None):
                    prev_size = int(self.casesize[0]), int(self.casesize[1])
                self.casesize = self.compute_caze_size(w, h)
                if self.casesize != prev_size:
                    dochange = True
                    self.on_case_size_changed(listitems)
                # ref x,y :
                prev_repere = None, None
                if self.carte_repere != (None, None):
                    prev_repere = int(self.carte_repere[0]), int(self.carte_repere[1])
                self.carte_repere = self.compute_delta_coords(w, h)
                if self.carte_repere != prev_repere:
                    dochange = True
                    self.on_carte_repere_changed(listitems)
                # application :
                if dochange:
                    # resize des formes :
                    self.update_shapes()
                    # resize des items :
                    self.resize_items(listitems)
                # marqueur
                self.carte_dimensions_initialized = True
                # callback
                self.on_carte_geometry_updated()

    def on_carte_geometry_updated(self):
        """
        Appelée lorsque self.casesize et self.carte_repere ont
        été recalculés
        """
        # à subclasser

    def on_case_size_changed(self, listitems):
        """
        Appelée lorsque la taille des cases a été modifiée.
        """
        # mise à jour de la vue graphique des cases
        for itemobj in listitems:
            self.update_item_view(itemobj)

    def on_carte_repere_changed(self, listitems):
        """
        Appelée lorsque le repère de positionnement a été modifié.
        """
        # mise à jour de la position des cases
        for itemobj in listitems:
            self.set_item_position(itemobj)

    def resize_items(self, listitems):
        """
        Appelle la méthode de resize des items si nécessaire.
        """
        # appel à une éventuelle méthode de resize des objets graphiques
        pass

    def show_resize_screen(self):
        """
        Affichage d'un écran d'attente
        """
        if self.carte_published:
            self.Mngr.on_resize_start()

    def hide_resize_screen(self):
        """
        Masquage de l'écran d'accueil
        """
        if self.carte_published:
            self.Mngr.on_resize_end()

    #-----> Gestion des formes vecto
    def draw_shapes(self):
        """
        Dessine les formes vectorielles
        """
        # cercles de highlight :
        self.draw_bot_highlights()
        # fond éventuel :
        self.draw_bg()
        # masque :
        self.draw_mask()

    def draw_bot_highlights(self):
        """
        Dessinne les éventueles formes de highlight des bots
        """
        # à subclasser

    def draw_mask(self):
        """
        Dessine un masque ne laissant apparaitre que le labyrinthe (clipping manuel). 
        Couche : layer = self.layersdict[ZoneCarteBase.SHAPE_MASK]
        """
        # à subclasser

    def draw_bg(self):
        """
        Crée le rectangle de fond en mode optimisé. 
        Couche : layer = self.layersdict[ZoneCarteBase.SHAPE_BG]
        """
        # à subclasser

    def highlight_player(self, robotlist, gambleinfos):
        """
        Identification du prochain joueur
        """
        # à subclasser

    def get_bot_highlight_datas(self, robotlist, gambleinfos):
        """
        Retourne les données de highlight du joueur actif
        """
        rdict = {
            "cbot": None,
            "color": None,
            "x0_b": None,
            "y0_b": None,
            "x0_a": None,
            "y0_a": None,
            "x1_b": None,
            "y1_b": None,
            "x1_a": None,
            "y1_a": None,
        }
        if gambleinfos != None:
            uid = gambleinfos["uid"]
            totalcoups = int(gambleinfos["total_coups"])
            # recherche du joueur courant :
            cbot = None
            if uid != None:
                for c in robotlist:
                    if c.uid == uid and c.alive:
                        cbot = c
                        break
            if cbot != None and self.casesize != (None, None):
                self.highlighted_bot = cbot
                rdict["cbot"] = cbot
                rdict["color"] = cbot.color
                # geom :
                xr, yr = cbot.x + 0.5, cbot.y + 0.5
                # coords non converties :
                x0_b, y0_b = xr - math.sqrt(2) / 2, yr - math.sqrt(2) / 2
                x0_a, y0_a = (
                    xr - totalcoups * math.sqrt(2) / 2,
                    yr - totalcoups * math.sqrt(2) / 2,
                )
                x1_b, y1_b = xr + math.sqrt(2) / 2, yr + math.sqrt(2) / 2
                x1_a, y1_a = (
                    xr + totalcoups * math.sqrt(2) / 2,
                    yr + totalcoups * math.sqrt(2) / 2,
                )
                # conversion :
                rdict["x0_b"], rdict["y0_b"] = (
                    x0_b * self.casesize[0] + self.carte_repere[0],
                    y0_b * self.casesize[1] + self.carte_repere[1],
                )
                rdict["x0_a"], rdict["y0_a"] = (
                    x0_a * self.casesize[0] + self.carte_repere[0],
                    y0_a * self.casesize[1] + self.carte_repere[1],
                )
                rdict["x1_b"], rdict["y1_b"] = (
                    x1_b * self.casesize[0] + self.carte_repere[0],
                    y1_b * self.casesize[1] + self.carte_repere[1],
                )
                rdict["x1_a"], rdict["y1_a"] = (
                    x1_a * self.casesize[0] + self.carte_repere[0],
                    y1_a * self.casesize[1] + self.carte_repere[1],
                )
            else:
                self.highlighted_bot = None
        return rdict

    def update_shapes(self):
        """
        Mise à jour des formes
        """
        # cercles de highlight :
        self.update_highlight()
        # fond éventuel :
        self.update_bg()
        # masque :
        self.update_mask()

    def update_highlight(self):
        """
        Mise à jour des formes de highlight
        """
        if self.lastcontentdict != None:
            robotlist = self.lastcontentdict["robots"]
            gambleinfos = None
            if "gambleinfos" in self.lastcontentdict.keys():
                gambleinfos = self.lastcontentdict["gambleinfos"]
            self.highlight_player(robotlist, gambleinfos)

    def update_mask(self):
        """
        Redimensionnement du masque ou du clipping
        """
        # à subclasser

    def update_bg(self):
        """
        Met à jour le rectangle de fond permettant de simuler
        le quadrillage
        """
        # à subclasser

    #-----> Publication de la carte
    def publish_carte(self, dictargs):
        """
        Affichage de la carte : publication complète
        
        Args:
            dictargs : dict généré par GameManager.publish_carte
        """
        # mémorisation
        self.lastcontentdict = dictargs
        # params :
        w, h = dictargs["w"], dictargs["h"]
        listmatrices = [
            dictargs["matrices"]["mat_base"],
            dictargs["matrices"]["mat_dangers"],
            dictargs["matrices"]["mat_bonus"],
            dictargs["matrices"]["mat_robots"],
            dictargs["matrices"]["mat_grenade"],
            dictargs["matrices"]["mat_target"],
            dictargs["matrices"]["animlay_animation"],
        ]
        if "animlay_debug" in dictargs["matrices"].keys():
            self.clear_layer(LabHelper.CASE_DEBUG)
            listmatrices.append(dictargs["matrices"]["animlay_debug"])
        # dimensions :
        if not self.carte_dimensions_initialized:
            self.init_carte_dimensions(w, h)
        # ré init couche animation :
        self.clear_layer(LabHelper.CASE_ANIMATION)
        # Formes :
        self.update_shapes()
        # publication statique:
        nbchange = 0
        for mat in listmatrices:
            lc = mat.get_list_cases()
            for c in lc:
                self.set_case(c)
                nbchange += 1
        # post traitement spécifique :
        self.on_carte_published()
        self.carte_published = True
        # Callback parent (Partie) :
        self.Mngr.on_carte_published()

    def on_carte_published(self):
        """
        Traitements spécifiques en fin de publication.
        """
        # à subclasser

    #-----> Publication réduite :
    def update_carte(self, dictargs):
        """
        Mise à jour de la carte à partir des change logs d'étape.
        
        Args:
            dictargs : dict généré par GameManager.update_carte
        """
        nbchange = 0
        has_anim = False
        diffdatas = dictargs["updatedict"]
        # liste des cases ajoutées ou modifiées
        add_list = diffdatas["cases_added"]
        if len(add_list) > 0:
            for c in add_list:
                self.set_case(c)
                nbchange += 1
        # liste des cases supprimées
        del_list = diffdatas["cases_deleted"]
        if len(del_list) > 0:
            for c in del_list:
                self.delete_case(c)
        # liste des cases déplacées :
        if LabHelper.ANIMATION_RESOLUTION != LabHelper.ANIMATION_RESOLUTION_PIXEL:
            # Rq : les animations par pixels sont gérées par GUIBase
            move_list = diffdatas["cases_moved"]
            if len(move_list) > 0:
                has_anim = True
                for c in move_list:
                    self.set_case(c)
                    nbchange += 1
        # liste de typecases ayant fait l'objet d'un clear
        clear_tc_list = diffdatas["cleared_typecases"]
        if len(clear_tc_list) > 0:
            for name in clear_tc_list:
                if name in self.layersdict.keys():
                    self.clear_layer(name)
        # liste des cases d'animation à créer ou modifier
        anim_list = diffdatas["cases_anim"]
        if len(anim_list) > 0:
            has_anim = True
            for c in anim_list:
                self.set_case(c)
                nbchange += 1
        # post traitement spécifique :
        self.on_carte_updated(dictargs, has_anim)

    def on_carte_updated(self, dictargs, has_anim):
        """
        Traitements spécifiques en fin de publication.
        
        Args:
            dictargs : dict généré par GameManager.update_carte
            has_anim : bool indiquant si il y a animation  
        """
        # à subclasser

    def set_case(self, case):
        """
        Crée ou modifie un item pour afficher la case
        """
        # Recherche de l'item associé
        previtem = self.get_item_for_case(case)
        # Création ou modification :
        if previtem == None:
            # création :
            newitem = self._create_itemObj_for_case(case)
        else:
            # modification:
            self._update_item_with_case(previtem, case)
            newitem = previtem
        # Enregistrement :
        self._register_item(case, newitem)
        return newitem

    def move_case(self, case, x, y):
        """
        Déplace la case aux coordonnées x, y
        """
        item = self.get_item_for_case(case)
        if item == None:
            item = self.set_case(case)
        xr, yr = self.convert_case_coords(x, y)
        item.set_real_coords(xr, yr)

    def delete_case(self, case):
        """
        Suppression d'une case
        """
        item = self.get_item_for_case(case)
        if item != None:
            layername = self.get_layername_for_case(case)
            if layername not in self.layers_of_shapes:
                item.delete_view()
            else:
                item.set_visible(False)
            # association :
            self._un_register_item(case, item)

    def show_bot_dead(self, robot):
        """
        Appelée pour lors de l'élimination de robot.
        """
        # à subclasser

    #-----> Gestion des items :
    def _register_item(self, case, item):
        """
        Enregistrement d'un item
        """
        layername = self.get_layername_for_case(case)
        # association :
        if layername in self.layers_by_dict:
            # association par clefs :
            itdict = self.layersdict[layername]
            if layername == LabHelper.CASE_ROBOT:
                itkey = case.uid
            elif layername == LabHelper.CASE_GRENADE:
                itkey = case.cuid
            else:
                # par défaut la clef est (x, y)
                itkey = (case.x, case.y)
            itdict[itkey] = item
        else:
            # liste d'items :
            itlist = self.layersdict[layername]
            if item not in itlist:
                itlist.append(item)

    def _un_register_item(self, case, item):
        """
        Supprime la référence à un item
        """
        layername = self.get_layername_for_case(case)
        # association :
        if layername in self.layers_by_dict:
            # association par clefs :
            itdict = self.layersdict[layername]
            if layername == LabHelper.CASE_ROBOT:
                itkey = case.uid
            elif layername == LabHelper.CASE_GRENADE:
                itkey = case.cuid
            elif layername == ZoneCarteBase.IMAGE_ZONE_ROBOT:
                # clef = uid de la case robot associée
                itkey = case.uid
            else:
                # par défaut la clef est (x, y)
                itkey = (case.x, case.y)
            itdict.pop(itkey)
        else:
            # liste d'items :
            itlist = self.layersdict[layername]
            if item in itlist:
                itlist.remove(item)

    def get_item_for_case(self, case):
        """
        Retourne l'item associé à la case
        """
        try:
            item = self._get_item_for_case_internal(case)
        except:
            item = None
        return item

    def get_layername_for_case(self, case):
        """
        Retourne le nom de la couche associée à la case
        """
        return self.casetype_datas[case.type_case]["name"]

    def get_zindex_for_case(self, case):
        """
        Retourne le zindex associé à une case
        """
        return self.casetype_datas[case.type_case]["z"]

    def get_zindex_for_layername(self, layername):
        """
        Retourne le zindex associé à une couche
        """
        if layername in self.casetype_datas.keys():
            return self.casetype_datas[layername]["z"]
        return None

    def _get_item_for_case_internal(self, case):
        """
        Pour accélérer les traitements on ne vérifie pas l'existence des
        clefs des dicts d'association.
        """
        layername = self.get_layername_for_case(case)
        # recherche
        (x, y) = (case.x, case.y)
        if layername in self.layers_by_dict:
            # association par clefs :
            itdict = self.layersdict[layername]
            if layername == LabHelper.CASE_ROBOT:
                itkey = case.uid
            elif layername == LabHelper.CASE_GRENADE:
                itkey = case.cuid
            else:
                # par défaut la clef est (x, y)
                itkey = (case.x, case.y)
            return itdict[itkey]
        else:
            # liste d'items :
            itlist = self.layersdict[layername]
            for item in itlist:
                if (item.x, item.y) == (x, y):
                    return item
        return None

    def get_all_items(self):
        """
        Retourne la liste de tous les items associés à des cases
        """
        rlist = list()
        for dictlayer in self.zindexslist:
            typecontent = dictlayer["typecontent"]
            if typecontent == "image":
                layername = dictlayer["name"]
                if layername in self.layers_by_dict:
                    itdict = self.layersdict[layername]
                    itvalues = itdict.values()
                    rlist.extend(list(itvalues))
                else:
                    itlist = self.layersdict[layername]
                    rlist.extend(itlist)
        return rlist

    def get_items_for_layer(self, layername):
        """
        Retourne tous les items d'une couche virtuelle
        """
        rlist = None
        if layername in self.layers_by_dict:
            itdict = self.layersdict[layername]
            itvalues = itdict.values()
            rlist = list(itvalues)
        else:
            rlist = self.layersdict[layername]
        return rlist

    def _create_itemObj_for_case(self, case):
        """
        Création d'un ItemObjectBase et de l'item graphique associé
        """
        # item :
        newitem = self.ItemObjectClass(self, case=case, typecontent="image")
        # zindex :
        z = self.get_zindex_for_case(case)
        newitem.set_zindex(z)
        # vue graphique :
        newitem.create_view()
        # mise à jour de l'item :
        self._update_item_with_case(newitem, case)
        # Retour :
        return newitem

    def _update_item_with_case(self, itemobj, case):
        """
        Met à jour l'item (objet et graphique) pour refléter la case
        """
        # case :
        itemobj.set_case(case)
        # vue graphique :
        self.update_item_view(itemobj)
        # autres paramètres :
        itemobj.x = case.x
        itemobj.y = case.y
        # position :
        self.set_item_position(itemobj)
        # visibilité :
        vis = case.visible
        itemobj.set_visible(vis)
        if case.type_case == LabHelper.CASE_ROBOT and not case.alive:
            itemobj.set_visible(False)

    def update_item_view(self, itemobj):
        """
        Mise à jour du contenu graphique associé à l'item
        """
        # image :
        case = itemobj.case
        actual_skinimg = itemobj.get_current_image()
        new_skinimg = self.skin.get_image_for_case(case, self.casesize)
        if actual_skinimg != new_skinimg:
            itemobj.set_current_image(new_skinimg)

    def set_item_position(self, itemobj):
        """
        Repositionne un item
        """
        case = itemobj.case
        xg, yg = self.get_real_coords_for_case(case)
        itemobj.set_real_coords(xg, yg)

    def get_real_coords_for_case(self, case):
        """
        Retourne les coords converties associées à la case.
        """
        # optimisation : on ne teste pas l'existence de la case
        # ou les valeurs des coords :
        xg, yg = 0, 0
        try:
            xg, yg = self.convert_case_coords(case.x, case.y)
        except:
            pass
        return xg, yg

    def convert_case_coords(self, x, y):
        """
        Conversion des coords x, y en coords réelles
        """
        dx, dy = self.carte_repere
        xr = math.floor(self.casesize[0] * x + dx)
        yr = math.floor(self.casesize[1] * y + dy)
        return xr, yr

    #-----> Nettoyage
    def clear_all(self):
        """
        Efface l'ensemble des couches
        """
        for layerdict in self.zindexslist:
            layername = layerdict["name"]
            self.clear_layer(layername)

    def clear_layer(self, name):
        """
        Efface une couche virtuelle
        """
        # effacement :
        itemlist = self.get_items_for_layer(name)
        if name not in self.layers_of_shapes:
            for item in itemlist:
                item.delete_view()
        else:
            for item in itemlist:
                item.set_visible(False)
        # ré initialisation de la couche :
        if name in self.layers_by_dict:
            self.layersdict[name] = dict()
        elif name not in self.layers_of_shapes:
            self.layersdict[name] = list()


#-----> Objet modélisant un item graphique de la carte (à subclasser)
class ItemObjectBase:
    """
    Objet modélisant un item graphique de la carte.
    """

    def __init__(
        self, zonecarte, graphobjref=None, typecontent=None, case=None, x=None, y=None
    ):
        """
        Constructeur
        """
        # carte : objet CarteTk parent de l'item graphique associé
        self.zonecarte = zonecarte
        # référence à l'objet graphique réel
        self.graphobjref = graphobjref
        # content : image ou shape
        self.typecontent = typecontent
        # éventuelle case associée
        self.case = case
        # coordonnées théoriques :
        self.x = x
        self.y = y
        # zindex :
        self.z = None
        # ref à l'image générée par le skin:
        self.skinImg = None

    def create_view(self):
        """
        Instancie l'implémentation graphique de self.case, spécifique au moteur de publication. 
        Enregistre l'objet ou un id équivalent dans self.graphobjref
        """
        # à subclasser

    def delete_view(self):
        """
        Supprime la vue graphique de self.case
        """
        # à subclasser

    def get_current_image(self):
        """
        Retourne la référence actuelle à l'image (générée par le skin) ou None.
        """
        return self.skinImg

    def set_case(self, case):
        """
        Met à jour au besoin la case associée.
        """
        if case != self.case:
            self.case = case

    def set_current_image(self, imgskin):
        """
        Affiche une nouvelle image (générée par le skin)
        """
        self.skinImg = imgskin
        # à subclasser

    def get_real_coords(self):
        """
        Retourne les coordonnées réelles (converties / la case) de la vue graphique
        """
        # à subclasser

    def set_real_coords(self, realx, realy):
        """
        Déplace la vue graphique aux coordonnées réelles (converties) realx, realy
        """
        # à subclasser

    def set_visible(self, show):
        """
        Affiche ou masque la vue graphique.
        * show : bool
        """
        # à subclasser

    def set_zindex(self, z):
        """
        Définit la profondeur
        """
        self.z = z
