#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Superclasse des skins de LabPyrinthe :

* logique applicative
* ressources par défaut (images, couleurs)

"""
# imports
import os, sys
import PIL.Image
from labpyproject.core.net.custom_TCP import CustomRequestHelper
from labpyproject.apps.labpyrinthe.gui.skinBase.colors import ColorHelper
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import LabHelper
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseDanger
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import CaseRobot

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["SkinBase"]
# classes
class SkinBase:
    """
    Superclasse des skins de LabPyrinthe.
    """

    def __init__(self, optmode=False, carte_resolution="40", frozen=False):
        """
        Constructeur
        
        Args:
            optmode (boolean): si True pointe vers les images de la carte sans canal alpha 
                (moins exigeant graphiquement)
            carte_resolution (string): dimension des images de la carte (pardéfaut 40*40 pxl, 
                en option 80*80 pxl)
            frozen (boolean): indique si l'application est exécutée dans l'interpréteur ou 
                sous forme d'exécutable
        """
        # résolution d'url
        # - frozen = True : main à la racine du projet
        # - frozen = False : main à la racine de labpyrinthe
        self.frozen = frozen
        # optimisation des performances graphiques :
        self.optmode = optmode
        self.carte_resolution = carte_resolution
        # Dict images et couleurs :
        self._srcdict = {
            "carte": dict(),
            "common": dict(),
            "accueil": dict(),
            "nav": dict(),
            "bots": dict(),
            "screens": dict(),
            "loading": dict(),
            "net": dict(),
        }
        self._coldict = {
            "carte": dict(),
            "bots": dict(),
            "nav": dict(),
            "net": dict(),
        }
        # Initialisations :
        self.listbtnstates = ["1", "2", "3", "4", "5"]
        self.init_paths()
        self.init_colors()
        self.init_rsc()

    def init_paths(self):
        """
        Initialisation des chemins référençant les ressources
        """
        # racine du jeu et du skin :
        self.gamepath = os.path.dirname(os.path.abspath(sys.argv[0]))
        if self.frozen:
            self.skinpath = (
                self.gamepath + "/labpyproject/apps/labpyrinthe/gui/skinBase/rsc/"
            )
        else:
            self.skinpath = self.gamepath + "/gui/skinBase/rsc/"
        # rsc communes :
        self.common_path = self.skinpath + "common/"
        # rsc accueil
        self.accueil_path = self.skinpath + "accueil/"
        # rsc écrans :
        self.screens_path = self.skinpath + "screens/"
        # loding
        self.loading_path = self.screens_path + "jauge/"
        # rsc nav :
        self.nav_path = self.skinpath + "btns/"
        # rsc carte :
        if self.optmode:
            # Optimisation des performances : on évite les transparences
            alphafolder = "no_alpha/"
        else:
            alphafolder = "alpha/"
        self.carte_path = (
            self.skinpath + "carte/" + alphafolder + self.carte_resolution + "/"
        )
        self.explosions_path = (
            self.skinpath + "carte/explosions/" + self.carte_resolution + "/"
        )

    def init_colors(self):
        """
        Initialisation des couleurs :
        """
        self._init_carte_colors()
        self._init_bots_colors()
        self._init_command_colors()
        self._init_net_colors()

    def init_rsc(self):
        """
        Initialisation des images :
        """
        self._init_common_rsc()
        self._init_accueil_rsc()
        self._init_screens_rsc()
        self._init_loading_rsc()
        self._init_command_rsc()
        self._init_carte_rsc()
        self._init_net_rsc()

    #-----> Conversion à subclasser
    def export_image_from_PIL(self, src):
        """
        Convertit une source PIL.Image dans le format attendu par
        le moteur graphique.
        """
        # à subclasser
        pass

    #-----> Initialisations des couleurs :
    def _init_carte_colors(self):
        """
        Initialisation des couleurs par défaut : carte
        """
        d = self._coldict["carte"]
        # couleur de fond du labyrinthe (quadrillage)
        d["bg_lab"] = "#CDC1C1"
        d["bot_dead"] = "#BEAEAE"

    def _init_bots_colors(self):
        """
        Initialisation des couleurs par défaut : bots
        """
        d = self._coldict["bots"]
        # titre : rq l'image est gérée dans la cat "nav"
        d["titre"] = "#330000"
        # fond bot not alive
        d["not_alive"] = "#9B8B8B"
        # txt
        d["txt"] = "#330000"

    def _init_command_colors(self):
        """
        Initialisation des couleurs par défaut : comandes
        """
        d = self._coldict["nav"]
        # dict des boutons de commandes
        d["btns_cmd"] = dict()
        d["btns_cmd"]["1"] = {"bgcolor": None, "bdcolor": "#330000"}
        d["btns_cmd"]["2"] = {"bgcolor": "#FFFFFF", "bdcolor": None}
        d["btns_cmd"]["3"] = {"bgcolor": None, "bdcolor": "#FFFFFF"}
        d["btns_cmd"]["4"] = {"bgcolor": "#5B3333", "bdcolor": None}
        d["btns_cmd"]["5"] = {"bgcolor": None, "bdcolor": "#CC3366"}
        # dict des boutons globaux
        d["btns_glb"] = dict()
        d["btns_glb"]["1"] = {"bgcolor": "#330000", "bdcolor": None}
        d["btns_glb"]["2"] = {"bgcolor": "#BEAEAE", "bdcolor": None}
        d["btns_glb"]["3"] = {"bgcolor": None, "bdcolor": "#BEAEAE"}
        d["btns_glb"]["4"] = {"bgcolor": "#BEAEAE", "bdcolor": None}
        d["btns_glb"]["5"] = {"bgcolor": "#BEAEAE", "bdcolor": None}
        # autre style :
        d["btns_alt"] = dict()
        d["btns_alt"]["1"] = {"bgcolor": None, "bdcolor": "#330000"}
        d["btns_alt"]["2"] = {"bgcolor": None, "bdcolor": "#BEAEAE"}
        d["btns_alt"]["3"] = {"bgcolor": None, "bdcolor": "#BEAEAE"}
        d["btns_alt"]["4"] = {"bgcolor": None, "bdcolor": "#BEAEAE"}
        d["btns_alt"]["5"] = {"bgcolor": "#BEAEAE", "bdcolor": None}
        # textes :
        d["titre"] = "#FFFFFF"
        d["texte"] = "#FFCC00"
        d["info"] = "#CCFF00"
        # couleurs de fonds :
        d["bg_action"] = "#DCAD1F"
        d["bg_direct"] = "#B9AD42"
        d["bg_param"] = "#DC7942"
        d["bg_valid"] = "#BA7842"
        d["bg_input"] = "#330000"

    def _init_net_colors(self):
        """
        Couleurs des flèches réseau
        """
        d = self._coldict["net"]
        # couleurs associées aux statuts de connection :
        d[CustomRequestHelper.STATUS_SHUTDOWN] = "#CC3366"
        d[CustomRequestHelper.STATUS_DISCONNECTED] = "#CDC1C1"
        d[CustomRequestHelper.STATUS_ERROR_CONNECTION] = "#CC3366"
        d[CustomRequestHelper.STATUS_UNDEFINED] = "#FFCC00"
        d[CustomRequestHelper.STATUS_CONNECTED] = "#669900"
        d[CustomRequestHelper.STATUS_REJECTED] = "#CC3366"

    #-----> Initialisations des images :
    def _init_common_rsc(self):
        """
        Initialise les ressources communes
        """
        d = self._srcdict["common"]
        path = self.common_path
        # définition des sources :
        d["transp"] = {"src": PIL.Image.open(path + "transp.png")}
        d["null"] = {"src": PIL.Image.open(path + "null.png")}

    def _init_screens_rsc(self):
        """
        Initialise les ressources d'habillages d'écrans
        """
        d = self._srcdict["screens"]
        path = self.screens_path
        # définition des sources :
        d["neutral"] = {"src": PIL.Image.open(path + "neutre.png")}
        d["txt_loading"] = {"src": PIL.Image.open(path + "txt_charge_appli.png")}
        d["txt_partie"] = {"src": PIL.Image.open(path + "txt_charge_partie.png")}
        d["txt_resize"] = {"src": PIL.Image.open(path + "txt_resize.png")}
        d["visuel_loading"] = {"src": PIL.Image.open(path + "visuel_charge_appli.png")}
        d["visuel_partie"] = {"src": PIL.Image.open(path + "visuel_charge_partie.png")}
        d["visuel_resize"] = {"src": PIL.Image.open(path + "visuel_resize.png")}
        d["entete"] = {"src": PIL.Image.open(path + "entete_final.png")}
        d["entete_light"] = {"src": PIL.Image.open(path + "entete_final_light.png")}
        d["footer4"] = {"src": PIL.Image.open(path + "footer_4.png")}
        d["footer_light"] = {"src": PIL.Image.open(path + "footer_light.png")}
        d["footer_tk"] = {"src": PIL.Image.open(path + "footer_tk.png")}
        d["decor_hunter"] = {"src": PIL.Image.open(path + "hunter_decor_2.png")}
        d["client_pg"] = {"src": PIL.Image.open(path + "txt_client_pg.png")}
        d["stand_pg"] = {"src": PIL.Image.open(path + "txt_stand_pg.png")}
        d["licence"] = {"src": PIL.Image.open(path + "txt_licence.png")}
        d["aide"] = {"src": PIL.Image.open(path + "aide_clavier_2.png")}
        d["txt_net_start"] = {"src": PIL.Image.open(path + "txt_net_start.png")}
        d["txt_net_wait"] = {"src": PIL.Image.open(path + "txt_net_wait.png")}
        d["bg_load"] = {"src": PIL.Image.open(path + "fond_courbe.png")}
        d["bg_menu"] = {"src": PIL.Image.open(path + "fond_mono_4_exp.png")}
        d["bg_load_2"] = {"src": PIL.Image.open(path + "fond_courbe_load.png")}
        d["bg_partie"] = {"src": PIL.Image.open(path + "fond_mono_3_exp.png")}
        # création des images exportées :
        for k in d.keys():
            d[k]["exportimg"] = self.export_image_from_PIL(d[k]["src"])

    def _init_loading_rsc(self):
        """
        Ressources supplémentaires pour les écrans de chargement
        """
        d = self._srcdict["loading"]
        path = self.loading_path
        d["load_1"] = {"src": PIL.Image.open(path + "jauge_def0001.png")}
        d["load_2"] = {"src": PIL.Image.open(path + "jauge_def0002.png")}
        d["load_3"] = {"src": PIL.Image.open(path + "jauge_def0003.png")}
        d["load_4"] = {"src": PIL.Image.open(path + "jauge_def0004.png")}
        d["load_5"] = {"src": PIL.Image.open(path + "jauge_def0005.png")}
        d["load_6"] = {"src": PIL.Image.open(path + "jauge_def0006.png")}
        d["load_7"] = {"src": PIL.Image.open(path + "jauge_def0007.png")}
        d["load_8"] = {"src": PIL.Image.open(path + "jauge_def0008.png")}
        d["load_9"] = {"src": PIL.Image.open(path + "jauge_def0009.png")}
        d["load_10"] = {"src": PIL.Image.open(path + "jauge_def0010.png")}
        d["load_11"] = {"src": PIL.Image.open(path + "jauge_def0011.png")}
        d["load_12"] = {"src": PIL.Image.open(path + "jauge_def0012.png")}
        d["load_13"] = {"src": PIL.Image.open(path + "jauge_def0013.png")}
        d["load_14"] = {"src": PIL.Image.open(path + "jauge_def0014.png")}
        d["load_15"] = {"src": PIL.Image.open(path + "jauge_def0015.png")}
        d["load_16"] = {"src": PIL.Image.open(path + "jauge_def0016.png")}
        d["load_17"] = {"src": PIL.Image.open(path + "jauge_def0017.png")}
        d["load_18"] = {"src": PIL.Image.open(path + "jauge_def0018.png")}
        d["load_19"] = {"src": PIL.Image.open(path + "jauge_def0019.png")}
        d["load_20"] = {"src": PIL.Image.open(path + "jauge_def0020.png")}
        # exports
        for imgdict in d.values():
            src = imgdict["src"]
            imgdict["exportimg"] = self.export_image_from_PIL(src)

    def _init_accueil_rsc(self):
        """
        Initialisation des ressources de l'écran d'accueil.
        """
        d = self._srcdict["accueil"]
        path = self.accueil_path
        # définition des sources :
        # - images fixes :
        d["visuel"] = {"src": PIL.Image.open(path + "visuel_menu_8.png")}
        d["consignes"] = {"src": PIL.Image.open(path + "txt_consigne_menu.png")}
        d["txt_menu"] = {"src": PIL.Image.open(path + "txt_menu.png")}
        # création des images exportées :
        for k in d.keys():
            d[k]["exportimg"] = self.export_image_from_PIL(d[k]["src"])
        # - boutons :
        self.listniveauxmenu = ["niv1", "niv2", "niv3"]
        self.listmodesmenu = ["partie", "demo"]
        names = self.listniveauxmenu + self.listmodesmenu
        states = ["1", "2", "3", "4"]  # pas d'état inactif
        for name in names:
            for state in states:
                img = name + "000" + state + ".png"
                imgsrc = PIL.Image.open(path + "btns/" + img)
                k = "btn_" + name + "_" + state
                # enregistrement et export
                d[k] = {"src": imgsrc, "exportimg": self.export_image_from_PIL(imgsrc)}

    def _init_command_rsc(self):
        """
        Initialise les ressources de navigation
        """
        self._init_command_buttons()
        self._init_command_imgs()

    def _init_command_buttons(self):
        """
        Boutons
        """
        d = self._srcdict["nav"]
        path = self.nav_path
        # définition des sources :
        self.listbtnsnames = [
            "top",
            "bottom",
            "left",
            "right",
            "move",
            "porte",
            "mur",
            "kill",
            "grenade",
            "mine",
            "valider",
            "radio_1",
            "radio_2",
            "radio_3",
            "radio_4",
            "radio_5",
            "radio_6",
            "radio_9",
            "radio_13",
            "radio_17",
            "radio_25",
            "menu",
            "menu_2",
            "quitter",
            "quitter_2",
            "start",
            "aide",
            "fullscreen",
        ]
        for name in self.listbtnsnames:
            bgn = "btn_" + name + "0001.png"
            bdn = "btn_" + name + "0002.png"
            bgsrc = PIL.Image.open(path + bgn)
            bdsrc = PIL.Image.open(path + bdn)
            size = bgsrc.size
            mode = "RGBA"
            if name in ["menu", "quitter", "menu_2", "quitter_2", "aide", "fullscreen"]:
                shapecoldict = self._coldict["nav"]["btns_glb"]
            elif name == "start":
                shapecoldict = self._coldict["nav"]["btns_alt"]
            else:
                shapecoldict = self._coldict["nav"]["btns_cmd"]
            for state in self.listbtnstates:
                bgcolor = shapecoldict[state]["bgcolor"]
                bdcolor = shapecoldict[state]["bdcolor"]
                imgbtn = PIL.Image.new(mode, size)
                if bgcolor != None:
                    bgimg = bgsrc.copy()
                    colbg = ColorHelper.color_png(bgimg, bgcolor)
                    imgbtn.paste(colbg, (0, 0), colbg)
                if bdcolor != None:
                    bdimg = bdsrc.copy()
                    colbd = ColorHelper.color_png(bdimg, bdcolor)
                    imgbtn.paste(colbd, (0, 0), colbd)
                # enregistrement :
                k = "btn_" + name + "_" + state
                d[k] = {"src": imgbtn, "exportimg": self.export_image_from_PIL(imgbtn)}

    def _init_command_imgs(self):
        """
        Images fixes
        """
        d = self._srcdict["nav"]
        path = self.nav_path
        # définition des sources :
        self.liststaticnames = [
            "titre_action",
            "titre_commande",
            "titre_direction",
            "titre_parametres",
            "distance",
            "distance_2",
            "puissance",
            "puissance_2",
            "silhouette",
            "silhouette0001",
            "titre_infos",
            "symbole_commande",
            "titre_joueurs",
            "visuel_deconnecte",
            "visuel_elimine",
            "visuel_spectateur",
        ]
        for name in self.liststaticnames:
            coltxt = None
            if name in [
                "titre_action",
                "titre_commande",
                "titre_direction",
                "titre_parametres",
            ]:
                coltxt = self.get_color("nav", "titre")
            elif name in ["distance", "puissance", "silhouette", "silhouette0001"]:
                coltxt = self.get_color("nav", "titre")
            elif name in ["txt_actions", "txt_ligne_cmd"]:
                coltxt = self.get_color("nav", "texte")
            elif name in ["titre_infos", "symbole_commande"]:
                coltxt = self.get_color("nav", "info")
            elif name == "titre_joueurs":
                coltxt = self.get_color("bots", "titre")
            src = PIL.Image.open(path + name + ".png")
            if coltxt != None:
                src = ColorHelper.color_png(src, coltxt)
            d[name] = {"src": src, "exportimg": self.export_image_from_PIL(src)}

    def _init_carte_rsc(self):
        """
        Définition des sources de la carte
        """
        d = self._srcdict["carte"]
        path = self.carte_path
        # définition des sources :
        d["mur_ext"] = {"src": PIL.Image.open(path + "mqlab_20002.png")}
        d["mur"] = {"src": PIL.Image.open(path + "mqlab_20003.png")}
        d["vide"] = {"src": PIL.Image.open(path + "mqlab_20004.png")}
        d["porte"] = {"src": PIL.Image.open(path + "mqlab_20005.png")}
        d["bonus"] = {"src": PIL.Image.open(path + "mqlab_20006.png")}
        d["hunter"] = {"src": PIL.Image.open(path + "mqlab_20010.png")}
        d["winner"] = {"src": PIL.Image.open(path + "mqlab_20011.png")}
        d["random"] = {"src": PIL.Image.open(path + "mqlab_20012.png")}
        d["tourist"] = {"src": PIL.Image.open(path + "mqlab_20013.png")}
        d["sapper"] = {"src": PIL.Image.open(path + "mqlab_20014.png")}
        d["builder"] = {"src": PIL.Image.open(path + "mqlab_20015.png")}
        d["grenade"] = {"src": PIL.Image.open(path + "mqlab_20016.png")}
        d["mine_1"] = {"src": PIL.Image.open(path + "mqlab_20017.png")}
        d["mine_5"] = {"src": PIL.Image.open(path + "mqlab_20018.png")}
        d["mine_9"] = {"src": PIL.Image.open(path + "mqlab_20019.png")}
        d["mine_13"] = {"src": PIL.Image.open(path + "mqlab_20020.png")}
        d["mine_17"] = {"src": PIL.Image.open(path + "mqlab_20021.png")}
        d["mine_25"] = {"src": PIL.Image.open(path + "mqlab_20022.png")}
        d["hunter_bg"] = {"src": PIL.Image.open(path + "mqlab_20034.png")}
        d["winner_bg"] = {"src": PIL.Image.open(path + "mqlab_20035.png")}
        d["random_bg"] = {"src": PIL.Image.open(path + "mqlab_20036.png")}
        d["tourist_bg"] = {"src": PIL.Image.open(path + "mqlab_20037.png")}
        d["sapper_bg"] = {"src": PIL.Image.open(path + "mqlab_20038.png")}
        d["builder_bg"] = {"src": PIL.Image.open(path + "mqlab_20039.png")}
        d["humain_bg"] = {"src": PIL.Image.open(path + "mqlab_20040.png")}
        d["sortie"] = {"src": PIL.Image.open(path + "mqlab_20041.png")}
        d["cible"] = {"src": PIL.Image.open(path + "mqlab_20042.png")}
        d["builder_fil"] = {"src": PIL.Image.open(path + "mqlab_20043.png")}
        d["hunter_fil"] = {"src": PIL.Image.open(path + "mqlab_20044.png")}
        d["random_fil"] = {"src": PIL.Image.open(path + "mqlab_20045.png")}
        d["sapper_fil"] = {"src": PIL.Image.open(path + "mqlab_20046.png")}
        d["tourist_fil"] = {"src": PIL.Image.open(path + "mqlab_20047.png")}
        d["winner_fil"] = {"src": PIL.Image.open(path + "mqlab_20048.png")}
        d["explosion_1"] = {"src": PIL.Image.open(path + "mqlab_20067.png")}
        d["explosion_2"] = {"src": PIL.Image.open(path + "mqlab_20068.png")}
        d["explosion_3"] = {"src": PIL.Image.open(path + "mqlab_20069.png")}
        d["explosion_4"] = {"src": PIL.Image.open(path + "mqlab_20070.png")}
        d["explosion_5"] = {"src": PIL.Image.open(path + "mqlab_20071.png")}
        d["number_1"] = {"src": PIL.Image.open(path + "perso0001.png")}
        d["number_2"] = {"src": PIL.Image.open(path + "perso0002.png")}
        d["number_3"] = {"src": PIL.Image.open(path + "perso0003.png")}
        d["number_4"] = {"src": PIL.Image.open(path + "perso0004.png")}
        d["number_5"] = {"src": PIL.Image.open(path + "perso0005.png")}
        d["number_6"] = {"src": PIL.Image.open(path + "perso0006.png")}
        d["number_7"] = {"src": PIL.Image.open(path + "perso0007.png")}
        d["number_8"] = {"src": PIL.Image.open(path + "perso0008.png")}
        d["number_9"] = {"src": PIL.Image.open(path + "perso0009.png")}
        d["number_10"] = {"src": PIL.Image.open(path + "perso0010.png")}
        d["human_bg"] = {"src": PIL.Image.open(path + "perso0011.png")}
        # debug
        rscpath2 = "carte/"
        path2 = self.skinpath + rscpath2
        d["debug1"] = {"src": PIL.Image.open(path2 + "debug0001.png")}
        d["debug2"] = {"src": PIL.Image.open(path2 + "debug0002.png")}
        d["debug3"] = {"src": PIL.Image.open(path2 + "debug0003.png")}

    def _init_net_rsc(self):
        """
        Flèches réseau colorées
        """
        d = self._srcdict["net"]
        path = self.nav_path
        # génération des images :
        coldict = self._coldict["net"]
        # send :
        src_send = PIL.Image.open(path + "fleches_net0001.png")
        for status, col in coldict.items():
            name = "send_" + status
            colimg = src_send.copy()
            colimg = ColorHelper.color_png(colimg, col)
            d[name] = {"src": colimg}
        # receive :
        src_rec = PIL.Image.open(path + "fleches_net0002.png")
        for status, col in coldict.items():
            name = "receive_" + status
            colimg = src_rec.copy()
            colimg = ColorHelper.color_png(colimg, col)
            d[name] = {"src": colimg}

    #-----> Getters de couleurs
    def get_color(self, cat, name, state=None):
        """
        Retourne une couleur
        """
        if cat in self._coldict.keys() and name in self._coldict[cat].keys():
            if isinstance(self._coldict[cat][name], dict):
                # cas des boutons
                d = self._coldict[cat][name]
                if state in d.keys():
                    return d[state]
            else:
                d = self._coldict[cat]
                return d[name]
        return None

    #-----> Getters d'images exportées
    def get_image(self, cat, name, size=None, state=None):
        """
        Retourne une image exportée
        
        * cat : catégorie de l'image
        * name : nom
        * size : (w, h) optionnel
        * state : int, pour les 5 états d'un bouton
        
        """
        if cat == "carte":
            # on teste en premier les images les plus demandées
            return self.get_dynamic_image(cat, name, size)
        elif state != None:
            return self.get_button_image(name, state)
        elif size != None:
            return self.get_dynamic_image(cat, name, size)
        else:
            return self.get_fixed_image(cat, name)

    def get_dynamic_image(self, cat, name, size):
        """
        Retourne une image à la taille demandée
        """
        imgexp = None
        if cat in self._srcdict.keys() and name in self._srcdict[cat].keys():
            dict_img = self._srcdict[cat][name]
            # au maximum on considère la taille de la source
            size = min(size, self.get_source_size(cat, name))
            if size in dict_img.keys():
                # l'image exportée a déja été calculée :
                imgexp = dict_img[size]
            else:
                # on resample:
                img = dict_img["src"]
                newimg = img.resize(size, PIL.Image.ANTIALIAS)
                # on ajoute au dict l'image exportée associée à la taille demandée :
                dict_img[size] = self.export_image_from_PIL(newimg)
                imgexp = dict_img[size]
        return imgexp

    def get_button_image(self, name, statenum):
        """
        Retourne l'image (taille fixe) associée au nom name et à l'indice
        d'état statenum
        """
        d = None
        if name in self.listbtnsnames:
            d = self._srcdict["nav"]
        elif name in self.listniveauxmenu or name in self.listmodesmenu:
            d = self._srcdict["accueil"]
        if d != None and str(statenum) in self.listbtnstates:
            k = "btn_" + name + "_" + str(statenum)
            return d[k]["exportimg"]
        return None

    def get_fixed_image(self, cat, name):
        """
        Retourne une image à sa taille originelle
        """
        if cat in self._srcdict.keys() and name in self._srcdict[cat].keys():
            d = self._srcdict[cat]
            if "exportimg" not in d[name].keys():
                d[name]["exportimg"] = self.export_image_from_PIL(d[name]["src"])
            return d[name]["exportimg"]
        return None

    def get_source_size(self, cat, name):
        """
        Retourne les dimensions de la source
        """
        size = None
        if cat in self._srcdict.keys() and name in self._srcdict[cat].keys():
            src = self._srcdict[cat][name]["src"]
            size = src.size
        return size

    def get_image_for_case(self, case, size, applyopt=True):
        """
        Retourne une image exportée associé à la donnée objet lab.Case (ou subclasse)
        
        * case : donnée objet de type lab.Case
        * size : dimensions (w, h)
        * applyopt : indique si l'on prend en compte self.optmode
        
        """
        typecase = case.type_case
        name = None
        # recherche du nom de l'image associée :
        if typecase == LabHelper.CASE_MUR_PERIMETRE:
            name = "mur_ext"
        elif typecase == LabHelper.CASE_MUR:
            name = "mur"
        elif typecase == LabHelper.CASE_VIDE:
            name = "vide"
        elif typecase == LabHelper.CASE_PORTE:
            name = "porte"
        elif typecase == LabHelper.CASE_BONUS:
            name = "bonus"
        elif typecase == LabHelper.CASE_ANIMATION:
            # à faire
            visible = case.visible
            if not visible:
                name = None
            else:
                scenario_anim = case.scenario_anim
                if scenario_anim == LabHelper.ANIMATION_SCENARIO["EXPLOSION"]:
                    local_step = case.local_step
                    if local_step == 0:
                        name = "explosion_1"
                    elif local_step == 1:
                        name = "explosion_2"
                    elif local_step == 2:
                        name = "explosion_3"
                    elif local_step == 3:
                        name = "explosion_4"
                    elif local_step == 4:
                        name = "explosion_5"
                    else:
                        name = "vide"
        elif typecase == LabHelper.CASE_ROBOT:
            # méthode dédiée :
            return self._get_image_for_bot(case, size, applyopt=applyopt)
        elif typecase == LabHelper.CASE_GRENADE:
            name = "grenade"
        elif typecase == LabHelper.CASE_DANGER:
            if case.danger_type == CaseDanger.DANGER_MINE:
                if case.danger_impact == 1:
                    name = "mine_1"
                elif case.danger_impact == 5:
                    name = "mine_5"
                elif case.danger_impact == 9:
                    name = "mine_9"
                elif case.danger_impact == 13:
                    name = "mine_13"
                elif case.danger_impact == 17:
                    name = "mine_17"
                elif case.danger_impact == 25:
                    name = "mine_25"
        elif typecase == LabHelper.CASE_SORTIE:
            name = "sortie"
        elif typecase == LabHelper.CASE_TARGET:
            name = "cible"
        elif typecase == LabHelper.CASE_DEBUG:
            if case.face == "1":
                name = "debug1"
            elif case.face == "2":
                name = "debug2"
            elif case.face == "3":
                name = "debug3"
        # retour de l'image associée :
        imgexp = None
        if name != None:
            if name in ["transp", "null"]:
                imgexp = self.get_image("common", name, size=size)
            else:
                imgexp = self.get_image("carte", name, size=size)
        return imgexp

    def _get_image_for_bot(self, case, size, applyopt=True):
        """
        Méthode dédiée à la représentation des robots. 
        applyopt : indique si l'on prend en compte self.optmode
        """
        behavior = case.behavior
        if behavior == CaseRobot.BEHAVIOR_HUMAN:
            return self._get_image_for_human(case, size, applyopt=applyopt)
        # bots
        color = case.color
        compound = False
        if color != None:
            compound = True
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
        imgexp = None
        if not compound:
            if name == "transp":
                imgexp = self.get_image("common", "transp", size=size)
            else:
                imgexp = self.get_image("carte", name, size=size)
        else:
            colorname = name + str(color) + str(case.alive)
            # La source dynamique existe t'elle ?
            if self.optmode and applyopt:
                suffix = "opt"
            else:
                suffix = "alpha"
            dynname = colorname + suffix
            if dynname not in self._srcdict["carte"].keys():
                # On crée les sources :
                bgsrc = self._srcdict["carte"][name + "_bg"]["src"]
                filsrc = self._srcdict["carte"][name + "_fil"]["src"]
                if case.alive:
                    # on colorise le fond :
                    bgimg = bgsrc.copy()
                    bgimg = ColorHelper.color_png(bgimg, color)
                    # on ajoute la vue filaire
                    filimg = filsrc.copy()
                    bgimg.paste(filimg, None, filimg)
                else:
                    # on colorise le fond :
                    coldead = self._coldict["carte"]["bot_dead"]
                    bgimg = bgsrc.copy()
                    bgimg = ColorHelper.color_png(bgimg, coldead)
                    # on ajoute la vue filaire
                    filimg = filsrc.copy()
                    bgimg.paste(filimg, None, filimg)
                # en mode optimisé :
                if self.optmode and applyopt:
                    # pas de transparence, on colle l'image sur une case vide :
                    cvsrc = self._srcdict["carte"]["vide"]["src"]
                    cvimg = cvsrc.copy()
                    cvimg.paste(bgimg, None, bgimg)
                    bgimg = cvimg
                # on enregistre la nouvelle source :
                self._srcdict["carte"][dynname] = {"src": bgimg}
            # Standard :
            imgexp = self.get_image("carte", dynname, size=size)
        return imgexp

    def _get_image_for_human(self, case, size, applyopt=True):
        """
        Méthode dédiée aux persos humains
        """
        # nom de base de l'image crée
        hnumber = int(case.human_number)
        if hnumber in range(1, 11):
            name = str("humain_" + str(hnumber))
            num = str("number_" + str(hnumber))
        else:
            # à améliorer
            name = "humain"
            num = None
        color = case.color
        colorname = name + str(color) + str(case.alive)
        # La source dynamique existe t'elle ?
        if self.optmode and applyopt:
            suffix = "opt"
        else:
            suffix = "alpha"
        dynname = colorname + suffix
        if dynname not in self._srcdict["carte"].keys():
            # On crée les sources :
            bgsrc = self._srcdict["carte"]["human_bg"]["src"]
            numsrc = None
            if num != None:
                numsrc = self._srcdict["carte"][num]["src"]
            if case.alive:
                # on colorise le fond :
                bgimg = bgsrc.copy()
                bgimg = ColorHelper.color_png(bgimg, color)
                if numsrc != None:
                    # on ajoute le numéro
                    compcolor = ColorHelper.get_complementary_color(color)
                    numimg = numsrc.copy()
                    numimg = ColorHelper.color_png(numimg, compcolor)
                    bgimg.paste(numimg, None, numimg)
            else:
                # on colorise le fond :
                coldead = self._coldict["carte"]["bot_dead"]
                bgimg = bgsrc.copy()
                bgimg = ColorHelper.color_png(bgimg, coldead)
                if numsrc != None:
                    # on ajoute le numéro
                    compcolor = ColorHelper.get_complementary_color(color)
                    numimg = numsrc.copy()
                    numimg = ColorHelper.color_png(numimg, compcolor)
                    bgimg.paste(numimg, None, numimg)
            # en mode optimisé :
            if self.optmode and applyopt:
                # pas de transparence, on colle l'image sur une case vide :
                cvsrc = self._srcdict["carte"]["vide"]["src"]
                cvimg = cvsrc.copy()
                cvimg.paste(bgimg, None, bgimg)
                bgimg = cvimg
            # on enregistre la nouvelle source :
            self._srcdict["carte"][dynname] = {"src": bgimg}
        # Standard :
        imgexp = self.get_image("carte", dynname, size=size)
        return imgexp

    def get_loading_images(self):
        """
        Retourne la liste des images de preloading
        """
        rlist = list()
        for dictimg in self._srcdict["loading"].values():
            rlist.append(dictimg["exportimg"])
        return rlist
