#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Composants graphiques simples
"""
# import
import tkinter as tk
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractSwitch
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractInput

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = [
    "CustomEntry",
    "CanvasSwitch",
    "CanvasImage",
    "CanvasSpacer",
    "CanvasSeparateur",
]
# classes
class CustomEntry(tk.Entry, AbstractInput):
    """
    Text Input personnalisé
    """

    def __init__(self, parent, **kwargs):
        """
        Constructeur
        """
        # générique :
        tk.Entry.__init__(self, parent, **kwargs)
        # spécifique :
        self.tktextvar = None
        if "textvariable" in kwargs.keys():
            self.tktextvar = kwargs["textvariable"]
        self.callback = None

    def register_callback(self, clb):
        """
        Enregistre le callback à appeler après validation (appui touche entrée)
        """
        self.callback = clb
        self.bind("<Return>", self.callback)

    def take_focus(self):
        """
        Méthode d'acquisition du focus input
        """
        self.focus_set()

    def get_input_value(self):
        """
        Getter du texte input
        """
        return self.tktextvar.get()

    def set_input_value(self, val):
        """
        Setter du texte input
        """
        if isinstance(val, str):
            self.tktextvar.set(val)


class CanvasSwitch(tk.Canvas, AbstractSwitch):
    """
    Implémentation graphique d'un bouton ou checkbutton
    """

    def __init__(self, parent, Mngr, skin, name, switch, bgcolor):
        """
        Constructeur
        
        * Mngr : référence à CommandeFrame
        * name : nom connu du skin pour retourner les images associées
        * switch : boolean indique si le bouton se comporte comme un checkbutton
        
        """
        # générique :
        tk.Canvas.__init__(
            self, parent, {"bg": bgcolor, "borderwidth": 0, "highlightthickness": 0}
        )
        # Manager :
        self.Mngr = Mngr
        # Skin :
        self.skin = skin
        # spécifique :
        self.name = name
        self._is_switch = switch
        self.current_state = AbstractSwitch.UNSELECTED
        # images
        self._init_images()
        # événements
        self._enabled = True
        self._bindings_set = False
        self._set_bindings()
        #
        self._show_state(self.current_state)

    def _init_images(self):
        """
        Initialise les images associées aux états
        """
        self.states_img = dict()
        self.states_img[AbstractSwitch.UNSELECTED] = self.skin.get_image(
            "nav", self.name, state=1
        )
        self.states_img[AbstractSwitch.OVER] = self.skin.get_image(
            "nav", self.name, state=2
        )
        self.states_img[AbstractSwitch.PRESSED] = self.skin.get_image(
            "nav", self.name, state=3
        )
        self.states_img[AbstractSwitch.SELECTED] = self.skin.get_image(
            "nav", self.name, state=4
        )
        self.states_img[AbstractSwitch.DISABLED] = self.skin.get_image(
            "nav", self.name, state=5
        )
        # Dimensions :
        w = self.states_img[AbstractSwitch.UNSELECTED].width()
        h = self.states_img[AbstractSwitch.UNSELECTED].height()
        self.configure(width=w)
        self.configure(height=h)
        # png transparent :
        transptk = self.skin.get_image("common", "transp", size=(w, h))
        self._transpimg = self.create_image(0, 0, image=transptk)
        self._current_image = self.create_image(0, 0, anchor="nw")

    def get_state(self):
        """
        Retourne l'état du bouton
        """
        return self.current_state

    def is_switch(self):
        """
        Indique si le bouton se comporte comme un switch
        """
        return self._is_switch

    def set_state(self, state):
        """
        Modifie l'état du bouton
        """
        if state in [AbstractSwitch.ENABLED, AbstractSwitch.DISABLED]:
            self._handle_activation(state == AbstractSwitch.ENABLED)
            if state == AbstractSwitch.ENABLED:
                state = AbstractSwitch.UNSELECTED
        self.current_state = state
        self._show_state(self.current_state, updateNow=False)

    def _handle_activation(self, enable):
        """
        Modifie l'état d'activation
        """
        if enable != self._enabled:
            self._enabled = enable
            if self._enabled:
                self._set_bindings()
            else:
                self._unset_bindings()

    def _show_state(self, state, updateNow=True):
        """
        Modifie l'apparence du bouton
        """
        if state in AbstractSwitch.STATES:
            if not self._enabled and state == AbstractSwitch.UNSELECTED:
                state = AbstractSwitch.DISABLED
            newimg = self.states_img[state]
            self.itemconfig(self._current_image, image=newimg)
            self.tag_raise(self._transpimg)
            if updateNow:
                self.update_idletasks()

    def _set_bindings(self):
        """
        Active les événements
        """
        if self._bindings_set:
            return
        self._bindings_set = True
        # Focus :
        self.takefocus = 1
        # Souris :
        self.bind("<Enter>", self._mouse_handler)  # over
        self.bind("<Leave>", self._mouse_handler)  # out
        self.bind("<Button-1>", self._mouse_handler)  # press
        # Focus :
        self.bind("<FocusIn>", self._focus_handler)
        self.bind("<FocusOut>", self._focus_handler)
        # Clavier :
        # self.bind("<space>", self._key_handler)
        self.bind("<KeyPress>", self._key_handler)
        self.bind("<KeyRelease>", self._key_handler)

    def _unset_bindings(self):
        """
        Désactive les événements
        """
        if not self._bindings_set:
            return
        self._bindings_set = False
        # Focus :
        self.takefocus = 0
        # Souris :
        self.unbind("<Enter>")
        self.unbind("<Leave>")
        self.unbind("<Button-1>")
        # Focus :
        self.unbind("<FocusIn>")
        self.unbind("<FocusOut>")
        # Clavier :
        # self.bind("<space>", self._key_handler)
        self.unbind("<KeyPress>")
        self.unbind("<KeyRelease>")

    def _mouse_handler(self, event):
        """
        Handler des evts souris
        """
        st = None
        if event.type == tk.EventType.Enter:
            st = CanvasSwitch.OVER
            self._show_state(st)
        elif event.type == tk.EventType.Leave:
            st = self.current_state
            self._show_state(st)
        elif event.type == tk.EventType.ButtonPress and event.num == 1:
            st = CanvasSwitch.PRESSED
            self._show_state(st)
        if st != None:
            self.Mngr.control_callback(self, st)

    def _focus_handler(self, event):
        """
        Handler des evts focus
        """
        st = None
        if event.type == tk.EventType.FocusIn:
            st = CanvasSwitch.OVER
            self._show_state(st)
        elif event.type == tk.EventType.FocusOut:
            st = self.current_state
            self._show_state(st)
        if st != None:
            self.Mngr.control_callback(self, st)

    def _key_handler(self, event):
        """
        Handler des evts clavier
        """
        st = None
        if event.type == tk.EventType.KeyPress:
            if event.keycode == 65 or event.keysym == "space":
                st = CanvasSwitch.PRESSED
                self._show_state(st)
        elif event.type == tk.EventType.KeyRelease:
            if event.keycode == 65 or event.keysym == "space":
                st = self.current_state
                self._show_state(st)
        if st != None:
            self.Mngr.control_callback(self, st)


class CanvasImage(tk.Canvas):
    """
    Image statique
    """

    def __init__(self, parent, skin, name, bgcolor, cat="nav"):
        """
        Constructeur
        
        * name : nom connu du skin pour retourner les images associées
        * cat : catégorie connue du skin comprenant la ref name (par défaut cat="nav")
        
        """
        # générique :
        tk.Canvas.__init__(
            self, parent, {"bg": bgcolor, "borderwidth": 0, "highlightthickness": 0}
        )
        # Skin instancié par la GUITk :
        self.skin = skin
        # spécifique :
        self.name = name
        # Image :
        self.width = self.winfo_width()
        self.height = self.winfo_height()
        tkimg = self.skin.get_image(cat, name)
        self._current_image = self.create_image(0, 0, image=tkimg, anchor="nw")
        w = tkimg.width()
        h = tkimg.height()
        self.configure(width=w)
        self.configure(height=h)


class CanvasSpacer(tk.Canvas):
    """
    Espacement
    """

    def __init__(self, parent, skin, size, bgcolor):
        """
        Constructeur
        """
        # générique :
        tk.Canvas.__init__(
            self, parent, {"bg": bgcolor, "borderwidth": 0, "highlightthickness": 0}
        )
        # Skin img.ImgSkin instancié par la GUITk :
        self.skin = skin
        # spécifique :
        self.size = size
        # Image :
        tkimg = self.skin.get_image("common", "transp", size=size)
        self._current_image = self.create_image(0, 0, image=tkimg, anchor="nw")
        w = size[0]
        h = size[1]
        self.configure(width=w)
        self.configure(height=h)


class CanvasSeparateur(tk.Canvas):
    """
    Séparateur horizontal ou vertical
    """

    def __init__(self, parent, axe, dist, color, linewidth=2):
        """
        Constructeur
        """
        # générique :
        kwargs = {"bg": color, "borderwidth": 0, "highlightthickness": 0}
        if axe == "x":
            self.width = kwargs["width"] = dist
            self.height = kwargs["height"] = linewidth * 2
        else:
            self.width = kwargs["width"] = 20
            self.height = kwargs["height"] = dist
        tk.Canvas.__init__(self, parent, **kwargs)
        # Style
        self.axe = axe
        self.linewidth = linewidth
        self.color = color
        if self.axe == "x":
            x0 = 0
            y0 = y1 = (self.height - self.linewidth) / 2
            x1 = self.width
        else:
            x0 = x1 = (self.width - self.linewidth) / 2
            y0 = 0
            y1 = self.height
        self.tkline = self.create_line(
            x0, y0, x1, y1, state="disabled", fill=self.color, width=self.linewidth
        )
