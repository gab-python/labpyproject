#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Données liées aux cibles de coups.

* TargetObject : modélise une cible temporaire
* TargetPath : chemin menant à une cible
* TargetPathStep : étape d'un TargetPath (case)

"""
# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["TargetObject", "TargetPath", "TargetPathStep"]
# classes :
class TargetObject:
    """
    Enregistre les données d'une cible temporaire
    """

    TARGET_MAIN = "TARGET_MAIN"  #: identifie une cible principale
    TARGET_TEMP = "TARGET_TEMP"  #: identifie une cible temporaire

    def __init__(self, typetarget, case, direct=None, axe=None, sens=None, score=0):
        """
        Modélise une cible de parcours
        
        Args:
            typetarget (str): TARGET_MAIN ou TARGET_TEMP
            case (Case): case associée
            direct (str): direction associée
            axe (str): horizontal ou vertical
            sens (int): positif ou négatif
            score (float): score associé à la cible
        """
        self.typetarget = typetarget
        self.case = case
        self.direct = direct
        self.axe = axe
        self.sens = sens
        self.x = case.x
        self.y = case.y
        self.score = score
        # accessibilité de la cible
        self.targetpath = None
        self.pathcost = 0
        # dernière case libre identifiée
        self.last_free_case = None
        # liste des cases associées
        self.listcases = None
        # validité
        self.discarded = False

    def __getitem__(self, prop):
        """
        Rend l'objet "subscriptable"
        """
        return getattr(self, prop)

    def __repr__(self):
        return "TO typetarget={} case={} axe={} sens={} x={} y={} score={} pathcost={}".format(
            self.typetarget,
            self.case,
            self.axe,
            self.sens,
            self.x,
            self.y,
            self.score,
            self.pathcost,
        )


class TargetPath:
    """
    Chemin menant à une cible
    """

    def __init__(self, steplist=None):
        """
        Constructeur
        
        Args:
            steplist : liste d'étapes TargetPathStep
        """
        if steplist == None:
            self._steplist = list()
        else:
            self._steplist = steplist
        self.cost = 0

    def add_pathstep(self, pathstep):
        """
        Ajoute une étape à la liste d'étapes
        """
        self._steplist.append(pathstep)

    def get_last_step(self):
        """
        Retourne l'étape finale ou None
        """
        if len(self._steplist) > 0:
            return self._steplist[-1]
        return None

    def get_steps_list(self):
        """
        Retourne la liste d'étapes
        """
        return self._steplist

    def get_coords_list(self):
        """
        Retourne la liste de coordonnées
        """
        clist = [(tps.x, tps.y) for tps in self._steplist]
        return clist

    def copy(self):
        """
        Retourne une copie de cet objet
        """
        clonelist = list()
        for tps in self._steplist:
            clone = tps.get_clone()
            clonelist.append(clone)
        return TargetPath(clonelist)

    def __repr__(self):
        return "\nTargetPath cost={} steplist={}".format(self.cost, self._steplist)


class TargetPathStep:
    """
    Etape (case) d'un TargetPath
    """

    def __init__(self, case):
        """
        Constructeur
        
        Args:
            case (Case): case associée à l'étape
        """
        self.case = case
        self.x = case.x
        self.y = case.y

    def get_clone(self):
        """
        Retourne la copie de cet objet
        """
        return TargetPathStep(self.case)

    def __repr__(self):
        return "\nTargetPathStep x={} y={} case={}".format(self.x, self.y, self.case)
