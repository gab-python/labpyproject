#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Carte (labyrinthe) : implémentation Tkinter
"""
# imports :
import tkinter as tk
from labpyproject.apps.labpyrinthe.gui.skinBase.zone_carte_base import ZoneCarteBase
from labpyproject.apps.labpyrinthe.gui.skinBase.zone_carte_base import ItemObjectBase

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ZoneCarte", "ItemObject"]
# classes
class ZoneCarte(tk.Canvas, ZoneCarteBase):
    """
    Equivalent graphique du LabLevel
    """

    def __init__(self, parent, Mngr, skin, **kwargs):
        """
        Constructeur
        """
        # Initialisation générique :
        tk.Canvas.__init__(
            self, parent, {"bg": "#FFFFFF", "borderwidth": 0, "highlightthickness": 0}
        )
        ZoneCarteBase.__init__(self, Mngr, skin, ItemObject, logperf=True)
        # Gestion du resize :
        self._init_resize()

    #-----> Surcharge de ZoneCarteBase
    def active_single_layer(self, layername, z):
        """
        Post initialisation d'une couche :
        
        * pour activer la couche de façon permanente (pygame)
        * pour insérer un marqueur de gestion des zindexs (tkinter)
            
        """
        if "splitters" not in self.layersdict.keys():
            self.layersdict["splitters"] = dict()
        # png transparent :
        transptk = self.skin.get_image("common", "transp", size=(1, 1))
        # création du séparateur :
        sepid = self.create_image(
            0, 0, image=transptk, state="disabled", tags=layername
        )
        self.layersdict["splitters"][layername] = sepid

    def get_canvas_dimensions(self):
        """
        Retourne les dimensions de l'objet graphique implémentant ZoneCarteBase
        """
        self.width = self.winfo_width()
        self.height = self.winfo_height()
        return self.width, self.height

    #-----> Resize spécifique
    def _init_resize(self):
        """
        Initialise la gestion du resize
        """
        self.width = self.height = None
        self.bind("<Configure>", self.on_resize)

    def on_resize(self, event):
        """
        Appelée lors d'un resize de l'application
        """
        self.carte_dimensions_initialized = False
        # enregistrement des dimensions
        self.width = event.width
        self.height = event.height
        # resize générique de la carte
        self.update_carte_geometry(event.width, event.height)
        # affichage
        self.after_idle(self._on_resize_end)

    def _on_resize_end(self):
        """
        Fin du process de resize
        """
        # Masquage de l'écran d'attente :
        self.hide_resize_screen()

    #-----> Gestion des formes vecto
    def draw_mask(self):
        """
        Dessine le masque ne laissant apparaitre que le labyrinthe
        """
        layer = self.layersdict[ZoneCarteBase.SHAPE_MASK]
        mask_left = self.create_rectangle(
            0, 0, 10, 10, fill="#FFFFFF", width=0, state="hidden", tags="mask_left"
        )
        item_left = ItemObject(self, graphobjref=mask_left, typecontent="shape")
        layer.append(item_left)
        mask_right = self.create_rectangle(
            0, 0, 10, 10, fill="#FFFFFF", width=0, state="hidden", tags="mask_right"
        )
        item_right = ItemObject(self, graphobjref=mask_right, typecontent="shape")
        layer.append(item_right)
        mask_top = self.create_rectangle(
            0, 0, 10, 10, fill="#FFFFFF", width=0, state="hidden", tags="mask_top"
        )
        item_top = ItemObject(self, graphobjref=mask_top, typecontent="shape")
        layer.append(item_top)
        mask_bottom = self.create_rectangle(
            0, 0, 10, 10, fill="#FFFFFF", width=0, state="hidden", tags="mask_bottom"
        )
        item_bottom = ItemObject(self, graphobjref=mask_bottom, typecontent="shape")
        layer.append(item_bottom)

    def draw_bg(self):
        """
        Crée le rectangle de fond en mode optimisé
        """
        bgcol = self.color_bg_lab
        bgr = self.create_rectangle(
            0, 0, 10, 10, fill=bgcol, width=0, state="hidden", tags="bgrect"
        )
        layer = self.layersdict[ZoneCarteBase.SHAPE_BG]
        itbg = ItemObject(self, graphobjref=bgr, typecontent="shape")
        layer.append(itbg)

    def draw_bot_highlights(self):
        """
        Dessine les cercles de highlight du joueur courant
        """
        layer = self.layersdict[ZoneCarteBase.SHAPE_HIGHLIGHT_ROBOT]
        defaultargs = {"fill": "", "outline": "#CCCCCC"}
        # cercle de signalisation du bot :
        c1 = self.create_oval(0, 0, 10, 10, defaultargs, width=3, tags="c_bot")
        itc1 = ItemObject(self, graphobjref=c1, typecontent="shape")
        self.itemconfig(c1, state="hidden")
        layer.append(itc1)
        # cecle de représentation de son champ d'action
        c2 = self.create_oval(0, 0, 100, 100, defaultargs, width=1, tags="c_action")
        itc2 = ItemObject(self, graphobjref=c2, typecontent="shape")
        self.itemconfig(c2, state="hidden")
        layer.append(itc2)

    def highlight_player(self, robotlist, gambleinfos):
        """
        Identification du prochain joueur
        """
        if gambleinfos == None or robotlist == None:
            return
        nbcoups = gambleinfos["coup"]
        totalcoups = gambleinfos["total_coups"]
        # données du joueur :
        hdatas = self.get_bot_highlight_datas(robotlist, gambleinfos)
        cbot = hdatas["cbot"]
        # maj des cercles de highlight :
        cerclebot = self.find_withtag("c_bot")
        cercleaction = self.find_withtag("c_action")
        if cbot != None:
            color = hdatas["color"]
            # identification du joueur :
            self.itemconfig(cerclebot, outline=color)
            self.coords(
                cerclebot,
                hdatas["x0_b"],
                hdatas["y0_b"],
                hdatas["x1_b"],
                hdatas["y1_b"],
            )
            if nbcoups == totalcoups:
                # rayon d'action :
                pass
            self.itemconfig(cercleaction, outline=color)
            self.coords(
                cercleaction,
                hdatas["x0_a"],
                hdatas["y0_a"],
                hdatas["x1_a"],
                hdatas["y1_a"],
            )
            # affichage :
            self.itemconfig(cerclebot, state="disabled")
            self.itemconfig(cercleaction, state="hidden")
        else:
            # masquage
            self.itemconfig(cerclebot, state="hidden")
            self.itemconfig(cercleaction, state="hidden")

    def update_mask(self):
        """
        Redimensionnement des 4 éléments du masque
        """
        # geom :
        x0, y0 = self.carte_repere
        wf = self.carte_dimensions[0] * self.casesize[0]
        hf = self.carte_dimensions[1] * self.casesize[1]
        x1, y1 = x0 + wf, y0 + hf
        wT = self.width
        hT = self.height
        # maj :
        left = self.find_withtag("mask_left")
        self.coords(left, 0, 0, x0, hT)
        self.itemconfig(left, state="disabled")
        right = self.find_withtag("mask_right")
        self.coords(right, x1, 0, wT, hT)
        self.itemconfig(right, state="disabled")
        top = self.find_withtag("mask_top")
        self.coords(top, 0, 0, wT, y0)
        self.itemconfig(top, state="disabled")
        bottom = self.find_withtag("mask_bottom")
        self.coords(bottom, 0, y1, wT, hT)
        self.itemconfig(bottom, state="disabled")

    def update_bg(self):
        """
        Met à jour le rectangle de fond permettant de simuler
        le quadrillage
        """
        x0, y0 = self.carte_repere
        wf = self.carte_dimensions[0] * self.casesize[0]
        hf = self.carte_dimensions[1] * self.casesize[1]
        x1, y1 = x0 + wf, y0 + hf
        bgr = self.find_withtag("bgrect")
        # mise à jour :
        self.coords(bgr, x0, y0, x1, y1)
        self.itemconfig(bgr, state="disabled")
        # cadre debug :
        cdr = self.find_withtag("cadrerect")
        w, h = self.winfo_width(), self.winfo_height()
        self.coords(cdr, 0, 0, w, h)
        self.itemconfig(cdr, state="disabled")

    #-----> Publication de la carte
    def on_carte_published(self):
        """
        Traitements spécifiques en fin de publication.
        """
        # Gestion des zindexs :
        self._manage_zindexs()
        # Update affichage :
        self.update_idletasks()

    def on_carte_updated(self, dictargs, has_anim):
        """
        Traitements spécifiques en fin de publication.
        
        Args:
            * dictargs : dict généré par GameManager.update_carte
            * has_anim : bool indiquant si il y a animation
        
        """
        # Gestion des zindexs :
        if not has_anim:
            # optimisation : la gestion des z-indexs coûte cher
            self._manage_zindexs()
        # Update affichage :
        self.update_idletasks()

    def _manage_zindexs(self):
        """
        Assure la cohérence des zindexs
        """
        lastrep = None
        #  couches :
        for layerdict in self.zindexslist:
            layername = layerdict["name"]
            # repère :
            rep = self.layersdict["splitters"][layername]
            if lastrep == None:
                self.tag_lower(rep)
                lastrep = rep
            else:
                listitem = list(reversed(self.find_all()))
                lastrep = listitem[0]
                self.tag_raise(rep, lastrep)
            # items :
            itemlist = self.get_items_for_layer(layername)
            for itemobj in itemlist:
                graphobjref = itemobj.graphobjref
                self.tag_raise(graphobjref, rep)


#-----> Objet modélisant un item graphique de la carte (subclassé)
class ItemObject(ItemObjectBase):
    """
    Implémentation Tkinter de ItemObjectBase
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
            newid = self.zonecarte.create_image(
                0, 0, anchor="nw", state="disabled", tags=typecase
            )
            self.graphobjref = newid

    def delete_view(self):
        """
        Supprime la vue graphique de self.case
        """
        self.zonecarte.delete(self.graphobjref)

    def set_current_image(self, imgskin):
        """
        Affiche une nouvelle image (générée par le skin)
        """
        # enregistrement de la ref :
        ItemObjectBase.set_current_image(self, imgskin)
        # Affichage :
        self.zonecarte.itemconfig(self.graphobjref, image=imgskin)

    def get_real_coords(self):
        """
        Retourne les coordonnées réelles (converties / la case) de la vue graphique
        """
        return self.zonecarte.coords(self.graphobjref)

    def set_real_coords(self, realx, realy):
        """
        Déplace la vue graphique aux coordonnées réelles (converties) realx, realy
        """
        xi, yi = self.get_real_coords()
        self.zonecarte.move(self.graphobjref, realx - xi, realy - yi)

    def set_visible(self, show):
        """
        Affiche ou masque lma vue graphique.
        """
        sti = self.zonecarte.itemcget(self.graphobjref, "state")
        if show:
            if sti == "hidden":
                self.zonecarte.itemconfig(self.graphobjref, state="disabled")
        else:
            self.zonecarte.itemconfig(self.graphobjref, state="hidden")
