#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
**Mécanique basique de gestion des événements pygame.**

Classes utilisées par les modules **core** et **widgets**.

.. note::
    V1 mécanique du type top -> bottom à faire évoluer en bottom -> top -> bottom 
    pour permettre la capture d'événements à différents moments du flux.
"""
# imports :
import pygame.locals

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = [
    "CustomEventManager",
    "GUIEventManager",
    "CustomBaseControl",
    "CustomBaseInput",
    "CustomBaseButton",
]
# classes :
class CustomEventManager:
    """
    Gestionnaire d'événements utilisé par composition par la GUI.
    """

    # familles de touches :
    LETTERS_KEYS = [
        pygame.locals.K_a,
        pygame.locals.K_b,
        pygame.locals.K_c,
        pygame.locals.K_d,
        pygame.locals.K_e,
        pygame.locals.K_f,
        pygame.locals.K_g,
        pygame.locals.K_h,
        pygame.locals.K_i,
        pygame.locals.K_j,
        pygame.locals.K_k,
        pygame.locals.K_l,
        pygame.locals.K_m,
        pygame.locals.K_n,
        pygame.locals.K_o,
        pygame.locals.K_p,
        pygame.locals.K_q,
        pygame.locals.K_r,
        pygame.locals.K_s,
        pygame.locals.K_t,
        pygame.locals.K_u,
        pygame.locals.K_v,
        pygame.locals.K_w,
        pygame.locals.K_x,
        pygame.locals.K_y,
        pygame.locals.K_z,
    ]  #: Liste des touches de lettres
    NUMBERS_KEYS = [
        pygame.locals.K_0,
        pygame.locals.K_1,
        pygame.locals.K_2,
        pygame.locals.K_3,
        pygame.locals.K_4,
        pygame.locals.K_5,
        pygame.locals.K_6,
        pygame.locals.K_7,
        pygame.locals.K_8,
        pygame.locals.K_9,
        pygame.locals.K_KP0,
        pygame.locals.K_KP1,
        pygame.locals.K_KP2,
        pygame.locals.K_KP3,
        pygame.locals.K_KP4,
        pygame.locals.K_KP5,
        pygame.locals.K_KP6,
        pygame.locals.K_KP7,
        pygame.locals.K_KP8,
        pygame.locals.K_KP9,
    ]  #: Liste des touches d'entiers
    PONCT_KEYS = [
        pygame.locals.K_EXCLAIM,
        pygame.locals.K_QUOTEDBL,
        pygame.locals.K_HASH,
        pygame.locals.K_DOLLAR,
        pygame.locals.K_AMPERSAND,
        pygame.locals.K_QUOTE,
        pygame.locals.K_LEFTPAREN,
        pygame.locals.K_RIGHTPAREN,
        pygame.locals.K_ASTERISK,
        pygame.locals.K_PLUS,
        pygame.locals.K_COMMA,
        pygame.locals.K_MINUS,
        pygame.locals.K_PERIOD,
        pygame.locals.K_SLASH,
        pygame.locals.K_COLON,
        pygame.locals.K_SEMICOLON,
        pygame.locals.K_LESS,
        pygame.locals.K_EQUALS,
        pygame.locals.K_GREATER,
        pygame.locals.K_QUESTION,
        pygame.locals.K_AT,
        pygame.locals.K_LEFTBRACKET,
        pygame.locals.K_BACKSLASH,
        pygame.locals.K_RIGHTBRACKET,
        pygame.locals.K_CARET,
        pygame.locals.K_UNDERSCORE,
        pygame.locals.K_BACKQUOTE,
        pygame.locals.K_KP_PERIOD,
        pygame.locals.K_KP_DIVIDE,
        pygame.locals.K_KP_MULTIPLY,
        pygame.locals.K_KP_MINUS,
        pygame.locals.K_KP_PLUS,
        pygame.locals.K_KP_EQUALS,
    ]  #: Liste des touches de ponctutaion
    ARROW_KEYS = [
        pygame.locals.K_UP,
        pygame.locals.K_DOWN,
        pygame.locals.K_RIGHT,
        pygame.locals.K_LEFT,
    ]  #: Liste des touches de flèches
    COMMAND_KEYS = [
        pygame.locals.K_BACKSPACE,
        pygame.locals.K_TAB,
        pygame.locals.K_RETURN,
        pygame.locals.K_ESCAPE,
        pygame.locals.K_SPACE,
        pygame.locals.K_DELETE,
        pygame.locals.K_KP_ENTER,
    ]  #: Liste des touches de commande
    # abonnement / désabonnement d'un contrôle
    CE_REGISTER = pygame.USEREVENT + 1  #: événement abonnement de contrôle
    CE_UNREGISTER = pygame.USEREVENT + 2  #: événement désabonnement de contrôle
    # événement de demande de focus pour un input
    CE_ASK_INPUT_FOCUS = pygame.USEREVENT + 3  #: événement demande de focus d'input
    # types d'événements ciblés par un contrôle :
    MOUSE_CLIC = "MOUSE_CLIC"  #: événement souris
    MOUSE_OVER = "MOUSE_OVER"  #: événement souris
    MOUSE_OUT = "MOUSE_OUT"  #: événement souris
    MOUSE_MOVE = "MOUSE_MOVE"  #: événement souris
    KEY_PRESSED = "KEY_PRESSED"  #: événement touche
    KEY_RELEASED = "KEY_RELEASED"  #: événement touche
    # méthodes
    def __init__(self, Mngr):
        """
        Constructeur
        
        Args:
            Mngr (GUIEventManager): interface de la GUI pygame
        """
        # ref à la GUI :
        self.Mngr = Mngr
        # initalisations :
        self._init_control_dict()

    def _init_control_dict(self):
        """
        Initialise le dict d'enregistrement des contrôles (boutons et inputs).
        """
        self.ctrl_dict = dict()
        self.ctrl_dict[CustomEventManager.MOUSE_CLIC] = list()
        self.ctrl_dict[CustomEventManager.MOUSE_MOVE] = list()
        self.ctrl_dict[CustomEventManager.KEY_PRESSED] = list()
        self.ctrl_dict[CustomEventManager.KEY_RELEASED] = list()
        self.ctrl_dict["InputControls"] = list()
        self.ctrl_dict["ButtonOver"] = None

    def handle_events(self):
        """
        Interface avec la GUI : méthode à appeler à chaque frame d'éxécution. 
        Dépile les événements pygame, applique les traitements internes, informe la GUI.
        """
        for e in pygame.event.get():
            if e.type == CustomEventManager.CE_REGISTER:
                self._register_control(e)
            elif e.type == CustomEventManager.CE_UNREGISTER:
                self._unregister_control(e)
            elif e.type == CustomEventManager.CE_ASK_INPUT_FOCUS:
                self._handle_entry_focus_event(e)
            elif e.type in [
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEBUTTONUP,
                pygame.MOUSEMOTION,
            ]:
                self._handle_mouse_evt(e)
            elif e.type in [pygame.KEYDOWN, pygame.KEYUP]:
                self._handle_key_evt(e)
            elif e.type == pygame.VIDEORESIZE:
                self.Mngr.on_resize_event(e)
            elif e.type == pygame.QUIT:
                # si on souhaite fermer avec la touche escape :
                # or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                # Rq: touche plutôt utilisée pour quitter le plein écran.
                self.Mngr.on_quit_event(e)
            elif e.type == pygame.ACTIVEEVENT:
                self.Mngr.on_active_event(e)

    def _handle_mouse_evt(self, evt):
        """
        Gestion interne des événements souris
        """
        ctrllist = None
        if evt.type == pygame.MOUSEBUTTONDOWN and evt.button == 1:
            # ie CustomEventManager.MOUSE_CLIC avec le bouton gauche
            ctrllist = self.ctrl_dict[CustomEventManager.MOUSE_CLIC]
        elif evt.type == pygame.MOUSEBUTTONUP and evt.button == 1:
            # release soit CustomEventManager.MOUSE_OVER
            ctrllist = self.ctrl_dict[CustomEventManager.MOUSE_MOVE]
        elif evt.type == pygame.MOUSEMOTION:
            # CustomEventManager.MOUSE_OVER ou CustomEventManager.MOUSE_OUT
            ctrllist = self.ctrl_dict[CustomEventManager.MOUSE_MOVE]
        if ctrllist == None:
            return
        # ctrl survolés ou non par la souris
        colidelist = list()
        noncolidelist = list()
        for ctrl in ctrllist:
            if ctrl.enabled and ctrl.visible:
                if ctrl.globalRect.collidepoint(evt.pos):
                    colidelist.append(ctrl)
                else:
                    noncolidelist.append(ctrl)
        # Filtrage : on sélectionne le ctrl activé, visible et de plus grand z-index :
        overctrl = None
        prevoverctrl = self.ctrl_dict["ButtonOver"]
        if len(colidelist) > 0:
            overctrl = colidelist[0]
        # contrôles survolés ou cliqués :
        if evt.type == pygame.MOUSEBUTTONDOWN:
            customevent = CustomEventManager.MOUSE_CLIC
        else:
            customevent = CustomEventManager.MOUSE_OVER
        # Out du précédent :
        if prevoverctrl != None and prevoverctrl != overctrl:
            prevoverctrl.handle_mouse_event(CustomEventManager.MOUSE_OUT, evt)
        # Over ou Clic du nouveau
        if overctrl != None:
            overctrl.handle_mouse_event(customevent, evt)
            self.ctrl_dict["ButtonOver"] = overctrl

    def _handle_entry_focus_event(self, evt):
        """
        Gère l'affectation du focus parmi les éventuels CustomBaseInput
        """
        entryctrl = evt.control
        for ctrl in self.ctrl_dict["InputControls"]:
            ctrl.focused = False
        entryctrl.focused = True

    def _handle_key_evt(self, evt):
        """
        Gestion interne des événements clavier
        """
        if evt.type == pygame.KEYUP:
            customevent = CustomEventManager.KEY_RELEASED
            alllist = self.ctrl_dict[CustomEventManager.KEY_RELEASED]
        else:
            customevent = CustomEventManager.KEY_PRESSED
            alllist = self.ctrl_dict[CustomEventManager.KEY_PRESSED]
        # propagation systématique : seul l'input focusé réagira
        for ctrl in alllist:
            if ctrl.enabled:
                ctrl.handle_key_event(customevent, evt)

    def _register_control(self, evt):
        """
        Abonnement d'un control (via propagation d'un evt CustomEventManager.CE_REGISTER).
        """
        ctrl = evt.control
        # Filtrage : CustomSprite héritant de CustomBaseControl
        # => tests à remplacer par une interface abstraite
        if (
            not isinstance(ctrl, CustomBaseControl)
            or not hasattr(ctrl, "globalRect")
            or not hasattr(ctrl, "visible")
            or not hasattr(ctrl, "global_layer")
        ):
            return
        eventtypes = ctrl.get_event_types()
        for evttype in eventtypes:
            # cas particulier des inputs text :
            if isinstance(ctrl, CustomBaseInput):
                if ctrl not in self.ctrl_dict["InputControls"]:
                    self.ctrl_dict["InputControls"].append(ctrl)
            # cas général :
            if evttype == CustomEventManager.MOUSE_CLIC:
                if ctrl not in self.ctrl_dict[evttype]:
                    self.ctrl_dict[evttype].append(ctrl)
            elif evttype in [
                CustomEventManager.MOUSE_OVER,
                CustomEventManager.MOUSE_OUT,
            ]:
                if ctrl not in self.ctrl_dict[CustomEventManager.MOUSE_MOVE]:
                    self.ctrl_dict[CustomEventManager.MOUSE_MOVE].append(ctrl)
            elif evttype == CustomEventManager.KEY_PRESSED:
                if ctrl not in self.ctrl_dict[CustomEventManager.KEY_PRESSED]:
                    self.ctrl_dict[CustomEventManager.KEY_PRESSED].append(ctrl)
            elif evttype == CustomEventManager.KEY_RELEASED:
                if ctrl not in self.ctrl_dict[CustomEventManager.KEY_RELEASED]:
                    self.ctrl_dict[CustomEventManager.KEY_RELEASED].append(ctrl)

    def _unregister_control(self, evt):
        """
        Désabonnement d'un control (via propagation d'un evt CustomEventManager.CE_UNREGISTER).
        """
        ctrl = evt.control
        eventtypes = ctrl.get_event_types()
        for evttype in eventtypes:
            # cas particulier des inputs text :
            if isinstance(ctrl, CustomBaseInput):
                if ctrl in self.ctrl_dict["InputControls"]:
                    self.ctrl_dict["InputControls"].remove(ctrl)
            # cas général :
            if evttype == CustomEventManager.MOUSE_CLIC:
                if ctrl in self.ctrl_dict[CustomEventManager.MOUSE_CLIC]:
                    self.ctrl_dict[CustomEventManager.MOUSE_CLIC].remove(ctrl)
            elif evttype in [
                CustomEventManager.MOUSE_OVER,
                CustomEventManager.MOUSE_OUT,
            ]:
                if ctrl in self.ctrl_dict[CustomEventManager.MOUSE_MOVE]:
                    self.ctrl_dict[CustomEventManager.MOUSE_MOVE].remove(ctrl)
            elif evttype == CustomEventManager.KEY_PRESSED:
                if ctrl in self.ctrl_dict[CustomEventManager.KEY_PRESSED]:
                    self.ctrl_dict[CustomEventManager.KEY_PRESSED].remove(ctrl)
            elif evttype == CustomEventManager.KEY_RELEASED:
                if ctrl in self.ctrl_dict[CustomEventManager.KEY_RELEASED]:
                    self.ctrl_dict[CustomEventManager.KEY_RELEASED].remove(ctrl)


class GUIEventManager:
    """
    "Interface" de la GUI utilisant par composition CustomEventManager.
    """

    def __init__(self):
        """
        Initialisation de la gestion des événements
        """
        # Manager d'événement :
        self._eventMngr = CustomEventManager(self)

    def handle_events(self):
        """
        Méthode à appeler à chaque frame d'exécution pour traiter les événements.
        """
        self._eventMngr.handle_events()

    def on_resize_event(self, event):
        """
        Méthode appelée par CustomEventManager lorsque survient l'événement pygame.VIDEORESIZE 
        (event a pour attributs : size, w, h).
        """
        # à subclasser
        pass

    def on_quit_event(self, event):
        """
        Méthode appelée par CustomEventManager lorsque survient l'événement pygame.QUIT 
        (l'événement n'a aucun attribut particulier).
        """
        # à subclasser
        pass

    def on_active_event(self, event):
        """
        Méthode appelée par CustomEventManager lorsque survient l'événement pygame.ACTIVEEVENT, 
        indiquant si la fenêtre a ou non le focus (gain : boolean (0/1) indiquant le focus, 
        state : non documenté).
        
        """
        # à subclasser
        pass


class CustomBaseControl:
    """
    Classe de base d'un contrôle utilisateur (bouton, entry).
    A implémenter dans une succlasse héritant de CustomSprite.
    """

    def __init__(self, evtdict, **kwargs):
        """
        Constructeur
        
        Args:
            evtdict (dict): {"evttypes":}, avec evttypes une liste de valeurs parmi : 
                MOUSE_CLIC, MOUSE_OVER, MOUSE_OUT, KEY_PRESSED
        """
        # spécifique :
        self._enabled = True
        self._focused = False
        # événements écoutés :
        self._eventdict = evtdict

    # activation du contrôle
    def _get_enabled(self):
        """Etat d'activation du contrôle."""
        return self._enabled

    def _set_enabled(self, val):
        if bool(val) != self._enabled:
            if bool(val):
                self._enabled = True
            else:
                self._enabled = False
            self.on_enable_changed()

    enabled = property(
        _get_enabled, _set_enabled
    )  #: Etat d'activation du contrôle (bool).

    def on_enable_changed(self):
        """
        Appelée lorsque self.enabled a été modifié.
        """
        # à subclasser
        pass

    # focus du contrôle
    def _get_focused(self):
        """Le contrôle a t'il le focus?"""
        return self._focused

    def _set_focused(self, val):
        if bool(val):
            self._focused = True
        else:
            self._focused = False

    focused = property(_get_focused, _set_focused)  #: Le contrôle a t'il le focus?

    def get_event_types(self):
        """
        Retourne la liste d'événements écoutés par le ctrl.
        """
        return self._eventdict["evttypes"]

    def register(self):
        """
        Abonnement auprès du manager d'événements. 
        A ajouter à la méthode générique d'ajout à la displaylist
        """
        if self._eventdict != None and "evttypes" in self._eventdict.keys():
            args = {"control": self}
            evt = pygame.event.Event(CustomEventManager.CE_REGISTER, args)
            self.fire_event(evt)

    def unregister(self):
        """
        Désabonnement auprès du manager d'événements. 
        A ajouter à la méthode générique de retrait de la displaylist
        """
        if self._eventdict != None and "evttypes" in self._eventdict.keys():
            args = {"control": self}
            evt = pygame.event.Event(CustomEventManager.CE_UNREGISTER, args)
            self.fire_event(evt)

    def fire_event(self, evt):
        """
        Dispatch l'événement evt.
        """
        pygame.event.post(evt)

    def handle_mouse_event(self, customeventtype, event):
        """
        Appelée par le manager d'événements
        
        Args:
            customeventtype : CustomEventManager.MOUSE_CLIC, CustomEventManager.MOUSE_OVER, 
                CustomEventManager.MOUSE_OUT
            event : pygame.MOUSEBUTTONDOWN ou pygame.MOUSEMOTION        
        """
        # à subclasser
        pass

    def handle_key_event(self, customeventtype, event):
        """
        Appelée par le manager d'événements
        
        Args:
            customeventtype : CustomEventManager.KEY_PRESSED ou CustomEventManager.KEY_RELEASED
            event : pygame.KEYDOWN ou pygame.KEYUP        
        """
        # à subclasser
        pass


class CustomBaseInput(CustomBaseControl):
    """
    Implémentation basique d'un input text.
    """

    # paramétrage par défaut :
    DEFAULT_EVT_DICT = {
        "evttypes": [CustomEventManager.KEY_PRESSED, CustomEventManager.MOUSE_CLIC]
    }  #: paramétrage par défaut
    # méthodes
    def __init__(self, evtdict=DEFAULT_EVT_DICT, **kwargs):
        """
        Constructeur
        """
        # générique
        CustomBaseControl.__init__(self, evtdict, **kwargs)
        # variable associée au contenu :
        self._inputext = ""

    def handle_key_event(self, customeventtype, event):
        """
        Appelée par le manager d'événements. Prise en charge de la touche d'effacement, 
        des touches de validation, mise à jour du texte associé au contrôle.
        
        Args:
            customeventtype : CustomEventManager.KEY_PRESSED ou CustomEventManager.KEY_RELEASED
            event : pygame.KEYDOWN ou pygame.KEYUP        
        """
        if self.focused:
            oldtext = str(self._inputext)
            reloadtext = True
            if customeventtype == CustomEventManager.KEY_PRESSED:
                if event.key in CustomEventManager.COMMAND_KEYS:
                    if event.key == pygame.locals.K_BACKSPACE:
                        # effacement dernier char :
                        if len(oldtext) > 0:
                            oldtext = oldtext[:-1]
                    elif event.key in [
                        pygame.locals.K_RETURN,
                        pygame.locals.K_KP_ENTER,
                    ]:
                        # validation :
                        self.on_entry_validated(event)
                        reloadtext = False
                    elif event.key == pygame.locals.K_SPACE:
                        oldtext += " "
                elif event.key in CustomEventManager.NUMBERS_KEYS:
                    oldtext += event.unicode
                elif event.key in CustomEventManager.PONCT_KEYS:
                    oldtext += event.unicode
                elif event.key in CustomEventManager.LETTERS_KEYS:
                    oldtext += event.unicode
                # maj variable interne :
                if reloadtext:
                    self._set_inputext(oldtext)

    def on_entry_validated(self, event):
        """
        Appelée par handle_key_event lorsqu'une touche entrée a été pressée.
        """
        # à subclasser
        pass

    def _get_inputext(self):
        """
        Simple getter
        """
        return self._inputext

    def _set_inputext(self, val):
        """
        Setter du texte associé au contrôle, retourne un boolean indiquant
        si la valeur a effectivement changée.
        """
        if val != self._inputext:
            self._inputext = val
            return True
        return False

    inputext = property(
        _get_inputext, _set_inputext
    )  #: texte d'input associé au contrôle

    def handle_mouse_event(self, customeventtype, event):
        """
        Appelée par le manager d'événements. Demande de focus.
        
        Args:
            customeventtype : CustomEventManager.MOUSE_CLIC, CustomEventManager.MOUSE_OVER, 
                CustomEventManager.MOUSE_OUT
            event : pygame.MOUSEBUTTONDOWN ou pygame.MOUSEMOTION        
        """
        if customeventtype == CustomEventManager.MOUSE_CLIC:
            # demande le focus
            self.ask_input_focus()

    def ask_input_focus(self):
        """
        Propage un evt de demande de focus.
        """
        evt = pygame.event.Event(
            CustomEventManager.CE_ASK_INPUT_FOCUS, {"control": self}
        )
        self.fire_event(evt)


class CustomBaseButton(CustomBaseControl):
    """
    Implémentation basique d'un bouton.
    """

    # Etats
    UNSELECTED = "UNSELECTED"  #: valeur d'état
    OVER = "OVER"  #: valeur d'état
    PRESSED = "PRESSED"  #: valeur d'état
    SELECTED = "SELECTED"  #: valeur d'état
    DISABLED = "DISABLED"  #: valeur d'état
    ENABLED = "ENABLED"  #: valeur d'état
    STATES = [
        UNSELECTED,
        OVER,
        PRESSED,
        SELECTED,
        DISABLED,
    ]  #: valeurs d'état possibles
    # méthodes :
    def __init__(self, switch=False, shortcutkey=None, **kwargs):
        """
        Constructeur
        
        Args:
            switch : False = bouton simple, True = bouton sélectionnable/désélectionnable
            shortcutkey : code de touche optionnel équivalent à un clic        
        """
        # paramétrage :
        evtdict = {
            "evttypes": [
                CustomEventManager.MOUSE_OVER,
                CustomEventManager.MOUSE_OUT,
                CustomEventManager.MOUSE_CLIC,
            ]
        }
        self._shortcutkey = shortcutkey
        if shortcutkey != None:
            evtdict["evttypes"].append(CustomEventManager.KEY_PRESSED)
            evtdict["evttypes"].append(CustomEventManager.KEY_RELEASED)
        # générique
        CustomBaseControl.__init__(self, evtdict, **kwargs)
        # spécifique :
        self._is_switch = switch
        self._current_state = CustomBaseButton.UNSELECTED
        self._view_state = None
        self._enabled = True

    def is_switch(self):
        """
        Indique si le bouton se comporte comme un switch.
        """
        return self._is_switch

    def get_state(self):
        """
        Retourne l'état du bouton.
        """
        return self._current_state

    def set_state(self, state):
        """
        Modifie l'état du bouton.
        """
        if state in [CustomBaseButton.ENABLED, CustomBaseButton.DISABLED]:
            self._handle_activation(state == CustomBaseButton.ENABLED)
            if state == CustomBaseButton.ENABLED:
                state = CustomBaseButton.UNSELECTED
        self._current_state = state
        self._show_state(self._current_state)

    def _handle_activation(self, enable):
        """
        Modifie l'état d'activation.
        """
        if enable != self._enabled:
            self._enabled = enable

    def _show_state(self, state):
        """
        Modifie l'apparence du bouton.
        """
        if state != self._view_state:
            self._view_state = state
            self.change_view_state(state)

    def change_view_state(self, state):
        """
        Modifie physiquement l'apparence du bouton.
        """
        # à subclasser
        pass

    def on_enable_changed(self):
        """
        Appelée lorsque self.enabled a été modifié.
        """
        if not self.enabled:
            self.set_state(CustomBaseButton.DISABLED)
        else:
            self.set_state(CustomBaseButton.ENABLED)

    def handle_mouse_event(self, customeventtype, event):
        """
        Appelée par le manager d'événements
        
        Args:
            customeventtype : CustomEventManager.MOUSE_CLIC, CustomEventManager.MOUSE_OVER, 
                CustomEventManager.MOUSE_OUT
            event : pygame.MOUSEBUTTONDOWN ou pygame.MOUSEMOTION        
        """
        st = None
        if customeventtype == CustomEventManager.MOUSE_OVER:
            st = CustomBaseButton.OVER
        elif customeventtype == CustomEventManager.MOUSE_OUT:
            st = self._current_state
        elif customeventtype == CustomEventManager.MOUSE_CLIC:
            st = CustomBaseButton.PRESSED
        if st != None and st != self._view_state:
            self._show_state(st)
            self.send_callback(st)

    def send_callback(self, state):
        """
        Méthode destinée à transmettre l'état au manager de ce contrôle.
        """
        # à subclasser
        pass

    def handle_key_event(self, customeventtype, event):
        """
        Appelée par le manager d'événements.
        
        Args:
            customeventtype : CustomEventManager.KEY_PRESSED ou CustomEventManager.KEY_RELEASED
            event : pygame.KEYDOWN ou pygame.KEYUP        
        """
        st = None
        if event.key == self._shortcutkey:
            if customeventtype == CustomEventManager.KEY_PRESSED:
                st = CustomBaseButton.PRESSED
            elif customeventtype == CustomEventManager.KEY_RELEASED:
                st = self._current_state
            if st != None:
                self._show_state(st)
                self.send_callback(st)
