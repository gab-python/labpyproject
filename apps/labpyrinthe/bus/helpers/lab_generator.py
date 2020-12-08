#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabGenerator : **générateur de cartes** au format texte, fournissant des services
d'échantillonnage et de mesure de densités sur des matrices.
"""
# imports :
import math
import labpyproject.core.random.custom_random as cr
from labpyproject.apps.labpyrinthe.bus.helpers.game_configuration import (
    GameConfiguration,
)
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import LabHelper
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import Matrice
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import Case

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["LabGenerator"]
# classes :
class LabGenerator:
    """
    Classe statique générant une carte textuelle (à parser ensuite)
    """

    def create_random_carte(
        self, fullrandom=True, width=30, height=20, propvide=0.55, propporte=0.05
    ):
        """
        Crée aléatoirement une carte texte. 
        Retourne une liste de lignes (comme le fait cio.load_text_file)
        """
        # proportions
        if GameConfiguration.is_game_configured():
            prop_vide = GameConfiguration.get_initial_density("vide")
            prop_porte = GameConfiguration.get_initial_density("porte")
            w, h = GameConfiguration.get_carte_dimensions()
        else:
            if fullrandom:
                prop_vide = cr.CustomRandom.randrange(45, 60) / 100
                prop_porte = cr.CustomRandom.randrange(1, 4) / 100
                w = cr.CustomRandom.randrange(25, 35)
                h = cr.CustomRandom.randrange(15, 25)
            else:
                prop_vide = propvide
                prop_porte = propporte
                w = width
                h = height
        # 1- matrice de murs :
        mat = LabGenerator._create_walls(w, h)
        # 2- cases vides : ajout de lignes et colonnes partielles
        LabGenerator._draw_vide_in_matrice(mat)
        innermat = mat.get_submatrice(1, 1, w - 2, h - 2)
        # 3- Ajustement densité :
        # Passe 1
        w1, h1 = math.ceil(w / 2), math.ceil(h / 2)
        listsubmat = LabGenerator.sample_submatrices(innermat, w1, h1, strictmode=False)
        for smat in listsubmat:
            LabGenerator._adjust_densite(smat, 1 - prop_vide)
        # Passe 2
        listsubmat = LabGenerator.sample_submatrices(innermat, 3, 3, strictmode=False)
        for smat in listsubmat:
            LabGenerator._adjust_densite(smat, 1 - prop_vide)
        # 4- portes :
        LabGenerator._add_portes(mat, prop_porte)
        # 5- sortie
        LabGenerator._add_sortie(mat)
        # 6- export txt :
        listlignes = list()
        nli = 1
        while nli <= h:
            ligne = mat.get_line(nli - 1)
            chaine = ""
            for case in ligne:
                chaine = chaine + case.face
            listlignes.append(chaine)
            nli += 1
        return listlignes

    create_random_carte = classmethod(create_random_carte)

    def _create_walls(self, w, h):
        """
        Crée une matrice w*h de murs
        """
        mat = Matrice()
        y = 0
        while y < h:
            x = 0
            while x < w:
                typecase = LabHelper.CASE_MUR
                typeface = LabHelper.get_txt_for_role(typecase)
                case = Case(x, y, typecase, typeface)
                mat.set_case(case)
                x += 1
            y += 1
        return mat

    _create_walls = classmethod(_create_walls)

    def _draw_vide_in_matrice(self, matrice):
        """
        Crée des lignes et colonnes de cases vides
        """
        w, h = matrice.get_dimensions()
        innermat = matrice.get_submatrice(1, 1, w - 2, h - 2)
        wi, hi = w - 2, h - 2
        # lignes
        nl = math.ceil(hi / (cr.CustomRandom.choice(range(14, 25)) / 10))
        nlines = 0
        indlines = cr.CustomRandom.sample(range(0, hi - 1), k=nl)
        oddmark = 1
        while nlines < nl:
            indl = indlines[nlines]
            ligne = innermat.get_line(indl)
            nb2add = min(
                math.ceil(cr.CustomRandom.choice(range(10, 100)) / 100 * wi), wi - 1
            )
            if oddmark // 3 == 0:
                xpt = cr.CustomRandom.choice(range(0, (wi - nb2add + 1)))
            if oddmark // 2 == 0:
                xpt = 0
            else:
                xpt = wi - nb2add + 1
            oddmark += 1
            cases2change = [case for case in ligne if xpt <= case.x <= xpt + nb2add - 1]
            for case in cases2change:
                case.type_case = LabHelper.CASE_VIDE
                case.face = LabHelper.CHAR_TXT_VIDE
            nlines += 1
        # colonnes :
        nc = math.ceil(wi / (cr.CustomRandom.choice(range(14, 25)) / 10))
        ncols = 0
        indcols = cr.CustomRandom.sample(range(0, wi - 1), k=nc)
        oddmark = 1
        while ncols < nc:
            indc = indcols[ncols]
            col = innermat.get_column(indc)
            nb2add = min(
                math.ceil(cr.CustomRandom.choice(range(10, 100)) / 100 * hi), hi - 1
            )
            if oddmark // 3 == 0:
                ypt = cr.CustomRandom.choice(range(0, (hi - nb2add + 1)))
            if oddmark // 2 == 0:
                ypt = 0
            else:
                ypt = hi - nb2add + 1
            oddmark += 1
            cases2change = [case for case in col if ypt <= case.y <= ypt + nb2add - 1]
            for case in cases2change:
                case.type_case = LabHelper.CASE_VIDE
                case.face = LabHelper.CHAR_TXT_VIDE
            ncols += 1

    _draw_vide_in_matrice = classmethod(_draw_vide_in_matrice)

    def sample_submatrices(self, matrice, w=5, h=4, strictmode=True):
        """
        Retourne une liste de sous matrices de taille w*h
        """
        wm, hm = matrice.get_dimensions()
        if wm <= w or hm <= h:
            return [matrice]
        fqx = wm // w
        rx = wm % w
        fqy = hm // h
        ry = hm % h
        rlist = list()
        xr, yr = matrice.get_lefttop_point()
        x = xr
        while x < wm:
            y = yr
            while y < hm:
                ws = w
                hs = h
                if y == yr + fqy * h and ry > 0:
                    hs = ry
                if x == xr + fqx * w and rx > 0:
                    ws = rx
                submat = matrice.get_submatrice(x, y, ws, hs, strictmode=strictmode)
                rlist.append(submat)
                y += hs
            x += ws
        return rlist

    sample_submatrices = classmethod(sample_submatrices)

    def _adjust_densite(self, matrice, proportion):
        """
        Ajuste la densité de cases de type mur dans matrice
        """
        dens = LabGenerator.estime_densite(matrice, [LabHelper.CASE_MUR])
        matlist = matrice.get_list_cases()
        nbc = len(matlist)
        m_add = v_add = 0
        if dens < proportion:
            # on rajoute des murs :
            prop_m = proportion - dens
            n_m = math.ceil(nbc * prop_m)
            l_v = cr.CustomRandom.sample(
                matrice.get_case_by_type(LabHelper.CASE_VIDE), k=n_m
            )
            while m_add < n_m:
                case = l_v[m_add]
                case.type_case = LabHelper.CASE_MUR
                case.face = LabHelper.CHAR_TXT_MUR
                m_add += 1
        else:
            # on rajoute du vide :
            prop_v = dens - proportion
            n_v = math.ceil(nbc * prop_v)
            l_m = cr.CustomRandom.sample(
                matrice.get_case_by_type(LabHelper.CASE_MUR), k=n_v
            )
            while v_add < n_v:
                case = l_m[v_add]
                case.type_case = LabHelper.CASE_VIDE
                case.face = LabHelper.CHAR_TXT_VIDE
                v_add += 1
        dens = LabGenerator.estime_densite(matrice, [LabHelper.CASE_MUR])

    _adjust_densite = classmethod(_adjust_densite)

    def _add_portes(self, matrice, proportion):
        """
        Ajout de portes à la matrice
        """
        w, h = matrice.get_dimensions()
        innermat = matrice.get_submatrice(1, 1, w - 2, h - 2)
        innerlist = innermat.get_list_cases()
        n = len(innerlist)
        np = math.ceil(n * proportion)
        np_done = 0
        cr.CustomRandom.shuffle(innerlist)
        for case in innerlist:
            if case.type_case == LabHelper.CASE_MUR:
                x = case.x
                y = case.y
                casesadj = matrice.get_cases_adjacentes(x, y)
                case_left = casesadj["left"]
                case_right = casesadj["right"]
                case_top = casesadj["top"]
                case_bottom = casesadj["bottom"]
                listfav = [LabHelper.CASE_VIDE]
                if (
                    case_left.type_case == LabHelper.CASE_MUR
                    and case_right.type_case == LabHelper.CASE_MUR
                    and (
                        case_top.type_case in listfav
                        and case_bottom.type_case in listfav
                    )
                ):
                    case.type_case = LabHelper.CASE_PORTE
                    case.face = LabHelper.CHAR_TXT_PORTE
                    np_done += 1
                elif (
                    case_top.type_case == LabHelper.CASE_MUR
                    and case_bottom.type_case == LabHelper.CASE_MUR
                    and (
                        case_left.type_case in listfav
                        and case_right.type_case in listfav
                    )
                ):
                    case.type_case = LabHelper.CASE_PORTE
                    case.face = LabHelper.CHAR_TXT_PORTE
                    np_done += 1
                if np_done == np:
                    break

    _add_portes = classmethod(_add_portes)

    def _add_sortie(self, matrice):
        """
        Ajoute la case sortie
        """
        w, h = matrice.get_dimensions()
        cases_perimetre = list()
        for case in matrice.get_list_cases():
            if (case.x in [1, w - 2] and case.y in (0, h - 1)) or (
                case.y in [1, h - 2] and case.x in (0, w - 1)
            ):
                cases_perimetre.append(case)
        case_sortie = cr.CustomRandom.choice(cases_perimetre)
        case_sortie.type_case = LabHelper.CASE_SORTIE
        case_sortie.face = LabHelper.CHAR_TXT_SORTIE

    _add_sortie = classmethod(_add_sortie)

    #-----> Calcul de densité (méthodes statiques)
    def estime_densite(self, submatrice, listtypescases):
        """
        Calcul de densité de case de types compris dans listtypescases sur une matrice
        """
        casesmesurees = submatrice.get_list_cases()
        w, h = submatrice.get_dimensions()
        occurences = 0
        for case in casesmesurees:
            if case.type_case in listtypescases:
                occurences += 1
        # calcul de densité :
        if w * h > 0:
            densite = occurences / (w * h)
            return densite
        else:
            return 0

    estime_densite = classmethod(estime_densite)

    def estime_densites_for_typecase_on_axis(self, matrice, axe, sens, listtypescases):
        """
        Estime la densité de case de type compris dans listtypescases, ligne à ligne ou colonne 
        à colonne sur :
        
        * la matrice : matrice
        * axe : x ou y
        * sens : + ou -
        
        Retourne si possible LabHelper.DENSITE_LARGEUR mesures sur LabHelper.DENSITE_PROFONDEUR 
        cases de profondeur
        """
        xmin, ymin = matrice.get_lefttop_point()
        w, h = matrice.get_dimensions()
        xmax, ymax = xmin + w - 1, ymin + h - 1
        x_r = y_r = None
        # mesures par lignes ou colonnes :
        dsm = dict()
        if axe == LabHelper.AXIS_X:
            if sens == LabHelper.DIR_POS:
                x_r = xmin
            else:
                x_r = xmax
            w = xmax - xmin + 1
            h = 1
            ly = [y for y in range(ymin, ymax + 1)]
            for y in ly:
                sm = matrice.get_submatrice(xmin, y, w, h)
                dsm[(x_r, y)] = LabGenerator.estime_densite(sm, listtypescases)
        else:
            if sens == LabHelper.DIR_POS:
                y_r = ymin
            else:
                y_r = ymax
            w = 1
            h = ymax - ymin + 1
            lx = [x for x in range(xmin, xmax + 1)]
            for x in lx:
                sm = matrice.get_submatrice(x, ymin, w, h)
                dsm[(x, y_r)] = LabGenerator.estime_densite(sm, listtypescases)
        dsm["sample_size"] = max(w, h)
        return dsm

    estime_densites_for_typecase_on_axis = classmethod(
        estime_densites_for_typecase_on_axis
    )

    #-----> Dénombrement de cases
    def compute_case_number(self, submatrice, listtypescases):
        """
        Calcul du nombre de cases de types compris dans listtypescases sur une matrice
        """
        casesmesurees = submatrice.get_list_cases()
        occurences = 0
        for case in casesmesurees:
            if case.type_case in listtypescases:
                occurences += 1
        return occurences

    compute_case_number = classmethod(compute_case_number)

    def compute_case_number_for_typecase_on_axis(
        self, matrice, axe, sens, listtypescases
    ):
        """
        Calcul du nombre de cases de type compris dans listtypescases, ligne à ligne ou 
        colonne à colonne sur :
        
        * la matrice : matrice
        * axe : x ou y
        * sens : + ou -
        
        Retourne si possible LabHelper.DENSITE_LARGEUR mesures sur LabHelper.DENSITE_PROFONDEUR 
        cases de profondeur
        """
        xmin, ymin = matrice.get_lefttop_point()
        w, h = matrice.get_dimensions()
        xmax, ymax = xmin + w - 1, ymin + h - 1
        x_r = y_r = None
        # mesures par lignes ou colonnes :
        dsm = dict()
        if axe == LabHelper.AXIS_X:
            if sens == LabHelper.DIR_POS:
                x_r = xmin
            else:
                x_r = xmax
            w = xmax - xmin + 1
            h = 1
            ly = [y for y in range(ymin, ymax + 1)]
            for y in ly:
                sm = matrice.get_submatrice(xmin, y, w, h)
                dsm[(x_r, y)] = LabGenerator.compute_case_number(sm, listtypescases)
        else:
            if sens == LabHelper.DIR_POS:
                y_r = ymin
            else:
                y_r = ymax
            w = 1
            h = ymax - ymin + 1
            lx = [x for x in range(xmin, xmax + 1)]
            for x in lx:
                sm = matrice.get_submatrice(x, ymin, w, h)
                dsm[(x, y_r)] = LabGenerator.compute_case_number(sm, listtypescases)
        dsm["sample_size"] = max(w, h)
        return dsm

    compute_case_number_for_typecase_on_axis = classmethod(
        compute_case_number_for_typecase_on_axis
    )
