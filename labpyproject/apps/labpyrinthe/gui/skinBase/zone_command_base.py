#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Commandes du jeu : logique applicative.
Implémentation générique de AbstractZoneCommand.
"""
# imports
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import LabHelper
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractZoneCommand
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractSwitch

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ZoneCommandBase"]
# classes
class ZoneCommandBase(AbstractZoneCommand):
    """
    Conteneur des commandes de jeu
    """

    # états de l'interface :
    STATE_MENU = "STATE_MENU" #: marqueur d'état
    STATE_GAME = "STATE_GAME" #: marqueur d'état
    # méthodes :
    def __init__(self, Mngr, skin):
        """
        Constructeur
        """
        # Manager : GUI
        self.Mngr = Mngr
        # ref au skin :
        self.skin = skin
        # type d'app :
        self.type_app = None
        # couleurs :
        self._init_colors()
        # caractéristiques du joueur :
        self._player_power = {
            "updated": False,
            "vitesse": None,
            "has_grenade": False,
            "portee_grenade": None,
            "puissance_grenade": None,
            "has_mine": False,
            "puissance_mine": None,
        }
        # variables :
        self.last_message = ""
        self._input_txt = None
        self._info_txt = None
        # état
        self.current_state = None
        # Création de l'interface
        self.ctrlsdict = None  # dict des boutons organisés par famille
        self.btnsdict = None  # dict de tous les boutons
        self.choiceentry = None  # input texte
        self.btn_valide = None  # bouton de validation de commande
        self.draw_interface()
        # Enregistrement des contrôles
        self.current_cmd = None
        self._register_controls()
        # Initialisations des commandes
        self._init_commandes()
        self._init_input()
        # Etat initial :
        self.set_state(ZoneCommandBase.STATE_MENU)

    def _init_colors(self):
        """
        Couleurs portées par le skin :
        """
        # textes
        self.color_titre = self.skin.get_color("nav", "titre")
        self.color_texte = self.skin.get_color("nav", "texte")
        self.color_info = self.skin.get_color("nav", "info")
        # fonds
        self.color_bg_action = self.skin.get_color("nav", "bg_action")
        self.color_bg_direct = self.skin.get_color("nav", "bg_direct")
        self.color_bg_param = self.skin.get_color("nav", "bg_param")
        self.color_bg_valid = self.skin.get_color("nav", "bg_valid")
        self.color_bg_input = self.skin.get_color("nav", "bg_input")

    def re_initialise(self):
        """
        Ré initialise l'objet
        """
        self._init_commandes()

    def register_APPType(self, app_type):
        """
        Défini le type d'appli associé.
        """
        self.type_app = app_type

    #-----> Publication, initialisations
    def draw_interface(self):
        """
        Création de l'interface
        """
        # à subclasser

    def _register_controls(self):
        """
        Identifie les contrôles après création de l'interface
        """
        self.ctrlsdict = dict()
        # Actions :
        self.ctrlsdict["actions"] = dict()
        self.ctrlsdict["actions"][self.btnsdict["move"]] = {
            "action": LabHelper.ACTION_MOVE,
            "code": "",
        }
        self.ctrlsdict["actions"][self.btnsdict["porte"]] = {
            "action": LabHelper.ACTION_CREATE_DOOR,
            "code": LabHelper.CHAR_PORTE,
        }
        self.ctrlsdict["actions"][self.btnsdict["mur"]] = {
            "action": LabHelper.ACTION_CREATE_WALL,
            "code": LabHelper.CHAR_MUR,
        }
        self.ctrlsdict["actions"][self.btnsdict["kill"]] = {
            "action": LabHelper.ACTION_KILL,
            "code": LabHelper.CHAR_KILL,
        }
        self.ctrlsdict["actions"][self.btnsdict["grenade"]] = {
            "action": LabHelper.ACTION_GRENADE,
            "code": LabHelper.CHAR_GRENADE,
        }
        self.ctrlsdict["actions"][self.btnsdict["mine"]] = {
            "action": LabHelper.ACTION_MINE,
            "code": LabHelper.CHAR_MINE,
        }
        # Directions :
        self.ctrlsdict["directions"] = dict()
        self.ctrlsdict["directions"][self.btnsdict["top"]] = {
            "code": LabHelper.CHAR_TOP
        }
        self.ctrlsdict["directions"][self.btnsdict["left"]] = {
            "code": LabHelper.CHAR_LEFT
        }
        self.ctrlsdict["directions"][self.btnsdict["right"]] = {
            "code": LabHelper.CHAR_RIGHT
        }
        self.ctrlsdict["directions"][self.btnsdict["bottom"]] = {
            "code": LabHelper.CHAR_BOTTOM
        }
        # Distances :
        self.ctrlsdict["distances"] = dict()
        self.ctrlsdict["distances"][self.btnsdict["d_1"]] = {"code": 1}
        self.ctrlsdict["distances"][self.btnsdict["d_2"]] = {"code": 2}
        self.ctrlsdict["distances"][self.btnsdict["d_3"]] = {"code": 3}
        self.ctrlsdict["distances"][self.btnsdict["d_4"]] = {"code": 4}
        self.ctrlsdict["distances"][self.btnsdict["d_5"]] = {"code": 5}
        self.ctrlsdict["distances"][self.btnsdict["d_6"]] = {"code": 6}
        # Puissances :
        self.ctrlsdict["puissances"] = dict()
        self.ctrlsdict["puissances"][self.btnsdict["p_1"]] = {"code": 1}
        self.ctrlsdict["puissances"][self.btnsdict["p_5"]] = {"code": 5}
        self.ctrlsdict["puissances"][self.btnsdict["p_9"]] = {"code": 9}
        self.ctrlsdict["puissances"][self.btnsdict["p_13"]] = {"code": 13}
        self.ctrlsdict["puissances"][self.btnsdict["p_17"]] = {"code": 17}
        self.ctrlsdict["puissances"][self.btnsdict["p_25"]] = {"code": 25}
        # Bouton valider :
        self.btn_valide = self.btnsdict["valider"]
        # Input cmd :
        self.ctrlsdict["input"] = self.choiceentry
        # Commande en cours :
        self.current_cmd = {
            "cmd": None,
            "action": None,
            "direction": None,
            "distance": None,
            "puissance": None,
            "cmd2send": None,
        }

    def _init_commandes(self):
        """
        Initialise les contrôles
        """
        # désactive les boutons :
        self.unactive_commande()

    def _init_input(self):
        """
        Bind initial de l'input
        """
        # initialise l'input :
        self.choiceentry.register_callback(self._on_entry_entered)
        self.choiceentry.take_focus()

    def post_init_controls(self):
        """
        Appelée si le LabHelper a été surchargé
        """
        # Actions :
        self.ctrlsdict["actions"][self.btnsdict["move"]]["code"] = ""
        self.ctrlsdict["actions"][self.btnsdict["porte"]]["code"] = LabHelper.CHAR_PORTE
        self.ctrlsdict["actions"][self.btnsdict["mur"]]["code"] = LabHelper.CHAR_MUR
        self.ctrlsdict["actions"][self.btnsdict["kill"]]["code"] = LabHelper.CHAR_KILL
        self.ctrlsdict["actions"][self.btnsdict["grenade"]][
            "code"
        ] = LabHelper.CHAR_GRENADE
        self.ctrlsdict["actions"][self.btnsdict["mine"]]["code"] = LabHelper.CHAR_MINE
        # Directions :
        self.ctrlsdict["directions"][self.btnsdict["top"]]["code"] = LabHelper.CHAR_TOP
        self.ctrlsdict["directions"][self.btnsdict["left"]][
            "code"
        ] = LabHelper.CHAR_LEFT
        self.ctrlsdict["directions"][self.btnsdict["right"]][
            "code"
        ] = LabHelper.CHAR_RIGHT
        self.ctrlsdict["directions"][self.btnsdict["bottom"]][
            "code"
        ] = LabHelper.CHAR_BOTTOM

    #-----> Messages d'info :
    def show_message(self, msg, is_input):
        """
        Affichage d'un message dans la zone info
        """
        if is_input:
            self._input_txt = msg
        else:
            self._info_txt = msg
        pub_txt = ""
        if self._info_txt not in ["", None]:
            pub_txt = self._info_txt
        if self._input_txt not in ["", None]:
            if self._info_txt not in ["", None]:
                pub_txt += "\n"
            pub_txt += self._input_txt
        self.last_message = pub_txt
        self.publish_message(pub_txt)

    def publish_message(self, msg):
        """
        Affichage d'un message dans la zone info
        """
        # à subclasser

    def _handle_txt_rollover(self, msg):
        """
        Gestion des textes de rollover (temporaires)
        """
        if msg == None:
            self.publish_message(self.last_message)
        else:
            self.publish_message(msg)

    #-----> Etats
    def set_state(self, state):
        """
        Changement d'état de la barre de commande
        
        Args:
            state: ZoneCommandBase.STATE_MENU ou ZoneCommandBase.STATE_GAME
        
        """
        if state != self.current_state:
            self.current_state = state
            self.apply_current_state()

    def apply_current_state(self):
        """
        Applique l'état courant
        """
        # à subclasser

    def handle_change_states(self, changelist, newstate):
        """
        Applique le changement d'état à la liste
        """
        for elt in changelist:
            if isinstance(elt, AbstractSwitch):
                elt.set_state(newstate)
            elif isinstance(elt, str):
                d = self.ctrlsdict[elt]
                for c in d.keys():
                    c.set_state(newstate)

    #-----> Commandes
    def active_commande(self):
        """
        Activation des commandes de jeu
        """
        # désactivation :
        self.unactive_commande()
        # activation commande et direction :
        activelist = ["actions", "directions"]
        self.handle_change_states(activelist, AbstractSwitch.ENABLED)

    def unactive_commande(self):
        """
        Désctivation des commandes de jeu
        """
        # désactive les boutons :
        desactivelist = [
            "actions",
            "directions",
            "distances",
            "puissances",
            self.btn_valide,
        ]
        self.handle_change_states(desactivelist, AbstractSwitch.DISABLED)

    def global_control_callback(self, ctrl, state):
        """
        Prend en charge les contrôles globaux, retourne un boolean
        indiquant si ctrl est un contrôle global.
        """
        isglobal = False
        # contrôles globaux (avec roll over)
        if ctrl in [self.btnsdict["menu"], self.btnsdict["quitter"]]:
            isglobal = True
            # txt d'info en rollover :
            txtover = None
            if state == AbstractSwitch.OVER:
                if ctrl == self.btnsdict["menu"]:
                    txtover = "Retour au menu (en quitant la partie en cours)."
                else:
                    txtover = "Quitter le jeu."
            self._handle_txt_rollover(txtover)
            # action transmise à la GUI :
            if state == AbstractSwitch.PRESSED:
                if ctrl == self.btnsdict["menu"]:
                    self.Mngr.ask_goto_menu()
                else:
                    self.Mngr.ask_quit_game()
        return isglobal

    def control_callback(self, ctrl, state):
        """
        Méthode appelée par les contrôles
        
        state :
        
        * AbstractSwitch.OVER
        * AbstractSwitch.PRESSED
        * AbstractSwitch.SELECTED
        * AbstractSwitch.UNSELECTED
        
        """
        if not isinstance(ctrl, AbstractSwitch):
            return
        # contrôles globaux (avec roll over) ?
        if self.global_control_callback(ctrl, state):
            # ne concerne pas les commandes de jeu
            return
        # contrôles de cmd (sans rollover)
        if state != AbstractSwitch.PRESSED:
            return
        prevstate = ctrl.get_state()
        # vars :
        cmd = None
        if self.current_cmd != None and "cmd" in self.current_cmd.keys():
            cmd = self.current_cmd["cmd"]
        deslectlist = list()
        selectlist = list()
        desactivelist = list()
        activelist = list()
        # Actions :
        if ctrl in self.ctrlsdict["actions"].keys():
            cmd = self.ctrlsdict["actions"][ctrl]["action"]
            code = self.ctrlsdict["actions"][ctrl]["code"]
            desactivelist.append("distances")
            desactivelist.append("puissances")
            if prevstate == AbstractSwitch.UNSELECTED:
                self.current_cmd["cmd"] = cmd
                self.current_cmd["action"] = code
                selectlist.append(ctrl)
                if cmd in [LabHelper.ACTION_GRENADE, LabHelper.ACTION_MINE]:
                    act, unact = self._filter_active_ctrl_for_command(cmd, "puissances")
                    activelist += act
                    desactivelist += unact
                else:
                    desactivelist.append("puissances")
                if cmd in [LabHelper.ACTION_MOVE, LabHelper.ACTION_GRENADE]:
                    act, unact = self._filter_active_ctrl_for_command(cmd, "distances")
                    activelist += act
                    desactivelist += unact
                    if (
                        cmd == LabHelper.ACTION_MOVE
                        and self.current_cmd["distance"] == None
                    ):
                        # par défaut on active d=1 :
                        selectlist.append(self.btnsdict["d_1"])
                        self.current_cmd["distance"] = 1
                else:
                    desactivelist.append("distances")
            elif prevstate == AbstractSwitch.SELECTED:
                self.current_cmd = {
                    "cmd": None,
                    "action": None,
                    "direction": None,
                    "distance": None,
                    "puissance": None,
                    "cmd2send": None,
                }
            deslectlist.append("actions")
            deslectlist.append("distances")
            deslectlist.append("puissances")
        # Direction :
        if ctrl in self.ctrlsdict["directions"].keys():
            code = self.ctrlsdict["directions"][ctrl]["code"]
            if prevstate == AbstractSwitch.UNSELECTED:
                self.current_cmd["direction"] = code
                selectlist.append(ctrl)
            elif prevstate == AbstractSwitch.SELECTED:
                self.current_cmd["direction"] = None
            deslectlist.append("directions")
        # Distance :
        if ctrl in self.ctrlsdict["distances"].keys():
            code = self.ctrlsdict["distances"][ctrl]["code"]
            if prevstate == AbstractSwitch.UNSELECTED:
                self.current_cmd["distance"] = code
                selectlist.append(ctrl)
            elif prevstate == AbstractSwitch.SELECTED:
                self.current_cmd["distance"] = None
            act, unact = self._filter_active_ctrl_for_command(cmd, "distances")
            desactivelist += unact
            desel = [c for c in act if c not in selectlist]
            deslectlist += desel
        # Puissance :
        if ctrl in self.ctrlsdict["puissances"].keys():
            code = self.ctrlsdict["puissances"][ctrl]["code"]
            if prevstate == AbstractSwitch.UNSELECTED:
                self.current_cmd["puissance"] = code
                selectlist.append(ctrl)
            elif prevstate == AbstractSwitch.SELECTED:
                self.current_cmd["puissance"] = None
            act, unact = self._filter_active_ctrl_for_command(cmd, "puissances")
            desactivelist += unact
            desel = [c for c in act if c not in selectlist]
            deslectlist += desel
        # Activation du bouton valider :
        if self._check_cmd_completion():
            activelist.append(self.btn_valide)
        else:
            desactivelist.append(self.btn_valide)
        # Gestion des états :
        self.handle_change_states(deslectlist, AbstractSwitch.UNSELECTED)
        self.handle_change_states(desactivelist, AbstractSwitch.DISABLED)
        self.handle_change_states(activelist, AbstractSwitch.ENABLED)
        self.handle_change_states(selectlist, AbstractSwitch.SELECTED)
        # Validation :
        if ctrl == self.btn_valide:
            self._send_command()
        # post traitement :
        self.post_control_callback()

    def post_control_callback(self):
        """
        Post traitement éventuel après gestion des callbacks de boutons
        """
        # à subclasser

    def _on_entry_entered(self, event):
        """
        Méthode de validation de l'input
        """
        self.current_cmd["cmd2send"] = self.choiceentry.get_input_value()
        self._send_command()
        self.choiceentry.set_input_value("")

    def _send_command(self):
        """
        Méthode de transmission de commande à la GUI
        """
        cmd = self.current_cmd["cmd2send"]
        self.Mngr.on_choice_made(cmd)
        self._command_sended()

    def _command_sended(self):
        """
        Ré initialise l'interface
        """
        # données :
        self.current_cmd = {
            "cmd": None,
            "action": None,
            "direction": None,
            "distance": None,
            "puissance": None,
            "cmd2send": None,
        }
        # contrôles :
        deslectlist = ["actions", "directions"]
        self.handle_change_states(deslectlist, AbstractSwitch.UNSELECTED)
        desactivelist = ["distances", "puissances", self.btn_valide]
        self.handle_change_states(desactivelist, AbstractSwitch.DISABLED)

    def _check_cmd_completion(self):
        """
        Examine si la commande peut être validée
        """
        complete = False
        cmd = self.current_cmd["cmd"]
        action = self.current_cmd["action"]
        direction = self.current_cmd["direction"]
        distance = self.current_cmd["distance"]
        puissance = self.current_cmd["puissance"]
        if cmd == LabHelper.ACTION_MOVE:
            if direction != None and distance != None:
                complete = True
        elif cmd in [
            LabHelper.ACTION_CREATE_DOOR,
            LabHelper.ACTION_CREATE_WALL,
            LabHelper.ACTION_KILL,
        ]:
            if direction != None:
                complete = True
        elif cmd == LabHelper.ACTION_GRENADE:
            if direction != None and distance != None and puissance != None:
                complete = True
        elif cmd == LabHelper.ACTION_MINE:
            if direction != None and puissance != None:
                complete = True
        # Chaine de cmd :
        if complete:
            cmd2send = action + direction
            if distance != None:
                cmd2send += str(distance)
            if cmd == LabHelper.ACTION_GRENADE:
                cmd2send += "-"
            if puissance != None:
                cmd2send += str(puissance)
            self.current_cmd["cmd2send"] = cmd2send
        else:
            self.current_cmd["cmd2send"] = None
        return complete

    def _filter_active_ctrl_for_command(self, cmd, ctrltype):
        """
        Filtre les contrôles à activer en fonction des caractéristiques du joueur
        """
        pp = self._player_power
        act_list = list()
        unact_list = list()
        if pp["updated"]:
            kprefix = ""
            indicemax = 0
            absmax = 25
            k = None
            if ctrltype == "distances":
                kprefix = "d_"
                if cmd == LabHelper.ACTION_MOVE:
                    indicemax = int(self._player_power["vitesse"])
                elif cmd == LabHelper.ACTION_GRENADE:
                    if self._player_power["has_grenade"]:
                        indicemax = int(self._player_power["portee_grenade"])
            if ctrltype == "puissances":
                kprefix = "p_"
                if cmd == LabHelper.ACTION_GRENADE:
                    if self._player_power["has_grenade"]:
                        indicemax = int(self._player_power["puissance_grenade"])
                elif cmd == LabHelper.ACTION_MINE:
                    if self._player_power["has_mine"]:
                        indicemax = int(self._player_power["puissance_mine"])
            i = 1
            while i <= absmax:
                k = kprefix + str(i)
                if k in self.btnsdict.keys():
                    ctrl = self.btnsdict[k]
                    if i <= indicemax:
                        act_list.append(ctrl)
                    else:
                        unact_list.append(ctrl)
                i += 1
            return act_list, unact_list
        else:
            return self.ctrlsdict[ctrltype], []

    #-----> Caractérisitiques des joueurs
    def update_player_power(self, robotdict):
        """
        Mise à jour des caractéristiques du joueur
        """
        d = self._player_power
        d["vitesse"] = robotdict["vitesse"]
        d["has_grenade"] = robotdict["has_grenade"]
        d["portee_grenade"] = robotdict["portee_grenade"]
        d["puissance_grenade"] = robotdict["puissance_grenade"]
        d["has_mine"] = robotdict["has_mine"]
        d["puissance_mine"] = robotdict["puissance_mine"]
        d["updated"] = True
