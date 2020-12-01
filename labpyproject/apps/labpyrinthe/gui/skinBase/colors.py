#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper statique de gestion des couleurs.
"""
from operator import itemgetter
import PIL.ImageColor
import labpyproject.core.random.custom_random as cr

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ColorHelper"]
# classe
class ColorHelper:
    """
    Helper statique fournissant une couleur unique (plus quelques services).
    """

    # variable statique
    _COLOR_LIST = None
    # méthodes
    def _init_colors(cls):
        """
        Initialise les couleurs dédiées aux robots
        
        Remarque : la génération de couleurs aléatoires produit beaucoup de teintes vertes!
        Principe : 3 entiers aléatoires entre 0-255 convertis en hexa via "{:02x}".format(n) et 
        concaténés avec "#" en préfixe.
        """
        # liste principale
        m = list()
        m.append(
            {
                "colorfam": "vert",
                "count": 0,
                "colorlist": [
                    ["#808000", 0],
                    ["#bfef45", 0],
                    ["#3cb44b", 0],
                    ["#469990", 0],
                    ["#aaffc3", 0],
                    ["#999966", 0],
                    ["#CCFF00", 0],
                    ["#33FF00", 0],
                    ["#669900", 0],
                    ["#336600", 0],
                ],
            }
        )
        m.append(
            {
                "colorfam": "rose",
                "count": 0,
                "colorlist": [
                    ["#fabebe", 0],
                    ["#911eb4", 0],
                    ["#e6beff", 0],
                    ["#f032e6", 0],
                    ["#FFCCFF", 0],
                    ["#FF33FF", 0],
                    ["#CC99FF", 0],
                    ["#CC00FF", 0],
                    ["#9900CC", 0],
                ],
            }
        )
        m.append(
            {
                "colorfam": "bleu",
                "count": 0,
                "colorlist": [
                    ["#42d4f4", 0],
                    ["#000075", 0],
                    ["#4363d8", 0],
                    ["#00CCFF", 0],
                    ["#0099FF", 0],
                    ["#3333FF", 0],
                    ["#0066CC", 0],
                    ["#000099", 0],
                ],
            }
        )
        m.append(
            {
                "colorfam": "jaune",
                "count": 0,
                "colorlist": [
                    ["#ffe119", 0],
                    ["#fffac8", 0],
                    ["#ffd8b1", 0],
                    ["#f58231", 0],
                    ["#FFFFCC", 0],
                    ["#FFFF00", 0],
                    ["#FFCC00", 0],
                    ["#FF9900", 0],
                    ["#FF6600", 0],
                ],
            }
        )
        m.append(
            {
                "colorfam": "rouge",
                "count": 0,
                "colorlist": [
                    ["#e6194B", 0],
                    ["#800000", 0],
                    ["#9A6324", 0],
                    ["#CC6666", 0],
                    ["#FF3300", 0],
                    ["#CC0000", 0],
                    ["#CC3366", 0],
                    ["#660000", 0],
                ],
            }
        )
        # """
        for coldict in m:
            collist = coldict["colorlist"]
            cr.CustomRandom.shuffle(collist)
        # """
        return m

    _init_colors = classmethod(_init_colors)

    def get_color(cls):
        """
        Retourne une couleur unique pour un robot
        """
        if cls._COLOR_LIST == None:
            cls._COLOR_LIST = cls._init_colors()
        l = cls._COLOR_LIST
        # familles de couleur les moins utilisées :
        l.sort(key=itemgetter("count"))
        minfam = l[0]["count"]
        redfam = [f for f in l if f["count"] == minfam]
        cr.CustomRandom.shuffle(redfam)
        # famille aléatoire parmis celles ci :
        famdict = redfam[0]
        collist = famdict["colorlist"]
        # couleurs les moins utilisées
        collist.sort(key=itemgetter(1))
        mincol = collist[0][1]
        redcol = [coltup for coltup in collist if coltup[1] == mincol]
        cr.CustomRandom.shuffle(redcol)
        # couleur aléatoire parmis celles ci
        coltupple = redcol[0]
        coltupple[1] += 1
        famdict["count"] += 1
        return coltupple[0]

    get_color = classmethod(get_color)

    def color_png(cls, png, hexcolor):
        """
        Teinte une image png avec la couleur hexcolor.
        
        From: http://darenatwork.blogspot.com/2013/10/how-to-replace-color-in-png-with-python.html
        """
        nr, ng, nb = PIL.ImageColor.getrgb(hexcolor)
        pixels = png.load()
        w, h = png.size
        for x in range(w):
            for y in range(h):
                a = pixels[x, y][3]
                if a != 0:
                    pixels[x, y] = nr, ng, nb, a
        return png

    color_png = classmethod(color_png)

    def alpha_png(cls, png, alpha):
        """
        Affecte la valeur alpha à la transparence des pixels de
        valeur alpha non nulle.
        """
        pixels = png.load()
        w, h = png.size
        for x in range(w):
            for y in range(h):
                r, g, b, a = pixels[x, y]
                if a != 0:
                    pixels[x, y] = r, g, b, alpha
        return png

    alpha_png = classmethod(alpha_png)

    def get_complementary_color(cls, color):
        """
        Retourne le complémentaire sur le cercle colorimétrique
        
        From: https://itsphbytes.wordpress.com/2016/08/29/complementary-colors-python-code/
        """
        # strip the # from the beginning
        color = color[1:]
        # convert the string into hex
        color = int(color, 16)
        # invert the three bytes
        # as good as substracting each of RGB component by 255(FF)
        comp_color = 0xFFFFFF ^ color
        # convert the color back to hex by prefixing a #
        comp_color = "#%06X" % comp_color
        # return the result
        return comp_color

    get_complementary_color = classmethod(get_complementary_color)

    def get_random_color(cls):
        """
        Génère une couleur hexa aléatoire.
        """
        hc = "#"
        for i in range(0, 3):
            nb = cr.CustomRandom.randrange(0, 256)
            hc += ColorHelper.get_hexa_code(nb)
        return hc

    get_random_color = classmethod(get_random_color)

    def get_hexa_code(cls, n):
        """
        Retourne les 2 chars de code hexa pour un entier n supposé entre 0 et 255, retourne None sinon.
        
        Remarque : valeurs de ref en %  (src : https://stackoverflow.com/questions/5445085/understanding-colors-on-android-six-characters/11019879#11019879)
        
        - 100% — FF
        - 95% — F2
        - 90% — E6
        - 85% — D9
        - 80% — CC
        - 75% — BF
        - 70% — B3
        - 65% — A6
        - 60% — 99
        - 55% — 8C
        - 50% — 80
        - 45% — 73
        - 40% — 66
        - 35% — 59
        - 30% — 4D
        - 25% — 40
        - 20% — 33
        - 15% — 26
        - 10% — 1A
        - 5% — 0D
        - 0% — 00
        """
        if not isinstance(n, int) or n not in range(0, 256):
            return None
        return "{:02x}".format(n)

    get_hexa_code = classmethod(get_hexa_code)
