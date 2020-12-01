#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
**Composants génériques pour pygame** supportant :

- boxmodel, 
- gestion récursive de la profondeur, 
- logique de publication.

Prototype fonctionnel.


**Classes de base non instanciées directement :**

- **BoxModelObject** : 

  - Superclasse de tous les objets positionnables dans le plan.
  - Porte tous les paramètres de position et de dimensions communs aux items terminaux et 
    aux conteneurs.
  - Dispose des méthodes de base de gestion du resize et du display.

- **MetricValue** :

  - Objet utilisé pour manipuler les attributs pouvant être exprimés en pixel ou en %.

- **BoundedMetricValue** :

  - Subclasse de MetricValue supportant des bornes min et max. Utilisé pour les dimensions.

- **VirtualItem** (BoxModelObject) :

  - Superclasse de tous les objets positionnables en "2.5 D" (plan + profondeur)
  - Apporte les attributs et méthodes de base pour la gestion des z-indexs (profondeur) 
  - Ainsi que la mécanique de publication (ajout/retrait d'un conteneur parent).

**Classes instanciables dans une application pygame :**

- **VirtualContainer** (VirtualItem)

  - Conteneur de VirtualItems étendant les méthodes de sa superclasse aux problématiques des 
    conteneurs, notamment support de trois layouts basiques : absolu, layout horizontal, 
    layout vertical.
  - Peut être utilisé dans une application réelle en tant que conteneur léger (ie ne prenant 
    pas en charge le display final de ses éléments sur une surface de publication).
  - Limite : peu adapté à des logiques d'animation puisque n'ayant pas de "surface propre". 
    L'animation devrait être propagée à chacun de ses enfants. Faisable directement pour 
    des déplacements (voir méthodes move et place), plus complexe (et risqué) pour des 
    animations de type alpha, color ou scale.

- **CustomSprite** (VirtualItem, pygame.sprite.DirtySprite)

  - Classe de base de tous les composants terminaux d'une application pygame (image, texte).
  - Hérite des propriétés et méthodes de VirtualItem (boxmodel, z-index, publication) 
  - et de DirtySprite pour l'optimisation du display.

- **RealContainer** (VirtualContainer, pygame.sprite.LayeredDirty)

  - Conteneur "réel" au sens ou celui-ci dispose d'une surface de publication propre sur 
    laquelle est "applatie" l'ensemble de sa hiérarchie.
  - Utilise par composition un LayerManager pour la gestion dynamique et récursive des z-indexs.
  - Hérite de LayeredDirty pour le display optimisé de sa hiérarchie de sprites.

- **RootContainer** (RealContainer, evt.GUIEventManager)

  - Conteneur racine d'une application pygame.
  - Diffère de RealContainer par la nature de sa surface de publication (pygame.display = 
    la surface "définitive" de
    publication pygame).
  - Dispose des méthodes de démarrage/arrêt du thread d'interface.
  - Initie le processus de resize en cas de fenêtre redimensionnable.
  - Dispatch les événements (top->bottom en V1) via les méthodes héritées de 
    events.GUIEventManager.

**Utilitaires de gestion de la profondeur (z-indexs ou layers) :**

Tous les conteneurs possèdent une ou plusieurs couche(s) locale(s), le système garantit 
la cohérence de la projection de ces couches imbriquées sur la liste de couches globales du 
LayeredDirty parent (RealContainer ou RootContainer) assurant la publication de la hiérarchie 
d'objets.

- **LayerManager** : gestionnaire des zindexs, assure la cohérence dynamique des couches 
  des VirtualContainers.
- **LayerStack** : modélisation des couches d'un VirtualContainer
- **LocalLayer** : modélisation d'une couche locale d'un LayerStack

.. note::
    **Implémentation opérationnelle :** voir module :doc:`labpyproject.core.pygame.widgets`

"""
# imports
import os
import re
import math
from fractions import Fraction
import pygame.locals
from operator import itemgetter, attrgetter
import labpyproject.core.pygame.events as evt

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = [
    "BoxModelObject",
    "MetricValue",
    "BoundedMetricValue",
    "VirtualItem",
    "VirtualContainer",
    "CustomSprite",
    "RealContainer",
    "RootContainer",
    "LayerManager",
    "LayerStack",
    "LocalLayer",
]
# classes
#-----> Boxmodel : classes de base
class BoxModelObject:
    """
    **Super classe portant les propriétés et méthodes fondamentales du box model.**
    
    - "position" au sens css du terme soit "fixed", "absolute", "static", "relative"
    - attributs locaux pouvant être exprimés en pixel ou pourcentage :
      "x", "y", "top", "left", "bottom", "right", "width", "height", "padding", "margin"
    - bornage des dimensions : "minwidth", "maxwidth", "minheight", "maxheight"
    - attributs d'alignement : "align", "valign"
    - attributs d'adaptation au contenu : "snapW", "snapH"
    - "flex" (int, default None) : valeur de flexibilité si le conteneur parent impose un
      layout (horizontal ou vertical à l'heure actuelle)

.. admonition:: Remarques:
    
    - l'origine du repère se situe dans le coin haut/gauche, l'axe des absisses est
      orientée vers la droite, celui des ordonnées vers le bas
    - les metrics en % sont calculés par rapport à la surface alouée par le parent
    - à la différence de css, width et height représentent les dimensions totales de la
      box, padding et margin inclus. Les dimensions du contenu et du fond (ou de la bordure),
      pouvant être moindres.
    - padding et margin sont uniformes sur chacun des bords (V1 : allège les calculs)
    - position "fixed" est gérée partiellement par les RealContainers du fait du clipping
      de leur surface de publication.
      
    """

    # propriétés statiques
    # 1- position
    # équivalent de la ppté css position fixed l'élément est positionné relativement à la fenêtre.
    POSITION_FIXED = "fixed"  #: équivalent de la ppté css position fixed, l'élément est positionné relativement à la fenêtre.
    # équivalent de la ppté css position absolute l'élément est positionné relativement à son parent sans "subir" de layout (normal flow css) de sa part.
    POSITION_ABSOLUTE = "absolute"  #: équivalent de la ppté css position absolute, l'élément est positionné relativement à son parent sans "subir" de layout (normal flow css) de sa part.
    # équivalent de la ppté css position static l'élément est positionné selon le layout de son conteneur parent.
    POSITION_STATIC = "static"  #: équivalent de la ppté css position static, l'élément est positionné selon le layout de son conteneur parent.
    # équivalent de la ppté css position relative l'élément est positionné selon le layout de son conteneur parent mais les offsets (left, right, top, bottom) sont ensuite appliqués. Valeur par défaut.
    POSITION_RELATIVE = "relative"  #: équivalent de la ppté css position relative, l'élément est positionné selon le layout de son conteneur parent mais les offsets (left, right, top, bottom) sont ensuite appliqués (valeur par défaut).
    POSITION_VALUES = [
        POSITION_FIXED,
        POSITION_ABSOLUTE,
        POSITION_STATIC,
        POSITION_RELATIVE,
    ]  #: liste des valeurs possibles pour l'attribut position
    # 2- propriétés liées aux dimensions et coordonnées
    METRIC_ATTR = [
        "xabs",
        "yabs",
        "top",
        "left",
        "bottom",
        "right",
        "width",
        "height",
        "padding",
        "margin",
    ]  #: références internes aux attributs de position et de dimension
    ALIGN_ATTR = ["align", "valign"]  #: attributs d'alignements
    SNAP_ATTR = ["snapW", "snapH"]  #: attributs d'adaptation au contenu
    FLEX_ATTR = ["flex"]  #: attribut de flex
    # types d'alignements :
    ALIGN_LEFT = "left"  #: valeur d'alignement
    ALIGN_CENTER = "center"  #: valeur d'alignement
    ALIGN_RIGHT = "right"  #: valeur d'alignement
    VALIGN_TOP = "top"  #: valeur d'alignement
    VALIGN_MIDDLE = "middle"  #: valeur d'alignement
    VALIGN_BOTTOM = "bottom"  #: valeur d'alignement
    # 3- Stratégies de mise à jour des metrics locales :
    SGY_COORD_RELATIVE = (
        "SGY_COORD_RELATIVE"  
    ) #: stratégie de positionnement relative (in flow)
    SGY_COORD_OFFSET = "SGY_COORD_OFFSET"  #: stratégie de positionnement par offsets
    SGY_COORD_ALIGN = "SGY_COORD_ALIGN"  #: stratégie de positionnement par alignement
    SGY_COORD_VALUE = "SGY_COORD_VALUE"  #: stratégie de positionnement par coordonnée
    SGY_DIM_FLEX = "SGY_DIM_FLEX"  #: stratégie de dimensionnement par flex
    SGY_DIM_OFFSETS = "SGY_DIM_OFFSETS"  #: stratégie de dimensionnement par offsets
    SGY_DIM_VALUE = (
        "SGY_DIM_VALUE"  
    ) #: stratégie de dimensionnement par dimension explicite
    # méthodes
    def __init__(self, **kwargs):
        """
        Constructeur
        
        Args:
            **kwargs : peut contenir toutes les propriétés de boxing supportées par BoxModelObject.
        """
        # 1- Initialisations :
        # nom (debug)
        self.name = str(self.__class__.__name__)
        if "name" in kwargs.keys():
            self.name = str(kwargs["name"])
        # propriété de positionnement : relative par défaut
        self._position = None
        # métriques :
        self.metricparams = dict()
        # coordonnées locales absolues:
        self.metricparams["xabs"] = MetricValue(0)
        self.metricparams["yabs"] = MetricValue(0)
        # Coordonnées locales imposées par le layout parent (px)
        self._xflow = 0
        self._yflow = 0
        # Coordonnées locales calculées en fonction de la position :
        self._xpos = 0
        self._ypos = 0
        self._pos_coords_updated = False
        # offsets :
        self.metricparams["left"] = None
        self.metricparams["right"] = None
        self.metricparams["top"] = None
        self.metricparams["bottom"] = None
        # dimensions :
        self.metricparams["width"] = BoundedMetricValue(0)
        self.metricparams["height"] = BoundedMetricValue(0)
        # padding et margin
        self.metricparams["padding"] = MetricValue(0)
        self.metricparams["margin"] = MetricValue(0)
        # metric en cas de stratégie SGY_DIM_FLEX :
        self.metricparams["SGY_DIM_FLEX"] = MetricValue(100, percent=True)
        # alignements:
        self._align = None
        self._valign = None
        # adaptation au contenu :
        self._snapW = False
        self._snapH = False
        # True si snapW ou snapH
        self.do_snap = False
        # Appartenance au flux de layout parent :
        self._in_flow = False
        # valeur de flex :
        self._flex = None
        # Liste des propriétés parsées qui n'ont plus leur valeur par défaut :
        self._non_default_properties = list()
        # Stratégies de mises à jour :
        self.compute_strategies = dict()
        self.compute_strategies["xabs"] = None
        self.compute_strategies["yabs"] = None
        self.compute_strategies["width"] = None
        self.compute_strategies["height"] = None
        # Rects de publication portant les valeurs calculées :
        # Rq : la propriété pygame obj.rect est redirigée vers obj.publicationRect
        self._publicationRect = pygame.Rect(
            0, 0, 0, 0
        )  # données pseudo globales dans le plan du RealContainer assurant la publication
        self._publicationRefRect = pygame.Rect(
            0, 0, 0, 0
        )  # données pseudo globales du plan de référence (parent ou root)
        self._unsnapped_publicationRect = pygame.Rect(
            0, 0, 0, 0
        )  # publication rect avant application du snap :
        # Rect global (par rapport au root), nécessaire pour les tests de collision (cf events)
        self._globalRect = pygame.Rect(0, 0, 0, 0)
        self._globalRect_updated = False
        # Rects internes : surfaces alouées au contenu et aux bordure/fond
        self._inner_rects_valide = False
        # les rect de contenu et bordure sont ils en coords locales ou globales
        self._content_scope_global = True
        self._contentRect = pygame.Rect(0, 0, 0, 0)
        self._borderRect = pygame.Rect(0, 0, 0, 0)
        # Resize :
        self.is_resized = False
        # BoxModelObject parent :
        self._parent = None
        # Référence au RootContainer :
        self._rootreference = None
        # 2- Parsing des propriétés :
        self._init_boxmodel(**kwargs)

    #-----> Initialisations
    def _init_boxmodel(self, **kwargs):
        """
        Initialise les propriétés de boxmodel
        """
        # 1- Position :
        pos = None
        if "position" in kwargs.keys():
            pos = kwargs["position"]
            self._non_default_properties.append("position")
        self.position = pos
        # 2- Parsing des propriétés :
        self.parse_properties(**kwargs)
        # 3- Définition des stratégies de mise à jour :
        self.define_strategy("xabs", "yabs", "width", "height")
        # 4- Post initialisations :
        self.post_control_boxmodel()

    def post_control_boxmodel(self):
        """
        Spécifie au besoin des valeurs par défaut (snaps).
        """
        if self.has_default_value("width") and self.snapW:
            self.width = "100%"
        if self.has_default_value("height") and self.snapH:
            self.height = "100%"

    def parse_position(self, val):
        """
        Parse un attribut de position.
        """
        value = BoxModelObject.POSITION_RELATIVE
        if isinstance(val, str):
            val = str(val).strip().lower()
            if val in BoxModelObject.POSITION_VALUES:
                value = val
        return value

    def parse_properties(self, **kwargs):
        """
        Parse les propriétés présentes dans kwargs.
        """
        for k, v in kwargs.items():
            ik = k  # clef interne
            if k in ["x", "y"]:
                # on ajoute le suffix "abs" indiquant qu'il s'agit d'une coordonnée
                # locale absolue :
                ik = k + "abs"
            if ik in BoxModelObject.METRIC_ATTR:
                if ik == "width":
                    minwidth = maxwidth = None
                    if "minwidth" in kwargs.keys():
                        minwidth = kwargs["minwidth"]
                    if "maxwidth" in kwargs.keys():
                        maxwidth = kwargs["maxwidth"]
                    self.metricparams[str(ik)] = self.parse_boundedmetric(
                        v, minwidth, maxwidth
                    )
                elif ik == "height":
                    minheight = maxheight = None
                    if "minheight" in kwargs.keys():
                        minheight = kwargs["minheight"]
                    if "maxheight" in kwargs.keys():
                        maxheight = kwargs["maxheight"]
                    self.metricparams[str(ik)] = self.parse_boundedmetric(
                        v, minheight, maxheight
                    )
                else:
                    self.metricparams[str(ik)] = self.parse_metric(v)
            elif ik in BoxModelObject.ALIGN_ATTR:
                value = self.parse_alignement(v)
                setattr(self, str(ik), value)
            elif ik in BoxModelObject.SNAP_ATTR:
                value = self.parse_snap(v)
                setattr(self, str(ik), value)
            elif ik in BoxModelObject.FLEX_ATTR:
                value = self.parse_flex(v)
                setattr(self, str(ik), value)
            self._non_default_properties.append(k)

    def has_default_value(self, propname):
        """
        Indique si la propriété de nom propname a une valeur par défaut.
        """
        if propname in self._non_default_properties:
            return False
        return True

    def parse_metric(self, value):
        """
        Parse une propriété de type BoxModelObject.METRIC_ATTR.
        
        Returns:
            un objet MetricValue ou None.
        """
        return MetricValue.parseMetric(value)

    def parse_boundedmetric(self, value, minvalue, maxvalue):
        """
        Parse une propriété de type BoxModelObject.METRIC_ATTR bornée.
        
        Returns:
            un objet BoundedMetricValue ou None.
        """
        return BoundedMetricValue.parseMetric(value, minvalue, maxvalue)

    def parse_alignement(self, value):
        """
        Parse une prorpiété de type BoxModelObject.ALIGN_ATTR.
        
        Returns:
            une valeur (voir ppté statiques) ou None
        """
        if value in [
            BoxModelObject.ALIGN_LEFT,
            BoxModelObject.ALIGN_CENTER,
            BoxModelObject.ALIGN_RIGHT,
        ] or value in [
            BoxModelObject.VALIGN_TOP,
            BoxModelObject.VALIGN_MIDDLE,
            BoxModelObject.VALIGN_BOTTOM,
        ]:
            return value
        return None

    def parse_snap(self, value):
        """
        Parse une propriété de type BoxModelObject.SNAP_ATTR.
        
        Returns:
            boolean
        """
        if isinstance(value, bool) and value == True:
            return True
        return False

    def parse_flex(self, value):
        """
        Parse l'attribut flex.
        """
        if isinstance(value, str) and MetricValue.REGEXP_INT.match(value):
            return abs(int(value))
        if isinstance(value, int):
            return abs(value)
        return None

    def define_strategy(self, *props):
        """
        Définit la stratégie de calcul de la propriété prop parmi (xabs, yabs, width, height).
        """
        for prop in props:
            if prop in ["xabs", "yabs"]:
                self.define_strategy_coord(prop)
            elif prop in ["width", "height"]:
                self.define_strategy_dim(prop)

    def define_strategy_coord(self, prop):
        """
        Stratégie de calcul de coordonnées.
        """
        if prop == "xabs":
            offset_1 = self.metricparams["left"]
            offset_2 = self.metricparams["right"]
            palign = self.align
        else:
            offset_1 = self.metricparams["top"]
            offset_2 = self.metricparams["bottom"]
            palign = self.valign
        # la prop est-elle orthogonale à l'axe de layout?
        orth_axis = False
        if self.in_flow:
            if (
                self.parent.direction == VirtualContainer.DIRECTION_HORIZONTAL
                and prop == "yabs"
            ):
                orth_axis = True
            if (
                self.parent.direction == VirtualContainer.DIRECTION_VERTICAL
                and prop == "xabs"
            ):
                orth_axis = True
        # Par priorité desc :
        if self.in_flow and self.position == BoxModelObject.POSITION_RELATIVE:
            if orth_axis:
                if offset_1 != None or offset_2 != None:
                    self.compute_strategies[prop] = BoxModelObject.SGY_COORD_OFFSET
                elif palign != None:
                    self.compute_strategies[prop] = BoxModelObject.SGY_COORD_ALIGN
                else:
                    self.compute_strategies[prop] = BoxModelObject.SGY_COORD_RELATIVE
            else:
                self.compute_strategies[prop] = BoxModelObject.SGY_COORD_RELATIVE
        elif offset_1 != None or offset_2 != None:
            self.compute_strategies[prop] = BoxModelObject.SGY_COORD_OFFSET
        elif palign != None:
            self.compute_strategies[prop] = BoxModelObject.SGY_COORD_ALIGN
        else:
            self.compute_strategies[prop] = BoxModelObject.SGY_COORD_VALUE

    def define_strategy_dim(self, prop):
        """
        Stratégie de calcul de dimension.
        """
        if prop == "width":
            offset_1 = self.metricparams["left"]
            offset_2 = self.metricparams["right"]
            direct_flow = VirtualContainer.DIRECTION_HORIZONTAL
        else:
            offset_1 = self.metricparams["top"]
            offset_2 = self.metricparams["bottom"]
            direct_flow = VirtualContainer.DIRECTION_VERTICAL
        # Par priorité desc :
        if self.in_flow and self.flex != None and self.parent.direction == direct_flow:
            self.compute_strategies[prop] = BoxModelObject.SGY_DIM_FLEX
        elif offset_1 != None and offset_2 != None:
            self.compute_strategies[prop] = BoxModelObject.SGY_DIM_OFFSETS
        else:
            self.compute_strategies[prop] = BoxModelObject.SGY_DIM_VALUE

    def discard_strategy(self, prop):
        """
        Invalide la stratégie associée à la propriété prop.
        """
        if prop in ["xabs", "yabs", "width", "height"]:
            self.compute_strategies[prop] = None

    #-----> Calculs, mise à jour
    def update_core_metrics(self, refrect):
        """
        Recalcul des metricparams x, y, width, height en fonction du rect de référence refrect
        représentant la surface alouée.
        """
        if refrect == None or refrect.width <= 0 or refrect.height <= 0:
            return False
        # 1- Dimensions :
        self.compute_dims(refrect)
        # 2- actualisation de padding et margin :
        self.compute_spaces(refrect)
        # 3- Coordonnées :
        self.compute_coords(refrect)

    def compute_dims(self, refrect):
        """
        Calcul de width et height en fonction du rect de référence refrect représentant
        la surface alouée.
        """
        self.update_dim("width", refrect)
        self.update_dim("height", refrect)

    def update_dim(self, prop, refrect):
        """
        Calcul de la dimension prop.
        """
        # stratégie de mise à jour :
        if self.compute_strategies[prop] == None:
            self.define_strategy_dim(prop)
        # paramètres de calcul :
        if prop == "width":
            offset_1 = self.metricparams["left"]
            offset_2 = self.metricparams["right"]
            dim = self.metricparams["width"]
            strategy = self.compute_strategies["width"]
            ref_dim = refrect.width
        else:
            offset_1 = self.metricparams["top"]
            offset_2 = self.metricparams["bottom"]
            dim = self.metricparams["height"]
            strategy = self.compute_strategies["height"]
            ref_dim = refrect.height
        # En fonction de la stratégie :
        val = None
        if strategy == BoxModelObject.SGY_DIM_FLEX:
            flexmetric = self.metricparams["SGY_DIM_FLEX"]
            val = flexmetric.get_value(refvalue=ref_dim)
        elif strategy == BoxModelObject.SGY_DIM_OFFSETS:
            val = ref_dim - (
                offset_1.get_value(refvalue=ref_dim)
                + offset_2.get_value(refvalue=ref_dim)
            )
        elif strategy == BoxModelObject.SGY_DIM_VALUE:
            val = dim.get_value(refvalue=ref_dim)
        if val != None:
            val = int(val)
        # enregistrement :
        self.set_metric_value(prop, val)

    def compute_spaces(self, refrect):
        """
        Calcul de padding ou margin.
        
        Rq : ces propriétés étant uniformes sur les 4 bords, on considère
        comme valeur de référence la moyenne des dimensions de refrect.
        """
        refval = math.ceil((refrect.width + refrect.height) / 2)
        # margin (externe) :
        self.update_space("margin", refval)
        # padding (interne) :
        self.update_space("padding", refval)

    def update_space(self, prop, refval):
        """
        Calcul d'une propriété de type padding ou margin.

        """
        # valeur de référence :
        val = self.metricparams[prop].get_value(refvalue=refval)
        # enregistrement :
        self.set_metric_value(prop, val)

    def compute_coords(self, refrect):
        """
        Calcul de xabs et yabs en fonction du rect de référence refrect représentant
        la surface alouée.
        
        RQ : les dimensions doivent être mises à jour auparavant.
        """
        self.update_coord("xabs", refrect)
        self.update_coord("yabs", refrect)

    def update_coord(self, prop, refrect):
        """
        Calcul de la coordonnée prop.
        """
        # stratégie de mise à jour :
        if self.compute_strategies[prop] == None:
            self.define_strategy_coord(prop)
        # paramètres de calcul :
        if prop == "xabs":
            offset_1 = self.metricparams["left"]
            offset_2 = self.metricparams["right"]
            palign = self.align
            coord = self.metricparams["xabs"]
            dim = self.metricparams["width"].get_value()
            strategy = self.compute_strategies["xabs"]
            ref_dim = refrect.width
        else:
            offset_1 = self.metricparams["top"]
            offset_2 = self.metricparams["bottom"]
            palign = self.valign
            coord = self.metricparams["yabs"]
            dim = self.metricparams["height"].get_value()
            strategy = self.compute_strategies["yabs"]
            ref_dim = refrect.height
        # En fonction de la stratégie :
        val = None
        if strategy in [
            BoxModelObject.SGY_COORD_RELATIVE,
            BoxModelObject.SGY_COORD_OFFSET,
        ]:
            val = 0
            if offset_1 != None:
                val = offset_1.get_value(refvalue=ref_dim)
            elif offset_2 != None:
                val = ref_dim - (dim + offset_2.get_value(refvalue=ref_dim))
        elif strategy == BoxModelObject.SGY_COORD_ALIGN:
            if palign in [BoxModelObject.ALIGN_LEFT, BoxModelObject.VALIGN_TOP]:
                val = 0
            elif palign in [BoxModelObject.ALIGN_CENTER, BoxModelObject.VALIGN_MIDDLE]:
                val = math.ceil((ref_dim - dim) / 2)
            elif palign in [BoxModelObject.ALIGN_RIGHT, BoxModelObject.VALIGN_BOTTOM]:
                val = ref_dim - dim
        elif strategy == BoxModelObject.SGY_COORD_VALUE:
            val = coord.get_value(refvalue=ref_dim)
        if val != None:
            val = int(val)
        # enregistrement :
        self.set_metric_value(prop, val)
        # discard des propriétés cachées derrière x et y
        self.discard_pos_coords()

    def get_metric_value(self, prop):
        """
        Retourne la valeur calculée de self.metricparams[prop]
        """
        if prop in self.metricparams.keys():
            return self.metricparams[prop].get_computedvalue()
        return None

    def set_metric_value(self, prop, val):
        """
        Affecte val à la valeur calculée de self.metricparams[prop]
        """
        if prop in self.metricparams.keys() and isinstance(val, int):
            self.metricparams[prop].set_computedvalue(val)

    #-----> Parent :
    def _get_parent(self):
        """VirtualContainer parent"""
        return self._parent

    def _set_parent(self, p):
        self._parent = p
        self.on_parent_changed()

    parent = property(_get_parent, _set_parent)  #: VirtualContainer parent

    def on_parent_changed(self):
        """
        Appelée lorsque la référence au parent est modifiée.
        """
        if self.parent != None:
            if self.parent.direction != None and self.position in [
                BoxModelObject.POSITION_RELATIVE,
                BoxModelObject.POSITION_STATIC,
            ]:
                self.in_flow = True
            else:
                self.in_flow = False
        else:
            self.in_flow = False

    #-----> Appartenance au "flow de layout" parent:
    def _get_in_flow(self):
        """Appartenance au "flow de layout" parent"""
        return self._in_flow

    def _set_in_flow(self, val):
        if isinstance(val, bool) and val != self._in_flow:
            self._in_flow = val
            self.on_in_flow_changed()

    in_flow = property(
        _get_in_flow, _set_in_flow
    )  #: Appartenance au "flow de layout" parent (bool)

    def on_in_flow_changed(self):
        """
        Appelée lorsque l'objet entre ou sort du flux de layout parent.
        """
        # on redéfinit les stratégies :
        self.define_strategy("xabs", "yabs", "width", "height")
        self.discard_resize()

    #-----> Root
    def _get_rootreference(self):
        """Recherche du RootContainer"""
        if self._rootreference == None:
            p = self.parent
            while p != None:
                if isinstance(p, RootContainer):
                    self._set_rootreference(p)
                    break
                p = p.parent
        return self._rootreference

    def _set_rootreference(self, rootcont):
        self._rootreference = rootcont

    root_reference = property(
        _get_rootreference, _set_rootreference
    )  #: référence au RootContainer

    #-----> Rects de publication
    def re_initialise_rects(self):
        """
        Ré initialisation des rects, conserve le paramétrage (métrics, alignements, snap).
        """
        self.publicationRect = pygame.Rect(0, 0, 0, 0)
        self.publicationRefRect = pygame.Rect(0, 0, 0, 0)
        self._unsnapped_publicationRect = pygame.Rect(0, 0, 0, 0)
        self.discard_inner_rects()
        self.discard_globalRect()

    def _get_publicationRect(self):
        """Rect de publication de l'objet."""
        return self._publicationRect

    def _set_publicationRect(self, val):
        if isinstance(val, pygame.Rect):
            self._publicationRect = val

    publicationRect = property(
        _get_publicationRect, _set_publicationRect
    )  #: Rect de publication de l'objet

    def _get_publicationRefRect(self):
        """Rect de publication de référence (celui du parent en général)."""
        return self._publicationRefRect

    def _set_publicationRefRect(self, val):
        if isinstance(val, pygame.Rect):
            newcoords = (int(val.x), int(val.y))
            oldcoords = (
                int(self._publicationRefRect.x),
                int(self._publicationRefRect.y),
            )
            newdims = (int(val.width), int(val.height))
            olddims = (
                int(self._publicationRefRect.width),
                int(self._publicationRefRect.height),
            )
            if newdims != olddims:
                self._publicationRefRect.x = newcoords[0]
                self._publicationRefRect.y = newcoords[1]
                self._publicationRefRect.width = newdims[0]
                self._publicationRefRect.height = newdims[1]
                self.on_publicationRefRect_dims_changed()
            elif newcoords != oldcoords:
                self._publicationRefRect.x = newcoords[0]
                self._publicationRefRect.y = newcoords[1]
                self.on_publicationRefRect_coords_changed()

    publicationRefRect = property(
        _get_publicationRefRect, _set_publicationRefRect
    )  #: Rect de publication de référence (celui du parent en général).

    def _get_unsnapped_publicationRect(self):
        """Rect de publication avant adaptation au contenu."""
        return self._unsnapped_publicationRect

    def _set_unsnapped_publicationRect(self, val):
        if isinstance(val, pygame.Rect):
            self._unsnapped_publicationRect = val

    unsnapped_publicationRect = property(
        _get_unsnapped_publicationRect, _set_unsnapped_publicationRect
    )  #: Rect de publication avant adaptation au contenu.

    def update_publicationRefRect_coords(self, x, y):
        """
        Modification des coordonnées seules du rect de publication de référence.
        """
        newcoords = int(x), int(y)
        oldcoords = (int(self._publicationRefRect.x), int(self._publicationRefRect.y))
        if newcoords != oldcoords:
            self._publicationRefRect.x = newcoords[0]
            self._publicationRefRect.y = newcoords[1]
            self.on_publicationRefRect_coords_changed()

    def on_fixed_child_parent_coords_changed(self):
        """
        Méthode dédiée aux éléments en position fixed, appelée par le container
        parent alternativement à update_publicationRefRect_coords.
        """
        if self.position == BoxModelObject.POSITION_FIXED:
            self.publicationRect.x = self.x + self.publicationRefRect.x
            self.publicationRect.y = self.y + self.publicationRefRect.y
            # offsets compensant les coords globales du parent
            if self.parent != None:
                pgx, pgy = self.parent.get_global_coords()
                self.publicationRect.x -= pgx
                self.publicationRect.y -= pgy
            self.on_publicationRect_coords_changed(False)

    def on_publicationRefRect_dims_changed(self):
        """
        Appelée lorsque les dimensions du rect de publication de référence
        (self._publicationRefRect) ont été modifiées (et éventuellement
        les coordonnées aussi).
        """
        # [Keep for debug] print("BMO|",self.name," on_publicationRefRect_dims_changed ! publicationRefRect=",self.publicationRefRect)
        # invalidation du resize :
        self.discard_resize()

    def on_publicationRefRect_coords_changed(self):
        """
        Appelée lorsque les coordonnées du rect de publication de référence
        (self._publicationRefRect) ont été modifiées (mais pas les dimensions).
        """
        # [Keep for debug] print("BMO|",self.name," on_publicationRefRect_coords_changed !")
        # maj des coords de self.publicationRect et de x et y
        self.update_pos_coords()
        # invalidation des rects internes :
        self.discard_inner_rects()
        # et du display
        self.discard_display()

    def _get_rect(self):
        """"Redirige la propriété rect vers self.publicationRect"""
        return self.publicationRect

    def _set_rect(self, val):
        # read-only, la vraie valeur est self.publicationRect
        pass

    rect = property(
        _get_rect, _set_rect
    )  #: Redirige la propriété rect vers self.publicationRect

    #-----> Surfaces alouées internes
    def discard_inner_rects(self):
        """
        Invalide les rects de publication interne (contenu et bordure).
        """
        self._inner_rects_valide = False

    def update_inner_rects(self):
        """
        Met à jour les rects de publication interne (contenu et bordure).
        """
        # contenu :
        self.update_content_rect()
        # border / bg :
        self.update_border_rect()
        # indicateur d'update
        self._inner_rects_valide = True

    def update_content_rect(self):
        """
        Met à jour le rect de contenu.
        """
        p = self.padding
        m = self.margin
        self._contentRect.x = p + m
        self._contentRect.y = p + m
        if self._content_scope_global:
            self._contentRect.x += self.publicationRect.x
            self._contentRect.y += self.publicationRect.y
        wc, hc = self.publicationRect.width, self.publicationRect.height
        self._contentRect.w = wc - 2 * (p + m)
        self._contentRect.h = hc - 2 * (p + m)

    def update_border_rect(self):
        """
        Met à jour le rect de bordure/fond.
        """
        m = self.margin
        self._borderRect.x = m
        self._borderRect.y = m
        if self._content_scope_global:
            self._borderRect.x += self.publicationRect.x
            self._borderRect.y += self.publicationRect.y
        self._borderRect.w = self.publicationRect.width - 2 * m
        self._borderRect.h = self.publicationRect.height - 2 * m

    def get_content_rect(self):
        """
        Retourne le Rect dédié à l'affichage du contenu, une
        fois margin et padding retirés.
        """
        if not self._inner_rects_valide:
            self.update_inner_rects()
        return self._contentRect

    def get_border_rect(self):
        """
        Retourne le Rect dédié à l'affichage d'une bordure ou d'un fond
        une fois margin retirée.
        """
        if not self._inner_rects_valide:
            self.update_inner_rects()
        return self._borderRect

    #-----> Rect de référence absolue
    def _get_globalRect(self):
        """Rect de référence absolu."""
        if not self._globalRect_updated:
            self.update_globalRect()
        return self._globalRect

    def _set_globalRect(self, val):
        if isinstance(val, pygame.Rect):
            self._globalRect = val

    globalRect = property(
        _get_globalRect, _set_globalRect
    )  #: Rect de référence absolu.

    def discard_globalRect(self):
        """
        Invalide le rect global.
        """
        self._globalRect_updated = False

    def update_globalRect(self):
        """
        Mise à jour du rect global.
        """
        rx, ry = self.get_global_coords()
        self._globalRect.x = rx
        self._globalRect.y = ry
        self._globalRect.width = self.rect.width
        self._globalRect.height = self.rect.height
        self._globalRect_updated = True

    def get_global_coords(self):
        """
        Retourne la position absolue exacte par rapport au Root.
        """
        gx, gy = self.rect.x, self.rect.y
        if self.root_reference != None:
            p = self.parent
            while p != None:
                px, py = p.get_scope_delta_coords()
                gx += px
                gy += py
                p = p.parent
        return gx, gy

    def get_scope_delta_coords(self):
        """
        Retourne le décallage dx, dy induit par le scope de contenu de cet objet.
        """
        dx, dy = 0, 0
        if not self._content_scope_global:
            dx += self.publicationRect.x
            dy += self.publicationRect.y
        return dx, dy

    #-----> Position
    def _get_position(self):
        """Position au cens css."""
        return self._position

    def _set_position(self, val):
        val = self.parse_position(val)
        if val != self._position:
            self._position = val
            self.on_position_changed(self._position)

    position = property(_get_position, _set_position)  #: Position au cens css.

    def on_position_changed(self, newposition):
        """
        Appelée lorsque l'attribut position a été modifié.
        """
        self.discard_resize()
        if newposition == BoxModelObject.POSITION_FIXED:
            root = self.root_reference
            if root != None:
                self.publicationRefRect = root.get_content_rect()
        # layout parent :
        if self.parent != None:
            self.parent.on_child_position_changed(self)

    #-----> Coordonnées locales absolues (hors flow de layout)
    def _get_xabs(self):
        """Abcisse locale absolue (hors flow de layout)."""
        return self.metricparams["xabs"].get_value()

    def _set_xabs(self, val):
        newmetric = self.parse_metric(val)
        oldmetric = self.metricparams["xabs"]
        if newmetric != None and newmetric != oldmetric:
            self.metricparams["xabs"] = newmetric
            self.on_abs_coord_changed("xabs")

    xabs = property(
        _get_xabs, _set_xabs
    )  #: Abcisse locale absolue, hors flow de layout (usage interne).

    def _get_yabs(self):
        """Ordonnée locale absolue (hors flow de layout)."""
        return self.metricparams["yabs"].get_value()

    def _set_yabs(self, val):
        newmetric = self.parse_metric(val)
        oldmetric = self.metricparams["yabs"]
        if newmetric != None and newmetric != oldmetric:
            self.metricparams["yabs"] = newmetric
            self.on_abs_coord_changed("yabs")

    yabs = property(
        _get_yabs, _set_yabs
    )  #: Ordonnée locale absolue, hors flow de layout (usage interne).

    def on_abs_coord_changed(self, prop):
        """
        Appelée lors d'un changement explicite de coordonnée absolue.
        """
        self.discard_strategy(prop)
        self.discard_pos_coords()

    #-----> Coordonnées locales imposées par le layout parent :
    def _get_xflow(self):
        """Abcisse locale imposée par le layout parent."""
        return self._xflow

    def _set_xflow(self, val):
        if isinstance(val, int) and val != self.xflow:
            self._xflow = val
            self.on_flow_coord_changed()

    xflow = property(
        _get_xflow, _set_xflow
    )  #: Abcisse locale calculée imposée par le layout parent (usage interne).

    def _get_yflow(self):
        """Ordonnée locale imposée par le layout parent."""
        return self._yflow

    def _set_yflow(self, val):
        if isinstance(val, int) and val != self.yflow:
            self._yflow = val
            self.on_flow_coord_changed()

    yflow = property(
        _get_yflow, _set_yflow
    )  #: Ordonnée locale calculée imposée par le layout parent (usage interne).

    def on_flow_coord_changed(self):
        """
        Appelée lors d'un changement explicite de coordonnée via le layout parent.
        """
        pass

    #-----> Interface d'accès aux coordonnées locales calculées en fonction de la position
    def _get_x(self):
        """Abcisse locale calculée en fonction de l'attribut position."""
        if not self._pos_coords_updated:
            self.update_pos_coords()
        return self._xpos

    def _set_x(self, val):
        if self.in_flow:
            self.xflow = val
        else:
            self.xabs = val

    x = property(_get_x, _set_x)  #: Abcisse locale publique.

    def _get_y(self):
        """Ordonnée locale calculée en fonction de l'attribut position."""
        if not self._pos_coords_updated:
            self.update_pos_coords()
        return self._ypos

    def _set_y(self, val):
        if self.in_flow:
            self.yflow = val
        else:
            self.yabs = val

    y = property(_get_y, _set_y)  #: Ordonnée locale publique.

    def discard_pos_coords(self):
        """
        Invalide les propriétés _xpos et _ypos,  attributs "cachés" derrière les getters de x et y.
        """
        self._pos_coords_updated = False

    def update_pos_coords(self):
        """
        Recalcule _xpos et _ypos, attributs "cachés" derrière les getters de x et y.
        """
        oldcoords = int(self._xpos), int(self._ypos)
        # axe de layout
        flow_direction = None
        if self.parent != None:
            flow_direction = self.parent.direction
        # axe X :
        self._xpos = 0
        if self.in_flow and flow_direction == VirtualContainer.DIRECTION_HORIZONTAL:
            self._xpos = self.xflow
            if self.position == BoxModelObject.POSITION_RELATIVE:
                self._xpos += self.xabs
        else:
            self._xpos = self.xabs
        # axe y :
        self._ypos = 0
        if self.in_flow and flow_direction == VirtualContainer.DIRECTION_VERTICAL:
            self._ypos = self.yflow
            if self.position == BoxModelObject.POSITION_RELATIVE:
                self._ypos += self.yabs
        else:
            self._ypos = self.yabs
        # indicateur de mise à jour :
        self._pos_coords_updated = True
        # update de publicationRect
        self.publicationRect.x = self.x + self.publicationRefRect.x
        self.publicationRect.y = self.y + self.publicationRefRect.y
        # cas particulier fixed
        if self.position == BoxModelObject.POSITION_FIXED:
            # offsets compensant les coords globales du parent
            if self.parent != None:
                pgx, pgy = self.parent.get_global_coords()
                self.publicationRect.x -= pgx
                self.publicationRect.y -= pgy
        # changement?
        if oldcoords != (self._xpos, self._ypos):
            return True
        return False

    #-----> Offsets locaux :
    def _get_left(self):
        """Offset de positionnement gauche."""
        return self.metricparams["left"].get_value()

    def _set_left(self, val):
        newmetric = self.parse_metric(val)
        oldmetric = self.metricparams["left"]
        if newmetric != oldmetric:
            self.metricparams["left"] = newmetric
            self.on_offset_changed("left")

    left = property(_get_left, _set_left)  #: Offset de positionnement gauche.

    def _get_right(self):
        """Offset de positionnement droit."""
        return self.metricparams["right"].get_value()

    def _set_right(self, val):
        newmetric = self.parse_metric(val)
        oldmetric = self.metricparams["right"]
        if newmetric != oldmetric:
            self.metricparams["right"] = newmetric
            self.on_offset_changed("right")

    right = property(_get_right, _set_right)  #: Offset de positionnement droit.

    def _get_top(self):
        """Offset de positionnement haut."""
        return self.metricparams["top"].get_value()

    def _set_top(self, val):
        newmetric = self.parse_metric(val)
        oldmetric = self.metricparams["top"]
        if newmetric != oldmetric:
            self.metricparams["top"] = newmetric
            self.on_offset_changed("top")

    top = property(_get_top, _set_top)  #: Offset de positionnement haut.

    def _get_bottom(self):
        """Offset de positionnement bas."""
        return self.metricparams["bottom"].get_value()

    def _set_bottom(self, val):
        newmetric = self.parse_metric(val)
        oldmetric = self.metricparams["bottom"]
        if newmetric != oldmetric:
            self.metricparams["bottom"] = newmetric
            self.on_offset_changed("bottom")

    bottom = property(_get_bottom, _set_bottom)  #: Offset de positionnement bas.

    def on_offset_changed(self, prop):
        """
        Appelée lors d'un changement explicite d'offset (top, bottom, left, right).
        """
        if prop in ["left", "right"]:
            coord = "xabs"
            dim = "width"
        else:
            coord = "yabs"
            dim = "height"
        self.discard_strategy(coord)
        self.discard_strategy(dim)
        self.discard_resize()
        self.discard_pos_coords()

    #-----> Dimensions totales (padding et margin compris)
    def _get_width(self):
        """Largeur totale (padding et margin compris)."""
        return self.publicationRect.width

    def _set_width(self, val):
        newmetric = self.parse_boundedmetric(val, self.minwidth, self.maxwidth)
        oldmetric = self.metricparams["width"]
        if newmetric != None and newmetric != oldmetric:
            self.metricparams["width"] = newmetric
            self.on_dimension_changed("width")

    width = property(
        _get_width, _set_width
    )  #: Largeur totale (padding et margin compris) publique.

    def _get_height(self):
        """Hauteur totale (padding et margin compris)."""
        return self.publicationRect.height

    def _set_height(self, val):
        newmetric = self.parse_boundedmetric(val, self.minheight, self.maxheight)
        oldmetric = self.metricparams["height"]
        if newmetric != None and newmetric != oldmetric:
            self.metricparams["height"] = newmetric
            self.on_dimension_changed("height")

    height = property(
        _get_height, _set_height
    )  #: Hauteur totale (padding et margin compris) publique.

    def on_dimension_changed(self, prop):
        """
        Appelée lors d'un changement explicite de dimensions (hors process de resize).
        """
        self.discard_strategy(prop)
        self.discard_resize()

    #-----> Bornage des dimensions :
    def _get_minwidth(self):
        """Largeur min en px."""
        return self.metricparams["width"].get_bound("min")

    def _set_minwidth(self, val):
        if val != self._get_minwidth():
            self.metricparams["width"].set_bound("min", val)
            self.on_dimension_bound_changed()

    minwidth = property(_get_minwidth, _set_minwidth)  #: Largeur min en px.

    def _get_maxwidth(self):
        """Largeur max en px."""
        return self.metricparams["width"].get_bound("max")

    def _set_maxwidth(self, val):
        if val != self._get_maxwidth():
            self.metricparams["width"].set_bound("max", val)
            self.on_dimension_bound_changed()

    maxwidth = property(_get_maxwidth, _set_maxwidth)  #: Largeur max en px.

    def _get_minheight(self):
        """Hauteur min en px."""
        return self.metricparams["height"].get_bound("min")

    def _set_minheight(self, val):
        if val != self._get_minheight():
            self.metricparams["height"].set_bound("min", val)
            self.on_dimension_bound_changed()

    minheight = property(_get_minheight, _set_minheight)  #: Hauteur min en px.

    def _get_maxheight(self):
        """Hauteur max en px."""
        return self.metricparams["height"].get_bound("max")

    def _set_maxheight(self, val):
        if val != self._get_maxheight():
            self.metricparams["height"].set_bound("max", val)
            self.on_dimension_bound_changed()

    maxheight = property(_get_maxheight, _set_maxheight)  #: Hauteur max en px.

    def on_dimension_bound_changed(self):
        """
        Appelée lorsqu'une borne de dimension a été modifiée.
        """
        self.discard_resize()

    #-----> Padding :
    def _get_padding(self):
        """Padding en px."""
        return self.metricparams["padding"].get_value()

    def _set_padding(self, val):
        newmetric = self.parse_metric(val)
        oldmetric = self.metricparams["padding"]
        if newmetric != None and newmetric != oldmetric:
            self.metricparams["padding"] = newmetric
            self.on_padding_changed()

    padding = property(_get_padding, _set_padding)  #: Padding en px.

    def on_padding_changed(self):
        """
        Appelée lorsque le padding a été modifié.
        """
        self.discard_inner_rects()
        self.discard_resize()

    #-----> margin :
    def _get_margin(self):
        """Margin en px."""
        return self.metricparams["margin"].get_value()

    def _set_margin(self, val):
        newmetric = self.parse_metric(val)
        oldmetric = self.metricparams["margin"]
        if newmetric != None and newmetric != oldmetric:
            self.metricparams["margin"] = newmetric
            self.on_margin_changed()

    margin = property(_get_margin, _set_margin)  #: Margin en px.

    def on_margin_changed(self):
        """
        Appelée lorsque la marge a été modifiée.
        """
        self.discard_inner_rects()
        self.discard_resize()

    #-----> Alignements :
    def _get_align(self):
        """Alignement horizontal."""
        return self._align

    def _set_align(self, val):
        newval = self.parse_alignement(val)
        oldval = self._align
        if newval != oldval:
            self._align = newval
            self.on_alignement_changed("align")

    align = property(_get_align, _set_align)  #: Alignement horizontal.

    def _get_valign(self):
        """Alignement vertical."""
        return self._valign

    def _set_valign(self, val):
        newval = self.parse_alignement(val)
        oldval = self._valign
        if newval != oldval:
            self._valign = newval
            self.on_alignement_changed("valign")

    valign = property(_get_valign, _set_valign)  #: Alignement vertical.

    def on_alignement_changed(self, prop):
        """
        Appelée lors d'un changement explicite d'alignement.
        """
        if prop == "align":
            coord = "xabs"
        else:
            coord = "yabs"
        self.discard_strategy(coord)
        self.discard_pos_coords()

    #-----> Snaps :
    def _get_snapW(self):
        """Adaptation à la largeur du contenu (bool)."""
        return self._snapW

    def _set_snapW(self, val):
        newval = self.parse_snap(val)
        oldval = self._snapW
        if newval != oldval:
            self._snapW = newval
            self.on_snap_changed()

    snapW = property(
        _get_snapW, _set_snapW
    )  #: Adaptation à la largeur du contenu (bool).

    def _get_snapH(self):
        """Adaptation à la hauteur du contenu (bool)."""
        return self._snapH

    def _set_snapH(self, val):
        newval = self.parse_snap(val)
        oldval = self._snapH
        if newval != oldval:
            self._snapH = newval
            self.on_snap_changed()

    snapH = property(
        _get_snapH, _set_snapH
    )  #: Adaptation à la hauteur du contenu (bool).

    def on_snap_changed(self):
        """
        Appelée lors d'un changement explicite de snap.
        """
        if self.snapW or self.snapH:
            self.do_snap = True
            # surcharge au besoin de width ou height :
            self.post_control_boxmodel()
        else:
            self.do_snap = False
        self.discard_resize()
        # layout parent :
        if self.parent != None:
            self.parent.on_child_snap_changed(self)

    #-----> Flex :
    def _get_flex(self):
        """Valeur de flex."""
        return self._flex

    def _set_flex(self, val):
        newval = self.parse_flex(val)
        if newval != self._flex:
            self._flex = newval
            self.on_flex_changed()

    flex = property(_get_flex, _set_flex)  #: Valeur de flex.

    def on_flex_changed(self):
        """
        Appelée lorsque l'attribut flex a été modifié.
        """
        if self.position in [
            BoxModelObject.POSITION_STATIC,
            BoxModelObject.POSITION_RELATIVE,
        ]:
            self.discard_resize()
            # layout parent :
            if self.parent != None:
                self.parent.on_child_flex_changed(self)

    #-----> Resize
    def resize(self, **kwargs):
        """
        Recalcul de la taille et de la position.
        Met à jour self.publicationRect, alias de self.rect.
        Rqs : l'attribut position est pris en compte dans les getters/setters de x et y,
        
        Returns: 
            True si le resize a été modifié
        """
        # [Keep for debug] print("BMO|",self.name," resize self.is_resized=",self.is_resized," rect=",self.rect)
        # tests préalables :
        if not self.do_compute_resize():
            return False
        # Maj des metrics : dimensions puis coordonnées
        self.update_core_metrics(self.publicationRefRect)
        # Maj de publicationRect :
        change = self.update_publicationRect()
        # snap :
        change_snap = False
        if self.do_snap:
            content_dims = self.get_item_dimensions()
            if content_dims != (None, None):
                change_snap = self.handle_item_snap(content_dims[0], content_dims[1])
        # statut
        self.is_resized = True
        # [Keep for debug] print("BMO|",self.name," resize change=",change," change_snap=",change_snap," rect=",self.rect)
        return change or change_snap

    def do_compute_resize(self):
        """
        Tests préalables aux calculs de resize.
        
        Returns:
            boolean
        """
        docompute = True
        if self.is_resized:
            return False
        # Position et référence globale :
        if self.position == BoxModelObject.POSITION_FIXED:
            self._publicationRefRect = self.root_reference.get_content_rect()
        if self.publicationRefRect == None:
            docompute = False
        return docompute

    def get_item_dimensions(self):
        """
        Doit retourner les dimensions réelles du contenu (texte, image).
        A implémenter dans les subclasses utilisant le snap.
        
        Returns:
            int, int
        """
        return None, None

    def discard_resize(self):
        """
        Marque l'objet comme non resizé.
        """
        # [Keep for debug] print("BMO|",self.name," discard_resize !*!")
        self.is_resized = False
        if self.parent != None:
            self.parent.on_child_unresized(self)

    #-----> Maj du rect de publication :
    def update_publicationRect(self, aftersnap=False):
        """
        Mise à jour de publicationRect.
        """
        oldcoords = (int(self.publicationRect.x), int(self.publicationRect.y))
        olddims = (int(self.publicationRect.width), int(self.publicationRect.height))
        # affectation
        self.publicationRect.x = self.x + self.publicationRefRect.x
        self.publicationRect.y = self.y + self.publicationRefRect.y
        self.publicationRect.width = self.get_metric_value("width")
        self.publicationRect.height = self.get_metric_value("height")
        # cas particulier fixed
        if self.position == BoxModelObject.POSITION_FIXED:
            # offsets compensant les coords globales du parent
            if self.parent != None:
                pgx, pgy = self.parent.get_global_coords()
                self.publicationRect.x -= pgx
                self.publicationRect.y -= pgy
        # mémorisation avant snap :
        if not aftersnap:
            self.unsnapped_publicationRect = self.publicationRect.copy()
        # Tests :
        test_dims = (self.publicationRect.width, self.publicationRect.height) != olddims
        test_coords = (self.publicationRect.x, self.publicationRect.y) != oldcoords
        if test_dims:
            self.on_publicationRect_dims_changed(aftersnap)
        elif test_coords:
            self.on_publicationRect_coords_changed(aftersnap)
        # retour :
        return test_dims or test_coords

    def on_publicationRect_dims_changed(self, aftersnap):
        """
        Appelée lors du process de resize quand les dimensions (et éventuellement
        les coords) de publicationRect ont été modifiées
        
        Args:
            aftersnap (boolean): True si consécutif à un calcul de snap, False sinon
        """
        # [Keep for debug] print("BMO|",self.name," on_publicationRect_dims_changed rect=",self.publicationRect)
        # Force la mise à jour des rects internes (contenu et fond) :
        self.discard_inner_rects()
        # invalide la référence absolue exacte
        self.discard_globalRect()
        # display :
        self.discard_display()

    def on_publicationRect_coords_changed(self, aftersnap):
        """
        Appelée lors du process de resize quand les coordonnées seules
        de publicationRect ont été modifiées (pas les dimensions).
        
        Args:
            aftersnap (boolean): True si consécutif à un calcul de snap, False sinon
        """
        # [Keep for debug] print("BMO|",self.name," on_publicationRect_coords_changed rect=",self.publicationRect)
        # Force la mise à jour des rects internes (contenu et fond) :
        self.discard_inner_rects()
        # invalide la référence absolue exacte
        self.discard_globalRect()
        # display :
        self.discard_display()

    #-----> Gestion générique du snap pour un objet terminal
    def handle_item_snap(self, content_width, content_height):
        """
        Implémentation du snap pour un item terminal.
        
        Args:
            content_width (int): largeur du contenu auquel s'adapter
            content_height (int): hauteur du contenu auquel s'adapter
            
        Met à jour self.publicationRect.
        A appeler au besoin dans une subclasse (texte, image).
        
        Returns: 
            boolean indiquant si un changement a été apporté.
        """
        change = False
        if (
            isinstance(content_width, int)
            and isinstance(content_height, int)
            and self.do_snap
        ):
            # recalcul des dimensions :
            p = self.padding
            m = self.margin
            if self.snapW:
                w = content_width + 2 * (p + m)
                self.set_metric_value("width", w)
            if self.snapH:
                h = content_height + 2 * (p + m)
                self.set_metric_value("height", h)
            # test de modification :
            if (self.publicationRect.width, self.publicationRect.height) != (
                self.get_metric_value("width"),
                self.get_metric_value("height"),
            ):
                change = True
                # mise à jour des coordonnées :
                if self.position != BoxModelObject.POSITION_STATIC:
                    self.compute_coords(self.publicationRefRect)
                # puis de publicationRect :
                self.update_publicationRect(aftersnap=True)
            # [Keep for debug] print("BMO|",self.name," > handlesnap change=",change," => self.rect=",self.rect)
        return change

    #-----> Layout imposé par le flow parent:
    def apply_parent_layout(self, prop, val):
        """
        Applique le layout imposé par le conteneur parent
        
        Args:
            prop (str): "x" ou "y"
            val (int)
        """
        oldval = getattr(self, prop)
        change = oldval != val
        if change:
            # mise à jour des coords :
            setattr(self, prop, val)
            self.update_pos_coords()
            # Force la mise à jour des rects internes (contenu et fond) :
            self.discard_inner_rects()
            # invalide la référence absolue exacte
            self.discard_globalRect()
        # [Keep for debug] print("BMO|",self.name," apply_parent_layout change=",change)
        return change

    #-----> Déplacement local sans modification des metrics xabs et yabs
    def place(self, x, y):
        """
        Positionne l'objet aux coordonnées locales x, y sans modifier les métrics,
        modifie directement self.publicationRect.
        """
        self.publicationRect.x = x + self.publicationRefRect.x
        self.publicationRect.y = y + self.publicationRefRect.y
        # invalide le display :
        self.discard_display()

    def move(self, dx, dy):
        """
        Applique le décallage dx, dy aux coordonnées locales x, y sans modifier les métrics,
        modifie directement self.publicationRect.
        """
        self.publicationRect.x += dx
        self.publicationRect.y += dy
        # invalide le display :
        self.discard_display()

    #-----> Indicateur de changement de rendu :
    def discard_placement(self):
        """
        La position a été modifiée, le rendu graphique dans la surface de publication
        du RealContainer assurant la publication n'est plus valable. Par contre le rendu
        "local" de cet objet reste valide.
        """
        change = self.update_pos_coords()
        if change and self.parent != None:
            self.parent.on_child_placement_discarded(self)

    def discard_display(self):
        """
        La position, les dimensions ou les rects internes (le contenu pour des subclasses)
        ont été modifiés, le rendu graphique n'est plus valable
        """
        if self.parent != None:
            self.parent.on_child_display_discarded(self)

    def draw_display(self):
        """
        Dessinne ou redessinne l'objet.
        """
        # à subclasser

    #-----> Debug
    def __repr__(self):
        return self.name


class MetricValue:
    """
    **Donnée de box model numérique pouvant être exprimée en pixel ou en pourcentage.**
    """

    # propriété statique :
    REGEXP_INT = re.compile(
        "0{1}|^[1-9]{1}[0-9]*"
    )  #: expression régulière de reconnaissance d'un int
    # méthode statique :
    def parseMetric(cls, val):
        """
        Parse une donnée et retourne un objet MetricValue (par défaut value=0, percent=False)
        ou None.
        
        Args:
            val: int ou str
        """
        percent = False
        value = None
        if isinstance(val, str):
            if (
                val[-1] == "%"
                and len(val) > 1
                and MetricValue.REGEXP_INT.match(val[:-1])
            ):
                percent = True
                value = int(val[:-1])
            elif MetricValue.REGEXP_INT.match(val):
                value = int(val)
        elif isinstance(val, int):
            value = val
        if value != None:
            return MetricValue(value, percent=percent)
        return None

    parseMetric = classmethod(parseMetric)
    # méthodes
    def __init__(self, value, percent=False):
        """
        Constructeur :
        
        Args:
            value : valeur numérique
            percent : bool
        
        """
        self.value = value
        self.percent = percent
        # dernière valeur calculée :
        self.lastcomputedvalue = 0
        if not self.percent:
            self.lastcomputedvalue = self.value

    def get_value(self, refvalue=None):
        """
        Retourne la valeur de la donnée, en prenant pour référence refvalue si
        la donnée est en pourcentage.
        """
        if refvalue != None:
            # passe d'actualisation
            if self.percent:
                val = self.value / 100 * refvalue
            else:
                val = self.value
            self.set_computedvalue(int(val))
        return self.lastcomputedvalue

    def get_computedvalue(self):
        """
        Retourne la valeur calculée.
        """
        return self.lastcomputedvalue

    def set_computedvalue(self, val):
        """
        Enregistre la valeur calculée en dehors de ce metric.
        """
        self.lastcomputedvalue = val

    def __eq__(self, other):
        """
        Opérateur de comparaison.
        """
        if other == None or not isinstance(other, MetricValue):
            return False
        elif self.value == other.value and self.percent == other.percent:
            return True
        return False

    def __str__(self):
        # debug
        return (
            "[Metric :value="
            + str(self.value)
            + " percent="
            + str(self.percent)
            + " lastcomputedvalue="
            + str(self.lastcomputedvalue)
            + "] "
        )


class BoundedMetricValue(MetricValue):
    """
    **MetricValue avec bornes min et max.**
    """

    # propriétés statiques
    DEFAULT_MIN = 0  #: borne min par défaut
    DEFAULT_MAX = 100000  #: borne max par défaut
    # méthode statique :
    def parseMetric(cls, val, minvalue, maxvalue):
        """
        Parse une donnée et retourne un objet BoundedMetricValue (par défaut value=0, percent=False)
        ou None.
        """
        bmv = None
        mv = MetricValue.parseMetric(val)
        if mv != None:
            bmv = BoundedMetricValue(
                mv.value, percent=mv.percent, minvalue=minvalue, maxvalue=maxvalue
            )
        else:
            bmv = BoundedMetricValue(None)
        return bmv

    parseMetric = classmethod(parseMetric)

    def parse_bound(cls, val):
        """
        Parse une valeur de borne.
        """
        value = None
        if isinstance(val, str) and MetricValue.REGEXP_INT.match(val):
            value = math.fabs(int(val))
        elif isinstance(val, int):
            value = math.fabs(val)
        return value

    parse_bound = classmethod(parse_bound)
    # méthodes :
    def __init__(self, value, percent=False, minvalue=None, maxvalue=None):
        """
        Constructeur :
        
        Args:
            value : valeur numérique
            percent : bool
            minvalue : int (o par défaut)
            maxvalue : int (100000 par défaut)        
        """
        MetricValue.__init__(self, None)
        # valeurs déja parsées
        self.value = value
        self.percent = percent
        # bornes :
        self.min_value = BoundedMetricValue.DEFAULT_MIN
        self.max_value = BoundedMetricValue.DEFAULT_MAX
        if minvalue != None:
            self.set_bound("min", minvalue)
        if maxvalue != None:
            self.set_bound("max", maxvalue)
        # dernière valeur calculée :
        self.lastcomputedvalue = 0
        if not self.percent:
            self.set_computedvalue(value)

    def get_bound(self, prop):
        """
        Getter de borne (prop = min ou max)
        """
        if prop == "min":
            return self.min_value
        elif prop == "max":
            return self.max_value
        return None

    def set_bound(self, prop, val):
        """
        Setter de borne (prop = min ou max)
        """
        realval = BoundedMetricValue.parse_bound(val)
        if realval != None:
            if prop == "min":
                self.min_value = realval
            elif prop == "max":
                self.max_value = realval
        else:
            if prop == "min":
                self.min_value = BoundedMetricValue.DEFAULT_MIN
            elif prop == "max":
                self.max_value = BoundedMetricValue.DEFAULT_MAX
        self.set_computedvalue(self.lastcomputedvalue)

    def set_computedvalue(self, val):
        """
        Enregistre la valeur calculée en dehors de ce metric : prise en compte des bornes.
        """
        if isinstance(val, int):
            val = min(val, self.max_value)
            val = max(val, self.min_value)
            self.lastcomputedvalue = val


class VirtualItem(BoxModelObject):
    """
    **BoxModelObject supportant les attributs de gestion des z-indexs (couches) ainsi que
    les propriétés et méthodes de base de la logique de publication.**

    Virtual indique que cet objet n'a pas de surface propre (au sens pygame) et qu'il n'est pas
    un objet de publication réel.
    """

    # méthodes
    def __init__(self, **kwargs):
        """
        Constructeur :
        
        Args:
            **kwargs : peut contenir local_layer ainsi que toutes les propriétés de boxing 
                supportées par BoxModelObject.
        """
        # générique :
        BoxModelObject.__init__(self, **kwargs)
        # Indique si l'objet contient une hiérarchie de couches internes à
        # prendre en charge par un RealContainer parent.
        self._is_stacked = False
        # Niveau d'imbrication dans la hiérarchie globale :
        self._level = None
        # ordre de publication :
        self.publication_order = None
        # l'item a t'il déja été publié?
        self.prevpublished = False
        # appartenance à la displaylist finale :
        self._added_to_displaylist = False
        # visibilité (indicatif uniquement)
        self._visible = True
        # layers :
        self._init_layers(**kwargs)

    def _init_layers(self, **kwargs):
        """
        Initialise les paramètres liés au z-index.
        """
        # layer locale / VirtualContainer parent :
        self._local_layer = None
        if "local_layer" in kwargs.keys():
            self.local_layer = int(kwargs["local_layer"])
        # layer de publication / LayeredDisplay :
        self._publication_layer = None
        # layer globale / root
        self._global_layer = None
        self._global_layer_updated = False

    def parse_layer(self, val):
        """
        Parse l'attribut local_layer.
        """
        if isinstance(val, int) and val >= 0:
            return val
        return None

    #-----> Hiérarchie : niveau
    def _get_level(self):
        """Niveau de l'objet dans la hiérarchie."""
        return self._level

    def _set_level(self, val):
        self._level = val

    level = property(
        _get_level, _set_level
    )  #: Niveau d'imbrication de l'objet dans la hiérarchie.

    #-----> Gestion de la profondeur (2.5 D) : couches locale et globale
    def _get_local_layer(self):
        """
        Couche locale par rapport au container parent
        """
        return self._local_layer

    def _set_local_layer(self, val):
        val = self.parse_layer(val)
        if val != None:
            self._local_layer = val

    local_layer = property(
        _get_local_layer, _set_local_layer
    )  #: Couche locale par rapport au container parent

    def _get_publication_layer(self):
        """
        Couche de publication dans le RealContainer assurant le display de cet objet.
        """
        return self._publication_layer

    def _set_publication_layer(self, val):
        self._publication_layer = val
        self._global_layer_updated = False

    publication_layer = property(
        _get_publication_layer, _set_publication_layer
    )  #: Couche de publication dans le RealContainer assurant le display de cet objet.

    def _get_global_layer(self):
        """
        Couche globale par rapport au Root.
        """
        if not self._global_layer_updated:
            # par défaut il s'agit de la couche de publication
            self._global_layer = self._publication_layer
            if self.root_reference != None:
                p = self.parent
                while p != None:
                    if isinstance(p, RealContainer) and p != self.root_reference:
                        # la couche globale équivaut alors au RealContainer
                        # de plus haut niveau (root excepté)
                        self._global_layer = p.publication_layer
                    p = p.parent
            self._global_layer_updated = True
        return self._global_layer

    def _set_global_layer(self, val):
        self._global_layer = val

    global_layer = property(
        _get_global_layer, _set_global_layer
    )  #: Couche globale par rapport au Root.

    def discard_layers(self):
        """
        Invalide les couches globales et de publication.
        """
        self._publication_layer = None
        self._global_layer = None
        self._global_layer_updated = False

    def _get_is_stacked(self):
        """
        Indique si l'objet contient une hiérarchie de couches internes à
        prendre en charge par un RealContainer parent.
        Toujours faux pour un VirtualItem.
        """
        return self._is_stacked

    def _set_is_stacked(self, val):
        self._is_stacked = val

    is_stacked = property(
        _get_is_stacked, _set_is_stacked
    )  #: Indique si l'objet contient une hiérarchie de couches internes à prendre en charge par un RealContainer parent (Toujours faux pour un VirtualItem).

    #-----> Visibilité :
    def _get_visible(self):
        """Visibilité (bool)."""
        # implémenté dans la subclasse CustomSprite
        return self._visible

    def _set_visible(self, val):
        # implémenté dans la subclasse CustomSprite
        if isinstance(val, bool) and val != self._visible:
            self._visible = val
            self.on_visibility_changed()

    visible = property(_get_visible, _set_visible)  #: Visibilité (bool)

    def on_visibility_changed(self):
        """
        Appelée lorsque self.visible a été modifié.
        """
        pass

    #-----> Logique de publication :
    def on_item_added(self, parent):
        """
        Appelée par le container parent lorsque l'item est ajouté
        """
        self.parent = parent
        if parent.level != None:
            self.level = parent.level + 1
        else:
            self._level = None

    def on_item_removed(self):
        """
        Appelée par le container parent lorsque l'item est supprimé
        """
        # self.parent = None
        self.root_reference = None
        self._level = None
        # self.re_initialise_rects()
        self.discard_layers()

    def on_parent_removed(self):
        """
        Propagé si un parent a été supprimé sans que celui ci ne supprime sa hiérarchie
        """
        # invalide le display :
        self.discard_display()
        # et les couches
        self.discard_layers()

    def update(self, *args):
        """
        Appelée à chaque frame.
        """
        pass

    def on_item_added_to_displaylist(self):
        """
        Appelée lorsque l'item (via sa hiérarchie parente) est publié par
        le root dans la displaylist finale.
        """
        self._added_to_displaylist = True

    def on_item_removed_from_displaylist(self):
        """
        Appelée lorsque l'item (via sa hiérarchie parente) est dé-publié par
        le root de la displaylist finale.
        """
        self._added_to_displaylist = False

    def belong_to_displaylist(self):
        """
        Indique si l'objet appartient à la displaylist finale.
        """
        return self._added_to_displaylist

    def _get_publication_order(self):
        """Ordre de publication."""
        return self._publication_order

    def _set_publication_order(self, val):
        self._publication_order = val

    publication_order = property(
        _get_publication_order, _set_publication_order
    )  #: Ordre de publication.
    #-----> Propagation d'événement
    def fire_event(self, evt):
        """
        Dispatch l'événement evt
        """
        pygame.event.post(evt)

    #----->  Infos
    def get_framerate(self):
        """
        Retourne le framerate de l'application.
        """
        if self.root_reference != None:
            return self.root_reference.framerate
        return None


class VirtualContainer(VirtualItem):
    """
    **VirtualItem dôté des capacités d'un conteneur :**
    
    * publication : ajout / suppression d'objets enfants
    * propagation du resize aux objets enfants
    * layouts basiques : via la propriété direction :
    
        - direction = None : layout absolu (canvas), cas par défaut
        - direction = "horizontal" : layout des éléments de position fixed ou absolute selon 
          l'axe x
        - direction = "vertical" : respectivement selon l'axe y

    Virtual indique que cet objet n'a pas de surface propre (au sens pygame). Comme VirtualItem 
    il ne s'agit pas d'un objet de publication réel. Par contre il s'inscrit dans la gestion 
    générique des couches et de la publication. Sa descendance sera publié réellement par 
    un RealContainer parent (Root par défaut).
    
    Todo:
        Support de la visibilité, actuellement effectif uniquement pour les composants disposant 
        d'une surface de publication.
    """

    # statique :
    DIRECTION_HORIZONTAL = [
        "horizontal",
        "h",
        "x",
    ]  #: valeurs de direction équivalentes
    DIRECTION_VERTICAL = ["vertical", "v", "y"]  #: valeurs de direction équivalentes
    DIRECTION_ATTR = [
        DIRECTION_HORIZONTAL,
        DIRECTION_VERTICAL,
    ]  #: valeurs de direction possibles
    # méthodes
    def __init__(self, bgcolor=None, **kwargs):
        """
        Constructeur
        
        Args:
            bgcolor (str): couleur héxa
            **kwargs : peut contenir direction ainsi que toutes les propriétés de VirtualItem.
        """
        # liste de tous les items (VirtualItem et VirtualContainer)
        self.relativechildItems = list()
        # liste des enfants à ajouter :
        self.childtoadd = list()
        # liste des enfants à supprimer :
        self.childtoremove = list()
        # listes des enfants sujets au layout ou non, au flex, au snap
        self.fixedchildlist = list()  # childs fixed (hors flow)
        self.absolutechildlist = list()  # childs absolute (hors flow)
        self.childtolayout = list()  # tous les childs in flow
        self.flexchildlist = list()  # childs in flow avec flex
        self.unflexchildlist = list()  # childs in flow sans flex
        self.layoutlistupdated = False
        # indicateur de mise à jour des surfaces alouées
        self._allocated_area_updated = False
        # indicateur de mise à jour de layout
        self._layout_updated = False
        # indicateur de mise à jour de snap :
        self._snap_updated = False
        # layout basique : direction (layout absolu par défaut)
        self._direction = None
        # générique :
        VirtualItem.__init__(self, **kwargs)
        # Couches internes à publier par un RealContainer parent : oui
        self.is_stacked = True
        # visibilité :
        self._visible = True
        # fond
        self.background = None
        # couleur de fond :
        self._bgcolor = None
        # affectation couleur et création du fond au besoin :
        self.bgcolor = bgcolor
        # debug
        self.resize_count = 0

    def _init_boxmodel(self, **kwargs):
        """
        Initialise les propriétés de boxmodel
        """
        # générique :
        BoxModelObject._init_boxmodel(self, **kwargs)
        # spécifique :
        direct = None
        if "direction" in kwargs.keys() and kwargs["direction"] in [
            VirtualContainer.DIRECTION_HORIZONTAL,
            VirtualContainer.DIRECTION_VERTICAL,
        ]:
            direct = kwargs["direction"]
        self.direction = direct

    def _init_layers(self, **kwargs):
        """
        Initialise les paramètres liés au z-index.
        """
        # générique :
        VirtualItem._init_layers(self, **kwargs)
        # couche locale par défaut :
        self.default_layer = 0

    #-----> Direction de layout
    def parse_direction(self, val):
        """
        Parse l'attribut direction
        
        Args:
            val (str)
        """
        rval = None
        if (
            val in VirtualContainer.DIRECTION_HORIZONTAL
            or val == VirtualContainer.DIRECTION_HORIZONTAL
        ):
            rval = VirtualContainer.DIRECTION_HORIZONTAL
        elif (
            val in VirtualContainer.DIRECTION_VERTICAL
            or val == VirtualContainer.DIRECTION_VERTICAL
        ):
            rval = VirtualContainer.DIRECTION_VERTICAL
        return rval

    def _get_direction(self):
        """Direction de layout."""
        return self._direction

    def _set_direction(self, val):
        val = self.parse_direction(val)
        if val != self._direction:
            self._direction = val
            self.on_direction_changed()

    direction = property(
        _get_direction, _set_direction
    )  #: Direction de layout (None par défaut)

    def on_direction_changed(self):
        """
        Appelée lorsque la propriété direction a été modifiée.
        """
        self.discard_layout_list()

    #-----> Fond
    def create_background(self):
        """
        Crée un CustomSprite de fond si bgcolor != None.
        """
        if self.bgcolor != None:
            self.background = CustomSprite(
                bgcolor=self.bgcolor,
                position=BoxModelObject.POSITION_ABSOLUTE,
                local_layer=0,
                width="100%",
                height="100%",
                name=self.name + "_bg",
            )
            self.add_item(self.background)

    def resize_background(self):
        """
        Resize le fond.
        """
        if self.background != None:
            bgrect = self.get_border_rect()
            self.background.publicationRefRect = bgrect
            self.background.resize()

    def update_backround_coords(self):
        """
        Met à jour les coordonnées du rect de publication du fond.
        """
        if self.background != None:
            bgrect = self.get_border_rect()
            self.background.update_publicationRefRect_coords(bgrect.x, bgrect.y)

    def _get_bgcolor(self):
        """Couleur de fond (str héxa) convertie au format pygame.Color."""
        return self._bgcolor

    def _set_bgcolor(self, val):
        if not isinstance(val, pygame.Color):
            try:
                val = pygame.Color(val)
            except ValueError:
                val = None
        if val != None and val != self._bgcolor:
            self._bgcolor = val
            self.on_bgcolor_changed()

    bgcolor = property(
        _get_bgcolor, _set_bgcolor
    )  #: Couleur de fond (str héxa) convertie au format pygame.Color.

    def on_bgcolor_changed(self):
        """
        Appelée lorsque la couleur de fond a été modifiée.
        """
        if self.background != None:
            self.background.bgcolor = self._bgcolor
        else:
            self.create_background()

    #-----> Rect global de référence
    def discard_globalRect(self):
        """
        Invalide la position globale absolue exacte
        """
        # générique :
        BoxModelObject.discard_globalRect(self)
        # propagation :
        for child in self.relativechildItems:
            child.discard_globalRect()

    #-----> Layout imposé par le flow parent:
    def apply_parent_layout(self, prop, val):
        """
        Applique le layout imposé par le conteneur parent
        
        Args:
            prop (str): "x" ou "y"
            val (int)
        """
        # générique :
        change = BoxModelObject.apply_parent_layout(self, prop, val)
        # [Keep for debug] print("VC|",self.name," apply_parent_layout prop, val=",prop, val," change=",change)
        # spécifique :
        if change:
            # invaide le layout des childs :
            self.discard_layout()

    #-----> Update
    def update(self, *args):
        """
        Appelée à chaque frame: gestion du resize.
        """
        # Resize au besoin :
        change = self.resize()
        # propagation :
        for child in self.relativechildItems:
            child.update()
        return change

    #-----> Resize
    def resize(self, **kwargs):
        """
        Recalcul de la taille et de la position
        
        * direction : None (canvas), horizontal (liste h), vertical (liste v)
        * si direction != None : prise en compte des attributs flex des childs
        * snapW (boolean) : si True le container définit sa largeur par rapport à son contenu
        * snapH (boolean) : si True le container définit sa hauteur par rapport à son contenu
        
        """
        # [Keep for debug] print("\nVC|",self.name," resize self.resize_count=",self.resize_count," ...")
        # Maj des listes de childs :
        if not self.layoutlistupdated:
            self.update_layout_list()
        # générique :
        resized = VirtualItem.resize(self, **kwargs)
        # Container :
        # 1- Redéfinition de la surface alouée et resize des childs
        if not self._allocated_area_updated:
            # Update complet
            # [Keep for debug] print("VC|",self.name," update_childs rect=",self.rect)
            self.update_childs()
        # optimisation : si le rect de contenu est "nul", inutile de poursuivre le process.
        # Rq : les rects internes ont put être mis à jour dans update_childs,
        # c'est pourquoi on fait ce test ensuite.
        contentRect = self.get_content_rect()
        if contentRect.w * contentRect.h <= 0:
            return False
        # 2- Layout :
        if not self._layout_updated:
            # [Keep for debug] print("VC|",self.name," layout_childs rect=",self.rect)
            self.layout_childs()
        # 3- Snap éventuel :
        if not self._snap_updated:
            # Adaptation au contenu :
            # [Keep for debug] print("VC|",self.name," handle_snap rect=",self.rect)
            self.handle_snap()
        # Indicateur de fin de resize pour post traitement :
        # [Keep for debug] print("VC|",self.name," fin resize : self.is_resized =",self.is_resized)
        if resized:
            self.on_resize_achieved()
        self.resize_count += 1
        return resized

    def mark_container_as_resized(self):
        """
        En cas de resize personnalisé, re valide tous les marqueurs de resize.
        """
        self.is_resized = True
        self._allocated_area_updated = True
        self._layout_updated = True
        self._snap_updated = True

    def on_publicationRefRect_coords_changed(self):
        """
        Appelée lorsque les coordonnées du rect de publication de référence
        (self._publicationRefRect) ont été modifiées (mais pas les dimensions).
        """
        # générique :
        BoxModelObject.on_publicationRefRect_coords_changed(self)
        # propagation aux childs :
        cr = self.get_content_rect()
        fulllist = self.relativechildItems
        # fond :
        self.update_backround_coords()
        if self.background != None:
            fulllist = fulllist[1:]
        # childs standards :
        for child in fulllist:
            if child.position != BoxModelObject.POSITION_FIXED:
                child.update_publicationRefRect_coords(cr.x, cr.y)
            else:
                child.on_fixed_child_parent_coords_changed()

    def on_publicationRect_dims_changed(self, aftersnap):
        """
        Appelée lors du process de resize quand les dimensions (et éventuellement
        les coords) de publicationRect ont été modifiées
        
        Args:
            aftersnap (boolean): True si consécutif à un calcul de snap, False sinon
        """
        # [Keep for debug] print("VC|",self.name," on_publicationRect_dims_changed")
        # invalidation des rects internes et du display :
        BoxModelObject.on_publicationRect_dims_changed(self, aftersnap)
        # box model conteneur :
        if not aftersnap:
            # invalidation des surfaces alouées :
            self.discard_allocated_area()
            # de l'éventuel snap :
            self.discard_snap()
        # du layout :
        self.discard_layout()

    def on_publicationRect_coords_changed(self, aftersnap):
        """
        Appelée lors du process de resize quand les coordonnées seules
        de publicationRect ont été modifiées (pas les dimensions).
        
        Args:
            aftersnap (boolean): True si consécutif à un calcul de snap, False sinon
        """
        # [Keep for debug] print("VC|",self.name," on_publicationRect_coords_changed")
        # invalidation des rects internes et du display :
        BoxModelObject.on_publicationRect_coords_changed(self, aftersnap)
        # invalidation du layout :
        self.discard_layout()

    def on_resize_achieved(self):
        """
        Appelée à la fin du process de resize de VirtualContainer pour post traitement éventuel.
        """
        # à subclasser au besoin
        pass

    #-----> Pseudos événements émis par les childs affectant le process de resize
    def on_child_unresized(self, child):
        """
        Appelée lorsqu'un child n'est plus resizé.
        
        Args:
            child (BoxModelObject)
        """
        if child != self.background:
            # [Keep for debug] print("VC[",self.name," on_child_unresized child=",child.name, " has_flex=",self.has_flexible_childs())
            if self.direction == None:
                child.resize()
            elif child.in_flow:
                self.discard_layout()
                if self.has_flexible_childs() and child.flex == None:
                    # update complet nécessaire
                    self.discard_allocated_area()
                if self.do_snap:
                    self.discard_snap()

    def on_child_placement_discarded(self, child):
        """
        Chaine de remontée des discard d'update jusqu'au prochain RealContainer.
        
        Args:
            child (BoxModelObject)
        """
        # [Keep for debug] print("VC[",self.name," on_child_placement_discarded child=",child.name)
        if child != self.background:
            if self.direction != None and child.in_flow:
                self.discard_layout()
            if self.do_snap:
                self.discard_snap()

    def on_child_position_changed(self, child):
        """
        Appelée par un child dont l'attribut position a été modifié.
        
        Args:
            child (BoxModelObject)
        """
        if self.direction != None:
            self.discard_layout_list()
            self.discard_layout()
        if self.do_snap:
            self.discard_snap()

    def on_child_flex_changed(self, child):
        """
        Appelée par un child dont l'attribut flex a été modifié.
        
        Args:
            child (BoxModelObject)
        """
        if self.direction != None:
            self.discard_layout_list()
            if child.in_flow:
                # update complet nécessaire
                self.discard_allocated_area()
            self.discard_layout()
            if self.do_snap:
                self.discard_snap()

    def on_child_snap_changed(self, child):
        """
        Appelée par un child dont l'attribut snap a été modifié.
        
        Args:
            child (BoxModelObject)
        """
        if self.direction != None:
            self.discard_layout()
        if self.do_snap:
            self.discard_snap()

    #-----> Update_childs :
    def update_childs(self):
        """
        Redéfinition systématique de la surface alouée à chaque child et appel
        à sa méthode resize (recalcul au besoin).
        """
        # [Keep for debug] print("VC|",self.name," update_childs contentRect=",self.get_content_rect())
        # listes de childs :
        abs_list = self.absolutechildlist
        fixed_list = self.fixedchildlist
        unflex_list = self.unflexchildlist
        flex_list = self.flexchildlist
        # surface alouée de référence
        if self.do_snap:
            # on repart de la version initiale du rect de publication :
            self.publicationRect = self.unsnapped_publicationRect.copy()
            self.discard_inner_rects()
        contentRect = self.get_content_rect()
        if contentRect.w * contentRect.h <= 0:
            return
        rootRect = None
        if self.root_reference != None:
            rootRect = self.root_reference.get_content_rect()
        # 1- Resize des childs hors flow (absolute ou fixed) :
        # - fixed :
        for child in fixed_list:
            child.publicationRefRect = rootRect
            child.resize()
        # - absolute :
        for child in abs_list:
            child.publicationRefRect = contentRect
            child.resize()
        # 2- Resize des childs in flow non flexibles
        unflexspace = 0
        for child in unflex_list:
            child.publicationRefRect = contentRect
            child.resize()
            if self.direction == VirtualContainer.DIRECTION_HORIZONTAL:
                unflexspace += child.width
            elif self.direction == VirtualContainer.DIRECTION_VERTICAL:
                unflexspace += child.height
        # 3- Resize des childs in flow flexibles :
        if self.direction != None:
            if self.direction == VirtualContainer.DIRECTION_HORIZONTAL:
                flexspace = contentRect.width - unflexspace
            elif self.direction == VirtualContainer.DIRECTION_VERTICAL:
                flexspace = contentRect.height - unflexspace
            if len(flex_list) > 0:
                totalflex = 0
                for child in flex_list:
                    totalflex += child.flex
                for child in flex_list:
                    childspace = math.floor(child.flex / totalflex * flexspace)
                    contentRectCopy = contentRect.copy()
                    if self.direction == VirtualContainer.DIRECTION_HORIZONTAL:
                        contentRectCopy.width = childspace
                    else:
                        contentRectCopy.height = childspace
                    child.publicationRefRect = contentRectCopy
                    child.resize()
        # 4- Eventuel fond :
        self.resize_background()
        # validation
        self._allocated_area_updated = True

    def discard_allocated_area(self):
        """
        Invalide la mise à jour des surfaces alouées aux childs.
        """
        # [Keep for debug] print("VC|",self.name," discard_allocated_area !")
        self._allocated_area_updated = False

    def has_flexible_childs(self):
        """
        Indique si un ou plusieurs childs sont flexibles.
        """
        # Maj des listes de childs :
        if not self.layoutlistupdated:
            self.update_layout_list()
        return len(self.flexchildlist) > 0

    #-----> Layout :
    def layout_childs(self):
        """
        Applique le layout basique (si direction != None) aux childs de position fixed ou relative.
        """
        # [Keep for debug] print("VC|",self.name," layout_childs :")
        # 1- Mise à jour des coords de référence :
        cr = self.get_content_rect()
        fulllist = self.relativechildItems
        # fond :
        self.update_backround_coords()
        # childs standards (hors fixed / ref 0,0 immuable)
        for child in fulllist:
            if child.position != BoxModelObject.POSITION_FIXED:
                child.update_publicationRefRect_coords(cr.x, cr.y)
        # 2- Flux de layout :
        if self.direction == None:
            self._layout_updated = True
            return
        if self.direction == VirtualContainer.DIRECTION_HORIZONTAL:
            dim = "width"
            dyn_coord = "x"
        else:
            dim = "height"
            dyn_coord = "y"
        delta = 0
        dyn_val = 0
        for child in self.childtolayout:
            child.apply_parent_layout(dyn_coord, dyn_val)
            delta = child.get_metric_value(dim)
            # [Keep for debug] print(" * layout child=",child.name," x=",child.x," y=",child.y," w=",child.width," h=",child.height)
            dyn_val += delta
        self._layout_updated = True

    def discard_layout(self):
        """
        Invalide le layout des childs.
        """
        self._layout_updated = False

    def discard_layout_list(self):
        """
        Invalide les listes de childs liées au layout.
        """
        self.layoutlistupdated = False

    def update_layout_list(self):
        """
        Reconstitue les listes de childs liées au layout.
        """
        fulllist = self.relativechildItems
        if self.background != None:
            fulllist = fulllist[1:]
        fullset = set(fulllist)
        # childs en position fixed :
        self.fixedchildlist = [
            c for c in fulllist if c.position == BoxModelObject.POSITION_FIXED
        ]
        # pas de flux de layout
        if self.direction == None:
            absset = fullset.difference(set(self.fixedchildlist))
            self.absolutechildlist = list(absset)
            self.unflexchildlist = self.flexchildlist = self.childtolayout = list()
            self.layoutlistupdated = True
            return
        # flux de layout
        self.absolutechildlist = list()
        self.childtolayout = list()
        self.flexchildlist = list()
        self.unflexchildlist = list()
        dosort = True
        for child in fulllist:
            if child.position in [
                BoxModelObject.POSITION_STATIC,
                BoxModelObject.POSITION_RELATIVE,
            ]:
                if child.publication_order == None:
                    dosort = False
                self.childtolayout.append(child)
                if child.flex != None:
                    self.flexchildlist.append(child)
                else:
                    self.unflexchildlist.append(child)
            elif child.position == BoxModelObject.POSITION_ABSOLUTE:
                self.absolutechildlist.append(child)
        if dosort:
            self.childtolayout = sorted(
                self.childtolayout, key=attrgetter("publication_order")
            )
        self.layoutlistupdated = True

    #-----> Snap :
    def handle_snap(self):
        """
        Prise en charge des snaps à la fin du process de resize : pour éviter un bouclage 
        sans fin du process on recalcule les rects en repositionnant au besoin les childs, 
        sans les re resizer.
        """
        childlist = self.get_snap_childs()
        if not self.do_snap or len(childlist) == 0:
            self._snap_updated = True
            return
        if len(childlist) > 0:
            # surface du contenu :
            child0 = childlist[0]
            unionrect = pygame.Rect(0, 0, 0, 0)
            if len(childlist) == 1:
                unionrect = child0.rect
            else:
                rectseq = [c.rect for c in childlist[1:]]
                unionrect = child0.rect.unionall(rectseq)
            cw, ch = unionrect.width, unionrect.height
            if cw * ch > 0:
                ox, oy = int(self.publicationRect.x), int(self.publicationRect.y)
                # générique :
                change = BoxModelObject.handle_item_snap(self, cw, ch)
                if change:
                    # invalidation des rects internes :
                    self.discard_inner_rects()
                    # deltas de coordonnées :
                    dx, dy = self.publicationRect.x - ox, self.publicationRect.y - oy
                    for child in childlist:
                        if child.position != BoxModelObject.POSITION_FIXED:
                            child.x += dx
                            child.y += dy
                    # Indicateur de modification post resize (pour adaptation d'un fond par ex)
                    self.on_snap_occured()
        self._snap_updated = True

    def discard_snap(self):
        """
        Invalide l'éventuel calcul de snap.
        """
        if self.do_snap:
            self._snap_updated = False
        else:
            self._snap_updated = True

    def get_snap_childs(self):
        """
        Retourne la liste des childs à prendre en compte pour les calculs de snap sauf le fond.
        """
        childlist = self.relativechildItems
        if self.background != None:
            childlist = self.relativechildItems[1:]
        return childlist

    def on_snap_occured(self):
        """
        Indique que self.publicationRect.width et/ou self.publicationRect.height ont été modifiées
        lors du process de resize par application d'un snap (adaptation au contenu).
        """
        # Resize de l'éventuel fond :
        self.resize_background()

    #-----> Publication :
    def add_item(self, *childs, **kwargs):
        """
        Ajout d'un ou plusieurs item(s) virtuel(s).
        
        Args:
            childs (list): liste de VirtualItem(s)
        """
        # gestion de la liste des items enfants
        for child in childs:
            # configuration :
            self.configure_child_added(child)
            # liste de publication :
            self.childtoadd.append(child)
        # publication :
        if self.parent != None and len(self.childtoadd) > 0:
            self.add_from_hierarchy(self.childtoadd)
            self.childtoadd = list()

    def configure_child_added(self, child):
        """
        Configuration au moment de l'ajout du child.
        
        Args:
            child (VirtualItem)
        """
        if isinstance(child, VirtualItem):
            # logique de publication
            if child not in self.relativechildItems:
                self.relativechildItems.append(child)
            child.on_item_added(self)
            # layer :
            if child.local_layer == None:
                child.local_layer = self.default_layer
            # boxmodel :
            if self.direction != None and child.position in [
                BoxModelObject.POSITION_STATIC,
                BoxModelObject.POSITION_RELATIVE,
            ]:
                # in flow : discards nécessaires
                self.discard_allocated_area()
                self.discard_snap()
                self.discard_layout_list()
            else:
                # hors flow : mise à jour du seul child
                if child.position == BoxModelObject.POSITION_FIXED:
                    rootRect = None
                    if self.root_reference != None:
                        rootRect = self.root_reference.get_content_rect()
                    # surface alouée
                    child.publicationRefRect = rootRect
                    # maj de la liste de childs associée :
                    self.fixedchildlist.append(child)
                else:
                    # surface alouée
                    child.publicationRefRect = self.get_content_rect()
                    # maj de la liste de childs associée :
                    self.absolutechildlist.append(child)
            # re publication d'un VirtualContainer :
            if child.is_stacked and child.prevpublished:
                # on ajoute sa hiérarchie interne :
                childrens = child.relativechildItems
                for c in childrens:
                    c.parent.add_item(c)

    def add_from_hierarchy(self, childlist):
        """
        Chaine de remontée des items à publier en direction du RealContainer.
        
        Args:
            childlist (list): liste de VirtualItem(s)
        """
        if len(childlist) > 0:
            if self.parent != None:
                self.parent.add_from_hierarchy(childlist)
            else:
                self.childtoadd.extend(childlist)

    def remove_item(self, *childs):
        """
        Suppression d'un ou plusieurs item(s) virtuel(s)
        
        Args:
            childs (list): liste de VirtualItem(s)
        """
        # gestion de la liste des items enfants
        for child in childs:
            # configuraion :
            self.configure_child_removed(child)
            self.childtoremove.append(child)
        # publication :
        if self.parent != None and len(self.childtoremove) > 0:
            self.remove_from_hierarchy(self.childtoremove)
            self.childtoremove = list()

    def configure_child_removed(self, child):
        """
        Configuration au moment de la suppression du child.
        
        Args:
            child (VirtualItem)
        """
        if isinstance(child, VirtualItem) and child in self.relativechildItems:
            # suppression de la liste :
            self.relativechildItems.remove(child)
            # box model :
            if self.direction != None and child.position in [
                BoxModelObject.POSITION_STATIC,
                BoxModelObject.POSITION_RELATIVE,
            ]:
                if child.flex != None:
                    # update complet nécessaire
                    self.discard_allocated_area()
                self.discard_layout_list()
                self.discard_layout()
            else:
                if child.position == BoxModelObject.POSITION_FIXED:
                    self.fixedchildlist.remove(child)
                else:
                    self.absolutechildlist.remove(child)

    def remove_from_hierarchy(self, childlist):
        """
        Chaine de remontée des items à supprimer en direction du RealContainer.
        
        Args:
            childlist (list): liste de VirtualItem(s)
        """
        if len(childlist) > 0:
            if self.parent != None:
                self.parent.remove_from_hierarchy(childlist)
            else:
                self.childtoremove.extend(childlist)

    def on_item_added(self, parent):
        """
        Appelée par le container parent lorsque l'item est ajouté.
        
        Args:
            parent (VirtualContainer)
        """
        # générique :
        VirtualItem.on_item_added(self, parent)
        if self._level != None:
            for child in self.relativechildItems:
                child.level = self._level + 1
        # spécifique :
        if len(self.childtoadd) > 0:
            self.parent.add_from_hierarchy(self.childtoadd)
            self.childtoadd = list()

    def on_item_removed(self):
        """
        Appelée par le container parent lorsque l'item est supprimé
        """
        # spécifique (avant suppression de la ref au parent) :
        if len(self.childtoremove) > 0:
            self.parent.remove_from_hierarchy(self.childtoremove)
            self.childtoremove = list()
        # propagation :
        self.on_parent_removed()
        # générique :
        VirtualItem.on_item_removed(self)

    def on_parent_removed(self):
        """
        Propagé si un parent a été supprimé sans que celui ne supprime sa hiérarchie.
        """
        for child in self.relativechildItems:
            child.on_parent_removed()

    def on_item_added_to_displaylist(self):
        """
        Appelée lorsque l'item (via sa hiérarchie parente) est publié par
        le root dans la displaylist finale.
        """
        VirtualItem.on_item_added_to_displaylist(self)
        for child in self.relativechildItems:
            child.on_item_added_to_displaylist()

    def on_item_removed_from_displaylist(self):
        """
        Appelée lorsque l'item (via sa hiérarchie parente) est dé-publié par
        le root de la displaylist finale.
        """
        VirtualItem.on_item_removed_from_displaylist(self)
        for child in self.relativechildItems:
            child.on_item_removed_from_displaylist()

    def _set_level(self, val):
        if val != self._level:
            self._level = val
        childval = None
        if self._level != None:
            childval = self._level + 1
        for child in self.relativechildItems:
            child.level = childval

    def xget_childs(self, context="publication"):
        """
        Retourne la liste de tous les items de la hiérarchie
        
        Args:
            context (str): permet de spécifier le contexte d'usage (par défaut "publication")
        """
        rlist = list()
        for child in self.relativechildItems:
            if isinstance(child, VirtualItem):
                rlist.append(child)
            if isinstance(child, VirtualContainer):
                rlist.extend(child.xget_childs(context=context))
        return rlist

    #-----> Indicateurs de changement de rendu :
    def on_child_display_discarded(self, child):
        """
        Chaine de remontée des discard d'update jusqu'au prochain RealContainer.
        
        Args:
            child (VirtualItem)
        """
        if self.parent != None:
            self.parent.on_child_display_discarded(child)


class CustomSprite(VirtualItem, pygame.sprite.DirtySprite):
    """
    **Sprite supportant le boxmodel, la mécanique de publication et l'update optimisé.**
    """

    def __init__(self, **kwargs):
        """
        Constructeur
        
        Args:
            **kwargs : peut contenir clip (bool) ainsi que toutes les propriétés de VirtualItem.
        """
        # générique
        pygame.sprite.DirtySprite.__init__(self)
        VirtualItem.__init__(self, **kwargs)
        # clipping :
        self._do_clip = None
        self._cliprect_getter = None  # méthode retournant un rect de clipping
        if "clip" in kwargs.keys():
            self.clip = kwargs["clip"]
        if "cliprect_getter" in kwargs.keys():
            self.cliprect_getter = kwargs["cliprect_getter"]
        # Couleur et surface de fond
        self.transp_color = pygame.Color("#FFFFFF00")
        self._bgcolor = self.transp_color
        if "bgcolor" in kwargs.keys():
            self.bgcolor = kwargs["bgcolor"]
        self.create_default_surface()
        # visibilité
        if "visible" in kwargs.keys():
            self.visible = kwargs["visible"]

    def _init_boxmodel(self, **kwargs):
        """
        Initialise les propriétés de boxmodel.
        """
        # générique :
        BoxModelObject._init_boxmodel(self, **kwargs)
        # spécifique : contenu et fond/bordure sont "blittés" sur la surface
        # par défaut en coordonnées locales
        self._content_scope_global = False

    def _get_bgcolor(self):
        """Couleur de fond (str héxa) convertie au format pygame.Color."""
        return self._bgcolor

    def _set_bgcolor(self, col):
        if not isinstance(col, pygame.Color):
            try:
                col = pygame.Color(col)
            except ValueError:
                col = self.transp_color
        if col != self._bgcolor:
            self._bgcolor = col
            # display :
            self.create_default_surface()
            self.discard_display()

    bgcolor = property(
        _get_bgcolor, _set_bgcolor
    )  #: Couleur de fond (str héxa) convertie au format pygame.Color.

    def create_default_surface(self):
        """
        Crée une surface de publication transparente par défaut.
        """
        if self.rect.width > 0 and self.rect.height > 0:
            self.image = pygame.Surface(
                (self.rect.width, self.rect.height), flags=pygame.locals.SRCALPHA
            )
            self.image = self.image.convert_alpha()
            self.image.fill(self.bgcolor, self.get_border_rect())
        else:
            self.image = pygame.Surface((0, 0))

    def get_pygame_surface(self):
        """
        Retourne la surface pygame de publication.
        """
        if self.image:
            return self.image
        return None

    #-----> Clipping :
    def _set_clip(self, val):
        if isinstance(val, bool):
            self._do_clip = val

    def _get_clip(self):
        """
        Clip le sprite à son rectangle de publication (defaut False).
        """
        return self._do_clip

    clip = property(
        _get_clip, _set_clip
    )  #: Clip le sprite à son rectangle de publication (defaut False).

    # cliprect_getter : méthode fournissant un rect de clipping particulier
    def _set_cliprect_getter(self, rectprovider):
        if callable(rectprovider):
            self._cliprect_getter = rectprovider
            self.clip = True

    def _get_cliprect_getter(self):
        """Méthode fournissant un rect de clipping particulier."""
        return self._cliprect_getter

    cliprect_getter = property(
        _get_cliprect_getter, _set_cliprect_getter
    )  #: Méthode fournissant un rect de clipping particulier.

    def get_display_dest(self):
        """
        Retourne le paramètre dest de l'opération de blit de draw_display.
        Prise en charge du clipping
        """
        dest = None
        area = None
        if self.clip:
            # on clip via la surface de référence
            maskrect = self.publicationRefRect
            if self.cliprect_getter:
                # le rect de clipping est fourni par cliprect_getter
                maskrect = self.cliprect_getter()
            cropRect = self.publicationRect.clip(maskrect)
            dx = cropRect.x - self.publicationRect.x
            dy = cropRect.y - self.publicationRect.y
            dest = (dx, dy)
            dw = cropRect.width
            dh = cropRect.height
            area = pygame.Rect(dx, dy, dw, dh)
        else:
            # par défaut :
            contentRect = self.get_content_rect()
            dest = (contentRect.x, contentRect.y)
        return dest, area

    #-----> Surcharge des super classes
    def discard_placement(self):
        """
        La position a été modifiée, le rendu graphique dans la surface de publication
        du RealContainer assurant la publication n'est plus valable. Par contre le rendu
        "local" de cet objet reste valide.
        """
        # générique :
        change = BoxModelObject.discard_placement(self)
        # spécifique :
        if change:
            self.dirty = 1

    def draw_display(self):
        """
        Dessine ou redessine l'objet.
        """
        # implémentation typique :
        self.create_default_surface()
        # blits spécifiques...
        # display pygame
        self.dirty = 1

    def _get_visible(self):
        """Visibilité du sprite."""
        return bool(pygame.sprite.DirtySprite._get_visible(self))

    def _set_visible(self, val):
        if isinstance(val, bool) and val != self._get_visible():
            pygame.sprite.DirtySprite._set_visible(self, int(val))
            self.discard_display()

    visible = property(_get_visible, _set_visible)  #: Visibilité du sprite (bool).


class RealContainer(VirtualContainer, pygame.sprite.LayeredDirty):
    """
    **Container "réel" disposant de sa surface de publication pygame et des capacités de gestion
    des z-indexs via l'utilisation d'un LayerManager par composition.**
    Pour sa descendance cet objet est vu comme un container, pour son parent il est considéré
    comme un objet terminal (ses couches internes sont applaties sur sa surface de publication).
    """

    def __init__(self, create_surface=True, **kwargs):
        """
        Constructeur
        
        Args:
            create_surface (boolean): création de la surface de publication dès l'initialisation.
            **kwargs : peut contenir toutes les propriétés de VirtualContainer.
        """
        # Initialise les propriétés de publication
        # - liste des sprites d'activation
        self._voidspritelist = list()
        # - listes de publication
        self._publicationlist = list()
        self._publicationorder = 0
        self._removelist = list()
        self._removeorder = 0
        # - indicateur et sprite de display
        self._display_updated = False
        self._pub_sprite = None
        self._bg_clear_surface = None
        self._publication_surface_discarded = False
        # - liste des descendants invalidés / display
        self.child_to_redraw = list()
        # couleur de fond : blanc par défaut
        if "bgcolor" not in kwargs.keys():
            kwargs["bgcolor"] = "#FFFFFF"
        self.transp_color = pygame.Color("#FFFFFF00")
        # générique
        pygame.sprite.LayeredDirty.__init__(self)
        VirtualContainer.__init__(self, **kwargs)
        # Couches internes à publier par un RealContainer parent : non
        self.is_stacked = False
        # Manager de couches :
        self._LayerManager = LayerManager(self)
        # Surface de publication :
        if create_surface:
            self.create_publication_surface()

    def _init_boxmodel(self, **kwargs):
        """
        Initialise les propriétés de boxmodel.
        """
        # générique :
        VirtualContainer._init_boxmodel(self, **kwargs)
        # spécifique : contenu et fond/bordure sont "blittés" sur la surface
        # par défaut en coordonnées locales
        self._content_scope_global = False

    def _init_publication(self):
        """
        Initialise les propriétés de publication.
        """
        # liste des sprites d'activation
        self._voidspritelist = list()
        # listes de publication
        self._publicationlist = list()
        self._publicationorder = 0
        self._removelist = list()
        self._removeorder = 0
        # indicateur et sprite de display
        self._display_updated = False
        self._pub_sprite = None
        self._bg_clear_surface = None
        self._publication_surface_discarded = False
        # liste des descendants invalidés / display
        self.child_to_redraw = list()

    #-----> Fond
    def create_background(self):
        """
        Annule le comportement de VirtualContainer : le fond monochrome
        est directement associé à la surface de publication.
        """
        return

    def _set_bgcolor(self, val):
        """
        Parsing de la couleur de fond (blanc par défaut) : on force la
        composante alpha pour enlever la transparence et ainsi éviter
        les phénomènes de rémanence lors des updates partiels.
        """
        if not isinstance(val, pygame.Color):
            try:
                val = pygame.Color(val)
            except ValueError:
                val = None
        if val != None and val != self._bgcolor:
            # pas de transparence :
            val.a = 255
            self._bgcolor = val
            self.on_bgcolor_changed()

    def on_bgcolor_changed(self):
        """
        Surcharge de VirtualContainer : discard la surface de publication.
        """
        self.discard_publication_surface()

    #-----> Surface de publication :
    def create_publication_surface(self):
        """
        Crée la surface de publication.
        """
        # display sprite
        if self._pub_sprite == None:
            self._pub_sprite = pygame.sprite.DirtySprite()
            self._pub_sprite.name = self.name + "_pubsprite"
        if self.rect.width > 0 and self.rect.height > 0:
            self._pub_sprite.image = pygame.Surface(
                (self.rect.width, self.rect.height), flags=pygame.locals.SRCALPHA
            )
            self._pub_sprite.rect = self.rect
            # clear / bg :
            clearsurf = self.get_clear_surface()
            self.clear(self._pub_sprite.image, clearsurf)
            # clipping
            self.set_clip(self.get_clipping_rect())
        else:
            self._pub_sprite.image = pygame.Surface((0, 0))
            self._pub_sprite.rect = pygame.Rect(0, 0, 0, 0)

    def get_clear_surface(self):
        """
        Retourne la surface équivalente au fond d'un VirtualContainer,
        utilisée en clear par LayeredDirty.
        """
        bgrect = self.get_border_rect()
        bgd = pygame.Surface((self.rect.width, self.rect.height))
        bgd.convert()
        bgd.fill(self.bgcolor, rect=bgrect)
        return bgd

    def update_publication_surface(self):
        """
        Re crée la surface de publication.
        """
        self.create_publication_surface()
        self._publication_surface_discarded = False

    def discard_publication_surface(self):
        """
        Invalide la surface de publication.
        """
        self._publication_surface_discarded = True

    def get_publication_sprite(self):
        """
        Retourne le DirtySprite de publication.
        """
        return self._pub_sprite

    def get_pygame_surface(self):
        """
        Retourne la surface pygame du sprite de publication.
        """
        if self._pub_sprite:
            return self._pub_sprite.image
        return None

    def get_clipping_rect(self):
        """
        Retourne le rect de clipping, par défaut self.borderRect.
        """
        return self.get_border_rect()

    #-----> Indicateurs de changement de rendu :
    def discard_placement(self):
        """
        La position a été modifiée, le rendu graphique dans la surface de publication
        du RealContainer assurant la publication n'est plus valable. Par contre le rendu
        "local" de cet objet reste valide.
        """
        # générique :
        change = BoxModelObject.discard_placement(self)
        # spécifique :
        if change and self._pub_sprite != None:
            self._pub_sprite.dirty = 1

    def on_child_display_discarded(self, child):
        """
        Chaine de remontée des discard d'update jusqu'au prochain RealContainer.
        """
        if child not in self.child_to_redraw:
            self.child_to_redraw.append(child)
        self._display_updated = False
        # [Keep for debug] print("RC|",self.name," on_child_display_discarded child=",child)
        self.discard_display()

    #-----> Update, resize, display :
    def update(self, *args):
        """
        Appelée à chaque frame:
        
        1. Publications éventuelles
        2. Resize générique
        3. Mise à jour du display
        
        """
        # 1- publication éventuelle
        self.manage_publicationlist()
        # 2- resize
        VirtualContainer.update(self, *args)
        # 3- display
        self.handle_display()

    def on_publicationRect_dims_changed(self, aftersnap):
        """
        Appelée lors du process de resize quand les dimensions (et éventuellement
        les coords) de publicationRect ont été modifiées.
        
        Args:
            aftersnap (boolean): True si consécutif à un calcul de snap, False sinon
        """
        # [Keep for debug] print("RC|",self.name," on_publicationRect_dims_changed")
        # générique
        VirtualContainer.on_publicationRect_dims_changed(self, aftersnap)
        # spécifique
        self.discard_publication_surface()

    def on_publicationRect_coords_changed(self, aftersnap):
        """
        Appelée lors du process de resize quand les coordonnées seules
        de publicationRect ont été modifiées (pas les dimensions).
        
        Args:
            aftersnap (boolean): True si consécutif à un calcul de snap, False sinon
        """
        # [Keep for debug] print("RC|",self.name," on_publicationRect_coords_changed")
        # générique
        VirtualContainer.on_publicationRect_coords_changed(self, aftersnap)
        # spécifique
        self.discard_publication_surface()

    def handle_display(self):
        """
        Gère l'affichage du RealContainer. Retourne le nombre de childs retracés.
        """
        # optimisation
        if not self.visible:
            return 0
        # [Keep for debug] print("RC|",self.name," handle_display self._display_updated=",self._display_updated)
        nb = 0
        if not self._display_updated:
            nb = int(len(self.child_to_redraw))
            # redraw de la descendance :
            for child in self.child_to_redraw:
                # [Keep for debug] print("RC|",self.name," redraw de child=",child.name)
                child.draw_display()
            # Re draw : sera déclenché par le prochain RealContainer dans la hiérarchie asc
            self.discard_display()
            # ré initialisations :
            self.child_to_redraw = list()
        return nb

    def draw_display(self):
        """
        Dessine ou redessine l'objet.
        """
        # optimisation
        if not self.visible:
            return
        # [Keep for debug] print("RC|",self.name," draw_display _use_update=",self._use_update)
        # clipping
        if pygame.sprite.LayeredDirty.get_clip(self) != self.get_clipping_rect():
            pygame.sprite.LayeredDirty.set_clip(
                self, screen_rect=self.get_clipping_rect()
            )
        # Update éventuel de la surface de publication
        if self._publication_surface_discarded:
            # publicationRect a été modifié, on retrace...
            self.update_publication_surface()
            # ... tout :
            # self.xforce_update()
        # On trace
        self.draw(self.get_pygame_surface())
        # optimisation (debug?) : LayeredDirty ne passe pas forcément les
        # sprites à dirty=0 après l'appel à draw.
        for sprite in self.sprites():
            sprite.dirty = 0
        # Marque le sprite de publication comme dirty
        self._pub_sprite.dirty = 1
        # Indicateur de mise à jour
        self._display_updated = True

    def xforce_update(self):
        """
        Force le redraw de tous les sprites de la displaylist.
        """
        for s in self.sprites():
            s.dirty = 1

    #-----> Logique de publication spécifique :
    def manage_publicationlist(self):
        """
        Ajoute/retire les items en attente.
        """
        dochange = False
        rects = list()
        # 1- suppression :
        if len(self._removelist) > 0:
            dochange = True
            fulldellist = list()
            for child in self._removelist:
                if isinstance(child, VirtualContainer) and child.is_stacked:
                    fulldellist.extend(
                        [c for c in child.xget_childs() if c not in fulldellist]
                    )
                elif child not in fulldellist:
                    fulldellist.append(child)
            rects.extend(self._remove_item_internal(*fulldellist))
            self._removelist = list()
        # 2- ajout :
        if len(self._publicationlist) > 0:
            dochange = True
            count = len(self._publicationlist)
            # 2.1- Def levels
            leveldefined = list()
            while count > 0:
                for child in self._publicationlist:
                    if (
                        child.level == None
                        and child.parent != None
                        and child.parent.level != None
                    ):
                        child.level = child.parent.level + 1
                    if child.level != None:
                        leveldefined.append(child)
                        self._publicationlist.remove(child)
                        count -= 1
            # 2.2- publication par levels croissants
            if len(leveldefined) > 0:
                rects.extend(self._add_item_internal(*leveldefined))
            self._publicationlist = list()
        # 3- ménage :
        if dochange:
            self._LayerManager.clean()
            self.clean_voidsprites()
            # [Keep for debug] self._LayerManager.trace(full=True)
        return rects, dochange

    def add_item(self, *childs, **kwargs):
        """
        Ajout d'un ou plusieurs item(s) virtuel(s).
        """
        for child in childs:
            # configuration :
            self.configure_child_added(child)
        self._add_to_publicationlist(childs)

    def add_from_hierarchy(self, childlist):
        """
        Chaine de remontée des items à publier en direction du RealContainer (aka self).
        """
        self._add_to_publicationlist(childlist)

    def _add_to_publicationlist(self, childs):
        for child in childs:
            if isinstance(child, VirtualItem):
                # mémorisation de l'ordre de publication
                child.publication_order = self._publicationorder
                self._publicationorder += 1
        self._publicationlist.extend(childs)

    def _add_item_internal(self, *childs, **kwargs):
        """
        Ajout d'un ou plusieurs item(s) virtuel(s).
        """
        # 1- Enregistrement générique (et définition de local_layer)
        virtitemslist = list()
        for child in childs:
            if isinstance(child, VirtualItem):
                virtitemslist.append(child)
        # 2- Gestion des z-indexs (publication_layer)
        virtitemslist = sorted(virtitemslist, key=attrgetter("level"))
        levelvalues = list()
        for item in virtitemslist:
            if item.level not in levelvalues:
                levelvalues.append(item.level)
        # levels croissants :
        for level in levelvalues:
            batchlevel = [item for item in virtitemslist if (item.level == level)]
            if len(batchlevel) > 0:
                batchlevel = sorted(
                    batchlevel, key=attrgetter("local_layer", "publication_order")
                )
                self._LayerManager.batch_add_item(*batchlevel)
        # 3- Publication :
        rects = list()
        virtitemslist = sorted(
            virtitemslist, key=attrgetter("level", "local_layer", "publication_order")
        )
        for child in virtitemslist:
            if isinstance(child, VirtualItem):
                child.prevpublished = True
                self.add_child_to_displaylist(child)
            if isinstance(child, CustomSprite):
                pygame.sprite.LayeredDirty.add(
                    self, child, layer=child.publication_layer
                )
                rects.append(child.rect)
            elif isinstance(child, RealContainer):
                pubsprite = child.get_publication_sprite()
                pygame.sprite.LayeredDirty.add(
                    self, pubsprite, layer=child.publication_layer
                )
                rects.append(pubsprite.rect)
            elif isinstance(child, VirtualContainer) and child.is_stacked:
                self.active_layer(child.publication_layer)
        return rects

    def add_child_to_displaylist(self, child):
        """
        Appelée lors de _add_item_internal, child est un VirtualItem.
        """
        if self.belong_to_displaylist():
            child.on_item_added_to_displaylist()

    def remove_item(self, *childs):
        """
        Suppression d'un ou plusieurs item(s) virtuel(s).
        """
        for child in childs:
            # configuraion :
            self.configure_child_removed(child)
        self._add_to_removelist(childs)

    def remove_from_hierarchy(self, childlist):
        """
        Chaine de remontée des items à supprimer en direction du RealContainer (aka self).
        """
        self._add_to_removelist(childlist)

    def _add_to_removelist(self, childs):
        self._removelist.extend(childs)

    def _remove_item_internal(self, *childs):
        """
        Suppression d'un ou plusieurs item(s) virtuel(s).
        """
        # 1- Suppression générique
        virtitemslist = list()
        for child in childs:
            # générique :
            if isinstance(child, VirtualItem):
                virtitemslist.append(child)
        # 2- Gestion des z-indexs (publication_layer)
        virtitemslist = sorted(virtitemslist, key=attrgetter("level"), reverse=True)
        levelvalues = list()
        for item in virtitemslist:
            if item.level not in levelvalues:
                levelvalues.append(item.level)
        levelvalues.sort(reverse=True)
        # levels décroissants :
        for level in levelvalues:
            batchlevel = [item for item in virtitemslist if (item.level == level)]
            if len(batchlevel) > 0:
                batchlevel = sorted(
                    batchlevel, key=attrgetter("local_layer"), reverse=True
                )
                self._LayerManager.batch_remove_item(*batchlevel)
        # 3- Publication :
        rects = list()
        for child in childs:
            if isinstance(child, RealContainer):
                pubsprite = child.get_publication_sprite()
                pygame.sprite.LayeredDirty.remove(self, pubsprite)
                rects.append(pubsprite.rect)
            if isinstance(child, CustomSprite):
                pygame.sprite.LayeredDirty.remove(self, child)
                rects.append(child.rect)
            if isinstance(child, VirtualItem):
                self.remove_child_from_displaylist(child)
                child.on_item_removed()
        return rects

    def remove_child_from_displaylist(self, child):
        """
        Appelée lors de _remove_item_internal, child est un VirtualItem.
        """
        if self.belong_to_displaylist():
            child.on_item_removed_from_displaylist()

    def xget_childs(self, context="publication"):
        """
        Retourne la liste de tous les items de la hiérarchie
        
        Args:
            context (str): permet de spécifier le contexte d'usage (par défaut "publication")
        """
        if context == "publication":
            # ce container prend en charge sa propre hiérarchie
            return list()
        else:
            return VirtualContainer.xget_childs(self, context=context)

    #-----> Gestion "physique" des couches :
    def doswap_layers(self, oldlayer, newlayer):
        """
        Echange les zindexs de deux couches.
        """
        usedlayers = self.layers().copy()
        if len(usedlayers) == 0:
            return
        if oldlayer in usedlayers:
            # retraits :
            oldlist = self.remove_sprites_of_layer(oldlayer)
            if not newlayer in usedlayers:
                self.active_layer(newlayer)
            newlist = self.remove_sprites_of_layer(newlayer)
            # ajouts :
            self.add(newlist, layer=oldlayer)
            self.add(oldlist, layer=newlayer)

    def active_layer(self, layer):
        """
        Active une couche par l'ajout d'un sprite invisible.
        """
        voidspr = self.get_void_sprite()
        self.add(voidspr, layer=layer)

    def get_void_sprite(self):
        """
        Crée un sprite invisible pour l'activation d'une couche.
        """
        voidspr = pygame.sprite.DirtySprite()
        voidspr.image = pygame.Surface((1, 1))
        voidspr.image.convert_alpha()
        voidspr.image.fill(pygame.Color("0xffffff00"))
        voidspr.rect = voidspr.image.get_rect()
        voidspr.dirty = 1
        self._voidspritelist.append(voidspr)
        return voidspr

    def clean_voidsprites(self):
        """
        Supprime les sprites d'activation.
        """
        for vspr in self._voidspritelist:
            # suppression standard
            pygame.sprite.LayeredDirty.remove(self, vspr)

    #-----> Visibilité :
    def _get_visible(self):
        return bool(self._pub_sprite.visible)

    def _set_visible(self, val):
        if isinstance(val, bool) and val != self._get_visible():
            self._pub_sprite.visible = int(val)
            self._pub_sprite.dirty = 1
            self.discard_display()

    visible = property(_get_visible, _set_visible)  #: Visibilité (bool)


class RootContainer(RealContainer, evt.GUIEventManager):
    """
    **Container racine de l'application.**
    """

    # statique
    # aspect-ratios standards en mono moniteur
    STD_ASPECT_RATIOS = [
        Fraction(1366, 768),
        Fraction(1920, 1080),
        Fraction(1440, 900),
        Fraction(1536, 864),
        Fraction(1600, 900),
        Fraction(1280, 800),
        Fraction(1280, 720),
        Fraction(1280, 1024),
        Fraction(1024, 768),
        Fraction(1680, 1050),
        Fraction(1360, 768),
        Fraction(1920, 1200),
        Fraction(800, 600),
        Fraction(1208, 768),
    ]  #: aspect-ratios standards en mono moniteur
    # modes plein écran :
    # résolution max du moniteur
    FULLSCREEN_MODE_MAX = "FULLSCREEN_MODE_MAX"  #: résolution max du moniteur
    # résolution supportée la plus proche des dimensions originelles de l'interface
    FULLSCREEN_MODE_NEAREST = "FULLSCREEN_MODE_NEAREST"  #: résolution supportée la plus proche des dimensions originelles de l'interface
    # mode par défaut :
    FULLSCREEN_MODE_DEFAULT = FULLSCREEN_MODE_NEAREST  #: mode par défaut
    # méthodes
    def __init__(self, resizable=True, framerate=60, icon=None, caption="", **kwargs):
        """
        LayeredDirty de plus haut niveau.
        
        Args:
            resizable (boolean): indique si l'application est redimensionnable, vrai par défaut
            framerate (int): 60 par défaut
            bgcolor (str hexa): couleur de fond, blanc par défaut
            icon (surface): surface pygame remplaçant l'icône par défaut
            caption (str): titre de la fenêtre
            **kwargs: toutes propriétés supportées par RealContainer
        
        Raises:
            Exception si width et height ne sont pas définis explicitement.
        """
        # test préalable :
        if "width" not in kwargs.keys() or "height" not in kwargs.keys():
            raise Exception(
                "RootContainer nécessite de définir explicitement les attributs width et height"
            )
        # initialisation pygame :
        os.environ["PYGAME_FREETYPE"] = "1"
        self._video_info = pygame.display.Info()
        pygame.init()
        # surface pour icône personnalisée :
        self.icon = icon
        # titre de la fenêtre
        self.caption = caption
        # surface du moniteur :
        self.monitor_width = None
        self.monitor_height = None
        # dimensions originelles
        self.original_size = None
        # dimensions de plein écran :
        self.fullscreen_size = None
        # plein écran :
        self._support_fullscreen = False
        self._is_fullscreen = False
        # resize :
        self.resizable = resizable
        self._init_resize()
        # framerate :
        self.framerate = framerate
        # surface de publication
        self.publication_surface = None
        # générique
        RealContainer.__init__(self, create_surface=False, **kwargs)
        evt.GUIEventManager.__init__(self)
        # displaylist (appartenance)
        self._added_to_displaylist = True
        # Niveau d'imbrication dans la hiérarchie globale :
        self._level = 0
        # init framerate :
        self._init_framerate()
        # init vidéo
        self._init_videomode()
        # surface initiale :
        self.create_publication_surface()

    def _init_boxmodel(self, **kwargs):
        """
        Initialise les propriétés de boxmodel
        """
        # Surcharge des paramètres :
        kwargs["position"] = BoxModelObject.POSITION_ABSOLUTE
        kwargs["x"] = kwargs["y"] = 0
        kwargs["top"] = kwargs["bottom"] = kwargs["left"] = kwargs["right"] = None
        kwargs["snapW"] = kwargs["snapH"] = False
        kwargs["align"] = kwargs["valign"] = None
        # générique :
        RealContainer._init_boxmodel(self, **kwargs)
        # Définition de la surface de référence
        self.publicationRefRect = pygame.Rect(
            0, 0, int(kwargs["width"]), int(kwargs["height"])
        )

    def _init_resize(self):
        """
        Initialise les propriétés liées au resize.
        """
        self.resize_frame_delay = 0
        self.last_resize_event = None

    #-----> Spécifique
    def _init_framerate(self):
        """
        Initialise le framerate.
        """
        self.clock = pygame.time.Clock()
        self.clock.tick(self.framerate)

    def _init_videomode(self):
        """
        Initialisation des propriétés vidéos.
        
        .. admonition::
            Attention: sous windows la résolution totale (si plusieurs moniteurs)
            n'est pas détectée. Le mode plein écran peut donc être activé en 
            multi écrans alors qu'il cause des bugs d'affichage.
            
            Remarque: une tentative de dénombrage des moniteurs avec Xlib n'a 
            pas été concluante (display.Display().screen_count() ne retourne
            pas le nombre exact d'écrans). 
            
        Todo:
            une solution pour windows via win32api: ::
        
            import platform
            if platform.system() == 'Windows':
                # par défaut on désactive le plein écran
                self._support_fullscreen = False
                # on essaye de dénombrer les écrans :
                try:
                    import win32api
                except Import Error:
                    print("win32api missing")
                else:
                    screencount = len(win32api.EnumDisplayMonitors())
                    if screencount == 1:
                        # on active le plein écran :
                        self._support_fullscreen = True
            
        """
        # résolution du moniteur
        self.monitor_width, self.monitor_height = (
            self._video_info.current_w,
            self._video_info.current_h,
        )
        # aspect ratio associé :
        aspect_ratio = 0
        if (
            isinstance(self.monitor_width, int)
            and isinstance(self.monitor_height, int)
            and self.monitor_width * self.monitor_height > 0
        ):
            aspect_ratio = Fraction(self.monitor_width, self.monitor_height)
        # ce ratio est il standard? (on doit éviter d'activer le plein écran
        # si il y a plusieurs moniteurs, cf perturbations de l'affichage
        # connues avec SDL 1.2)
        if aspect_ratio in RootContainer.STD_ASPECT_RATIOS:
            self._support_fullscreen = True
        # todo: patch windows via win32api
        # mémorisation des dimensions originelles :
        self.original_size = (
            self.get_metric_value("width"),
            self.get_metric_value("height"),
        )
        self.rect.width, self.rect.height = self.original_size
        # résolution la plus proche supportée dans les modes vidéo de la plate
        # forme :
        if self._support_fullscreen:
            lm = pygame.display.list_modes()
            if len(lm) > 0:
                modelist = list()
                for s in lm:
                    w, h = s[0], s[1]
                    dw = math.fabs(w - self.original_size[0])
                    dh = math.fabs(h - self.original_size[1])
                    sortdict = {"size": s, "surf": w * h, "delta": dw + dh}
                    modelist.append(sortdict)
                if (
                    RootContainer.FULLSCREEN_MODE_DEFAULT
                    == RootContainer.FULLSCREEN_MODE_MAX
                ):
                    # on prend la plus grande résolution supportée par le moniteur
                    modelist.sort(key=itemgetter("surf"), reverse=True)
                elif (
                    RootContainer.FULLSCREEN_MODE_DEFAULT
                    == RootContainer.FULLSCREEN_MODE_NEAREST
                ):
                    # on prend celle qui se rapproche le plus de la surface originelle
                    modelist.sort(key=itemgetter("delta"))
                # la surface de plein écran :
                self.fullscreen_size = modelist[0]["size"]

    def toggle_fullscreen(self):
        """
        Entre / sort du mode plein écran.
        """
        if self._support_fullscreen:
            self._is_fullscreen = not self._is_fullscreen
            if self._is_fullscreen:
                self.width, self.height = self.fullscreen_size
            else:
                self.width, self.height = self.original_size
            self.discard_publication_surface()
            self.update()

    def is_fullscreen(self):
        """Indique si l'application est en plein écran."""
        return self._is_fullscreen

    def support_fullscreen(self):
        """
        Indique si le plein écran est supporté
        """
        return self._support_fullscreen

    #-----> Surcharge de RealContainer :
    def add_child_to_displaylist(self, child):
        """
        Appelée lors de _add_item_internal, child est un VirtualItem.
        """
        # Root est toujours dans la displaylist
        child.on_item_added_to_displaylist()
        # événements : évite que la Queue Pygame soit saturée lors de l'initialisation
        self.handle_events()

    def remove_child_from_displaylist(self, child):
        """
        Appelée lors de _remove_item_internal, child est un VirtualItem.
        """
        # Root est toujours dans la displaylist
        child.on_item_removed_from_displaylist()
        # événements : évite que la Queue Pygame soit saturée lors de l'initialisation
        self.handle_events()

    def create_publication_surface(self):
        """
        Crée la surface de publication.
        """
        # configuration :
        pygame.display.quit()
        pygame.display.init()
        # icon (avant set_mode)
        if isinstance(self.icon, pygame.Surface):
            pygame.display.set_icon(self.icon)
        # titre fenêtre
        pygame.display.set_caption(self.caption)
        # mode
        if self._support_fullscreen and self._is_fullscreen:
            # mode plein écran :
            self.publication_surface = pygame.display.set_mode(
                self.fullscreen_size,
                pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF,
            )
        else:
            # mode fenêtré :
            if not self.resizable:
                self.publication_surface = pygame.display.set_mode(
                    (self.rect.width, self.rect.height)
                )
            else:
                self.publication_surface = pygame.display.set_mode(
                    (self.rect.width, self.rect.height), pygame.RESIZABLE
                )
        # surface de clear :
        self._bg_clear_surface = pygame.Surface((self.rect.width, self.rect.height))
        self._bg_clear_surface.convert()
        self._bg_clear_surface.fill(self.bgcolor, rect=self.rect)
        self.clear(self.publication_surface, self._bg_clear_surface)
        # clipping
        self.set_clip(self.rect)

    def update(self, *args):
        """
        Englobe la méthode héritée de RealContainer dans un test. Permet de
        catcher l'exception éventuellement générée par la fermeture de la fenêtre
        lors d'un process de publication.
        """
        try:
            RealContainer.update(self, *args)
        except Exception as e:
            if pygame.display.get_init():
                # si le display est encore initialisé alors il s'agit bien d'une erreur
                raise (e)

    def handle_display(self):
        """
        Gère l'affichage du RootContainer.
        """
        # [Keep for debug] print("...\nROOT| handle_display self._display_updated=",self._display_updated)
        if not self._display_updated:
            self._display_updated = True
            # Update éventuel de la surface de publication
            if self._publication_surface_discarded:
                # publicationRect a été modifié, on retrace...
                self.update_publication_surface()
                # ... tout :
                # self.xforce_update()
            # redraw de la descendance :
            for child in self.child_to_redraw:
                # [Keep for debug] print("ROOT redraw de child=",child.name," rect=",child.rect)
                child.draw_display()
            # Re draw :
            rects = self.draw(self.publication_surface)
            # [Keep for debug] print("ROOT >> handle_display rects=",rects)
            pygame.display.update(rects)
            # ré initialisations :
            self.child_to_redraw = list()

    def xget_childs(self, context="publication"):
        """
        Retourne la liste de tous les items de la hiérarchie : annule le comportement 
        de RealContainer.
        
        Args:
            context (str): permet de spécifier le contexte d'usage (par défaut "publication")
        """
        return VirtualContainer.xget_childs(self, context=context)

    #-----> Thread
    def start_GUI(self):
        """
        Démarre le process de gestion de la GUI.
        """
        self.gui_process_active = True
        self.run_GUI_process()

    def stop_GUI(self):
        """
        Stop le process de gestion de la GUI.
        """
        self.gui_process_active = False

    def run_GUI_process(self):
        """
        Boucle de gestion de la GUI
        """
        while self.gui_process_active:
            # pré-traitements personnalisés :
            self.before_frame_processed()
            # événements :
            self.handle_events()
            # publication, propagation des updates, resize et display :
            self.update()

    def before_frame_processed(self):
        """
        Appelée à chaque frame d'exécution avant les traitements génériques de
        Root (événements puis update graphique).
        """
        return

    def on_quit_event(self, event):
        """
        Méthode appelée par CustomEventManager lorsque survient l'événement pygame.QUIT. 
        Rq : l'événement n'a aucun attribut particulier.
        """
        # pygame :
        self.close_Root()
        # à subclasser au besoin

    def close_Root(self):
        """
        Fermeture du root pygame.
        """
        # Arrêt de la boucle run :
        self.stop_GUI()
        # Evite l'erreur "video system not initialized" lors de l'appel à
        # pygame.event.get() dans la version initiale de handle_events :
        self.handle_events = lambda: None
        # Clôture de Pygame :
        pygame.quit()

    #-----> Resize spécifique :
    def resize(self, **kwargs):
        """
        Surcharge de VirtualContainer.resize()
        """
        # [Keep for debug] print("\n\nROOT Update...")
        # générique :
        resized = RealContainer.resize(self, **kwargs)
        # self._LayerManager.trace()
        if resized:
            self._display_updated = False
            self.discard_publication_surface()

    def on_resize_event(self, event):
        """
        Méthode appelée par CustomEventManager lorsque survient l'événement pygame.VIDEORESIZE. 
        Rq : attributs : size, w, h
        """
        self.width = self.height = "100%"
        self.publicationRefRect.width = int(event.w)
        self.publicationRefRect.height = int(event.h)
        self.discard_resize()


#-----> Z indexs : gestionnaire de couches
class LayerManager:
    """
    **Objet modélisant la gestion des couches (z-indexs), utilisé par composition par
    un RealContainer.**
    """

    def __init__(self, root):
        """
        Constructeur
        
        Args:
            root (RealContainer)
        """
        # RealContainer associé :
        self.root = root
        # LayerStack Root :
        self.rootstack = LayerStack(self.root, None, None, self, 0)
        self.rootstack.globallayer = 0
        # dict cont / LayerStack
        self.stackdict = {root: self.rootstack}
        # liste des couches à supprimer
        self._unusedlayerlist = list()

    def trace(self, full=False):
        """Debug."""
        # debug
        print("LayerManager... ")
        self.rootstack.trace(full=full)
        print("--- Couches réelles de ", self.root.name, "  ---")
        for layer in self.root.layers():
            print("> layer = ", layer)
            layersprites = self.root.get_sprites_from_layer(layer)
            if full:
                for sp in layersprites:
                    if hasattr(sp, "name") and hasattr(sp, "publication_layer"):
                        print(
                            "  - ", sp.name, " publication_layer=", sp.publication_layer
                        )
                    else:
                        print("  - ", sp)
            else:
                print(" -> layersprites : ", len(layersprites), " éléments.")

    def register_layerstack(self, stackobj):
        """
        Enregistre un nouvel objet LayerStack associé à un conteneur.
        
        Args:
            stackobj (LayerStack)
        """
        if stackobj != None:
            cont = stackobj.container
            self.stackdict[cont] = stackobj

    def unregister_layerstack(self, stackobj):
        """
        Supprime la référence à stackobj
        
        Args:
            stackobj (LayerStack)
        """
        if stackobj.container in self.stackdict.keys():
            del self.stackdict[stackobj.container]

    def batch_add_item(self, *items):
        """
        Publication en batch d'une liste d'items.
        
        Args:
            *items (list): liste de VirtualItem ou VirtualContainer
                
        Définit l'attribut publication_layer de chaque item, gère les dépendances. 
        Le process de publication fait en sorte que la hiérarchie de parents soit connue 
        de ce manager.
        """
        swaplist = list()
        # Ajout délégué à l'objet ContainerLayers parent
        for item in items:
            parent = item.parent
            parentstack = self.get_stack_for_container(parent)
            parentstack.add_item(item)
        # application des offsets aux objets existants
        swaplist.extend(self.handle_changes_internal())
        # Gestion physique des couches de la display list :
        self.update_displaylist(swaplist, True)

    def batch_remove_item(self, *items):
        """
        Dé publication en batch d'une liste d'items.
        
        Args:
            *items (list): liste de VirtualItem ou VirtualContainer
        """
        swaplist = list()
        # Ajout délégué à l'objet ContainerLayers parent
        for item in items:
            parent = item.parent
            parentstack = self.get_stack_for_container(parent)
            parentstack.remove_item(item)
        # application des offsets aux objets existants
        swaplist.extend(self.handle_changes_internal())
        # Gestion physique des couches de la display list :
        self.update_displaylist(swaplist, False)

    def handle_changes_internal(self):
        """
        Applique les décallages de couches portés par les offsets.
        """
        # mise à jour interne :
        swaplist = self.rootstack.apply_offset(None)
        return swaplist

    def update_displaylist(self, changelist, doadd):
        """
        Applique les décallages de couches à la displaylist.
        """
        if doadd:
            # offsets > 0
            changelist = sorted(changelist, key=itemgetter(0), reverse=True)
        else:
            changelist = sorted(changelist, key=itemgetter(0))
        for changetup in changelist:
            self.root.doswap_layers(*changetup)

    def clean(self):
        """
        Nettoyage des structures de données.
        """
        # liste des LayerStacks :
        stacklist = [s for s in self.stackdict.values()]
        stacklist.sort(key=attrgetter("level"), reverse=True)
        stacklist.sort(key=attrgetter("locallayer"), reverse=True)
        # suppression récursive des couches locales vides :
        changelist = list()
        for stack in stacklist:
            layerindices = [ind for ind in stack.locallayerdict.keys()]
            layerindices.sort(reverse=True)
            for ind in layerindices:
                layer = stack.locallayerdict[ind]
                if layer.is_empty():
                    globalrange = layer.get_globalrange()
                    changelist.extend([l for l in globalrange])
                    stack.delete_layer(ind)
        # définition des offsets :
        self.rootstack.handle_changelist(changelist, False)
        # application des offsets :
        swaplist = self.rootstack.apply_offset(None)
        # décallages physiques :
        self.update_displaylist(swaplist, False)

    def get_stack_for_container(self, cont):
        """
        Retourne l'objet LayerStack associé à un VirtualContainer.
        """
        if cont in self.stackdict.keys():
            return self.stackdict[cont]
        return None


class LayerStack:
    """
    **Modélise la pile de couches d'un conteneur.**
    """

    def __init__(self, container, parentstack, parentlayer, layerMngr, locallayer):
        """
        Constructeur
        
        Args:
            container (VirtualContainer): le container considéré
            parentstack (LayerStack): LayerStack de son parent
            parentlayer (LocalLayer): couche locale du parent
            layerMngr (LayerManager): gestionnaire de zindexs mobilisé
            locallayer (int): indice local dans la pile parente
        """
        # VirtualContainer associé :
        self.container = container
        self.name = "LS de " + self.container.name
        # LayerStack associé au conteneur parent
        self.parentstack = parentstack
        self.level = 0
        if self.parentstack != None:
            self.level = self.parentstack.level + 1
        # couche locale du parent :
        self.parentlayer = parentlayer
        # ref au LayerManager
        self.layerMngr = layerMngr
        # indice local dans la pile parente :
        self.locallayer = locallayer
        # couche globale associée à la couche locale 0
        self._globallayer = None
        if isinstance(self.container, RealContainer):
            self._globallayer = 0
        # offset pour différer les décallages de couches
        self.offset = 0
        # dict d'indice de couche locale / LocalLayer
        self.locallayerdict = dict()
        # création de la couche 0 :
        self.create_base_layer()

    def create_base_layer(self):
        """
        Crée la couche 0 à l'initialisation.
        """
        newlayer = self.create_locallayer(0)[1]
        if self.globallayer != None:
            newlayer.globallayer = self.globallayer
        self.post_create_layer(newlayer)

    def get_base_layer(self):
        """
        Retourne la couche 0.
        """
        if 0 in self.locallayerdict.keys():
            return self.locallayerdict[0]
        return None

    def trace(self, full=False):
        """Debug."""
        # debug
        px = "   " * self.level
        txt = (
            px
            + " > LayerStack de "
            + self.container.name
            + "[local="
            + str(self.locallayer)
            + " global="
            + str(self.globallayer)
            + " offset="
            + str(self.offset)
            + " globalrange="
            + str(self.get_globalrange())
            + "]"
        )
        print(txt)
        for locallayer in self.locallayerdict.values():
            locallayer.trace(full=full)

    def is_empty(self):
        """
        Indique si la stack est vide de couches.
        """
        indices = [ind for ind in self.locallayerdict.keys()]
        return len(indices) == 0

    def add_item(self, item):
        """
        Ajoute un VirtualItem ou VirtualContainer.
        """
        newlayer = newstackobj = change1 = change2 = None
        # liste des couches globales mobilisées
        changelist = list()
        # Création de la couche locale au besoin :
        local_layer = item.local_layer
        if local_layer not in self.locallayerdict.keys():
            change1, newlayer = self.create_locallayer(local_layer)
            if change1 != None:
                changelist.extend(change1)
                # Gestion des modifications par offsets:
                self.handle_changelist(list(change1), True)
            # Enregistrement après propagation des offsets :
            self.post_create_layer(newlayer)
        # En fonction de l'item :
        if isinstance(item, VirtualItem):
            if item.is_stacked:
                change2, newstackobj = self.add_container(item, local_layer)
                self.layerMngr.register_layerstack(newstackobj)
                if change2 != None:
                    changelist.extend(change2)
            else:
                self.add_element(item, local_layer)
        # Gestion des modifications par offsets:
        if change2 != None:
            self.handle_changelist(list(change2), True)
        # Enregistrement après propagation des offsets :
        if newstackobj != None:
            self.post_add_stack(newstackobj)
        # Retour :
        return changelist

    def remove_item(self, item):
        """
        Supprime l'item (son éventuelle hiérarchie est prise en charge par le LayerManager).
        """
        # liste des couches globales libérées
        changelist = list()
        # En fonction de l'item :
        local_layer = item.local_layer
        if isinstance(item, VirtualItem):
            if item.is_stacked:
                change = self.remove_container(item, local_layer)
                if change != None:
                    changelist.extend(change)
            else:
                self.remove_element(item, local_layer)
        # Gestion des modifications :
        self.handle_changelist(changelist, False)
        # Retour :
        return changelist

    def handle_changelist(self, changelist, doadd):
        """
        Gestion des décallages de couches.
        """
        if len(changelist) > 0:
            if doadd:
                changelist.sort()
            else:
                changelist.sort(reverse=True)
            for change in changelist:
                fromlayer = change
                if doadd:
                    offset = 1
                else:
                    offset = -1
                # propagation vers le RealContainer
                self.fire_offset_change(fromlayer, offset)

    def add_element(self, element, local_layer):
        """
        Ajoute un VirtualItem dans la couche locale local_layer.
        """
        # les éléments sont ajoutés dans la couche globale de base de
        # la couche locale
        layer = self.locallayerdict[local_layer]
        layer.add_element(element)
        return None

    def add_container(self, cont, local_layer):
        """
        Ajoute un conteneur dans la couche locale local_layer.
        """
        layer = self.locallayerdict[local_layer]
        newstack = LayerStack(cont, self, layer, self.layerMngr, local_layer)
        changes = layer.add_stack(newstack)
        return changes, newstack

    def post_add_stack(self, stackobj):
        """
        Enregistrement d'un LayerStack dans sa couche locale.
        """
        local_layer = stackobj.locallayer
        layer = self.locallayerdict[local_layer]
        layer.register_stack(stackobj)

    def remove_element(self, element, local_layer):
        """
        Supprime un VirtualItem de la couche locale local_layer.
        """
        layer = self.locallayerdict[local_layer]
        layer.remove_element(element)
        return None

    def remove_container(self, cont, local_layer):
        """
        Supprime un conteneur de la couche locale local_layer.
        """
        layer = self.locallayerdict[local_layer]
        stackobj = self.layerMngr.get_stack_for_container(cont)
        changes = layer.remove_stack(stackobj)
        return changes

    def create_locallayer(self, indice):
        """
        Crée une couche locale.
        """
        if indice not in self.locallayerdict.keys():
            # création :
            newlocallayer = LocalLayer(self, indice, self.layerMngr)
            # placement dans la pile :
            returnrange = None
            if self.globallayer != None:
                globind = self._globallayer + self.offset
                if indice > 0:
                    i = 0
                    while i < indice:
                        if i in self.locallayerdict.keys():
                            prevlayer = self.locallayerdict[i]
                            prevrange = prevlayer.get_globalrange()
                            globind = prevrange[-1] + 1
                        i += 1
                    returnrange = range(globind, globind + 1)
                newlocallayer.globallayer = globind
            return returnrange, newlocallayer
        return None, None

    def post_create_layer(self, layerobj):
        """
        Enregistrement d'une nouvelle couche locale.
        """
        local_layer = layerobj.locallayer
        if local_layer not in self.locallayerdict.keys():
            self.locallayerdict[local_layer] = layerobj

    def delete_layer(self, indice):
        """
        Supprime l'entrée associée à l'indice de la couche.
        """
        if indice in self.locallayerdict.keys():
            del self.locallayerdict[indice]

    def apply_offset(self, swaplist):
        """
        Applique les décallages cumulés de couches, retourne une liste de swaps à appliquer
        aux couches globales physiques.
        """
        if swaplist == None:
            swaplist = list()
        if self.globallayer != None and self.offset != None and self.offset != 0:
            swaptup = (int(self.globallayer), int(self.globallayer + self.offset))
            if swaptup not in swaplist:
                swaplist.append(swaptup)
            self.globallayer += self.offset
            self.container.publication_layer = self.globallayer
        for locallayer in self.locallayerdict.values():
            locallayer.apply_offset(swaplist)
        self.offset = 0
        return swaplist

    def fire_offset_change(self, fromlayer, delta):
        """
        Remonte l'événement de décallage jusqu'au RealContainer.
        """
        if self.container == RealContainer or self.parentstack == None:
            # on propage vers le bas :
            if delta != None and delta != 0:
                self.register_offset(fromlayer, delta)
        else:
            # on remonte :
            self.parentstack.fire_offset_change(fromlayer, delta)

    def register_offset(self, fromlayer, delta):
        """
        Enregistre un décallage delta à appliquer ultérieurement aux couches globales >= fromlayer.
        """
        if self.globallayer + self.offset >= fromlayer:
            self.offset += delta
        for locallayer in self.locallayerdict.values():
            locallayer.register_offset(fromlayer, delta)

    def _get_globallayer(self):
        return self._globallayer

    def _set_globallayer(self, val):
        self._globallayer = val
        # initialisation au besoin de la couche de base :
        baselayer = self.get_base_layer()
        if baselayer != None and baselayer.globallayer == None:
            baselayer.globallayer = self._globallayer

    globallayer = property(
        _get_globallayer, _set_globallayer
    )  #: indice de la couche globale associée

    def get_globalrange(self):
        """
        Retourne la liste consécutive de couches globales associées à la hiérarchie.
        """
        globalrange = None
        if self.globallayer != None:
            startind = self.globallayer + self.offset
            stopind = startind + 1
            for locallayer in self.locallayerdict.values():
                childrange = locallayer.get_globalrange()
                if childrange != None and len(childrange) > 0:
                    stopind = max(stopind, childrange[-1] + 1)
            stopind = max(stopind, startind + 1)
            globalrange = range(startind, stopind)
        return globalrange


class LocalLayer:
    """
    **Modélise une couche locale de conteneur.**
    """

    def __init__(self, parentstack, locallayer, layerMngr):
        """
        Constructeur
        
        Args:
            parentstack (LayerStack): LayerStack du conteneur parent    
            locallayer (int): indice local dans la pile parente
            layerMngr (LayerManager): gestionnaire de zindexs mobilisé
        """
        # LayerStack associé au conteneur parent
        self.parentstack = parentstack
        self.name = "- LL " + str(locallayer) + " de " + self.parentstack.name
        # ref au LayerManager
        self.layerMngr = layerMngr
        # indice local dans la pile parente :
        self.locallayer = locallayer
        # couche globale associée à la couche de base :
        self._globallayer = None
        # offset pour différer les décallages de couches
        self.offset = 0
        # liste des VirtualItems de la couche de base :
        self.itemslist = list()
        # Liste des LayerStack au dessus de la couche de base
        self.childstacklist = list()

    def trace(self, full=False):
        """Debug."""
        # debug
        px = ""
        if self.parentstack != None:
            px = "   " * (self.parentstack.level + 1)
        txt = (
            px
            + " * LocalLayer"
            + "[local="
            + str(self.locallayer)
            + " global="
            + str(self.globallayer)
            + " offset="
            + str(self.offset)
            + " globalrange="
            + str(self.get_globalrange())
            + "]"
        )
        if full:
            for item in self.itemslist:
                txt += (
                    "\n"
                    + px
                    + " - "
                    + item.name
                    + " layers : glob.="
                    + str(item.global_layer)
                    + " pub.="
                    + str(item.publication_layer)
                )
        print(txt)
        for childstack in self.childstacklist:
            childstack.trace(full=full)

    def is_empty(self):
        """
        Indique si la couche est vide d'éléments.
        """
        if len(self.itemslist) == 0 and len(self.childstacklist) == 0:
            return True
        return False

    def add_element(self, child):
        """
        Ajoute un VirtualItem à la couche de base.
        """
        if child not in self.itemslist:
            self.itemslist.append(child)
        child.publication_layer = self.globallayer

    def add_stack(self, childstack):
        """
        Ajoute un LayerStack au dessus de la couche de base, sans l'enregistrer (cf propagation offsets). 
        Retourne une range de couches globales utilisées par la pile.
        """
        globalrange = self.get_globalrange()
        indice = globalrange[-1] + 1
        if childstack not in self.childstacklist:
            childstack.globallayer = indice
            returnrange = childstack.get_globalrange()
            return returnrange
        return None

    def register_stack(self, childstack):
        """
        Ajoute la pile à la liste des piles locales.
        """
        if childstack not in self.childstacklist:
            self.childstacklist.append(childstack)

    def remove_element(self, child):
        """
        Supprime un VirtualItem de la couche de base.
        """
        if child in self.itemslist:
            self.itemslist.remove(child)

    def remove_stack(self, childstack):
        """
        Supprime un layerStack. 
        Retourne une range de couches globales libérées par la pile.
        """
        if childstack in self.childstacklist:
            returnrange = childstack.get_globalrange()
            self.childstacklist.remove(childstack)
            self.layerMngr.unregister_layerstack(childstack)
            return returnrange
        return None

    def apply_offset(self, swaplist):
        """
        Applique les décallages cumulés de couches, retourne une liste de swaps à appliquer
        aux couches globales physiques.
        """
        if self.globallayer != None and self.offset != None and self.offset != 0:
            swaptup = (int(self.globallayer), int(self.globallayer + self.offset))
            if swaptup not in swaplist:
                swaplist.append(swaptup)
            self.globallayer += self.offset
            self.update_items()
        for childstack in self.childstacklist:
            childstack.apply_offset(swaplist)
        self.offset = 0
        self.offsetlocked = False

    def update_items(self):
        """
        Met à jour les couches globales des items.
        """
        for item in self.itemslist:
            item.publication_layer = self.globallayer

    def register_offset(self, fromlayer, delta):
        """
        Enregistre un décallage delta à appliquer ultérieurement aux couches globales >= fromlayer.
        """
        if self.globallayer + self.offset >= fromlayer:
            self.offset += delta
        for childstack in self.childstacklist:
            childstack.register_offset(fromlayer, delta)

    def _get_globallayer(self):
        return self._globallayer

    def _set_globallayer(self, val):
        self._globallayer = val

    globallayer = property(
        _get_globallayer, _set_globallayer
    )  #: indice de la couche globale associée

    def get_globalrange(self):
        """
        Retourne la liste consécutive de couches globales associées à la hiérarchie.
        """
        globalrange = None
        if self.globallayer != None:
            startind = self.globallayer + self.offset
            stopind = startind + 1
            for childstack in self.childstacklist:
                childrange = childstack.get_globalrange()
                if len(childrange) > 0:
                    stopind = max(stopind, childrange[-1] + 1)
            stopind = max(stopind, startind + 1)
            globalrange = range(startind, stopind)
        return globalrange
