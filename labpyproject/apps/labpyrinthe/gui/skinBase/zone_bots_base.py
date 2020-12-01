#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Infos bots : logique applicative.
Implémentation générique de AbstractZoneBots.
"""
# imports :
from labpyproject.apps.labpyrinthe.gui.skinBase.interfaces import AbstractZoneBots
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseRobot

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ZoneBotsBase"]
# classes :
class ZoneBotsBase(AbstractZoneBots):
    """
    Zone d'information sur les robots
    """

    def __init__(self, mngr, skin):
        """
        Constructeur
        """
        # Manager : zone_partie
        self.mngr = mngr
        # GUI:
        self.gui_mngr = None
        # type d'app :
        self.type_app = None
        # ref au skin :
        self.skin = skin
        # phase partie :
        self.partie_state = None
        # couleurs :
        self._init_colors()
        # initialisation
        self.uid = None
        self.interface_drawn = False

    def registerGUI(self, gui):
        """
        Enregistre la GUI et le type d'app associé
        """
        self.gui_mngr = gui
        self.register_APPType(gui.type_app)

    def register_APPType(self, app_type):
        """
        Défini le type d'appli associé.
        """
        self.type_app = app_type

    def _init_colors(self):
        """
        Couleurs portées par le skin :
        """
        # textes :
        self.color_txt = self.skin.get_color("bots", "txt")
        # fond bots éliminé :
        self.color_not_alive = self.skin.get_color("bots", "not_alive")

    def re_initialise(self):
        """
        Ré initialise l'objet
        """
        # clear :
        self.clear_bots_list()
        self.interface_drawn = False

    def clear_bots_list(self):
        """
        Efface la liste des bots publiée
        """
        # à subclasser

    def setuid(self, uid):
        """
        Définit l'uid associé au joueur
        """
        self.uid = uid

    def register_partie_state(self, state):
        """
        Enregistre l'état actuel de la partie
        """
        self.partie_state = state
        self.apply_partie_state()

    def apply_partie_state(self):
        """
        Adapte l'interface en fonction de la phase de la partie
        """
        # à subclasser au besoin
        pass

    #-----> Publication
    def draw_interface(self, robotlist):
        """
        Crée l'interface au premier affichage
        """
        # à subclasser

    def publish_robotlist(self, robotlist, gambleinfos):
        """
        Méthode d'affichage publique
        """
        uid = None
        if gambleinfos != None:
            uid = gambleinfos["uid"]
        # Publication initiale :
        if not self.interface_drawn:
            self.draw_interface(robotlist)
            self.interface_drawn = True
        # Mise à jour :
        for case in robotlist:
            img = self.get_robot_image(case)
            txt = self.get_robot_text(case)
            bgcolor = None
            hcolor = "#FFFFFF"
            fgcolor = None
            if uid != None and case.uid == uid:
                hcolor = case.color
            if case.alive == False:
                color = self.color_not_alive
                bgcolor = color
                fgcolor = "#FFFFFF"
            self.update_bot_item(case, txt, img, bgcolor, fgcolor, hcolor)

    def show_bot_dead(self, robot):
        """
        Appelée pour lors de l'élimination de robot.
        """
        # à subclasser

    def update_bot_item(self, case, txt, img, bgcolor, fgcolor, hcolor):
        """
        Met à jour un item de la liste d'infos robots
        """
        # à subclasser

    def get_case_size(self):
        """
        Retourne la taille de l'image du robot
        """
        # à subclasser

    def get_robot_image(self, case):
        """
        Retourne l'image associée au robot
        """
        return self.skin.get_image_for_case(case, self.get_case_size(), applyopt=False)

    def get_txt_legende(self):
        """
        Retourne le texte de légende
        """
        chaine = "Légende :\n"
        puce = "* "
        chaine += puce + "agg. : aggressivité du robot (entre 0 et 1)\n"
        chaine += puce + "i.s. : instinct de survie du robot (entre 0 et 1)\n"
        chaine += puce + "vit. : vitesse du joueur (nombre de coups par tour)\n"
        chaine += puce + "mine : puissance max des mines\n"
        chaine += puce + "gre. : portée grenade max / puissance grenade max\n"
        return chaine

    def get_robot_text(self, case):
        """
        Retourne la chaine de caractère représentant les caractéristiques du robot. 
        A afficher avec une font monospace
        """
        # params :
        entete = ["nom", "agg.", "i.s.", "vit.", "mine", "gre."]
        dims = [12 + 2, 4 + 2, 4 + 2, 4 + 2, 4 + 2, 5 + 2]
        sep = "|"
        # génération :
        chaine = " " + sep
        if case == None:
            # entête formaté :
            i = 0
            for mot in entete:
                chaine += mot.center(dims[i]) + sep
                i += 1
            chaine = chaine[: len(chaine) - 1]
        elif case == "sep":
            # séparateur de lignes :
            w = 1
            for nb in dims:
                w += nb + 1
            chaine = "-" * w
        else:
            # chaine robot :
            nom = self._get_nom_for_robot(case)
            chaine += nom.center(dims[0]) + sep
            chaine += str(case.aggressivite).center(dims[1]) + sep
            survie = self._get_survie_for_robot(case)
            chaine += survie.center(dims[2]) + sep
            chaine += str(case.vitesse).center(dims[3]) + sep
            mine = self._get_mine_for_robot(case)
            chaine += mine.center(dims[4]) + sep
            grenade = self._get_grenade_for_robot(case)
            chaine += grenade.center(dims[5])
        return chaine

    def _get_grenade_for_robot(self, case):
        """
        Formate les données liées aux grenades
        """
        if not case.has_grenade:
            grenade = "-/-"
        else:
            portee = str(case.portee_grenade)
            puissance = str(case.puissance_grenade)
            grenade = portee + "/" + puissance
        return grenade

    def _get_mine_for_robot(self, case):
        """
        Formate les données liées aux mines
        """
        if not case.has_mine:
            mine = "-"
        else:
            mine = str(case.puissance_mine)
        return mine

    def _get_survie_for_robot(self, case):
        """
        Formate l'instint de survie
        """
        if case.human:
            survie = "-"
        else:
            survie = str(case.instinct_survie)
        return survie

    def _get_nom_for_robot(self, case):
        """
        Génère un nom pour un robot
        """
        if case.human:
            nom = "Joueur " + str(case.human_number)
        else:
            if case.behavior == CaseRobot.BEHAVIOR_BUILDER:
                nom = "Maçon " + str(case.number)
            elif case.behavior == CaseRobot.BEHAVIOR_RANDOM:
                nom = "Random " + str(case.number)
            elif case.behavior == CaseRobot.BEHAVIOR_HUNTER:
                nom = "Chasseur " + str(case.number)
            elif case.behavior == CaseRobot.BEHAVIOR_TOURIST:
                nom = "Touriste " + str(case.number)
            elif case.behavior == CaseRobot.BEHAVIOR_WINNER:
                nom = "Winner " + str(case.number)
            elif case.behavior == CaseRobot.BEHAVIOR_SAPPER:
                nom = "Mineur " + str(case.number)
        return nom
