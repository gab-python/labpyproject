#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ecran d'attente : implémentation Pygame.
"""
# import
import math
import pygame.transform
import labpyproject.core.pygame.widgets as wgt
import labpyproject.apps.labpyrinthe.gui.skinPygame.uitools as uit
from labpyproject.apps.labpyrinthe.gui.skinBase.screen_wait_base import ScreenWaitBase

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ScreenWait", "ScaledText", "SimplePreloader"]
# classe
class ScreenWait(wgt.VStack, ScreenWaitBase):
    """
    Ecran d'attente
    """

    def __init__(
        self, mngr, skin, initialstate, show_infos=False, show_carte=False, **kwargs
    ):
        """
        Constructeur
        """
        # Manager : GUI
        self.mngr = mngr
        # ref au skin :
        self.skin = skin
        # publication info et input
        self.show_infos = show_infos
        # carte texte (preload partie) :
        self.show_carte = show_carte
        # objets graphiques :
        self.widget_image = None
        self.infotext = None
        self.choiceentry = None
        self.txt_carte = None
        self.img_txt_carte = None
        # variables :
        self._input_txt = None
        self._info_txt = None
        # générique :
        wgt.VStack.__init__(
            self, width="100%", height="100%", bgcolor="#FFFFFF", **kwargs
        )
        ScreenWaitBase.__init__(self, skin, initialstate)

    def draw_interface(self):
        """
        Création de l'interface
        """
        # 1- Header si chargement
        if self.get_initial_state() == ScreenWaitBase.STATE_LOADING:
            self.header = uit.WImage("screens", "entete_light", self.skin, fixed=False)
            self.add_item(self.header)
            bg_name = "bg_load"
        else:
            bg_name = "bg_load_2"
        # 2- Canvas de contenu
        self.canvas_content = wgt.Stack(
            width="100%", height="100%", bgcolor="#FFFFFF", flex=1
        )
        self.add_item(self.canvas_content)
        # visuel de fond
        self.bg_graph = uit.WImage(
            "screens",
            bg_name,
            self.skin,
            fixed=False,
            valign="top",
            width="100%",
            position="absolute",
            local_layer=0,
            fillmode="cover",
        )
        self.canvas_content.add_item(self.bg_graph)
        # preloader et txt
        self.zone_preload = wgt.HStack(width="100%", height="100%")
        self.canvas_content.add_item(self.zone_preload)
        self.zone_carte_txt = wgt.Stack(height="100%", padding="5%", flex=1)
        self.zone_preload.add_item(self.zone_carte_txt)
        self.widget_preload = SimplePreloader(self.skin, valign="middle", height="30%")
        self.zone_preload.add_item(self.widget_preload)
        self.zone_txt = wgt.Stack(height="30%", flex=1, valign="middle", padding="5%")
        self.zone_preload.add_item(self.zone_txt)
        self.widget_image = uit.WImage(
            self.cat_img,
            self.name_img,
            self.skin,
            fixed=True,
            align="left",
            valign="middle",
            position="absolute",
        )
        self.zone_txt.add_item(self.widget_image)
        # Info et input :
        if self.show_infos:
            # zone info :
            self.infotext = uit.WText(
                "PoppinsMedium",
                16,
                self.skin,
                width="80%",
                height="100%",
                snapH=True,
                bottom=80,
                textalign="center",
                align="center",
                fgcolor="#330000",
                bgcolor="#FFFFFF00",
                visible=False,
            )
            self.canvas_content.add_item(self.infotext)
            # zone input :
            self.choiceentry = uit.WEntry(
                "PoppinsMedium",
                16,
                self.skin,
                align="center",
                textalign="center",
                bottom=50,
                height=27,
                width="200",
                fgcolor="#330000",
                bgcolor="#BEAEAE",
                visible=False,
            )
            # initialise l'input :
            self.choiceentry.register_callback(self._on_entry_entered)
            self.choiceentry.take_focus()
            self.canvas_content.add_item(self.choiceentry)
        # texte carte :
        if self.show_carte:
            self.txt_carte = ScaledText(
                "UbuntuMono",
                12,
                self.skin,
                snapW=True,
                height=1000,
                snapH=True,
                padding=0,
                align="right",
                valign="middle",
                fgcolor="#330000",
                bgcolor="#FFFFFF00",
            )
            self.zone_carte_txt.add_item(self.txt_carte)
        # 3- Footer si chargement
        if self.get_initial_state() == ScreenWaitBase.STATE_LOADING:
            self.footer = wgt.HStack(width="100%", height=50, bgcolor="#330000")
            self.add_item(self.footer)

    #-----> Etat
    def set_state(self, statename):
        """
        Modification du visuel
        """
        # spécifique :
        self.show_txt_carte("")
        # générique :
        ScreenWaitBase.set_state(self, statename)

    def show_preload(self, show):
        """
        Démarre / arrête le preloader.
        """
        if show:
            self.widget_preload.start()
        else:
            self.widget_preload.stop()

    def show_image(self, img):
        """
        Affiche l'image img
        """
        if self.widget_image != None and img != None:
            self.widget_image.load_surface(img)

    #-----> Infos
    def show_message(self, msg, is_input, rollover=False):
        """
        Affichage d'un message dans la zone info
        """
        if self.infotext == None:
            return
        if is_input:
            self._input_txt = msg
            self.choiceentry.visible = True
        else:
            self._info_txt = msg
        pub_txt = ""
        if self._info_txt not in ["", None]:
            pub_txt = self._info_txt
        if self._input_txt not in ["", None]:
            if self._info_txt not in ["", None]:
                pub_txt += "\n"
            pub_txt += self._input_txt
        self.publish_message(pub_txt)

    def publish_message(self, msg):
        """
        Affichage d'un message dans la zone info
        """
        self.infotext.visible = True
        self.infotext.text = msg

    def show_txt_carte(self, txt):
        """
        Affiche la vue texte de la carte
        """
        if self.txt_carte:
            txt.strip()
            self.txt_carte.text = txt

    #-----> Input
    def _on_entry_entered(self, event):
        """
        Méthode de validation de l'input
        """
        cmd = self.choiceentry.get_input_value()
        self.mngr.on_choice_made(cmd)
        self.choiceentry.set_input_value("")


class ScaledText(uit.WText):
    """
    Texte rescalable (pour carte texte)
    """

    def __init__(self, fontname, size, skin, text="", scale=2.12, **kwargs):
        """
        Constructeur
        
        Args:
            * kwargs : voir uit.WText
            * scale (int): facteur d'échelle w/h
            
        Rq: 2.12 permet de rendre UbuntuMono "carrée"
        """
        # ratio w/h
        self.scale = scale
        # générique
        uit.WText.__init__(self, fontname, size, skin, text=text, **kwargs)

    def draw_display(self):
        """
        Dessinne ou redessinne l'objet.
        """
        # optimisation
        if not self.visible:
            return
        # publication du texte :
        if self.text_surface == None or not self._textrender_updated:
            # rendu au besoin :
            self.render_text(self.text)
        if self.text_surface != None:
            # rescale :
            w, h = self.text_size
            newsize = math.ceil(self.scale * w), h
            scaled_surface = pygame.transform.smoothscale(self.text_surface, newsize)
            # update dims :
            self.text_size = newsize
            self.discard_resize()
            # ré initialise la surface par défaut:
            self.create_default_surface()
            # publication :
            # blit interne :
            brect = self.get_border_rect()
            self.image.blit(scaled_surface, (brect.x, brect.y), area=brect)


class SimplePreloader(wgt.Image):
    """
    Jauge de préchargement
    """

    def __init__(self, skin, **kwargs):
        """
        Constructeur
        """
        # ref au skin
        self.skin = skin
        # liste d'images
        self.imglist = self.skin.get_loading_images()
        # activité
        self.do_run = False
        self.current_indice = None
        # générique :
        surf = self.imglist[0]
        wgt.Image.__init__(self, surface=surf, fixed=False, name="preload", **kwargs)

    def start(self):
        """
        Démarre le preload
        """
        # activité :
        self.do_run = True
        # charge la première image :
        self.current_indice = 0
        surf = self.imglist[self.current_indice]
        self.load_surface(surf)

    def stop(self):
        """
        Arrête le preload
        """
        # activité :
        self.do_run = False

    def update(self, *args):
        """
        Appelée à chaque frame (surcharge de VirtualItem)
        """
        if self.do_run:
            nb = len(self.imglist)
            if self.current_indice < nb - 1:
                self.current_indice += 1
            else:
                self.current_indice = 0
            surf = self.imglist[self.current_indice]
            self.load_surface(surf)
