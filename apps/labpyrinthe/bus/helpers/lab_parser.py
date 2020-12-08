#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabParser: parse et exporte les données du labyrinthe
"""
# imports :
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import LabHelper
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import LabLevel
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import Case
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseRobot
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseDanger
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseGrenade
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseBonus
from labpyproject.apps.labpyrinthe.bus.commands.cmd_helper import CommandHelper

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["LabParser"]
# classes :
class LabParser:
    """
    **Parseur de Labyrinthes**
    """

    def __init__(self):
        """
        Constructeur
        """
        # initialisations :
        self.re_initialise()

    def re_initialise(self):
        """
        Ré initialisation avant une nouvelle partie
        """
        # Niveau (couches de matrices) :
        self._lablevel = None
        # Liste des cases associées aux robots
        self._liste_robots = None

    #-----> A- Parsing
    def parse_labyrinthe(self, kwargs):
        """
        Génération d'un LabLevel à partir d'une carte texte et des dicts de cases
        robot, danger, bonus.
        Parsing initial.
        """
        # initialisation :
        self._lablevel = LabLevel()
        # parsing de la carte de base :
        cartetxt = kwargs["cartetxt"]
        if type(cartetxt) is str:
            cartetxt = cartetxt.split("\n")
        self._parse_base_layers(cartetxt)
        # parsing des couches additionnelles :
        self._liste_robots = list()
        self._parse_xtras_layers(kwargs)
        # retour :
        return self._lablevel, self._liste_robots

    def update_bots_or_XTras(self, kwargs):
        """
        Mise à jour des cases robot, bonus ou danger du labyrinthe.
        """
        # parsing avec mise à jour :
        self._parse_xtras_layers(kwargs)
        return self._liste_robots

    def delete_robot(self, robot):
        """
        Supprime un robot de la liste
        """
        if self._liste_robots and robot in self._liste_robots:
            self._liste_robots.remove(robot)

    def _parse_base_layers(self, lignes):
        """
        Parse la carte textuelle et instancie les objets (niveau, matrices et cases).
        
        .. note::
           Origine du repère (0,0) en haut/gauche, x>=0 vers la droite, y>=0 vers le bas
        """
        i = 0  # incrément lignes
        # Création des matrices :
        for ligne in lignes:
            j = 0  # incrément colonnes
            for char in ligne:
                role = LabHelper.get_role_of_char(char)
                face = LabHelper.get_repr_for_role(role)
                if role == LabHelper.CASE_ROBOT:
                    # par défaut, dans la matrice, on remplace le robot par une case vide
                    role = LabHelper.CASE_VIDE
                    face = LabHelper.get_repr_for_role(role)
                case = Case(j, i, role, face)
                self._lablevel.set_case(case)
                j += 1
            i += 1
        # Identification des murs extérieurs :
        flatmatrice = self._lablevel.get_flat_matrice()
        w, h = flatmatrice.get_dimensions()
        cases_mur = self._lablevel.get_typecase_set(LabHelper.CASE_MUR)
        for case in cases_mur:
            xc = case.x
            yc = case.y
            if (xc == 0 or xc == w - 1) or (yc == 0 or yc == h - 1):
                typecase = LabHelper.CASE_MUR_PERIMETRE
                face = LabHelper.get_repr_for_role(LabHelper.CASE_MUR_PERIMETRE)
                newcase = Case(xc, yc, typecase, face)
                self._lablevel.set_case(newcase)

    def _parse_xtras_layers(self, kwargs):
        """
        Traite les couches additionnelles (robot, bonus, danger) non comprises dans
        la carte txt
        """
        for k in kwargs.keys():
            typecase = self._extract_typecase_from_uid(k)
            if typecase in LabHelper.FAMILLE_EXPORT_DICT:
                strdict = kwargs[k]
                if type(strdict) == dict:
                    objdict = strdict  # déja parsé
                else:
                    objdict = CommandHelper.split_cmd_sequence(strdict)
                case = None
                if typecase == LabHelper.CASE_ROBOT:
                    caserobot = self._get_case_robot_by_uid(objdict["uid"])
                    if caserobot == None:
                        case = CaseRobot(objdict)
                        self._liste_robots.append(case)
                    else:
                        caserobot.update_dyn_props(objdict)
                elif typecase == LabHelper.CASE_BONUS:
                    case = CaseBonus(objdict)
                elif typecase == LabHelper.CASE_DANGER:
                    case = CaseDanger(objdict)
                elif typecase == LabHelper.CASE_GRENADE:
                    case = CaseGrenade(objdict)
                if case != None:
                    self._lablevel.set_case(case)

    def _get_case_robot_by_uid(self, uid):
        """
        Retourne la case robot de self._liste_robots d'uid uid ou None
        """
        if self._liste_robots:
            for c in self._liste_robots:
                if c.uid == uid:
                    return c
        return None

    #-----> B- Exports
    def get_repr_view(self, matrice=None):
        """
        Retourne la représentation texte du labyrinthe pour affichage
        """
        if matrice == None:
            flatmatrice = self._lablevel.get_flat_matrice()
        else:
            flatmatrice = matrice
        if flatmatrice == None or flatmatrice.get_dimensions() == (0, 0):
            return None
        # création du labyrinthe
        hm = flatmatrice.get_dimensions()[1]
        l = list()
        j = 0
        # publication :
        while j < hm:
            chaine = ""
            ligne = flatmatrice.get_line(j)
            for case in ligne:
                chaine = chaine + case.face
            chaine = chaine + "\n"
            l.append(chaine)
            j += 1
        # retour :
        chaine_aff = "\n"
        for lignes in l:
            chaine_aff = chaine_aff + lignes
        return chaine_aff

    def get_parsing_datas(self):
        """
        Retourne un dictionnaire à sérialiser comprenant toutes les données nécessaires 
        au parsing
        """
        # données :
        cartetxt = self.get_txt_view()
        labdicts = self._export_lab_dicts()
        # dictionnaire complet :
        msgdict = dict()
        msgdict["cartetxt"] = cartetxt
        for tc in labdicts.keys():
            count = 0
            listdict = labdicts[tc]
            for d in listdict:
                tmpid = self._create_parsing_uid(tc, count)
                msgdict[tmpid] = d
                count += 1
        # retour :
        return msgdict

    def get_bots_datas(self, full=True):
        """
        Retourne uniquement les données de parsing associées aux bots
        """
        # données
        botsdatas = self._export_lab_dicts(typecase=LabHelper.CASE_ROBOT, full=full)
        # dict de retour :
        msgdict = dict()
        count = 0
        listdict = botsdatas[LabHelper.CASE_ROBOT]
        for d in listdict:
            tmpid = self._create_parsing_uid(LabHelper.CASE_ROBOT, count)
            msgdict[tmpid] = d
            count += 1
        # retour :
        return msgdict

    def get_parsedicts_for_listcases(self, listcase):
        """
        Retourne un dict à parser pour une liste de cases
        """
        # dict de propriétés
        labdicts = dict()
        for c in listcase:
            tc = c.type_case
            if tc not in labdicts.keys():
                labdicts[tc] = list()
            labdicts[tc].append(c.get_properties_dict())
        # dict de retour :
        msgdict = dict()
        for tc in labdicts.keys():
            count = 0
            listdict = labdicts[tc]
            for d in listdict:
                tmpid = self._create_parsing_uid(tc, count)
                msgdict[tmpid] = d
                count += 1
        # retour :
        return msgdict

    def _create_parsing_uid(self, name, i):
        """
        Crée un uid pour une case additionnelle
        """
        return str(name + "_" + str(i))

    def _extract_typecase_from_uid(self, uid):
        """
        Retourne le type de case associé à l'uid
        """
        tc = None
        if "_" in uid:
            splitlist = uid.split("_")
            tc = splitlist[0]
        return tc

    def get_txt_view(self, matrice=None):
        """
        Retourne la représentation texte du labyrinthe (couche de base) pour parsing
        """
        if matrice == None:
            flatmatrice = self._lablevel.get_flat_matrice(full=False)
        else:
            flatmatrice = matrice
        if flatmatrice == None or flatmatrice.get_dimensions() == (0, 0):
            return None
        # création du labyrinthe
        hm = flatmatrice.get_dimensions()[1]
        l = list()
        j = 0
        # publication :
        while j < hm:
            chaine = ""
            ligne = flatmatrice.get_line(j)
            for case in ligne:
                chaine = chaine + LabHelper.get_txt_for_role(case.type_case)
            chaine = chaine + "\n"
            l.append(chaine)
            j += 1
        # retour :
        chaine_aff = ""
        for lignes in l:
            chaine_aff = chaine_aff + lignes
        chaine_aff.strip()
        return chaine_aff

    def _export_lab_dicts(self, typecase=None, full=True):
        """
        Exporte les dict de parsing des cases omises de la vue texte du labyrinthe
        typecase : si spécifié ne renvoit que le dict associé
        """
        labdict = dict()
        famille = None
        if typecase != None:
            famille = [typecase]
        else:
            famille = LabHelper.FAMILLE_EXPORT_DICT
        for tc in famille:
            labdict[tc] = list()
            listcase = self._lablevel.get_typecase_set(tc)
            for c in listcase:
                propdict = c.get_properties_dict(full=full)
                if propdict != None:
                    labdict[tc].append(propdict)
        return labdict
