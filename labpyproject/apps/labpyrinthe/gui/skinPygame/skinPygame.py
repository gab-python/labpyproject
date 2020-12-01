#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Implémentation Pygame de SkinBase.
"""
# imports :
import math, cmath
import os, sys
import PIL.Image
import pygame.freetype
from labpyproject.apps.labpyrinthe.gui.skinBase.colors import ColorHelper
from labpyproject.apps.labpyrinthe.gui.skinBase.skin_base import SkinBase
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseRobot

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["SkinPygame"]
# classe :
class SkinPygame(SkinBase):
    """
    Implémentation Pygame de SkinBase
    """

    # statique :
    # mode de resize par défaut des images (scale ou skin, voir uitools.WImage)
    SCALE_RESIZEMODE = "SCALE_RESIZEMODE"  #: scaling surface
    SKIN_RESIZEMODE = "SKIN_RESIZEMODE"  #: recalcul PIL + cache skin
    DEFAULT_RESIZEMODE = SCALE_RESIZEMODE  #: mode resize par défaut
    # types et couleurs zones dangers
    DGR_FACTOR_COLOR = {
        0: "#99CC00",
        1: "#FFCC00",
        2: "#3399FF",
        3: "#FF00FF",
        4: "#9900CC",
    } #: couleurs associées aux niveaux de dangerosité
    DGR_FACTOR_ALPHA = 80  #: alpha valeur pygame (80 / 255 * 100) en %
    # méthodes :
    def __init__(self, optmode=False, frozen=False):
        """
        Constructeur
        """
        # générique :
        SkinBase.__init__(self, optmode=optmode, carte_resolution="80", frozen=frozen)
        # spécifique :
        self._init_fonts()

    #-----> Conversion à subclasser
    def export_image_from_PIL(self, src):
        """
        Convertit une source PIL.Image dans le format attendu par
        le moteur graphique.
        """
        # spécifique
        mode = src.mode
        size = src.size
        data = src.tobytes()
        # plus rapide que pygame.image.fromstring
        surf = pygame.image.frombuffer(data, size, mode)
        return surf

    def convert_surface_for_PIL(self, surf):
        """
        Réciproque, convertit une surface Pygame en image PIL
        """
        bufferstr = pygame.image.tostring(surf, "RGBA")
        size = surf.get_size()
        pilimg = PIL.Image.frombytes("RGBA", size, bufferstr)
        return pilimg

    #-----> Outil couleur
    def color_surface(self, surf, newcolor):
        """
        Copie la surface en la colorisant avec newcolor. 
        Rq : seule la part RGB de newcolor est prise en compte
        
        From : https://gamedev.stackexchange.com/questions/26550/how-can-a-pygame-image-be-colored
        """
        rsurf = surf.copy()
        # élimine les précédentes valeurs RGB en conservant A
        rsurf.fill((0, 0, 0, 255), None, pygame.BLEND_RGBA_MULT)
        # affecte les nouvelles valeurs RGB
        rsurf.fill(newcolor[0:3] + (0,), None, pygame.BLEND_RGBA_ADD)
        return rsurf

    #-----> Initialisations des ressources :
    def init_rsc(self):
        """
        Initialisation des images :
        """
        # générique :
        SkinBase.init_rsc(self)
        # rsc zone_bots :
        self._init_zonebots_rsc()
        # rsc zones dangers
        self._init_zones_dangers()
        # graphes radars
        self._init_features_radars()

    def _init_zonebots_rsc(self):
        """
        Ressources supplémentaires pour la zone_bots
        """
        self._srcdict["zonebots"] = dict()
        d = self._srcdict["zonebots"]
        if self.frozen:
            path = (
                self.gamepath
                + "/labpyproject/apps/labpyrinthe/gui/skinPygame/rsc/zonebots/"
            )
        else:
            path = self.gamepath + "/gui/skinPygame/rsc/zonebots/"
        d["high_bot"] = {"src": PIL.Image.open(path + "fond_high_bot.png")}
        d["mark_dead"] = {"src": PIL.Image.open(path + "eclair.png")}
        d["mark_dead_alt"] = {"src": PIL.Image.open(path + "marque_dead.png")}
        d["mark_deconnect"] = {"src": PIL.Image.open(path + "deconnected.png")}
        d["radar_txt"] = {"src": PIL.Image.open(path + "radar.png")}
        d["picto_vitesse"] = {"src": PIL.Image.open(path + "picto_vitesse.png")}
        d["picto_grenade"] = {"src": PIL.Image.open(path + "picto_grenade.png")}
        d["picto_mine"] = {"src": PIL.Image.open(path + "picto_mine.png")}
        d["picto_croix"] = {"src": PIL.Image.open(path + "picto_croix.png")}

    def _init_command_colors(self):
        """
        Initialisation des couleurs (surcharge) : commandes
        """
        d = self._coldict["nav"]
        # dict des boutons de commandes
        d["btns_cmd"] = dict()
        d["btns_cmd"]["1"] = {"bgcolor": None, "bdcolor": "#330000"}
        d["btns_cmd"]["2"] = {"bgcolor": "#FFCC00", "bdcolor": "#330000"}
        d["btns_cmd"]["3"] = {"bgcolor": "#9900CC", "bdcolor": "#330000"}
        d["btns_cmd"]["4"] = {"bgcolor": "#FF33FF", "bdcolor": "#330000"}
        d["btns_cmd"]["5"] = {"bgcolor": None, "bdcolor": "#FFFFFF"}
        # dict des boutons globaux
        d["btns_glb"] = dict()
        d["btns_glb"]["1"] = {"bgcolor": "#CC3366", "bdcolor": None}
        d["btns_glb"]["2"] = {"bgcolor": "#FFCC00", "bdcolor": None}
        d["btns_glb"]["3"] = {"bgcolor": None, "bdcolor": "#FF9900"}
        d["btns_glb"]["4"] = {"bgcolor": None, "bdcolor": "#FFCC00"}
        d["btns_glb"]["5"] = {"bgcolor": "#8C9557", "bdcolor": None}
        # autre style :
        d["btns_alt"] = dict()
        d["btns_alt"]["1"] = {"bgcolor": None, "bdcolor": "#330000"}
        d["btns_alt"]["2"] = {"bgcolor": None, "bdcolor": "#FF33FF"}
        d["btns_alt"]["3"] = {"bgcolor": None, "bdcolor": "#9900CC"}
        d["btns_alt"]["4"] = {"bgcolor": None, "bdcolor": "#BEAEAE"}
        d["btns_alt"]["5"] = {"bgcolor": "#BEAEAE", "bdcolor": None}
        # textes :
        d["texte"] = "#330000"
        d["texte_dis"] = "#FFFFFF"
        d["texte_info"] = "#CCFF00"
        # couleurs de fonds :
        d["bg_command"] = "#8C9557"  # "#BEAEAE"
        d["bg_info"] = "#330000"
        d["bg_input"] = "#CCFF00"

    def _init_command_imgs(self):
        """
        Images fixes (surcharge) : commandes
        """
        d = self._srcdict["nav"]
        path = self.nav_path
        # définition des sources :
        self.liststaticnames = [
            "distance_2",
            "puissance_2",
            "silhouette",
            "silhouette0001",
        ]
        for name in self.liststaticnames:
            col_en = self._coldict["nav"]["texte"]
            col_dis = self._coldict["nav"]["texte_dis"]
            src = PIL.Image.open(path + name + ".png")
            src2 = PIL.Image.open(path + name + ".png")
            src_en = ColorHelper.color_png(src, col_en)
            src_dis = ColorHelper.color_png(src2, col_dis)
            d[name] = {"src": src_en, "exportimg": self.export_image_from_PIL(src_en)}
            d[name + "_dis"] = {
                "src": src_dis,
                "exportimg": self.export_image_from_PIL(src_dis),
            }
        # visuels
        vis_names = ["visuel_elimine", "visuel_spectateur"]
        for name in vis_names:
            src = PIL.Image.open(path + name + ".png")
            d[name] = {"src": src, "exportimg": self.export_image_from_PIL(src)}

    def _init_zones_dangers(self):
        """
        Surfaces dynamiques permettant de visualiser les zones
        de dangers (mines, robots).
        """
        # Dict de gestion du cache de formes :
        # clef = (vitesse, impact, portee)
        self._srcdict["zonedangers"] = dict()
        # on pré génère les combinaisons suivantes :
        vitesse = 1
        ip_list = [(1, 1), (1, 2), (1, 3), (5, 2), (5, 3), (9, 3)]
        for ip in ip_list:
            impact = ip[0]
            portee = ip[1]
            # génération de l'entrée :
            self.get_image_for_zone_danger(vitesse, impact, portee, 4)

    def _init_features_radars(self):
        """
        Surfaces dynamiques associées aux graphes radars des caractéristiques
        des robots.
        """
        # Dict dédié
        self._srcdict["radargraph"] = dict()
        # on génère l'image générique :
        self._create_generic_radar()

    #-----> Gestion des fonts :
    def _init_fonts(self):
        """
        Initialise la gestion des fonts
        """
        self.gamepath = os.path.dirname(os.path.abspath(sys.argv[0]))
        if self.frozen:
            self.pygameSkinpath = (
                self.gamepath
                + "/labpyproject/apps/labpyrinthe/gui/skinPygame/rsc/fonts/"
            )
        else:
            self.pygameSkinpath = self.gamepath + "/gui/skinPygame/rsc/fonts/"
        # dict des fonts par fontname :
        self._fontdict = dict()
        d = self._fontdict
        # précaution :
        if not pygame.freetype.was_init():
            pygame.freetype.init()
        # enregistrement des sources
        d[None] = {"src": None, "standarddict": dict(), "freetypedict": dict()}
        src_ubuntumono = self.pygameSkinpath + "Ubuntu_Mono/UbuntuMono-Regular.ttf"
        d["UbuntuMono"] = {
            "src": src_ubuntumono,
            "standarddict": dict(),
            "freetypedict": dict(),
        }
        src_poppins = self.pygameSkinpath + "Poppins/Poppins-Medium.ttf"
        d["PoppinsMedium"] = {
            "src": src_poppins,
            "standarddict": dict(),
            "freetypedict": dict(),
        }
        src_poppins_black = self.pygameSkinpath + "Poppins/Poppins-Black.ttf"
        d["PoppinsBlack"] = {
            "src": src_poppins_black,
            "standarddict": dict(),
            "freetypedict": dict(),
        }
        src_poppins_bold = self.pygameSkinpath + "Poppins/Poppins-Bold.ttf"
        d["PoppinsBold"] = {
            "src": src_poppins_bold,
            "standarddict": dict(),
            "freetypedict": dict(),
        }

    def get_FontObject(self, fontname, size, freetypefont=False):
        """
        Retourne un objet :
        
        - pygame.font.Font si freetypefont=False
        - freetype.font.Font sinon
        
        """
        fontobj = None
        if fontname in self._fontdict.keys():
            if freetypefont:
                d = self._fontdict[fontname]["freetypedict"]
            else:
                d = self._fontdict[fontname]["standarddict"]
            if isinstance(size, int) and size > 0:
                if size in d.keys():
                    fontobj = d[size]
                else:
                    # Création et mise en cache d'un objet :
                    src = self._fontdict[fontname]["src"]
                    if freetypefont:
                        fontobj = pygame.freetype.Font(src, size=size)
                        fontobj.origin = True
                        fontobj.ucs4 = True
                    else:
                        fontobj = pygame.font.Font(src, size)
                    d[size] = fontobj
        return fontobj

    #-----> Spécifique :
    def get_image_for_BotItem(self, case, size):
        """
        Retourne les images du switch BotItem associé à la case.
        """
        # gestion du cache :
        keyname = self._get_base_name_for_bot(case) + case.color
        if keyname not in self._srcdict["zonebots"].keys():
            # 1- Sources png PIL :
            surfdict = self._get_surface_set_for_bot(case, size)
            cadre = surfdict["cadre"]
            cadre_ombre = surfdict["cadre_ombre"]
            bot_col = surfdict["bot_col"]
            bot_ombre = surfdict["bot_ombre"]
            bot_dead = surfdict["bot_dead"]
            mark_dead = surfdict["mark_dead"]
            mark_deconnect = surfdict["mark_deconnect"]
            # 2- Surfaces utilisées dans le switch
            surflist = list()
            # s1 : bot coloré
            surflist.append(bot_col)
            # s2 : bot ombré
            surfover = pygame.Surface(size, flags=pygame.SRCALPHA)
            surfover.blit(bot_ombre, (2, 2))
            surfover.blit(bot_col, (0, 0))
            surflist.append(surfover)
            # s3 : bot ombré encadré
            surfselect = pygame.Surface(size, flags=pygame.SRCALPHA)
            surfselect.blit(cadre_ombre, (1, 1))
            surfselect.blit(cadre, (0, 0))
            surfselect.blit(bot_ombre, (2, 2))
            surfselect.blit(bot_col, (0, 0))
            surflist.append(surfselect)
            # s4 : bot dead
            surfdead = pygame.Surface(size, flags=pygame.SRCALPHA)
            surfdead.blit(bot_dead, (0, 0))
            surfdead.blit(mark_dead, (0, 0))
            surflist.append(surfdead)
            # s5 : bot deconnect (humain)
            if case.behavior == CaseRobot.BEHAVIOR_HUMAN:
                surfdec = pygame.Surface(size, flags=pygame.SRCALPHA)
                surfdec.blit(bot_col, (0, 0))
                surfdec.blit(mark_deconnect, (0, 0))
                surflist.append(surfdec)
            # 3- cache
            self._srcdict["zonebots"][keyname] = surflist
        # retour :
        rsurf = self._srcdict["zonebots"][keyname]
        return rsurf

    def _get_surface_set_for_bot(self, case, size):
        """
        Retourne les surfaces élémentaires d'un BotItem
        """
        rdict = {
            "cadre": None,
            "cadre_ombre": None,
            "bot_col": None,
            "bot_ombre": None,
            "bot_dead": None,
            "mark_dead": None,
            "mark_deconnect": None,
        }
        color = case.color
        colombre = pygame.Color("#330000")
        # cadre coloré :
        cadre_png = None
        cadrecolorname = "high_bot" + str(color)
        if cadrecolorname not in self._srcdict["zonebots"].keys():
            cadre_src = self._srcdict["zonebots"]["high_bot"]["src"]
            cadre_png = cadre_src.copy()
            cadre_png = ColorHelper.color_png(cadre_png, color)
            self._srcdict["zonebots"][cadrecolorname] = {"src": cadre_png}
        rdict["cadre"] = self.get_image("zonebots", cadrecolorname, size=size)
        # cadre ombré
        rdict["cadre_ombre"] = self.color_surface(rdict["cadre"], colombre)
        # perso
        rdict["bot_col"] = self.get_image_for_case(case, size)
        # perso ombré :
        rdict["bot_ombre"] = self.color_surface(rdict["bot_col"], colombre)
        # bot dead
        case.alive = False
        rdict["bot_dead"] = self.get_image_for_case(case, size)
        case.alive = True
        # mark dead :
        rdict["mark_dead"] = self.get_image("zonebots", "mark_dead", size=size)
        # mark deconnect :
        rdict["mark_deconnect"] = self.get_image(
            "zonebots", "mark_deconnect", size=size
        )
        # retour ;
        return rdict

    def _get_base_name_for_bot(self, case):
        """
        Retourne le nom de base de l'image associée au bot
        """
        name = None
        behavior = case.behavior
        if behavior == CaseRobot.BEHAVIOR_HUNTER:
            name = "hunter"
        elif behavior == CaseRobot.BEHAVIOR_WINNER:
            name = "winner"
        elif behavior == CaseRobot.BEHAVIOR_RANDOM:
            name = "random"
        elif behavior == CaseRobot.BEHAVIOR_TOURIST:
            name = "tourist"
        elif behavior == CaseRobot.BEHAVIOR_SAPPER:
            name = "sapper"
        elif behavior == CaseRobot.BEHAVIOR_BUILDER:
            name = "builder"
        elif behavior == CaseRobot.BEHAVIOR_HUMAN:
            hnumber = int(case.human_number)
            if hnumber in range(1, 11):
                name = str("humain_" + str(hnumber))
            else:
                name = "humain"
        return name

    #-----> Zones de dangers
    def get_image_for_zone_danger(self, vitesse, impact, portee, dangerfactor):
        """
        Retourne une surface pygame normalisée pour une taille de case 80*80
        
        * vitesse : vitesse d'un robot ou 0 pour une mine
        * impact : impact de mine ou grenade
        * portee : portee d'une grenade
        * dangerfactor : valeur dans [0, 1, 2, 3, 4]
        
        """
        surf = None
        if dangerfactor in SkinPygame.DGR_FACTOR_COLOR.keys():
            # la surface existe t'elle ?
            d = self._srcdict["zonedangers"]
            k = (vitesse, impact, portee)
            if not k in d.keys():
                # on génère la combinaison :
                self._create_zone_danger_entry_Surf(vitesse, impact, portee)
            # la surface associée au type
            surf = d[k][dangerfactor]["exportimg"]
        return surf

    def get_color_for_dangerfactor(self, dangerfactor):
        """
        Retourne la couleur hexa associé au facteur de danger
        """
        if dangerfactor in SkinPygame.DGR_FACTOR_COLOR.keys():
            return SkinPygame.DGR_FACTOR_COLOR[dangerfactor]
        return None

    def _get_coords_for_zone(self, vitesse, impact=0, portee=0, unit=80):
        """
        Retourne la liste de coordonnées des points du polygone représentant
        la zone
        
        * vitesse : vitesse du robot (0 pour une mine)
        * impact : entier dans [1, 5, 9, 13, 17, 25]
        * portee : portée de la grenade (0 pour une mine)
        * unit : taille considérée pour une case
        
        """
        # paramètres
        unit = math.floor(unit)
        delta = vitesse
        if impact * portee > 0:
            delta += portee - 1
        delta = math.floor(delta)
        # demi dimension du cadre total de la zone :
        hdim = unit * (0.5 + delta)
        if impact in [5, 9]:
            hdim += unit
        elif impact >= 13:
            hdim += 2 * unit
        # 1- Génération du parcours du quart haut / gauche :
        cLT = list()
        # demi "empreinte" gauche :
        startpoint = 0, hdim + 1 / 2 * unit
        eL = self.get_first_half_shape(startpoint, impact, unit)
        x, y = eL[-1]
        # demi "empreinte" haute par symétrie :
        center = hdim, hdim
        eT = self._apply_rotation_and_axissym(eL, center, -cmath.pi / 2, axis="y")
        # Test de jonction ?
        dojoin = self._pointlists_do_join(eL, eT)
        if dojoin:
            # le chemin est complet :
            eL.extend(eT)
            cLT = eL
        else:
            # escalier gauche lié à la vitesse ?
            complete = False
            escL = escT = None
            if vitesse > 1:
                escL = list()
                nbsteps = vitesse - 1
                step = 0
                while step < nbsteps:
                    x += unit
                    escL.append((x, y))
                    y += unit
                    escL.append((x, y))
                    step += 1
                # génération de l'escalier haut par symétrie
                escT = self._apply_rotation_and_axissym(
                    escL, center, -cmath.pi / 2, axis="y"
                )
                # on complète les listes gauche et haut :
                eL.extend(escL)
                escT.extend(eT)
                eT = escT
                # Test de jonction ?
                dojoin = self._pointlists_do_join(eL, eT)
                if dojoin:
                    # le chemin est complet :
                    eL.extend(eT)
                    cLT = eL
                    complete = True
            # planchers lié à la portée ?
            if not complete:
                ptL = eL[-1]
                ptT = eT[0]
                sympoint = ptT[0], ptL[1]
                eL.append(sympoint)
                eL.extend(eT)
                cLT = eL
        # 2- Génération du quart haut / droit par symétrie :
        cRT = self._apply_rotation_and_axissym(cLT, center, -cmath.pi / 2)
        # 3- Concaténation du parcours haut :
        cT = cLT
        cT.extend(cRT)
        # 4- Génération du parcours bas par symétrie :
        cB = self._apply_rotation_and_axissym(cT, center, 0, axis="x")
        # 5- Concaténation du parcours final :
        cFull = cT
        cFull.extend(cB)
        # 6- Décallage des coords de (unit, unit):
        dcFull = [(x + unit, y + unit) for (x, y) in cFull]
        cFull = dcFull
        # dimension totale
        fulldim = 2 * (hdim + unit)
        return cFull, fulldim

    def get_first_half_shape(self, startpoint, impact, unit):
        """
        Retourne les coords de la demi empreinte gauche liée à l'impact.
        """
        x, y = startpoint
        rlist = list()
        if impact in [0, 1]:
            rlist.append((x, y))
        elif impact == 5:
            rlist.append((x, y))
            x += unit
            rlist.append((x, y))
            y += unit
            rlist.append((x, y))
        elif impact == 9:
            y += unit
            rlist.append((x, y))
        elif impact == 13:
            rlist.append((x, y))
            x += unit
            rlist.append((x, y))
            y += unit
            rlist.append((x, y))
            x += unit
            rlist.append((x, y))
            y += unit
            rlist.append((x, y))
        elif impact == 17:
            rlist.append((x, y))
            x += unit
            rlist.append((x, y))
            y += unit
            rlist.append((x, y))
            x -= unit
            rlist.append((x, y))
            y += unit
            rlist.append((x, y))
        elif impact == 25:
            y -= 2 * unit
            rlist.append((x, y))
        return rlist

    def _pointlists_do_join(self, plist1, plist2):
        """
        Indique si le dernier point de plist1 se connecte au premier de plist2
        """
        dojoin = False
        pt1 = plist1[-1]
        pt2 = plist2[0]
        dist = math.sqrt((pt2[0] - pt1[0]) ** 2 + (pt2[1] - pt1[1]) ** 2)
        if dist <= 1:
            dojoin = True
        return dojoin

    def _apply_rotation_and_axissym(self, plist, center, angle, axis=None):
        """
        Retourne une liste après transformations de la liste de coordonnées plist
        
        - par application d'une rotation autour du point center si angle != 0
        - par symétrie axiale (si axis="x" ou "y") / l'axe passant par center
        - inverse la liste en cas de symétrie axiale
        
        Rq : n'ajoute pas les points déja présents dans plist
        """
        rlist = list()
        for pt in plist:
            # rotation autour de center
            if angle != 0:
                newpt = self._rotate_point(pt, center, angle)
            else:
                newpt = pt[0], pt[1]
            # puis symétrie axiale
            if axis == "x":
                newpt = self._hor_sym_point(newpt, center[1])
            elif axis == "y":
                newpt = self._vert_sym_point(newpt, center[0])
            # évite les doublons entre empreintes :
            if newpt not in plist:
                rlist.append(newpt)
        if axis != None:
            rlist.reverse()
        return rlist

    def _rotate_point(self, pt, center, angle):
        """
        Calcule les coords de l'image de pt par une rotation autour du
        point center de valeur angle (radians)
        """
        zc = complex(center[0], center[1])
        zpt = complex(pt[0], pt[1])
        za = cmath.rect(1, angle)
        zr = za * (zpt - zc) + zc
        newpt = zr.real, zr.imag
        return newpt

    def _vert_sym_point(self, pt, xsym):
        """
        Calcule les coords de l'image de pt par une symétrie d'axe vertical
        d'absisse xsym
        """
        return 2 * xsym - pt[0], pt[1]

    def _hor_sym_point(self, pt, ysym):
        """
        Respectivement symétrie horizontale
        """
        return pt[0], 2 * ysym - pt[1]

    def _create_zone_danger_entry_Surf(self, vitesse, impact, portee):
        """
        Génère les exports colorés pour la combinaison.
        L'enregistre dans self._srcdict["zonedangers"] avec la clef
        (vitesse, impact, portee)
        """
        # création de l'entrée
        d = self._srcdict["zonedangers"]
        k = (vitesse, impact, portee)
        d[k] = dict()
        # coords des tracés :
        u = 20
        scalefact = 80 / u
        bdwidth = max(1, int(7 - scalefact))
        fullpts, fulldim = self._get_coords_for_zone(
            vitesse, impact=impact, portee=portee, unit=u
        )
        movepts, movedim = fullpts, fulldim
        if impact * portee > 0:
            movepts, movedim = self._get_coords_for_zone(
                vitesse, impact=0, portee=0, unit=u
            )
            delta = int((fulldim - movedim) / 2)
            deltamovepts = [(x + delta, y + delta) for (x, y) in movepts]
            movepts = deltamovepts
        # Exports colorés Pygame :
        exports = list()
        for df in SkinPygame.DGR_FACTOR_COLOR.keys():
            col = self.get_color_for_dangerfactor(df)
            exports.append((df, col))
        for nc in exports:
            name = nc[0]
            color = nc[1]
            # Entrée par type
            d[k][name] = dict()
            # Surface totale colorée
            fullsurf = self._create_base_surface_for_zone(
                fullpts, fulldim, movepts, movedim, shapecolor=color, width=bdwidth
            )
            # rescale :
            if scalefact != 1:
                sdim = int(fulldim * scalefact)
                fullsurf = pygame.transform.scale(fullsurf, (sdim, sdim))
            # enregistrement :
            d[k][name]["exportimg"] = fullsurf

    def _create_base_surface_for_zone(
        self, fullpts, fulldim, movepts, movedim, shapecolor="#FFFFFF", width=5
    ):
        """
        Trace l'image de la zone directement sur une surface.
        """
        # couleurs
        bgcolor = pygame.Color(shapecolor)
        bgcolor.a = SkinPygame.DGR_FACTOR_ALPHA
        bdcolor = pygame.Color(shapecolor)
        bdcolor.a = SkinPygame.DGR_FACTOR_ALPHA
        bdcolor.a = math.floor(255 * 0.8)
        bdwidth = width
        # surface :
        wf = hf = fulldim
        surf = pygame.Surface((wf, hf), flags=pygame.SRCALPHA)
        # 1- Full
        # bg :
        pygame.draw.polygon(surf, bgcolor, fullpts, 0)
        # bd :
        pygame.draw.polygon(surf, bdcolor, fullpts, bdwidth)
        # 2- Move
        bgcolor.a *= 2
        # bg :
        pygame.draw.polygon(surf, bgcolor, movepts, 0)
        # bd :
        pygame.draw.polygon(surf, bdcolor, movepts, bdwidth)
        # retour
        return surf

    #-----> Graphes radars des caractéristiques des robots
    def get_radar_graph_for_bot(self, robot):
        """
        Génère le graphe radar d'un robot.
        Pas de mise en cache (probas de réutilisation faibles)
        """
        # données :
        featvalues = robot.get_features_radar_datas()
        dgrfactor = robot.get_danger_factor_for_bot(None)
        color = pygame.Color(self.get_color_for_dangerfactor(dgrfactor))
        color.a = SkinPygame.DGR_FACTOR_ALPHA * 2
        features = CaseRobot.FEATURES
        # géométrie
        w, h = 110, 110
        center = 55, 55
        radius = 45
        angles = [0, 60, 120, 180, 240, 300]
        # points :
        radarpts = []
        for i in range(0, 6):
            feat = features[i]
            radangle = math.radians(angles[i])
            value = featvalues[feat]
            refpt = center[0], center[1] - value * radius
            rotpt = refpt
            if radangle > 0:
                rotpt = self._rotate_point(refpt, center, radangle)
            radarpts.append(rotpt)
        # tracé :
        radar_surf = pygame.Surface((w, h), flags=pygame.SRCALPHA)
        pygame.draw.polygon(radar_surf, color, radarpts)
        # axes et seuils :
        gen_surf = self._srcdict["radargraph"]["generic"]["exportimg"]
        radar_surf.blit(gen_surf, (0, 0))
        # retour sans mise en cache :
        return radar_surf

    def _create_generic_radar(self):
        """
        Génère la surface 80*80 générique représentant les axes et seuils
        des caractéristiques.
        """
        # géométrie
        w, h = 110, 110
        center = 55, 55
        radius = 45
        angles = [0, 60, 120, 180, 240, 300]
        linew = 1
        # seuils :
        thresdict = CaseRobot.get_feature_threshold_dict()
        features = CaseRobot.FEATURES
        # 1- axes principaux :
        main_color = pygame.Color("#330000")
        axis_surf = pygame.Surface((w, h), flags=pygame.SRCALPHA)
        main_pts = [(center[0], center[1] - radius)]
        for angle in angles[1:]:
            radangle = math.radians(angle)
            refpt = main_pts[0]
            rotpt = self._rotate_point(refpt, center, radangle)
            main_pts.append(rotpt)
        for i in range(0, 3):
            pt1 = main_pts[i]
            pt2 = main_pts[i + 3]
            pygame.draw.line(axis_surf, main_color, pt1, pt2, linew)
        # 2- Seuils :
        # thres_color = pygame.Color("#BEAEAE")
        thres_color = main_color
        thres_surf = pygame.Surface((w, h), flags=pygame.SRCALPHA)
        # 100% :
        pygame.draw.aalines(thres_surf, thres_color, True, main_pts)
        # middle, high :
        for thres in ["middle", "high"]:
            thres_pts = []
            for i in range(0, 6):
                feat = features[i]
                radangle = math.radians(angles[i])
                value = thresdict[feat][thres]
                refpt = center[0], center[1] - value * radius
                rotpt = refpt
                if radangle > 0:
                    rotpt = self._rotate_point(refpt, center, radangle)
                thres_pts.append(rotpt)
            pygame.draw.aalines(thres_surf, thres_color, True, thres_pts)
        # 3- Textes :
        txt_surf = self.get_image("zonebots", "radar_txt", size=(w, h))
        # 4- Surface finale :
        surf = pygame.Surface((w, h), flags=pygame.SRCALPHA)
        surf.blit(thres_surf, (0, 0))
        surf.blit(axis_surf, (0, 0))
        surf.blit(txt_surf, (0, 0))
        # 5- Enregistrement :
        d = self._srcdict["radargraph"]
        d["generic"] = {"exportimg": surf}
