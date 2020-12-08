#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Carte (labyrinthe) : implémentation Pygame
"""
# imports :
import pygame
import math
import labpyproject.core.pygame.core as co
import labpyproject.core.pygame.widgets as wgt
import labpyproject.apps.labpyrinthe.gui.skinPygame.uitools as uit
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import LabHelper, Case
from labpyproject.apps.labpyrinthe.gui.skinPygame.skinPygame import SkinPygame
from labpyproject.apps.labpyrinthe.gui.skinBase.zone_carte_base import ZoneCarteBase
from labpyproject.apps.labpyrinthe.gui.skinBase.zone_carte_base import ItemObjectBase
from labpyproject.apps.labpyrinthe.gui.skinPygame.botview import BotView
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractSwitch

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ZoneCarte", "ItemObject", "CaseView", "BotViewCarte", "ZoneDangerRobot"]
# classes
class ZoneCarte(wgt.Stack, ZoneCarteBase):
    """
    Equivalent graphique du LabLevel
    """

    # statique :
    MAX_CASE_SIZE = 80 #: taille max d'une case (cf sources png en 80*80)
    SHOW_TARGETS = False #: affichage de la cible du robot
    # méthodes
    def __init__(self, Mngr, skin, **kwargs):
        """
        Constructeur
        """
        # liste de recyclage dédiée aux items de cases robot :
        self._bots_recyclelist = None
        # fond quadrillage :
        self.bg_quad = None
        # générique :
        wgt.Stack.__init__(self, margin="1%", **kwargs)
        ZoneCarteBase.__init__(
            self, Mngr, skin, ItemObject, max_casesize=ZoneCarte.MAX_CASE_SIZE,
        )
        # zones robots :
        self._zone_robot_list = list()
        self._zone_robot_mask_rect = None  # rect de clipping
        self._zone_robot_mask_rect_updated = False
        # target
        self._target_item = None

    #-----> Zones robots
    def add_zone_robot(self, itemobj):
        """
        Publie et enregistre un item ZoneDangerRobot
        """
        spriteobj = itemobj.graphobjref
        spriteobj.cliprect_getter = self.get_zone_mask
        spriteobj.local_layer = self.get_zindex_for_layername(
            ZoneCarteBase.IMAGE_ZONE_ROBOT
        )
        self.add_item(spriteobj)
        self._zone_robot_list.append(itemobj)

    def remove_zone_robot(self, itemobj):
        """
        Supprime un item ZoneDangerRobot
        """
        spriteobj = itemobj.graphobjref
        self.remove_item(spriteobj)
        self._zone_robot_list.remove(itemobj)

    #-----> Interactivité / bots
    def control_callback(self, ctrl, state):
        """
        Méthode appelée par les switchs des BotViews
        """
        if isinstance(ctrl, BotViewCarte):
            case = ctrl.case
            if state in [
                AbstractSwitch.OVER,
                AbstractSwitch.UNSELECTED,
                AbstractSwitch.SELECTED,
            ]:
                # synchro carte / zone bots via la zone partie
                self.Mngr.set_bot_state(case, state, self)

    def handle_bot_state(self, case, state, caller):
        """
        Synchro des roll over/out sur les bots depuis la zone partie
        """
        c = None
        showzone = False
        selectbot = True
        if state in [
            AbstractSwitch.OVER,
            AbstractSwitch.UNSELECTED,
            AbstractSwitch.SELECTED,
        ]:
            if state == AbstractSwitch.OVER:
                c = case
                showzone = True
                if caller == self:
                    selectbot = False
            else:
                c = self.highlighted_bot
        self._highlight_case_robot(c, showzone=showzone, selectbot=selectbot)

    #-----> Initialisation des couches
    def active_single_layer(self, layername, z):
        """
        Post initialisation d'une couche :
        pour activer la couche de façon permanente (pygame)
        """
        # Création d'un Customprite transparent :
        actspr = co.CustomSprite(width=1, height=1, local_layer=z)
        self.add_item(actspr)

    #-----> Dimensions
    def get_canvas_dimensions(self):
        """
        Retourne les dimensions de l'objet graphique implémentant ZoneCarteBase
        """
        contentrect = self.get_content_rect()
        return contentrect.width, contentrect.height

    #-----> Resize : surcharge optimisée
    def on_publicationRefRect_coords_changed(self):
        """
        Appelée lorsque les coordonnées du rect de publication de référence
        (self._publicationRefRect) ont été modifiées (mais pas les dimensions).
        """
        # générique :
        co.VirtualContainer.on_publicationRefRect_coords_changed(self)
        # resize des formes :
        if self.carte_published:
            self.update_shapes()

    def on_publicationRect_dims_changed(self, aftersnap):
        """
        Appelée lors du process de resize quand les dimensions (et éventuellement
        les coords) de publicationRect ont été modifiées
        aftersnap : True si consécutif à un calcul de snap, False sinon
        """
        # invalidation des rects internes et du display :
        co.BoxModelObject.on_publicationRect_dims_changed(self, aftersnap)
        # invalidation des dimensions de la carte
        self.carte_dimensions_initialized = False

    def on_publicationRect_coords_changed(self, aftersnap):
        """
        Appelée lors du process de resize quand les coordonnées seules
        de publicationRect ont été modifiées (pas les dimensions).
        aftersnap : True si consécutif à un calcul de snap, False sinon
        """
        # invalidation des rects internes et du display :
        co.BoxModelObject.on_publicationRect_dims_changed(self, aftersnap)
        # invalidation des dimensions de la carte
        self.carte_dimensions_initialized = False

    def resize(self, **kwargs):
        """
        Recalcul de la taille et de la position
        """
        # resize générique minimal :
        change = co.BoxModelObject.resize(self, **kwargs)
        if change:
            # Recalcul au besoin de la taille des cases et du repère de positionnement
            contentRect = self.get_content_rect()
            self.update_carte_geometry(contentRect.width, contentRect.height)
            # marque le resize comme achevé :
            self.mark_container_as_resized()
        return change

    def on_case_size_changed(self, listitems):
        """
        Appelée lorsque la taille des cases a été modifiée.
        """
        # optimisation : redéfinition des surfaces alouées, les objets
        # graphiques mettront eux mêmes leur contenu à jour
        wc, hc = self.casesize
        for itemobj in listitems:
            spriteobj = itemobj.graphobjref
            spriteobj.width = wc
            spriteobj.height = hc

    def on_carte_repere_changed(self, listitems):
        """
        Appelée lorsque le repère de positionnement a été modifié.
        """
        # mise à jour de la position des cases
        # Rq : économise l'appel à update_publicationRect (qui sera appelé lors
        # du resize) induit par itemobj.set_real_coords dans la méthode initiale
        # de ZoneCarteBase.
        for itemobj in listitems:
            case = itemobj.case
            xg, yg = self.get_real_coords_for_case(case)
            itemobj.graphobjref.x = xg
            itemobj.graphobjref.y = yg

    def resize_items(self, listitems):
        """
        Appelle la méthode de resize des items si nécessaire.
        """
        contentRect = self.get_content_rect()
        for itemobj in listitems:
            spriteobj = itemobj.graphobjref
            # maj rect de publication parent (/ positionnement)
            spriteobj.publicationRefRect = contentRect
            # resize
            spriteobj.resize()

    def on_carte_geometry_updated(self):
        """
        Appelée lorsque self.casesize et self.carte_repere ont
        été recalculés
        """
        self._discard_zone_robot_mask()

    def _discard_zone_robot_mask(self):
        """
        Discard du rect de clipping des zones
        """
        self._zone_robot_mask_rect_updated = False
        # discard des zones :
        for itemobj in self._zone_robot_list:
            spriteobj = itemobj.graphobjref
            spriteobj.discard_display()
            spriteobj.discard_resize()

    def _update_zone_robot_mask(self):
        """
        Update du rect de clipping des zones
        """
        wu, hu = self.carte_dimensions
        wc, hc = self.casesize
        dx, dy = self.carte_repere
        contentRect = self.get_content_rect()
        x = contentRect.x + dx + wc
        y = contentRect.y + dy + hc
        w = (wu - 2) * wc
        h = (hu - 2) * hc
        self._zone_robot_mask_rect = pygame.Rect(x, y, w, h)
        self._zone_robot_mask_rect_updated = True

    def get_zone_mask(self):
        """
        Retourne le rect de clipping des zones
        """
        if not self._zone_robot_mask_rect_updated:
            try:
                self._update_zone_robot_mask()
            except:
                self._zone_robot_mask_rect = None
        return self._zone_robot_mask_rect

    #-----> Publication carte
    def on_carte_published(self):
        """
        Traitements spécifiques en fin de publication.
        """
        # premier affichage
        if not self.carte_published:
            self.discard_allocated_area()
            self.discard_layout()
            # target :
            self._create_target_item()

    def on_carte_updated(self, dictargs, has_anim):
        """
        Traitements spécifiques en fin de publication.
        
        Args:
            * dictargs : dict généré par GameManager.update_carte
            * has_anim : bool indiquant si il y a animation
        
        """
        if self.highlighted_bot:
            self._show_bot_target(self.highlighted_bot)

    def show_bot_dead(self, robot):
        """
        Appelée pour lors de l'élimination de robot.
        """
        botitem = self.get_item_for_case(robot)
        # sélection :
        if botitem != None:
            botview = botitem.graphobjref
            botview.enabled = False

    #-----> Target
    def _create_target_item(self):
        """
        Création d'un item pour l'affichage de cible
        """
        if ZoneCarte.SHOW_TARGETS:
            case = Case(
                0, 0, LabHelper.CASE_TARGET, LabHelper.CHAR_REPR_TARGET, visible=False
            )
            self._target_item = self.set_case(case)

    def _show_bot_target(self, robot, targettype="main"):
        """
        Affichage de cible : target_type = "temp" ou "main"
        """
        if ZoneCarte.SHOW_TARGETS:
            target = None
            if targettype == "temp":
                target = robot.get_temp_target()
            elif targettype == "main":
                target = robot.get_main_target()
            if target != None:
                case = target.case
                self.move_case(self._target_item.case, case.x, case.y)
                self._target_item.set_visible(True)
            else:
                self._target_item.set_visible(False)

    #-----> Gestion des formes vecto
    def draw_bg(self):
        """
        Crée le rectangle de fond en mode optimisé. 
        Couche : layer = self.layersdict[ZoneCarteBase.SHAPE_BG]
        """
        bgcol = self.skin.get_color("carte", "bg_lab")
        bgrect = self.get_bg_rect()
        self.bg_quad = co.CustomSprite(
            width="100%", height="100%", name="bg", bgcolor=bgcol
        )
        self.bg_quad.publicationRefRect = bgrect
        # enregistrement :
        layer = self.layersdict[ZoneCarteBase.SHAPE_BG]
        itbg = ItemObject(self, graphobjref=self.bg_quad, typecontent="shape")
        layer.append(itbg)
        # zindex :
        z = None
        for layerdict in self.zindexslist:
            layername = layerdict["name"]
            if layername == ZoneCarteBase.SHAPE_BG:
                z = layerdict["z"]
                break
        self.bg_quad.local_layer = z
        # publication :
        self.add_item(self.bg_quad)

    def update_bg(self):
        """
        Met à jour le rectangle de fond permettant de simuler
        le quadrillage
        """
        self.bg_quad.visible = True
        bgrect = self.get_bg_rect()
        self.bg_quad.publicationRefRect = bgrect
        self.bg_quad.resize()

    def get_bg_rect(self):
        """
        Rect de fond spécifique
        """
        cr = None
        if self.casesize != (None, None):
            wc, hc = self.casesize
            nbw, nbh = self.carte_dimensions
            mw, mh = wc * nbw, hc * nbh
            contR = self.get_content_rect()
            carteRep = self.carte_repere
            rx = carteRep[0] + contR.x
            ry = carteRep[1] + contR.y
            cr = pygame.Rect(rx + 2, ry + 2, mw - 4, mh - 4)
        else:
            cr = pygame.Rect(0, 0, 0, 0)
        return cr

    def highlight_player(self, robotlist, gambleinfos):
        """
        Identification du prochain joueur
        """
        if gambleinfos == None or robotlist == None:
            return
        # nouvelle case :
        hdatas = self.get_bot_highlight_datas(robotlist, gambleinfos)
        cbot = hdatas["cbot"]
        if cbot != None:
            self.highlighted_bot = cbot
        else:
            self.highlighted_bot = None
        # ref du bot highlighté :
        listitems = self.get_items_for_layer(LabHelper.CASE_ROBOT)
        for itemobj in listitems:
            botview = itemobj.graphobjref
            botview.set_current_highbotcase(self.highlighted_bot)
        # affichage
        self._highlight_case_robot(self.highlighted_bot)

    def _highlight_case_robot(self, case, showzone=False, selectbot=True):
        """
        Highlight graphique
        """
        highlighteditem = None
        botitem = self.get_item_for_case(case)
        # sélection :
        if botitem != None:
            botview = botitem.graphobjref
            if selectbot:
                botview.highlight(True)
            botview.show_zone_danger(showzone)
            highlighteditem = botitem
            self._show_bot_target(case)
        # désélections :
        listitems = self.get_items_for_layer(LabHelper.CASE_ROBOT)
        for itemobj in listitems:
            if itemobj != highlighteditem:
                botview = itemobj.graphobjref
                botview.highlight(False)
                botview.show_zone_danger(False)

    #-----> Update d'items
    def update_item_view(self, itemobj):
        """
        Mise à jour du contenu graphique associé à l'item
        """
        case = itemobj.case
        typecase = case.type_case
        # BotView : modification des images lors de la définition de la case
        if typecase != LabHelper.CASE_ROBOT:
            # image simple :
            actual_skinimg = itemobj.get_current_image()
            imgsize = self.casesize
            if CaseView.RESIZEMODE == SkinPygame.SCALE_RESIZEMODE:
                imgsize = ZoneCarte.MAX_CASE_SIZE, ZoneCarte.MAX_CASE_SIZE
            new_skinimg = self.skin.get_image_for_case(case, imgsize)
            if actual_skinimg != new_skinimg:
                itemobj.set_current_image(new_skinimg)
        else:
            # Resize (au besoin) du Botview :
            if itemobj.graphobjref:
                itemobj.graphobjref.width = self.casesize[0]
                itemobj.graphobjref.height = self.casesize[1]


#-----> Objet modélisant un item graphique de la carte (subclassé)
class ItemObject(ItemObjectBase):
    """
    Implémentation Pygame de ItemObjectBase
    """

    def __init__(
        self, zonecarte, graphobjref=None, typecontent=None, case=None, x=None, y=None
    ):
        """
        Constructeur
        """
        ItemObjectBase.__init__(
            self,
            zonecarte,
            graphobjref=graphobjref,
            typecontent=typecontent,
            case=case,
            x=x,
            y=y,
        )

    def create_view(self):
        """
        Instancie l'implémentation graphique d'une case, spécifique au moteur de publication.
        Enregistre l'objet ou un id équivalent dans self.graphobjref
        """
        if self.case != None:
            typecase = self.case.type_case
            if typecase == LabHelper.CASE_ROBOT:
                # BotViewCarte :
                self.graphobjref = BotViewCarte(
                    self.zonecarte, self.zonecarte.skin, self.case, position="absolute"
                )
                # ZoneDangerRobot
                zdr = ZoneDangerRobot(self.zonecarte, botitem=self.graphobjref)
                # association :
                self.graphobjref.zone_danger = zdr
            else:
                self.graphobjref = CaseView(
                    self.case, self.zonecarte.skin, position="absolute"
                )
            self.graphobjref.local_layer = self.z
            self.zonecarte.add_item(self.graphobjref)

    def delete_view(self):
        """
        Supprime la vue graphique de self.case
        """
        self.set_case(None)
        if isinstance(self.graphobjref, BotViewCarte):
            zoneitem = self.graphobjref.zone_danger
            zoneitem.delete_view()
        self.zonecarte.remove_item(self.graphobjref)

    def set_case(self, case):
        """
        Met à jour au besoin la case associée.
        """
        if case != self.case:
            self.case = case
            self.graphobjref.change_case(case)

    def set_current_image(self, imgskin):
        """
        Affiche une nouvelle image (générée par le skin)
        """
        # enregistrement de la ref :
        ItemObjectBase.set_current_image(self, imgskin)
        # dimensions :
        wc, hc = self.zonecarte.casesize
        self.graphobjref.width = wc
        self.graphobjref.height = hc
        # Affichage (et update) :
        self.graphobjref.load_surface(imgskin)

    def get_real_coords(self):
        """
        Retourne les coordonnées réelles (converties / la case) de la vue graphique
        """
        return self.graphobjref.x, self.graphobjref.y

    def set_real_coords(self, realx, realy):
        """
        Déplace la vue graphique aux coordonnées réelles (converties) realx, realy
        """
        self.graphobjref.x = realx
        self.graphobjref.y = realy
        # update
        self.graphobjref.update_publicationRect()

    def set_visible(self, show):
        """
        Affiche ou masque la vue graphique.
        * show : bool
        """
        self.graphobjref.visible = show


class CaseView(wgt.Image):
    """
    Vue d'une case image (hors bots)
    """

    # mode de resize :
    RESIZEMODE = SkinPygame.SKIN_RESIZEMODE #: mode de resize des images
    # méthodes
    def __init__(self, case, skin, resizemode=RESIZEMODE, **kwargs):
        """
        Constructeur:
        
        * kwargs : voir wgt.Image
        * resizemode : scale (scaling surface) ou skin (resize PIL)
            
        Rq : pour la carte, le cache du skin s'avère plus efficace que le
        resize de surface
        """
        # ref au skin :
        self.skin = skin
        # case associée :
        self.case = None
        # mode de resize :
        self.resizemode = resizemode
        # générique :
        wgt.Image.__init__(self, surface=None, fixed=False, **kwargs)
        # initialisation de la source :
        self.change_case(case)

    def change_case(self, case):
        """
        Ré initialise la case associée.
        """
        if case != self.case:
            self.case = case
            maxsize = ZoneCarte.MAX_CASE_SIZE
            surf = None
            if self.case != None:
                surf = self.skin.get_image_for_case(self.case, (maxsize, maxsize))
            self.load_surface(surf)

    #-----> Surcharge de WImage :
    def get_surface_for_size(self, newsize):
        """
        Retourne une nouvelle surface à la taille newsize
        """
        newsurf = None
        if newsize != (0, 0):
            if self.resizemode == SkinPygame.SKIN_RESIZEMODE:
                # spécifique : génération de l'image resizée via PIL
                newsurf = self.skin.get_image_for_case(self.case, size=newsize)
            elif self.resizemode == SkinPygame.SCALE_RESIZEMODE:
                # générique : via rescale de la surface source
                newsurf = wgt.Image.get_surface_for_size(self, newsize)
        return newsurf

    def get_source_size(self):
        """
        Retourne les dimensions de la source
        """
        return ZoneCarte.MAX_CASE_SIZE, ZoneCarte.MAX_CASE_SIZE


class BotViewCarte(BotView):
    """
    Subclasse apportant la gestion de la zone de danger du robot.
    """

    def __init__(self, Mngr, skin, case, **kwargs):
        """
        Constructeur
        """
        # générique :
        BotView.__init__(self, Mngr, skin, case, **kwargs)
        # objet ZoneDangerRobot associé, défini à postériori :
        self.zone_danger = None

    def show_zone_danger(self, show):
        """
        Affiche/masque la zone danger associée
        """
        if self.zone_danger != None:
            if show:
                self.zone_danger.update_view()
            self.zone_danger.set_visible(show)


class ZoneDangerRobot(ItemObjectBase):
    """
    Implémentation pygame de ItemZoneRobot.
    """

    def __init__(self, zonecarte, botitem=None):
        """
        Constructeur
        """
        case = None
        if botitem != None:
            case = botitem.case
        # générique :
        ItemObjectBase.__init__(self, zonecarte, case=case)
        # skin associé :
        self.skin = self.zonecarte.skin
        # objet BotViewCarte associé :
        self.botitem = botitem
        # identification de l'image associée à la zone
        self.zonekey = None
        self.placekey = None
        # publication :
        self.create_view()
        self.set_visible(False)

    def create_view(self):
        """
        Création du widget graphique
        """
        if self.case != None:
            # publication
            self.graphobjref = wgt.Image(fixed=False, clip=True, position="absolute")
            self.zonecarte.add_zone_robot(self)
            # contenu
            self.update_view()

    def delete_view(self):
        """
        Supprime la vue graphique de self.case
        """
        self.zonecarte.remove_zone_robot(self)

    def update_view(self):
        """
        Mise à jour de la vue graphique
        """
        if self.case != None:
            bot = self.case
            # Clef d'image :
            newImgKey = None
            zdsurf = None
            alive = bot.alive
            # facteur de danger / case highlightée :
            highcase = self.botitem.get_current_highbotcase()
            dgr_factor = None
            if highcase != None:
                dgr_factor = self.botitem.case.get_apparent_danger_factor_for_bot(
                    highcase
                )
            if dgr_factor != None:
                if alive:
                    vitesse = bot.current_vitesse
                    impact = 0
                    portee = 0
                    if bot.has_grenade:
                        impact = max(bot.get_puissance_list("grenade"))
                        portee = bot.portee_grenade
                    if dgr_factor == 0:
                        newImgKey = (vitesse, 0, 0, dgr_factor)
                    else:
                        newImgKey = (vitesse, impact, portee, dgr_factor)
                # Changement d'image?
                if newImgKey not in [None, self.zonekey]:
                    self.zonekey = newImgKey
                    self.placekey = None
                    zdsurf = self.skin.get_image_for_zone_danger(
                        newImgKey[0], newImgKey[1], newImgKey[2], newImgKey[3]
                    )
                # chargement au besoin :
                if zdsurf != None:
                    self.set_current_image(zdsurf)
            else:
                self.set_visible(False)

    def place_and_size_graphObjRef(self):
        """
        S'assure des dimensions et de la position du widget image
        """
        if self.skinImg != None:
            # Clef :
            newPlaceKey = int(self.botitem.x), int(self.botitem.y)
            if newPlaceKey != self.placekey:
                self.placekey = newPlaceKey
                # 1- Dimensions
                # tailles unitaires :
                zdw, zdh = self.skinImg.get_size()  # taille pour casesize = 80*80
                wzone_unit, hzone_unit = zdw / 80, zdh / 80
                wcase, hcase = self.zonecarte.casesize
                # taille réelle :
                wzone = wzone_unit * wcase
                hzone = hzone_unit * hcase
                self.graphobjref.width = math.floor(wzone)
                self.graphobjref.height = math.floor(hzone)
                # 2- Position
                xrep, yrep = self.zonecarte.carte_repere
                xcase = self.botitem.case.x
                ycase = self.botitem.case.y
                xzone_unit = xcase - wzone_unit // 2
                yzone_unit = ycase - hzone_unit // 2
                xzone = math.floor(xzone_unit * wcase + xrep)
                yzone = math.floor(yzone_unit * hcase + yrep)
                self.graphobjref.x = xzone
                self.graphobjref.y = yzone
                # update
                self.graphobjref.update_publicationRect()

    def set_current_image(self, imgskin):
        """
        Affiche une nouvelle image (générée par le skin)
        """
        # enregistrement ref :
        self.skinImg = imgskin
        # affichage (et update) :
        self.graphobjref.load_surface(imgskin)

    def get_real_coords(self):
        """
        Retourne les coordonnées réelles (converties / la case) de la vue graphique
        """
        return self.graphobjref.x, self.graphobjref.y

    def set_real_coords(self, realx, realy):
        """
        Déplace la vue graphique aux coordonnées réelles (converties) realx, realy
        """
        self.graphobjref.x = realx
        self.graphobjref.y = realy
        # update
        self.graphobjref.update_publicationRect()

    def set_visible(self, show):
        """
        Affiche ou masque la vue graphique.
        show : bool
        """
        if show:
            self.place_and_size_graphObjRef()
        self.graphobjref.visible = show
