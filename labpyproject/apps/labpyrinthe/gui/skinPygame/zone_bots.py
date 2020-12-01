#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Panneau d'information sur les robots : implémentation Pygame
"""
# imports
import math
import pygame
import labpyproject.core.pygame.core as co
import labpyproject.core.pygame.widgets as wgt
from labpyproject.apps.labpyrinthe.bus.game_manager import GameManager
from labpyproject.apps.labpyrinthe.app.app_types import AppTypes
import labpyproject.apps.labpyrinthe.gui.skinPygame.uitools as uit
from labpyproject.apps.labpyrinthe.gui.skinBase.zone_bots_base import ZoneBotsBase
from labpyproject.apps.labpyrinthe.gui.skinPygame.botview import BotView
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractSwitch

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ZoneBots", "BotList", "BotItem"]
# classe
class ZoneBots(wgt.Stack, ZoneBotsBase):
    """
    Zone d'information sur les robots
    """

    # méthodes
    def __init__(self, mngr, skin, **kwargs):
        """
        Constructeur
        """
        # ref au skin :
        self.skin = skin
        # case highlightée
        self._highlight_case = None
        # robotlist courante :
        self.robotlist = None
        # cache des graphs radars :
        self.graphradars = None
        # objets de publication :
        self.zone_content = None
        self.zone_titre = None
        self.img_bot = None
        self.nom_bot = None
        self.nb_coups = None
        self.img_radar = None
        self.col_details = None
        self.img_vitesse = None
        self.txt_vitesse = None
        self.img_grenade = None
        self.txt_grenade = None
        self.img_mine = None
        self.txt_mine = None
        self.img_croix = None
        self.txt_croix = None
        self.zone_liste = None
        self.botitemsdict = None
        self.zone_wait_partie = None
        self.img_wait_partie = None
        self.spacer_wait1 = None
        self.spacer_wait2 = None
        self.spacer_wait3 = None
        self.btn_start = None
        self.zone_wait_demo = None
        self.img_wait_demo = None
        # type de jeu
        self.current_game_mode = None
        # générique :
        wgt.Stack.__init__(self, bgcolor="#FFFFFF00", **kwargs)
        ZoneBotsBase.__init__(self, mngr, skin)
        # interface
        self.draw_interface(None)

    def re_initialise(self):
        """
        Ré initialise l'objet
        """
        # générique :
        ZoneBotsBase.re_initialise(self)
        # spécifique :
        self.graphradars = None

    def control_callback(self, ctrl, state):
        """
        Méthode appelée par les switchs des BotItems
        """
        if ctrl == self.btn_start and state == AbstractSwitch.PRESSED and self.gui_mngr:
            # Envoie l'ordre de démarrage de la partie :
            self.gui_mngr.user_start_partie()
        if isinstance(ctrl, BotItem):
            case = ctrl.case
            if state in [
                AbstractSwitch.OVER,
                AbstractSwitch.UNSELECTED,
                AbstractSwitch.SELECTED,
            ]:
                # synchro carte / zone bots via la zone partie
                self.mngr.set_bot_state(case, state, self)

    def handle_bot_state(self, case, state, caller):
        """
        Synchro des roll over/out sur les bots depuis la zone partie
        """
        c = None
        if state in [
            AbstractSwitch.OVER,
            AbstractSwitch.UNSELECTED,
            AbstractSwitch.SELECTED,
        ]:
            if state == AbstractSwitch.OVER:
                c = case
            else:
                c = self._highlight_case
        if c != None:
            self.show_bot_infos(c)

    def register_type_partie(self, game_mode):
        """
        Enregistre le type de jeu (partie ou démo)
        """
        self.current_game_mode = game_mode

    #----->  Surcharge de ZoneBotsBase
    def apply_partie_state(self):
        """
        Adapte l'interface en fonction de la phase de la partie
        """
        if (
            self.zone_content == None
            or self.zone_wait_partie == None
            or self.zone_wait_demo == None
        ):
            return
        out_of_scene = "100%"
        if self.partie_state in [GameManager.PARTIE_INIT, GameManager.PARTIE_CHOSEN]:
            self.zone_content.left = out_of_scene
            self.zone_wait_partie.left = out_of_scene
            self.zone_wait_demo.left = out_of_scene
        elif self.partie_state in [GameManager.PARTIE_CREATED]:
            self.bgcolor = "#FFFFFF00"
            self.zone_content.left = out_of_scene
            if self.type_app == AppTypes.APP_CLIENT:
                if self.current_game_mode == GameManager.GAME_MODE_PARTIE:
                    self.zone_wait_partie.left = 0
                    self.zone_wait_demo.left = out_of_scene
                else:
                    self.zone_wait_partie.left = out_of_scene
                    self.zone_wait_demo.left = 0
        elif self.partie_state in [
            GameManager.PARTIE_STARTED,
            GameManager.PARTIE_ENDED,
        ]:
            self.bgcolor = "#FFFFFF80"
            self.zone_content.left = 0
            self.zone_wait_partie.left = out_of_scene
            self.zone_wait_demo.left = out_of_scene

    def publish_robotlist(self, robotlist, gambleinfos):
        """
        Méthode d'affichage publique
        """
        self.bgcolor = "#FFFFFF80"
        # doit on republier complètement?
        if self.robotlist != None and robotlist != None:
            oldkey = None
            if len(self.robotlist) > 0:
                oldkey = ""
                for r in self.robotlist:
                    oldkey += r.uid
            newkey = None
            if len(robotlist) > 0:
                newkey = ""
                for r in robotlist:
                    newkey += r.uid
            if newkey != oldkey:
                # on efface :
                self.clear_bots_list()
        if robotlist != None:
            self.robotlist = robotlist.copy()
        else:
            self.robotlist = None
        # publication
        uid = None
        if gambleinfos != None:
            uid = gambleinfos["uid"]
        # Publication :
        self.draw_interface(robotlist)
        if self.robotlist != None:
            # case highlightée :
            highcase = None
            for case in robotlist:
                if uid != None and case.uid == uid:
                    highcase = case
                    break
            if highcase == None and len(robotlist) > 0:
                highcase = robotlist[0]
            self._highlight_case = highcase
            # Mise à jour :
            for case in robotlist:
                bitem = self.botitemsdict[case.uid]
                bitem.set_current_highbotcase(self._highlight_case)
                if case.alive == False:
                    bitem.enabled = False
                else:
                    bitem.highlight(False)
            if highcase != None:
                bitem = self.botitemsdict[highcase.uid]
                bitem.highlight(True)
                self.show_bot_infos(highcase)
        self.update()

    def draw_interface(self, robotlist):
        """
        Crée l'interface au premier affichage
        """
        # conteneur global, détails
        if self.zone_content == None:
            # conteneur global :
            self.zone_content = wgt.VStack(
                width="100%",
                height="100%",
                snapH=True,
                padding="5",
                valign="middle",
                name="zone_content",
            )
            self.add_item(self.zone_content)
            # zone titre : nom & coups, détails
            self.zone_titre = wgt.Stack(
                width=320, height=146, name="zone_titre", align="center"
            )
            self.zone_content.add_item(self.zone_titre)
            # nom et coups
            self.nom_bot = uit.WText(
                "PoppinsBlack",
                24,
                self.skin,
                height=36,
                snapW=True,
                padding=0,
                name="nom_bot",
                fgcolor=self.color_txt,
                bgcolor="#FFFFFF00",
                textalign="left",
                left=0,
                y=15,
            )
            self.zone_titre.add_item(self.nom_bot)
            self.nb_coups = uit.WText(
                "PoppinsBlack",
                24,
                self.skin,
                height=36,
                snapW=True,
                padding=0,
                name="nb_coups",
                fgcolor="#330000",
                bgcolor="#FFFFFF00",
                textalign="left",
                right=0,
                y=15,
            )
            self.zone_titre.add_item(self.nb_coups)
            # détails
            self.img_bot = uit.WImage(
                None,
                None,
                self.skin,
                fixed=True,
                position="absolute",
                width=80,
                height=80,
                x=20,
                y=51,
            )
            self.zone_titre.add_item(self.img_bot)
            self.img_radar = uit.WImage(
                None,
                None,
                self.skin,
                fixed=True,
                position="absolute",
                width=110,
                height=110,
                x=110,
                y=36,
            )
            self.zone_titre.add_item(self.img_radar)
            self.col_details = wgt.Stack(width=90, height=110, x=230, y=36)
            self.zone_titre.add_item(self.col_details)
            # vitesse
            self.img_vitesse = uit.WImage(
                "zonebots",
                "picto_vitesse",
                self.skin,
                fixed=True,
                position="absolute",
                width=20,
                height=20,
                x=0,
                y=15,
            )
            self.col_details.add_item(self.img_vitesse)
            self.txt_vitesse = uit.WText(
                "PoppinsBold",
                16,
                self.skin,
                width=65,
                height=20,
                x=25,
                y=15,
                padding=0,
                fgcolor=self.color_txt,
                bgcolor="#FFFFFF00",
            )
            self.col_details.add_item(self.txt_vitesse)
            # grenade
            self.img_grenade = uit.WImage(
                "zonebots",
                "picto_grenade",
                self.skin,
                fixed=True,
                position="absolute",
                width=20,
                height=20,
                x=0,
                y=35,
            )
            self.col_details.add_item(self.img_grenade)
            self.txt_grenade = uit.WText(
                "PoppinsBold",
                16,
                self.skin,
                width=65,
                height=20,
                x=25,
                y=35,
                padding=0,
                fgcolor=self.color_txt,
                bgcolor="#FFFFFF00",
            )
            self.col_details.add_item(self.txt_grenade)
            # mine
            self.img_mine = uit.WImage(
                "zonebots",
                "picto_mine",
                self.skin,
                fixed=True,
                position="absolute",
                width=20,
                height=20,
                x=0,
                y=55,
            )
            self.col_details.add_item(self.img_mine)
            self.txt_mine = uit.WText(
                "PoppinsBold",
                16,
                self.skin,
                width=65,
                height=20,
                x=25,
                y=55,
                padding=0,
                fgcolor=self.color_txt,
                bgcolor="#FFFFFF00",
            )
            self.col_details.add_item(self.txt_mine)
            # croix
            self.img_croix = uit.WImage(
                "zonebots",
                "picto_croix",
                self.skin,
                fixed=True,
                position="absolute",
                width=20,
                height=20,
                x=0,
                y=75,
            )
            self.col_details.add_item(self.img_croix)
            self.txt_croix = uit.WText(
                "PoppinsBold",
                16,
                self.skin,
                width=65,
                height=20,
                x=25,
                y=75,
                padding=0,
                fgcolor=self.color_txt,
                bgcolor="#FFFFFF00",
            )
            self.col_details.add_item(self.txt_croix)
        # Zone liste :
        if robotlist != None and self.zone_liste == None:
            self.zone_liste = BotList(
                self,
                self.skin,
                robotlist,
                name="zone_list",
                width="100%",
                align="center",
                snapW=True,
                maxwidth=450,
                snapH=True,
                flex=1,
            )
            self.zone_content.add_item(self.zone_liste)
            self.botitemsdict = self.zone_liste.draw_interface()
        # écrans d'attente :
        if self.zone_wait_partie == None:
            self.zone_wait_partie = wgt.VStack(
                width="100%",
                height="100%",
                snapH=False,
                local_layer=1,
                valign="middle",
                name="zone_wait_partie",
            )
            self.add_item(self.zone_wait_partie)
            self.spacer_wait1 = uit.Spacer(flex=1)
            self.zone_wait_partie.add_item(self.spacer_wait1)
            self.img_wait_partie = uit.WImage(
                "screens",
                "txt_net_start",
                self.skin,
                flex=7,
                fixed=False,
                align="center",
            )
            self.zone_wait_partie.add_item(self.img_wait_partie)
            self.spacer_wait2 = uit.Spacer(flex=1)
            self.zone_wait_partie.add_item(self.spacer_wait2)
            self.btn_start = uit.WButton(
                self, self.skin, "start", flex=2, fixed=False, align="center"
            )
            self.zone_wait_partie.add_item(self.btn_start)
            self.spacer_wait3 = uit.Spacer(flex=1)
            self.zone_wait_partie.add_item(self.spacer_wait3)
        if self.zone_wait_demo == None:
            self.zone_wait_demo = wgt.Stack(
                width="100%",
                height="100%",
                snapH=False,
                local_layer=2,
                valign="middle",
                name="zone_wait_demo",
            )
            self.add_item(self.zone_wait_demo)
            self.img_wait_demo = uit.WImage(
                "screens",
                "txt_net_wait",
                self.skin,
                fixed=False,
                align="center",
                valign="middle",
            )
            self.zone_wait_demo.add_item(self.img_wait_demo)
        # indicateur de publication
        self.interface_drawn = True
        # synchro
        self.apply_partie_state()

    def clear_bots_list(self):
        """
        Efface la liste des bots publiée
        """
        self.bgcolor = "#FFFFFF00"
        if self.zone_content:
            self.zone_content.remove_item(self.zone_liste)
        self.zone_liste = None
        self.botitemsdict = None
        self.robotlist = None
        if self.img_bot:
            self.img_bot.load_surface(None)
        if self.nom_bot:
            self.nom_bot.text = ""

    def show_bot_dead(self, robot):
        """
        Appelée pour lors de l'élimination de robot.
        """
        uid = robot.uid
        if uid in self.botitemsdict.keys():
            botitem = self.botitemsdict[uid]
            # sélection :
            if botitem != None:
                botitem.enabled = False

    #-----> Spécifique :
    def show_bot_infos(self, case):
        """
        Affiche l'image, le nom et les infos du bot
        """
        # Nom :
        nom = self._get_nom_for_robot(case)
        self.nom_bot.text = nom
        # nombre de coups :
        totalcoups = case.current_gamble_count
        currentcoups = case.current_gamble_number + 1
        nbcoups = "coup " + str(currentcoups) + " / " + str(totalcoups)
        self.nb_coups.text = nbcoups
        # Image :
        botsurf = self.skin.get_image_for_case(case, (80, 80))
        self.img_bot.load_surface(botsurf)
        # Image radar :
        radarsurf = self._get_radar_surf_for_bot(case)
        self.img_radar.load_surface(radarsurf)
        # vitesse :
        self.txt_vitesse.text = str(case.vitesse)
        # grenade :
        self.txt_grenade.text = self._get_grenade_for_robot(case)
        # mine :
        self.txt_mine.text = self._get_mine_for_robot(case)
        # morts :
        total, innocents = case.get_killed_counts()
        self.txt_croix.text = str(total) + " (" + str(innocents) + ")"

    def _get_radar_surf_for_bot(self, robot):
        """
        Mise en cache des images radars
        """
        if self.graphradars == None:
            self.graphradars = dict()
        dgrf = robot.get_danger_factor_for_bot(None)
        k = (robot, dgrf)
        if k not in self.graphradars.keys():
            self.graphradars[k] = self.skin.get_radar_graph_for_bot(robot)
        return self.graphradars[k]


#-----> Liste de Bots
class BotList(wgt.VStack):
    """
    Liste de BotItems
    """

    def __init__(self, mngr, skin, robotlist, **kwargs):
        """
        Constructeur
        """
        # ref zonebots :
        self.mngr = mngr
        # ref au skin
        self.skin = skin
        # liste des cases robot :
        self.robotlist = robotlist
        # dict case/BotItem :
        self.botitemsdict = None
        # liste de lignes :
        self.linelist = None
        # nombre de bots par ligne
        self.nb_bots_per_line = 8
        # marge des lignes (en px):
        self.line_margin = 5
        # générique :
        wgt.VStack.__init__(self, **kwargs)

    def draw_interface(self):
        """
        Première publication de la liste.
        """
        self.botitemsdict = dict()
        self.linelist = list()
        if self.robotlist == None:
            return
        nbbots = len(self.robotlist)
        if nbbots > 0:
            # ligne de séparation
            self.spacer_zones = uit.Spacer(
                width="80%",
                maxwidth=320,
                height=12,
                margin=5,
                bgcolor="#330000",
                align="center",
            )
            self.add_item(self.spacer_zones)
            # nombre de bots par lignes :
            nbperline = self.nb_bots_per_line
            halfnb = math.ceil(nbbots / 2)
            if halfnb > nbperline:
                nbperline = halfnb
            n = 0
            npl = 0
            while n < nbbots:
                if n % nbperline == 0:
                    # nouvelle ligne
                    line = wgt.HStack(
                        margin=self.line_margin, flex=1, snapW=True, snapH=True,
                    )
                    self.add_item(line)
                    self.linelist.append(line)
                    npl = 0
                case = self.robotlist[n]
                bitem = BotItem(
                    self.mngr, self.skin, case, name=case.uid, flex=1, visible=True
                )
                self.botitemsdict[case.uid] = bitem
                line.add_item(bitem)
                n += 1
                npl += 1
                if n == nbbots and npl < nbperline:
                    spacer = uit.Spacer(flex=nbperline - npl)
                    line.add_item(spacer)
        # Resize immédiat :
        self.update()
        return self.botitemsdict


#-----> Item de liste
class BotItem(BotView):
    """
    Item de la liste de joueurs
    """

    # statique :
    DGR_DY = 2 #: décalage du rectangle coloré indiquant le niveau de dangerosité
    DGR_HEIGHT = 5 #: hauteur du rectangle coloré indiquant le niveau de dangerosité
    # méthodes
    def __init__(self, mngr, skin, case, **kwargs):
        """
        Constructeur
        """
        # générique :
        BotView.__init__(self, mngr, skin, case, **kwargs)
        # zone indicateur de danger :
        self._dgr_subsurface = None
        self._dgr_color = "#FFFFFF"

    #-----> Surcharge de BotView
    def highlight(self, dohigh):
        """
        Marque le switch comme sélectionné ou non
        
        Args:
            dohigh : bool
        """
        # zone de danger :
        self._update_danger_factor_subsurface()
        # générique
        BotView.highlight(self, dohigh)

    #-----> Spécifique : subsurface facteur de danger
    def _update_danger_factor_subsurface(self):
        """
        Met à jour la subsurface représentant le facteur de danger.
        """
        if self.current_highbotcase != None:
            dgr_factor = self.case.get_apparent_danger_factor_for_bot(
                self.current_highbotcase
            )
            dgr_color = self.skin.get_color_for_dangerfactor(dgr_factor)
            if dgr_color != None:
                self._dgr_color = dgr_color
            if self._dgr_subsurface:
                self._dgr_subsurface.fill(pygame.Color(dgr_color))
                # cadre :
                subrect = pygame.Rect(
                    1,
                    self.rect.height - BotItem.DGR_HEIGHT,
                    self.rect.width - 2,
                    BotItem.DGR_HEIGHT,
                )
                x0, y0 = 0, 0
                w, h = subrect.width - 1, subrect.height - 1
                fullpts = [
                    (x0, y0),
                    (x0 + w, y0),
                    (x0 + w, y0 + h),
                    (x0, y0 + h),
                    (x0, y0),
                ]
                surf = self._dgr_subsurface
                if not self.case.alive:
                    bdcolor = pygame.Color("#BEAEAE")
                else:
                    bdcolor = pygame.Color("#330000")
                bdwidth = 1
                pygame.draw.polygon(surf, bdcolor, fullpts, bdwidth)

    #-----> Surcharge de widget Image / indicateur zone de danger
    def draw_display(self):
        """
        Dessine ou redessine l'objet.
        """
        # générique
        wgt.Image.draw_display(self)
        # spécifique :
        self._update_danger_factor_subsurface()

    def compute_image_size(self):
        """
        Calcul la taille d'image en fonction de l'espace aloué et des dimensions 
        de la source.
        """
        # générique
        wn, hn = wgt.Image.compute_image_size(self)
        # espace aloué à l'indicateur coloré :
        if (wn, hn) != (None, None):
            hn += BotItem.DGR_DY + BotItem.DGR_HEIGHT
        return wn, hn

    def get_surface_for_size(self, newsize):
        """
        Retourne une nouvelle surface à la taille newsize
        """
        # espace aloué à l'indicateur coloré :
        w, h = newsize
        h -= BotItem.DGR_DY + BotItem.DGR_HEIGHT
        # générique
        return wgt.Image.get_surface_for_size(self, (w, h))

    def get_item_dimensions(self):
        """
        Doit retourner les dimensions réelles du contenu (texte, image).
        A implémenter dans les subclasses utilisant le snap.
        """
        # générique
        img_w, img_h = wgt.Image.get_item_dimensions(self)
        # espace aloué à l'indicateur coloré :
        if (img_w, img_h) != (None, None):
            img_h += BotItem.DGR_DY + BotItem.DGR_HEIGHT
        return img_w, img_h

    #-----> Surcharge de core CustomSprite / indicateur zone de danger
    def create_default_surface(self):
        """
        Crée une surface transparente par défaut
        Ajoute en subsurface l'indicateur de danger.
        """
        # générique :
        co.CustomSprite.create_default_surface(self)
        # subsurface indicateur de danger :
        if self.width * self.height > 0:
            subrect = pygame.Rect(
                1,
                self.rect.height - BotItem.DGR_HEIGHT,
                self.rect.width - 2,
                BotItem.DGR_HEIGHT,
            )
            self._dgr_subsurface = self.image.subsurface(subrect)
            self._dgr_subsurface.fill(pygame.Color(self._dgr_color))
            # cadre :
            x0, y0 = 0, 0
            w, h = subrect.width, subrect.height
            fullpts = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h), (x0, y0)]
            surf = self._dgr_subsurface
            bdcolor = pygame.Color("#330000")
            bdwidth = 1
            pygame.draw.polygon(surf, bdcolor, fullpts, bdwidth)
