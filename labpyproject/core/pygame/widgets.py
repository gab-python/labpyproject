#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
**Jeu de widgets basiques destinés à construire une interface pygame.**

Combine les modules core et events pour produire des objets fonctionnels.

* Root : conteneur racine de l'application
* Canvas, HBox, VBox : RealContainers (sans layout, avec layout horizontal ou vertical)
* Stack, HStack, VStack : VirtualContainers (sans layout, avec layout horizontal ou vertical)
* Image : objet image
* Background : fond monochrome
* Text : champ texte multi ligne (utilisant un objet pygame.font.Font ou pygame.freetype.Font)
* Entry : text entry dérivé de Text
* TextButton : bouton avec zone de texte et fond monochrome
* Button : bouton image

.. note::
    * box model et z-index : gérés par les superclasses du module :doc:`labpyproject.core.pygame.core`
    * support minimal des événements : gérés par les superclasses du module :doc:`labpyproject.core.pygame.events`

"""
# imports :
import math
import pygame.freetype
import labpyproject.core.pygame.events as evt
import labpyproject.core.pygame.core as co

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = [
    "Background",
    "Image",
    "Text",
    "Entry",
    "TextButton",
    "Button",
    "Stack",
    "HStack",
    "VStack",
    "Canvas",
    "HBox",
    "VBox",
    "Root",
]
# classes :
#-----> Widgets terminaux
class Background(co.CustomSprite):
    """
    Sprite image destiné à des fonds monochromes.
    """

    def __init__(self, bgcolor, **kwargs):
        """
        DirtySprite pouvant être positionné relativement à son parent.
       
        Args:
            bgcolor (str): couleur hexa (#xxxxxx ou 0xxxxxxxxx)
        """
        # couleur de fond :
        if bgcolor != None:
            kwargs["surface_color"] = bgcolor
        # générique :
        co.CustomSprite.__init__(self, **kwargs)


class Image(co.CustomSprite):
    """
    Widget image basique.
    """

    def __init__(
        self, surface=None, file=None, fixed=True, fillmode="contain", **kwargs
    ):
        """
        Constructeur.
        
        Args:
            src : une surface pygame
            file : chemin absolu vers un fichier image
            fixed (boolean): indique si l'image est redimmensionnable
            fillmode : "contain" (image complètement visible, défaut), ou "cover" 
                (l'image remplit entièrement le cadre aloué)            
        """
        # surface source
        self.source_surface = surface
        # surface courante :
        self.current_surface = None
        # élasticité :
        self.fixed = fixed
        # remplissage du cadre :
        self.fillmode = fillmode
        # générique :
        co.CustomSprite.__init__(self, **kwargs)
        # géométrie :
        self.post_init_boxmodel()
        # fichier à charger (chemin absolu)
        self._file = file
        if self._file != None:
            self.load_file(self._file)
        if self.source_surface != None:
            self.load_surface(self.source_surface)

    def post_init_boxmodel(self):
        """
        Spécifie au besoin des valeurs par défaut.
        """
        if self.has_default_value("width"):
            self.width = "100%"
        if self.has_default_value("snapW"):
            self.snapW = True
        if self.has_default_value("height"):
            self.height = "100%"
        if self.has_default_value("snapH"):
            self.snapH = True

    def load_file(self, file):
        """
        Charge un fichier image (file : chemin absolu).
        """
        surf = None
        if file != None:
            self._file = file
            try:
                surf = pygame.image.load(file)
            except pygame.error as e:
                raise Exception("Pygame image loading error : " + e)
        if surf != None:
            self.source_surface = None
            self.load_surface(surf)
        else:
            self.create_default_surface()

    def load_surface(self, surface):
        """
        Charge une surface pygame.
        """
        if surface != None and isinstance(surface, pygame.Surface):
            # surface source
            self.source_surface = surface
            # création de la surface courante :
            self.current_surface = None
            self.create_current_surface()
        else:
            self.source_surface = self.current_surface = None
            self.create_default_surface()
        self.discard_display()

    def draw_display(self):
        """
        Dessine ou redessine l'objet.
        """
        # optimisation
        if not self.visible:
            return
        # implémentation typique :
        self.create_default_surface()
        # création de la surface courante au besoin :
        if self.source_surface != None:
            if self.current_surface == None:
                self.create_current_surface()
            # on copie la surface aux coordonnées locales de content_rect:
            if self.current_surface != None:
                dest, area = self.get_display_dest()
                self.image.blit(self.current_surface, dest, area=area)
        # indicateur de redraw
        self.dirty = 1

    def get_item_dimensions(self):
        """
        Doit retourner les dimensions réelles du contenu (texte, image).
        A implémenter dans les subclasses utilisant le snap.
        """
        img_w, img_h = None, None
        if not self.fixed or self.current_surface == None:
            self.create_current_surface()
        if self.current_surface != None:
            img_w, img_h = self.current_surface.get_size()
        return img_w, img_h

    def create_current_surface(self):
        """
        Crée la surface aux dimensions actuelles d'affichage.
        """
        recreate = True
        # Taille en fonction des dimensions actuelles
        newsize = self.compute_image_size()
        # optimisation :
        if self.current_surface != None:
            cursize = self.current_surface.get_size()
            if newsize == cursize:
                recreate = False
        # création au besoin :
        if recreate:
            self.current_surface = self.get_surface_for_size(newsize)

    def get_surface_for_size(self, newsize):
        """
        Retourne une nouvelle surface à la taille newsize.
        """
        newsurf = None
        if (
            newsize != (None, None)
            and self.source_surface != None
            and newsize[0] > 0
            and newsize[1] > 0
        ):
            maxsize = self.source_surface.get_size()
            newsize = min(newsize, maxsize)
            newsurf = pygame.transform.smoothscale(self.source_surface, newsize)
        return newsurf

    def get_source_size(self):
        """
        Retourne les dimensions de la source.
        """
        ws, hs = None, None
        if self.source_surface != None:
            ws, hs = self.source_surface.get_size()
        return ws, hs

    def compute_image_size(self):
        """
        Calcul la taille d'image en fonction de l'espace aloué et des dimensions de la source.
        """
        wn, hn = None, None
        ws, hs = self.get_source_size()
        if (ws, hs) != (None, None):
            content_rect = self.get_content_rect()
            w, h = content_rect.w, content_rect.h
            src_ratio = ws / hs
            if self.fillmode == "contain":
                # visibilité totale de l'image
                fact_c_s = min(w / ws, h / hs)
            else:
                # "cover" : remplissage complet :
                fact_c_s = max(w / ws, h / hs)
            hn = math.ceil(fact_c_s * hs)
            wn = math.ceil(src_ratio * hn)
        return wn, hn


class Text(co.CustomSprite):
    """
    Widget texte basique.
    """

    # params statiques d'alignement horizontal du texte :
    LEFT_ALIGN = "left"  #: valeur d'alignement
    CENTER_ALIGN = "center"  #: valeur d'alignement
    RIGHT_ALIGN = "right"  #: valeur d'alignement
    # classes :
    def __init__(
        self,
        fontobj,
        text="",
        fgcolor="0x000000",
        linespacing=0,
        textalign=LEFT_ALIGN,
        **kwargs
    ):
        """
        Constructeur
        
        Args:
            fontobj : un objet pygame.font.Font (de préférence) ou pygame.freetype.Font 
                (support de caractères plus large mais rendu et wrap moins bons)
            text : le texte à afficher
            fgcolor : couleur du texte
            bgcolor : couleur du fond (transparent par défaut)
            size : taille du texte en points (par défaut celle de l'objet fontobj)
            linespacing : espacement interlignes
            textalign : alignement horizontal du texte (gauche par défaut), 
                uniquement pour un objet pygame.font.Font

        Rq : clipping à implémenter dans draw_display, en subclassant
        CustomSprite.get_display_dest pour prendre en compte les différences
        de rects de publication.
        """
        # objet pygame.freetype.Font :
        self._fontobj = None
        self._typefont = None
        if isinstance(fontobj, pygame.freetype.Font):
            self._fontobj = fontobj
            self._typefont = "freetype"
        elif isinstance(fontobj, pygame.font.Font):
            self._fontobj = fontobj
            self._typefont = "font"
        # chaine txt
        self._text = None
        # écart interlignes
        self._linespace = 0
        if isinstance(linespacing, int):
            self._linespace = linespacing
        # alignement horizontal du texte :
        self._textalign = Text.LEFT_ALIGN
        if textalign in [Text.LEFT_ALIGN, Text.CENTER_ALIGN, Text.RIGHT_ALIGN]:
            self._textalign = textalign
        # surface de rendu du texte :
        self._textrender_updated = False
        self.text_surface = None
        self.text_size = None, None
        # générique :
        co.CustomSprite.__init__(self, **kwargs)
        self.post_init_boxmodel()
        # couleur du texte : noir par défaut
        self._fgcolor = None
        if fgcolor != None:
            self.fgcolor = fgcolor
        # couleur de fond ; hérité de CustomSprite
        # affichage :
        if text != None:
            self.text = text

    def _get_fgcolor(self):
        return self._fgcolor

    def _set_fgcolor(self, col):
        """Couleur du texte."""
        if not isinstance(col, pygame.Color):
            try:
                col = pygame.Color(col)
            except ValueError:
                col = pygame.Color("#000000")
        if col != self._fgcolor:
            self._fgcolor = col
            # display :
            self.discard_render()
            self.discard_display()

    fgcolor = property(
        _get_fgcolor, _set_fgcolor
    )  #: Couleur du texte (hexa) convertie en pygame.Color

    def post_init_boxmodel(self):
        """
        Spécifie au besoin des valeurs par défaut.
        """
        if self.has_default_value("width"):
            self.width = "100%"
        if self.has_default_value("snapW"):
            self.snapW = False
        if self.has_default_value("height"):
            self.height = "100%"
        if self.has_default_value("snapH"):
            self.snapH = True
        if self.has_default_value("padding"):
            self.padding = 2

    def discard_resize(self):
        """
        Marque l'objet comme non resizé.
        """
        # générique :
        co.BoxModelObject.discard_resize(self)
        # spécifique :
        self.discard_render()

    def get_item_dimensions(self):
        """
        Doit retourner les dimensions réelles du contenu (texte, image). 
        A implémenter dans les subclasses utilisant le snap.
        """
        if not self._textrender_updated:
            self.render_text(self.text)
        return self.text_size

    def draw_display(self):
        """
        Dessinne ou redessinne l'objet.
        """
        # optimisation
        if not self.visible:
            return
        # ré initialise la surface par défaut:
        self.create_default_surface()
        # publication du texte :
        if self.text_surface == None or not self._textrender_updated:
            # rendu au besoin :
            self.render_text(self.text)
        if self.text_surface != None:
            # blit :
            brect = self.get_border_rect()
            self.image.blit(self.text_surface, (brect.x, brect.y), area=brect)

    def _get_text(self):
        """Contenu textuel à afficher."""
        return self._text

    def _set_text(self, val):
        if isinstance(val, str) and val != self._text:
            self._text = str(val)
            self.discard_render()
            self.discard_resize()

    text = property(_get_text, _set_text)  #: texte associé au widget

    def discard_render(self):
        """
        Indique que le texte doit être rendu à nouveau.
        """
        self.text_surface = None
        self.text_size = None, None
        self._textrender_updated = False
        self.discard_display()

    def render_text(self, txt=None):
        """
        Rendu du texte sur la surface dédiée self.text_surface.
        """
        if self.rect.w <= 0 or self.rect.h <= 0:
            self.discard_render()
            self.text_size = None, None
            return
        # surface de rendu du texte :
        self.create_text_surface()
        # affichage du texte :
        chaine = txt
        if txt == None:
            chaine = self._text
        if len(chaine) == 0:
            chaine = " "
        # wrap
        self.text_size = None, None
        if self._typefont == "freetype":
            self.text_size = self.wrap_text_freetype(self.text_surface, chaine)
        elif self._typefont == "font":
            self.text_size = self.wrap_text_font(self.text_surface, chaine)
        else:
            self.dirty = 1
            return
        # rendu
        self.dirty = 1
        # maj
        self._textrender_updated = True

    def create_text_surface(self):
        """
        Crée la surface de rendu du texte.
        """
        self.text_surface = pygame.Surface(
            (self.rect.width, self.rect.height), flags=pygame.locals.SRCALPHA
        )
        self.text_surface.fill(self.transp_color, self.rect)
        if self._bgcolor != None and self._bgcolor.a == 255:
            # optimise le rendu de texte
            self.text_surface.fill(self._bgcolor, self.get_border_rect())

    def wrap_text_freetype(self, surf, txt):
        """
        Wrap simple inspiré de : https://www.pygame.org/docs/ref/freetype.html#pygame.freetype.Font.render_to
        """
        if not isinstance(txt, str):
            return
        # pré traitement du texte
        lines = txt.split("\n")
        # paramètres
        font = self._fontobj
        font.origin = True
        # géométrie :
        content_rect = self.get_content_rect()
        width, height = content_rect.w, content_rect.h
        xc, yc = content_rect.x, content_rect.y
        lspace = self._linespace
        if lspace == 0:
            lspace = 2
        line_spacing = font.get_sized_height() + lspace
        x, y = xc, yc + font.get_sized_ascender()
        space = font.get_rect(" ")
        txtwidth = 0
        txtheight = y
        # wrap
        for line in lines:
            words = line.split(" ")
            for word in words:
                bounds = font.get_rect(word)
                if x + bounds.width + bounds.x >= width:
                    x, y = xc, y + line_spacing
                    txtheight += line_spacing
                if x + bounds.width + bounds.x >= width:
                    break
                if y + bounds.height - bounds.y >= height:
                    break
                font.render_to(surf, (x, y), None, fgcolor=self.fgcolor)
                x += bounds.width + space.width
                txtwidth = max(txtwidth, x)
            x, y = xc, y + line_spacing
            if line != lines[-1]:
                txtheight += line_spacing
        return int(txtwidth), int(txtheight)

    def wrap_text_font(self, surf, txt):
        """
        Wrap alternatif.
        """
        if not isinstance(txt, str):
            return
        # pré traitement du texte
        lines = txt.split("\n")
        # paramètres
        font = self._fontobj
        # géométrie :
        content_rect = self.get_content_rect()
        width, height = content_rect.w, content_rect.h
        xc, yc = content_rect.x, content_rect.y
        line_spacing = font.get_linesize() + self._linespace
        # largeur :
        i = 0
        while i < len(lines):
            line = lines[i]
            lw = font.size(line)[0]
            if lw > 0:
                subline = line
                splitindex = math.floor(len(line) * width / lw)
                while lw > width:
                    lastspace = subline.rfind(" ")
                    if lastspace != -1:
                        splitindex = lastspace
                    else:
                        splitindex -= 1
                    subline = line[0:splitindex]
                    lw = font.size(subline)[0]
                if splitindex < len(line):
                    lines[i] = subline.lstrip()
                    lines.insert(i + 1, line[splitindex:].lstrip())
            i += 1
        # hauteur :
        realheight = line_spacing * len(lines)
        if realheight > height:
            i = len(lines)
            while realheight > height:
                i -= 1
                realheight = line_spacing * i
            if i > 0:
                lines = lines[0:i]
                lastline = lines[-1]
                if len(lastline) > 6:
                    lastline = lastline[0:-6] + "[...]"
                    lines[i - 1] = lastline
        # rendu :
        x, y = xc, yc
        txtwidth = 0
        txtheight = 0
        bgcol = None
        if self._bgcolor != None and self._bgcolor.a == 255:
            bgcol = self._bgcolor
        for line in lines:
            surfline = font.render(line, True, self.fgcolor, bgcol)
            sw = surfline.get_size()[0]
            if self._textalign == Text.CENTER_ALIGN:
                x = math.ceil((width - sw) / 2)
            elif self._textalign == Text.RIGHT_ALIGN:
                x = math.ceil(width - sw)
            surf.blit(surfline, (x, y))
            txtwidth = max(txtwidth, sw + x)
            x, y = xc, y + line_spacing
            txtheight = y
            if line != lines[-1]:
                txtheight += line_spacing
        return txtwidth, txtheight


class Entry(Text, evt.CustomBaseInput):
    """
    Entry text.
    """

    def __init__(
        self,
        fontobj,
        text="",
        fgcolor="0x000000",
        bgcolor="0xFFFFFF00",
        linespacing=2,
        snapW=False,
        snapH=False,
        **kwargs
    ):
        """
        Constructeur
        """
        # générique :
        Text.__init__(
            self,
            fontobj,
            text=text,
            fgcolor=fgcolor,
            bgcolor=bgcolor,
            linespacing=linespacing,
            snapW=snapW,
            snapH=snapH,
            **kwargs
        )
        evt.CustomBaseInput.__init__(self, **kwargs)

    def on_item_added_to_displaylist(self):
        """
        Appelée lorsque l'item (via sa hiérarchie parente) est publié par
        le root dans la displaylist finale.
        """
        # générique :
        co.VirtualItem.on_item_added_to_displaylist(self)
        # events :
        self.register()

    def on_item_removed_from_displaylist(self):
        """
        Appelée lorsque l'item (via sa hiérarchie parente) est dé-publié par
        le root de la displaylist finale.
        """
        # générique :
        co.VirtualItem.on_item_removed_from_displaylist(self)
        # events :
        self.unregister()

    def _set_inputext(self, val):
        """
        Setter du texte associé au contrôle.
        """
        changed = evt.CustomBaseInput._set_inputext(self, val)
        if changed:
            self.text = val

    def on_entry_validated(self, event):
        """
        Appelée par handle_key_event lorsqu'une touche entrée a été pressée.
        """
        # à subclasser
        pass


class TextButton(Text, evt.CustomBaseButton):
    """
    Widget button dérivé du widget Text
    """

    def __init__(
        self,
        fontobj,
        statesdict,
        text="",
        snapW=True,
        snapH=True,
        switch=False,
        shortcutkey=None,
        **kwargs
    ):
        """
        Constructeur
        
        Args:
            statesdict : dict décrivant les couleurs du texte et du fond pour les états 
                de CustomBaseButton
            switch : False = bouton simple, True = bouton sélectionnable/désélectionnable
            shortcutkey : code de touche optionnel équivalent à un clic
        
        Exemple: ::
        
            statesdict = {"UNSELECTED":(fgcolor, bgcolor),
                           "OVER":(fgcolor, bgcolor),
                           "PRESSED":(fgcolor, bgcolor),
                           "SELECTED":(fgcolor, bgcolor),
                           "DISABLED":(fgcolor, bgcolor)}
        """
        # couleurs de texte et de fond :
        self._parse_statesdict(statesdict)
        fgc = self._statesdict["UNSELECTED"]["fgcolor"]
        bgc = self._statesdict["UNSELECTED"]["bgcolor"]
        # générique :
        Text.__init__(
            self,
            fontobj,
            text=text,
            fgcolor=fgc,
            bgcolor=bgc,
            snapW=snapW,
            snapH=snapH,
            **kwargs
        )
        evt.CustomBaseButton.__init__(
            self, switch=switch, shortcutkey=shortcutkey, **kwargs
        )

    def on_item_added_to_displaylist(self):
        """
        Appelée lorsque l'item (via sa hiérarchie parente) est publié par
        le root dans la displaylist finale.
        """
        # générique :
        co.VirtualItem.on_item_added_to_displaylist(self)
        # events :
        self.register()

    def on_item_removed_from_displaylist(self):
        """
        Appelée lorsque l'item (via sa hiérarchie parente) est dé-publié par
        le root de la displaylist finale.
        """
        # générique :
        co.VirtualItem.on_item_removed_from_displaylist(self)
        # events :
        self.unregister()

    def _parse_statesdict(self, stdict):
        """
        Analyse le dict d'états passé en paramètres.
        """
        default_fgc = "0x000000"
        default_bgc = "0xFFFFFF"
        self._statesdict = dict()
        for st in evt.CustomBaseButton.STATES:
            self._statesdict[st] = dict()
            fgc = bgc = None
            if st in stdict.keys():
                ctup = stdict[st]
                if isinstance(ctup, tuple):
                    if len(ctup) >= 1:
                        fgc = ctup[0]
                    if len(ctup) >= 2:
                        bgc = ctup[1]
                if fgc == None:
                    fgc = default_fgc
                if bgc == None:
                    bgc = default_bgc
                self._statesdict[st]["fgcolor"] = fgc
                self._statesdict[st]["bgcolor"] = bgc

    def change_view_state(self, state):
        """
        Modifie physiquement l'apparence du bouton.
        """
        cdict = self._statesdict[state]
        self.fgcolor = pygame.Color(cdict["fgcolor"])
        self.bgcolor = pygame.Color(cdict["bgcolor"])
        self.discard_render()

    def send_callback(self, state):
        """
        Méthode destinée à transmettre l'état au manager de ce contrôle.
        """
        # à subclasser
        pass


class Button(Image, evt.CustomBaseButton):
    """
    Widget bouton image.
    """

    def __init__(
        self,
        statesdict,
        switch=False,
        shortcutkey=None,
        defaultstate="UNSELECTED",
        **kwargs
    ):
        """
        Constructeur
        
        Args:
            statesdict : dict décrivant les surfaces pour les états de CustomBaseButton
        
        Exemple: :: 
        
            statesdict = {"UNSELECTED":surface1,
                           "OVER":surface2,
                           "PRESSED":surface3,
                           "SELECTED":surface4,
                           "DISABLED":surface5}
        """
        # spécifique :
        self.source_statesdict = statesdict
        defaultsurf = self.source_statesdict[defaultstate]
        # générique :
        Image.__init__(self, surface=defaultsurf, **kwargs)
        evt.CustomBaseButton.__init__(
            self, switch=switch, shortcutkey=shortcutkey, **kwargs
        )

    def on_item_added_to_displaylist(self):
        """
        Appelée lorsque l'item (via sa hiérarchie parente) est publié par
        le root dans la displaylist finale.
        """
        # générique :
        co.VirtualItem.on_item_added_to_displaylist(self)
        # events :
        self.register()

    def on_item_removed_from_displaylist(self):
        """
        Appelée lorsque l'item (via sa hiérarchie parente) est dé-publié par
        le root de la displaylist finale.
        """
        # générique :
        co.VirtualItem.on_item_removed_from_displaylist(self)
        # events :
        self.unregister()

    def change_view_state(self, state):
        """
        Modifie physiquement l'apparence du bouton.
        """
        if state in self.source_statesdict.keys():
            newsurf = self.source_statesdict[state]
            self.source_surface = None
            self.load_surface(newsurf)

    def send_callback(self, state):
        """
        Méthode destinée à transmettre l'état au manager de ce contrôle.
        """
        # à subclasser
        pass


#-----> Widgets conteneurs virtuels (conteneurs légers, pour mettre en page le contenu d'un conteneur réel)
class Stack(co.VirtualContainer):
    """
    Widget Canvas virtuel.
    """

    def __init__(self, **kwargs):
        """
        Constructeur
        """
        # générique :
        co.VirtualContainer.__init__(self, **kwargs)


class HStack(Stack):
    """
    Box virtuelle à layout horizontal.
    """

    def __init__(self, **kwargs):
        """
        Constructeur
        """
        kwargs["direction"] = co.VirtualContainer.DIRECTION_HORIZONTAL
        Stack.__init__(self, **kwargs)


class VStack(Stack):
    """
    Box virtuelle à layout vertical.
    """

    def __init__(self, **kwargs):
        """
        Constructeur
        """
        kwargs["direction"] = co.VirtualContainer.DIRECTION_VERTICAL
        Stack.__init__(self, **kwargs)


#-----> Widgets conteneurs réels :
class Canvas(co.RealContainer):
    """
    Widget Canvas réel.
    """

    def __init__(self, **kwargs):
        """
        Constructeur
        """
        # générique :
        co.RealContainer.__init__(self, **kwargs)


class HBox(Canvas):
    """
    Box réelle à layout horizontal.
    """

    def __init__(self, **kwargs):
        """
        Constructeur
        """
        kwargs["direction"] = co.VirtualContainer.DIRECTION_HORIZONTAL
        Canvas.__init__(self, **kwargs)


class VBox(Canvas):
    """
    Box réelle à layout vertical.
    """

    def __init__(self, **kwargs):
        """
        Constructeur
        """
        kwargs["direction"] = co.VirtualContainer.DIRECTION_VERTICAL
        Canvas.__init__(self, **kwargs)


#-----> Widget Root (conteneur racine)
class Root(co.RootContainer):
    """
    Conteneur racine de l'application.
    """

    def __init__(
        self, width, height, resizable=True, bgcolor="#FFFFFF", framerate=120, **kwargs
    ):
        """
        Constructeur
        
        Args:
            width : largeur initiale de la fenêtre
            height : hauteur initiale de la fenêtre
        """
        # générique :
        co.RootContainer.__init__(
            self,
            resizable=resizable,
            framerate=framerate,
            width=width,
            height=height,
            bgcolor=bgcolor,
            **kwargs
        )
