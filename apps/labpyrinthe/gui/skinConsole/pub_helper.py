#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper de publication de l'interface console.
"""
# imports :
import math
import labpyproject.core.net.custom_TCP as ctcp
from labpyproject.apps.labpyrinthe.app.app_types import AppTypes

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["PublicationHelper"]
# classes :
class PublicationHelper:
    """
    Helper de publication de textes de GUIConsole
    """

    # statique
    EXT_BDR = chr(9608) #: caractère pour bordure extérieure
    INT_BDR = chr(9618) #: caractère pour bordure intérieure
    # méthodes
    def __init__(self):
        """
        Constructeur
        """
        # type d'application (client / serveur / standalone)
        self.type_app = None
        # Etat :
        self.partie_state = None
        # Dimensions globales :
        self._width = None
        self._height = None
        self._default_width = 80
        self._default_height = 30
        # identifiants de contenus :
        self._content_names = [
            "header",
            "footer",
            "info",
            "wait",
            "menu",
            "carte",
            "bots",
            "server_list",
            "server_partie",
        ]
        # identifiants d'écrans :
        self._screen_names = ["wait", "menu", "partie", "server"]
        # cache de contenu :
        self._cache_dict = dict()
        # contenus unitaires :
        self._cache_dict["header"] = {"updated": False, "value": None, "content": None}
        self._cache_dict["footer"] = {"updated": False, "value": None, "content": None}
        self._cache_dict["info"] = {"updated": False, "value": None, "content": None}
        self._cache_dict["wait"] = {"updated": False, "value": None, "content": None}
        self._cache_dict["menu"] = {"updated": False, "value": None, "content": None}
        self._cache_dict["carte"] = {"updated": False, "value": None, "content": None}
        self._cache_dict["bots"] = {"updated": False, "value": None, "content": None}
        self._cache_dict["server_list"] = {
            "updated": False,
            "value": None,
            "content": None,
        }
        self._cache_dict["server_partie"] = {
            "updated": False,
            "value": None,
            "content": None,
        }
        # écrans :
        self._cache_dict["screen_wait"] = {"updated": False, "txt": None}
        self._cache_dict["screen_menu"] = {"updated": False, "txt": None}
        self._cache_dict["screen_partie"] = {"updated": False, "txt": None}
        self._cache_dict["screen_server"] = {"updated": False, "txt": None}
        # dernier écran affiché :
        self._last_screen_name = None
        # mémo textes de msg et d'input :
        self._input_txt = None
        self._info_txt = None

    def discard_content(self, name):
        """
        Invalide un type de contentu
        """
        if name in self._content_names:
            # discard écrans liés :
            if name in ["wait", "header", "footer", "info"]:
                self._cache_dict["screen_wait"]["updated"] = False
            if name in ["menu", "header", "footer", "info"]:
                self._cache_dict["screen_menu"]["updated"] = False
            if name in ["carte", "bots", "header", "footer", "info"]:
                self._cache_dict["screen_partie"]["updated"] = False
            if name in [
                "wait",
                "header",
                "footer",
                "info",
                "server_list",
                "server_partie",
            ]:
                self._cache_dict["screen_server"]["updated"] = False

    #-----> Interface avec la GUI :
    def register_partie_state(self, state):
        """
        Enregistre l'état actuel de la partie
        """
        if state != self.partie_state:
            self.partie_state = state

    #-----> Ecrans complets :
    def get_screen(self, name, **kwargs):
        """
        Interface de publication d'écrans
        
        * name : str in self._screen_names
        * kwargs :
        
            * msg = str pour "wait"
            
        """
        txt = None
        if name in self._screen_names:
            # contenu de l'écran :
            if name == "wait":
                txt = self._get_screen_wait()
            elif name == "menu":
                txt = self._get_screen_menu()
            elif name == "partie":
                dictargs = None
                if "dictargs" in kwargs.keys():
                    dictargs = kwargs["dictargs"]
                txt = self._get_screen_partie(dictargs)
            elif name == "server":
                dictargs = None
                if "dictargs" in kwargs.keys():
                    dictargs = kwargs["dictargs"]
                txt = self._get_screen_server(dictargs)
            self._last_screen_name = name
        # retour :
        return txt

    def update_screen_with_info(self, dictargs):
        """
        Republie le dernier écran en modifiant le message d'info
        """
        self.update_content("info", dictargs=dictargs)
        txt = self.get_screen(self._last_screen_name)
        return txt

    def update_screen(self):
        """
        Republie le dernier écran
        """
        txt = self.get_screen(self._last_screen_name)
        return txt

    def _get_screen_wait(self):
        """
        Retourne l'écran d'attente
        """
        extchar = PublicationHelper.EXT_BDR
        intchar = PublicationHelper.INT_BDR
        txt = None
        if not self._cache_dict["screen_wait"]["updated"]:
            # Dimensions
            w, h = self._default_width, self._default_height
            # Header :
            block_header = self._get_sub_block(
                "header", w - 2, None, bottomchar=intchar
            )
            # Info :
            block_info = self._get_sub_block("info", w - 2, None, topchar=intchar)
            # Footer :
            block_footer = self._get_sub_block("footer", w - 2, None, topchar=intchar)
            # wait :
            h_w = h
            real_blocks = [
                b for b in [block_header, block_info, block_footer] if b != None
            ]
            for block in real_blocks:
                h_w -= self.mesure_content(block)[1]
            block_wait = self._get_sub_block("wait", w - 2, h_w, xchar=None, ychar=None)
            # publication finale :
            block_list = [
                b
                for b in [block_header, block_wait, block_info, block_footer]
                if b != None
            ]
            final_content = list()
            for block in block_list:
                final_content.extend(block)
            # cadre global :
            framed_final = self.draw_frame(final_content, xchar=extchar, ychar=extchar)
            # txt :
            txt = self.get_text_from_content(framed_final)
            self._cache_dict["screen_wait"]["txt"] = txt
            self._cache_dict["screen_wait"]["updated"] = True
        else:
            txt = self._cache_dict["screen_wait"]["txt"]
        return txt

    def _get_screen_menu(self):
        """
        Retourne l'écran de menu :
        """
        extchar = PublicationHelper.EXT_BDR
        intchar = PublicationHelper.INT_BDR
        txt = None
        if not self._cache_dict["screen_menu"]["updated"]:
            # Dimensions
            w, h = self._default_width, self._default_height
            # Header :
            block_header = self._get_sub_block(
                "header", w - 2, None, bottomchar=intchar
            )
            # Info :
            block_info = self._get_sub_block("info", w - 2, None, topchar=intchar)
            # Footer :
            block_footer = self._get_sub_block("footer", w - 2, None, topchar=intchar)
            # menu :
            h_m = h
            real_blocks = [
                b for b in [block_header, block_info, block_footer] if b != None
            ]
            for block in real_blocks:
                h_m -= self.mesure_content(block)[1]
            block_menu = self._get_sub_block("menu", w - 2, h_m, xchar=None, ychar=None)
            # publication finale :
            block_list = [
                b
                for b in [block_header, block_menu, block_info, block_footer]
                if b != None
            ]
            final_content = list()
            for block in block_list:
                final_content.extend(block)
            # cadre global :
            framed_final = self.draw_frame(final_content, xchar=extchar, ychar=extchar)
            # txt :
            txt = self.get_text_from_content(framed_final)
            self._cache_dict["screen_menu"]["txt"] = txt
            self._cache_dict["screen_menu"]["updated"] = True
        else:
            txt = self._cache_dict["screen_menu"]["txt"]
        return txt

    def _get_screen_partie(self, dictargs):
        """
        Retourne l'écran partie
        """
        extchar = PublicationHelper.EXT_BDR
        intchar = PublicationHelper.INT_BDR
        txt = None
        if not self._cache_dict["screen_partie"]["updated"]:
            # Dimensions
            w = self._default_width
            # Game :
            # carte :
            if dictargs != None:
                self.update_content("carte", dictargs=dictargs)
            block_carte = self._cache_dict["carte"]["content"]
            # liste bots :
            if dictargs != None:
                self.update_content("bots", dictargs=dictargs)
            block_bots = self._cache_dict["bots"]["content"]
            # ligne carte + bots :
            if block_carte == None or block_bots == None:
                return None
            block_game = self.create_line_content(
                [block_carte, block_bots],
                vsep="  " + intchar + "  ",
                leftsep=" ",
                rightsep=" ",
            )
            game_width, game_height = self.mesure_content(block_game)
            pubw = max(game_width, w - 2)
            pubh = max(game_height, 25)
            block_game = self.place_content_in_frame(block_game, pubw, pubh)
            # Header :
            block_header = self._get_sub_block("header", pubw, None, bottomchar=intchar)
            # Info :
            block_info = self._get_sub_block("info", pubw, None, topchar=intchar)
            # Footer :
            block_footer = self._get_sub_block("footer", pubw, None, topchar=intchar)
            # publication finale :
            block_list = [
                b
                for b in [block_header, block_game, block_info, block_footer]
                if b != None
            ]
            final_content = list()
            for block in block_list:
                final_content.extend(block)
            # cadre global :
            framed_final = self.draw_frame(final_content, xchar=extchar, ychar=extchar)
            # txt :
            txt = self.get_text_from_content(framed_final)
            self._cache_dict["screen_partie"]["txt"] = txt
            self._cache_dict["screen_partie"]["updated"] = True
        else:
            txt = self._cache_dict["screen_partie"]["txt"]
        return txt

    def _get_screen_server(self, dictargs):
        """
        Retourne l'écran serveur
        """
        extchar = PublicationHelper.EXT_BDR
        intchar = PublicationHelper.INT_BDR
        txt = None
        if not self._cache_dict["screen_server"]["updated"]:
            # Dimensions
            w = self._default_width
            # Liste clients :
            if dictargs != None:
                self.update_content("server_list", dictargs=dictargs)
            block_liste = self._cache_dict["server_list"]["content"]
            # infos partie :
            block_partie = self._cache_dict["server_partie"]["content"]
            # bloc serveur complet :
            block_serveur = self.create_column_content(
                [block_liste, block_partie], hsep="*", topsep=" ", bottomsep=" "
            )
            svr_width, svr_height = self.mesure_content(block_serveur)
            pubw = max(svr_width, w - 2)
            pubh = max(svr_height, 25)
            block_serveur = self.place_content_in_frame(block_serveur, pubw, pubh)
            # Header :
            block_header = self._get_sub_block("header", pubw, None, bottomchar=intchar)
            # Info :
            block_info = self._get_sub_block("info", pubw, None, topchar=intchar)
            # Footer :
            block_footer = self._get_sub_block("footer", pubw, None, topchar=intchar)
            # publication finale :
            block_list = [
                b
                for b in [block_header, block_serveur, block_info, block_footer]
                if b != None
            ]
            final_content = list()
            for block in block_list:
                final_content.extend(block)
            # cadre global :
            framed_final = self.draw_frame(final_content, xchar=extchar, ychar=extchar)
            # txt :
            txt = self.get_text_from_content(framed_final)
            self._cache_dict["screen_server"]["txt"] = txt
            self._cache_dict["screen_server"]["updated"] = True
        else:
            txt = self._cache_dict["screen_server"]["txt"]
        return txt

    def _get_sub_block(
        self,
        name,
        w,
        h,
        xchar=None,
        topchar=None,
        bottomchar=None,
        ychar=None,
        leftchar=None,
        rightchar=None,
    ):
        """
        Retourne un block de contenu unitaire ou None
        """
        block = None
        if name in self._content_names:
            orig_value = self._cache_dict[name]["value"]
            if orig_value != None:
                updated = self._cache_dict[name]["updated"]
                unit_cont = self._cache_dict[name]["content"]
                cont_width = self.mesure_content(unit_cont)[0]
                if not updated or cont_width != w:
                    placed_cont = self.place_content_in_frame(orig_value, w, h)
                    framed_cont = self.draw_frame(
                        placed_cont,
                        xchar=xchar,
                        topchar=topchar,
                        bottomchar=bottomchar,
                        ychar=ychar,
                        leftchar=leftchar,
                        rightchar=rightchar,
                    )
                    self._cache_dict[name]["content"] = framed_cont
                    self._cache_dict[name]["updated"] = True
                block = self._cache_dict[name]["content"]
        return block

    #-----> Update des contenus unitaires :
    def update_content(self, name, **kwargs):
        """
        Interface de mise à jour de contenus
        
        * name : str in self._content_names
        * kwargs :
        
            * msg = str pour les contenus "menu", "info", "header", "wait"
            * dictargs = dict pour les contenus "carte" et "bots"
            
        """
        if name in self._content_names:
            # discard :
            self.discard_content(name)
            self._cache_dict[name]["content"] = None
            # update local :
            content = None
            if name == "carte" and "dictargs" in kwargs.keys():
                content = self._update_carte(kwargs["dictargs"])
                self._cache_dict[name]["content"] = content
                self._cache_dict[name]["updated"] = True
            elif name == "bots" and "dictargs" in kwargs.keys():
                content = self._update_listbots(kwargs["dictargs"])
                self._cache_dict[name]["content"] = content
                self._cache_dict[name]["updated"] = True
            elif name == "server_list" and "dictargs" in kwargs.keys():
                content = self._update_server_list(kwargs["dictargs"])
                self._cache_dict[name]["content"] = content
                self._cache_dict[name]["updated"] = True
            elif name == "server_partie" and "dictargs" in kwargs.keys():
                content = self._update_server_partie(kwargs["dictargs"])
                self._cache_dict[name]["content"] = content
                self._cache_dict[name]["updated"] = True
            elif (
                name == "footer"
                and "dictargs" in kwargs.keys()
                and self.type_app in [AppTypes.APP_SERVER, AppTypes.APP_CLIENT]
            ):
                if self.type_app == AppTypes.APP_SERVER:
                    content = self._format_server_NETInfos(kwargs["dictargs"])
                elif self.type_app == AppTypes.APP_CLIENT:
                    content = self._format_client_NETInfos(kwargs["dictargs"])
                content = self.wrap_content(content, self._default_width - 2)
                self._cache_dict[name]["value"] = content
                self._cache_dict[name]["updated"] = False
            elif name == "info" and "dictargs" in kwargs.keys():
                dictargs = kwargs["dictargs"]
                msg = None
                if "msg" in dictargs.keys():
                    msg = dictargs["msg"]
                is_input = False
                if "is_input" in dictargs.keys():
                    is_input = dictargs["is_input"]
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
                if pub_txt in ["", None]:
                    self._cache_dict[name]["value"] = None
                else:
                    content = pub_txt.split("\n")
                    content = self.wrap_content(content, self._default_width - 2)
                    self._cache_dict[name]["value"] = content
            elif "msg" in kwargs.keys():
                msg = str(kwargs["msg"])
                if msg in ["", None]:
                    self._cache_dict[name]["value"] = None
                else:
                    content = msg.split("\n")
                    content = self.wrap_content(content, self._default_width - 2)
                    self._cache_dict[name]["value"] = content
                self._cache_dict[name]["updated"] = False

    def _update_carte(self, dictargs):
        """
        Mise à jour du contenu de la carte
        """
        # Données :
        cartetxt = dictargs["txt"]
        w, h = dictargs["w"], dictargs["h"]
        # création du contenu :
        carte = self._create_carte_content(cartetxt, w, h)
        return self.wrap_content(carte, None)

    def _update_listbots(self, dictargs):
        """
        Mise à jour des robots
        """
        # Données :
        listrobots = dictargs["robots"]
        # création du contenu :
        bots = self._create_bots_content(listrobots)
        return self.wrap_content(bots, None)

    def _update_server_partie(self, dictargs):
        """
        Infos partie
        """
        partlist = self._create_server_info_partie(dictargs)
        return self.wrap_content(partlist, None)

    def _update_server_list(self, dictargs):
        """
        Mise à jour de la liste de clients
        """
        svrlist = self._create_server_list(dictargs)
        return self.wrap_content(svrlist, None)

    #-----> Publication des contenus unitaires :
    def _create_carte_content(self, cartetxt, w, h):
        """
        Crée la liste de lignes associées à la carte
        """
        rlignes = list()
        titre = ""
        rlignes.append(titre)
        # lignes significatives
        csplit = cartetxt.split("\n")
        lignes = list()
        for l in csplit:
            if len(l) > 0:
                lignes.append(l)
        # Entête :
        entete1 = " " * 2 + "y" + " "
        entete2 = " " + "x" + " " * 2
        j = 0
        while j < w:
            if j <= 9:
                entete1 += " "
                entete2 += str(j)
            else:
                d = str(j)[0]
                u = str(j)[1]
                entete1 += d
                entete2 += u
            j += 1
        ne = len(entete1)
        entete3 = " " * ne
        rlignes.append(entete1)
        rlignes.append(entete2)
        rlignes.append(entete3)
        # Carte :
        i = 0
        while i < h:
            if i <= 9:
                d = " " * 2 + str(i) + " "
            else:
                d = " " + str(i) + " "
            rlignes.append(d + lignes[i])
            i += 1
        rlignes.append("")
        # Retour :
        return rlignes

    def _create_bots_content(self, listrobots):
        """
        Crée la liste de lignes associée aux infos robots
        """
        rlignes = list()
        titre = ""
        rlignes.append(titre)
        # Entete :
        txtcols = ["", "x", "y", "agg.", "vit.", "min.", "gre.", "actif"]
        dims = [1, 3, 3, 4, 4, 4, 5, 5]
        w = 1
        for nb in dims:
            w += nb + 1
        vsep = "-" * w
        rlignes.append(vsep)
        sep = "|"
        entete = sep
        i = 0
        while i < len(dims):
            entete += txtcols[i].center(dims[i]) + sep
            i += 1
        rlignes.append(entete)
        rlignes.append(vsep)
        # Infos
        for robot in listrobots:
            ligne = sep
            ligne += str(robot.face).center(dims[0]) + sep
            if robot.x == None:
                ligne += str("/").center(dims[1]) + sep
            else:
                ligne += str(robot.x).center(dims[1]) + sep
            if robot.y == None:
                ligne += str("/").center(dims[2]) + sep
            else:
                ligne += str(robot.y).center(dims[2]) + sep
            ligne += str(robot.aggressivite).center(dims[3]) + sep
            ligne += str(robot.vitesse).center(dims[4]) + sep
            if not robot.has_mine:
                m = "0"
            else:
                m = str(robot.puissance_mine)
            ligne += m.center(dims[5]) + sep
            if not robot.has_grenade:
                g = "0/0"
            else:
                g = str(robot.portee_grenade) + "/" + str(robot.puissance_grenade)
            ligne += g.center(dims[6]) + sep
            if not robot.alive:
                a = "N"
            else:
                a = "O"
            ligne += a.center(dims[7]) + sep
            rlignes.append(ligne)
        rlignes.append(vsep)
        rlignes.append("")
        # Retour :
        return rlignes

    def _create_server_info_partie(self, dictargs):
        """
        Infos à propos de la partie
        """
        msg = ""
        if "msg" in dictargs.keys():
            msg = dictargs["msg"]
        content = msg.split("\n")
        l = len(content)
        if 1 < l:
            if l < 12:
                n = 12 - l
                msg += "\n" * n
            msg = " " * 68 + "\n" + msg
            content = msg.split("\n")
        content = self.wrap_content(content, 68)
        return content

    def _create_server_list(self, dictargs):
        """
        Mise à jour de la liste de clients
        """
        rlignes = list()
        # Données
        cdicts = dictargs["clients"]
        clientslist = list()
        for uid in cdicts.keys():
            clientslist.append(cdicts[uid])
        # Publi :
        ligne = "Clients : "
        rlignes.append(ligne)
        rlignes.append("")
        if len(clientslist) == 0:
            ligne = "Aucun client connecté.".center(64)
            rlignes.append(ligne)
        else:
            ligne = "-" * 64
            rlignes.append(ligne)
            ligne = (
                "|"
                + "uid".center(5)
                + "|"
                + "client read ad.".center(21)
                + "|"
                + "server write ad.".center(21)
                + "|"
                + "statut".center(12)
                + "|"
            )
            rlignes.append(ligne)
            ligne = "-" * 64
            rlignes.append(ligne)
            for cdict in clientslist:
                # ligne standard
                uid = str(cdict["uid"]).center(5)
                clt_read = self._format_NET_address(cdict["client_read"]).center(21)
                svr_write = self._format_NET_address(cdict["server_write"]).center(21)
                clt_status = self._format_status(cdict["client_status"]).center(12)
                ligne = (
                    "|"
                    + uid
                    + "|"
                    + clt_read
                    + "|"
                    + svr_write
                    + "|"
                    + clt_status
                    + "|"
                )
                rlignes.append(ligne)
                if cdict["client_status"] in [
                    ctcp.CustomRequestHelper.STATUS_CONNECTED,
                    ctcp.CustomRequestHelper.STATUS_UNDEFINED,
                ]:
                    # lignes détails
                    u_send = "unit.=" + str(cdict["unit_sended_request_count"])
                    u_send_total = "total=" + str(cdict["total_sended_request_count"])
                    err_send = "nb err=" + str(
                        cdict["connect_send_error_count"] + cdict["send_error_count"]
                    )
                    u_rec = "unit.=" + str(cdict["unit_received_request_count"])
                    u_rec_total = "total=" + str(cdict["total_received_request_count"])
                    is_rec_err = (
                        " "  # "error:" + str(cdict["last_receive_error"] != None)
                    )
                    # détail send
                    ligne = (
                        "|"
                        + " " * 5
                        + "| -> "
                        + u_send.center(16)
                        + " "
                        + u_send_total.center(16)
                        + " "
                        + err_send.center(16)
                        + "  |"
                    )
                    rlignes.append(ligne)
                    # détail receive
                    ligne = (
                        "|"
                        + " " * 5
                        + "| <- "
                        + u_rec.center(16)
                        + " "
                        + u_rec_total.center(16)
                        + " "
                        + is_rec_err.center(16)
                        + "  |"
                    )
                    rlignes.append(ligne)
                ligne = "-" * 64
                rlignes.append(ligne)
        rlignes.append(" " * 64)
        return rlignes

    def _format_client_NETInfos(self, dictargs):
        """
        Met à jour les infos réseau d'un client, publiées en footer
        dictargs : dict généré par la méthode dispatch_network_infos
        du composant réseau
        """
        rlignes = list()
        # données
        svrdict = dictargs["server"]
        svr_add = self._format_NET_address(svrdict["address"])
        server_status = str(svrdict["server_status"])
        clt_status = str(svrdict["connection_status"])
        cltdict = dictargs["client"]
        clt_read_add = self._format_NET_address(cltdict["read_address"])
        # publication :
        txt = (
            "Serveur ("
            + svr_add
            + " | statut : "
            + self._format_status(server_status)
            + ")"
        )
        rlignes.append(txt)
        txt = (
            "Client  ("
            + clt_read_add
            + " | statut : "
            + self._format_status(clt_status)
            + ")"
        )
        rlignes.append(txt)
        return rlignes

    def _format_server_NETInfos(self, dictargs):
        """
        Met à jour les infos réseau d'un serveur, publiées en footer
        dictargs : dict généré par la méthode dispatch_network_infos
        du composant réseau
        """
        rlignes = list()
        # données
        svrdict = dictargs["server"]
        svr_add = self._format_NET_address(svrdict["address"])
        server_status = str(svrdict["connection_status"])
        error_count = str(len(svrdict["connect_errors"]))
        # publication :
        txt = (
            "Serveur ("
            + svr_add
            + " | statut : "
            + self._format_status(server_status)
            + " | errors : "
            + error_count
            + ")"
        )
        rlignes.append(txt)
        return rlignes

    def _format_status(self, status):
        """
        Formate le code de statut issu de CustomRequestHelper
        """
        out = ""
        if status == ctcp.CustomRequestHelper.STATUS_SHUTDOWN:
            out = "fermé"
        elif status == ctcp.CustomRequestHelper.STATUS_DISCONNECTED:
            out = "déconnecté"
        elif status == ctcp.CustomRequestHelper.STATUS_ERROR_CONNECTION:
            out = "en erreur"
        elif status == ctcp.CustomRequestHelper.STATUS_UNDEFINED:
            out = "indéfini"
        elif status == ctcp.CustomRequestHelper.STATUS_CONNECTED:
            out = "connecté"
        elif status == ctcp.CustomRequestHelper.STATUS_REJECTED:
            out = "refusé"
        else:
            out = "inconnu"
        return out

    def _format_NET_address(self, address):
        """
        Formatage ip:port
        """
        if address == None or not isinstance(address, tuple):
            radd = "?:?"
        else:
            ips = address[0]
            ports = address[1]
            if ips == "":
                ips = "localhost"
            radd = str(ips) + ":" + str(ports)
        return radd

    #-----> Utilitaires de publication :
    def get_text_from_content(self, content):
        """
        Transforme une liste de lignes en paragraphe
        """
        txt = ""
        for line in content:
            txt += line
            txt += "\n"
        return txt

    def wrap_content(self, content, maxwidth):
        """
        Wrap et conformation du texte.
        content est une liste de lignes str
        Retourne un nouvel objet content
        """
        if maxwidth == None:
            maxwidth = self.mesure_content(content)[0]
        wraplist = list()
        # wrap
        w = 0
        for line in content:
            w = max(w, len(line))
            if len(line) <= maxwidth:
                wraplist.append(line)
            else:
                n = len(line)
                subline = None
                while n > 0:
                    subline = line[0:maxwidth]
                    wraplist.append(subline)
                    line = line[maxwidth:]
                    n = len(line)
        w = min(w, maxwidth)
        # complétion :
        returnlist = list()
        for line in wraplist:
            wl = len(line)
            dx = w - wl
            returnlist.append(line + dx * " ")
        # mise à jour
        return returnlist

    def mesure_content(self, content):
        """
        Retourne les dimensions de la liste de lignes
        """
        if content == None:
            return 0, 0
        w = 0
        h = len(content)
        for line in content:
            w = max(w, len(line))
        return w, h

    def place_content_in_frame(self, content, framew, frameh, walign=1, halign=1):
        """
        Centre un contenu (wrappé) dans un cadre de dims framew, frameh.
        Rq : espaces impairs en cas de centrage: le surplus de 1 est placé
        à droite (x) en bas (y)
        walign / halign :
        
        * 0 : haut / gauche
        * 1 : center / middle
        * 2 : droite / bas
        
        Retourne un nouveau contenu
        """
        placelist = list()
        space = " "
        wc, hc = self.mesure_content(content)
        if framew != None and wc < framew:
            dx = framew - wc
            if walign == 0:
                dxright = dx
                dxleft = 0
            elif walign == 1:
                dxright = math.ceil(dx / 2)
                dxleft = dx - dxright
            elif walign == 2:
                dxright = 0
                dxleft = dx
            for line in content:
                newline = dxleft * space + line + dxright * space
                placelist.append(newline)
        else:
            placelist = content
        if frameh != None and hc < frameh:
            dy = frameh - hc
            if halign == 0:
                dybottom = dy
                dytop = 0
            elif halign == 1:
                dybottom = math.ceil(dy / 2)
                dytop = dy - dybottom
            elif halign == 2:
                dybottom = 0
                dytop = dy
            if framew != None:
                spaceline = framew * space
            else:
                spaceline = wc * space
            newcontent = list()
            if dybottom > 0:
                newcontent += (spaceline,) * dybottom
            for line in placelist:
                newcontent.append(line)
            if dytop > 0:
                newcontent += (spaceline,) * dytop
        else:
            newcontent = placelist
        return newcontent

    def create_line_content(
        self, celllist, vsep=" | ", leftsep="", rightsep="", walign=1, halign=1
    ):
        """
        Concatène horizontalement les contenus compris dans celllist
        en les séparant via le pattern vsep. leftsep et rightsep seront
        ajoutés à gauche et à droite.
        Retourne une liste de lignes
        """
        # Dimensions :
        cellheight = list()
        for cell in celllist:
            hc = self.mesure_content(cell)[1]
            cellheight.append(hc)
        # centrage vertical si nécessaire :
        newcelllist = list()
        frameh = max(cellheight)
        if min(cellheight) != max(cellheight):
            for cell in celllist:
                newcell = self.place_content_in_frame(
                    cell, None, frameh, walign=walign, halign=halign
                )
                newcelllist.append(newcell)
        else:
            newcelllist = celllist
        # concaténation :
        newcontent = list()
        nbcell = len(newcelllist)
        for i in range(0, frameh):
            line = ""
            if leftsep != None and len(leftsep) > 0:
                line += leftsep
            for cell in newcelllist:
                cellline = cell[i]
                line += cellline
                if cell != newcelllist[nbcell - 1]:
                    line += vsep
            if rightsep != None and len(rightsep) > 0:
                line += rightsep
            newcontent.append(line)
        # retour :
        return newcontent

    def create_column_content(
        self, celllist, hsep="-", topsep="=", bottomsep="=", walign=1, halign=1
    ):
        """
        Concatène verticalement les contenus compris dans celllist
        en les séparant via le pattern hsep
        Retourne une liste de lignes
        """
        # Dimensions :
        cellwidth = list()
        for cell in celllist:
            wc = self.mesure_content(cell)[0]
            cellwidth.append(wc)
        # centrage horizontal si nécessaire :
        newcelllist = list()
        framew = max(cellwidth)
        if min(cellwidth) != max(cellwidth):
            for cell in celllist:
                newcell = self.place_content_in_frame(
                    cell, framew, None, walign=walign, halign=halign
                )
                newcelllist.append(newcell)
        else:
            newcelllist = celllist
        # concaténation :
        newcontent = list()
        nbcell = len(newcelllist)
        line = ""
        if topsep != None and len(topsep) > 0:
            line = framew * topsep[0]
        newcontent.append(line)
        for cell in newcelllist:
            for line in cell:
                newcontent.append(line)
            if cell != newcelllist[nbcell - 1]:
                line = framew * hsep[0]
                newcontent.append(line)
        if bottomsep != None and len(bottomsep) > 0:
            line = framew * bottomsep[0]
            newcontent.append(line)
        # retour :
        return newcontent

    def draw_frame(
        self,
        content,
        xchar="*",
        topchar=None,
        bottomchar=None,
        ychar="*",
        leftchar=None,
        rightchar=None,
    ):
        """
        Encadre le contenu avec les caractères passés en paramètre. 
        Rq : lignes top bottom en xchar. 
        Retourne le nouveau contenu
        """
        if topchar == None and xchar != None:
            topchar = xchar
        if bottomchar == None and xchar != None:
            bottomchar = xchar
        if leftchar == None and ychar != None:
            leftchar = ychar
        if rightchar == None and ychar != None:
            rightchar = ychar
        tempcontent = list()
        w = self.mesure_content(content)[0]
        # bords H
        if topchar != None and isinstance(topchar, str):
            line = w * topchar[0]
            tempcontent.append(line)
        for line in content:
            tempcontent.append(line)
        if bottomchar != None and isinstance(bottomchar, str):
            line = w * bottomchar[0]
            tempcontent.append(line)
        # bords V
        newcontent = list()
        for line in tempcontent:
            if leftchar != None and isinstance(leftchar, str):
                newline = leftchar[0] + line
            else:
                newline = line
            if rightchar != None and isinstance(rightchar, str):
                newline += rightchar[0]
            newcontent.append(newline)
        return newcontent
