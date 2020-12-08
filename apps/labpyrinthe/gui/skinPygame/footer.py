#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pied de page du jeu
"""
# imports
import labpyproject.core.pygame.widgets as wgt
from labpyproject.core.net.custom_TCP import CustomRequestHelper
from labpyproject.apps.labpyrinthe.app.app_types import AppTypes
import labpyproject.apps.labpyrinthe.gui.skinPygame.uitools as uit

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["Footer"]
# classe
class Footer(wgt.Stack):
    """
    Footer de la GUI pygame
    """

    def __init__(self, skin, **kwargs):
        """
        Constructeur
        """
        # type d'appli :
        self.type_app = None
        # ref au skin :
        self.skin = skin
        # objets graphiques
        self.widget_bg = None
        self.content = None
        self.app_img = None
        self.canvas_pictos_net = None
        self.picto_send = None
        self.picto_receive = None
        self.txt_net = None
        self.space = None
        self.licence_img = None
        # générique :
        wgt.Stack.__init__(self, width="100%", height="50", bgcolor="#FFFFFF")
        # création :
        self._create_interface_step1()

    def _create_interface_step1(self):
        """
        Création de l'interface de base
        """
        # Fond image :
        self.widget_bg = uit.WImage(
            "screens", "footer4", self.skin, fixed=False, width="100%", fillmode="cover"
        )
        self.add_item(self.widget_bg)
        # block content :
        self.content = wgt.HStack(width="100%", height=40, top=10, bgcolor="#330000")
        self.add_item(self.content)

    def _create_interface_step2(self):
        """
        Achève la création de l'interface une fois le type d'appli connu.
        """
        # Type appli :
        self.app_img = None
        if self.type_app == AppTypes.APP_STANDALONE:
            self.app_img = uit.WImage(
                "screens", "stand_pg", self.skin, fixed=True, padding=5
            )
        if self.type_app == AppTypes.APP_CLIENT:
            self.app_img = uit.WImage(
                "screens", "client_pg", self.skin, fixed=True, padding=5
            )
        self.content.add_item(self.app_img)
        # spacer :
        self.space = uit.Spacer(flex=1, height=1)
        self.content.add_item(self.space)
        # infos réseau :
        if self.type_app == AppTypes.APP_CLIENT:
            self.canvas_pictos_net = wgt.Stack(width=450, height=40)
            self.content.add_item(self.canvas_pictos_net)
            def_status = CustomRequestHelper.STATUS_DISCONNECTED
            self.picto_receive = uit.WImage(
                "net", "receive_" + def_status, self.skin, fixed=True, height=10, top=8
            )
            self.canvas_pictos_net.add_item(self.picto_receive)
            self.picto_send = uit.WImage(
                "net", "send_" + def_status, self.skin, fixed=True, height=10, bottom=8
            )
            self.canvas_pictos_net.add_item(self.picto_send)
            self.txt_net = uit.WText(
                "UbuntuMono",
                14,
                self.skin,
                snapW=True,
                snapH=True,
                left=25,
                valign="middle",
                padding=0,
                fgcolor="#8C9557",
                bgcolor="#330000",
            )
            self.canvas_pictos_net.add_item(self.txt_net)
        # spacer :
        self.space = uit.Spacer(flex=1, height=1)
        self.content.add_item(self.space)
        # licence :
        self.licence_img = uit.WImage(
            "screens", "licence", self.skin, fixed=True, padding=5
        )
        self.content.add_item(self.licence_img)

    def set_app_type(self, apptype):
        """
        Appelée lorsque la GUI connait le type d'application associée (client, serveur, standalone)
        """
        self.type_app = apptype
        # fin création interface
        self._create_interface_step2()

    def show_NETInfos(self, dictargs):
        """
        Affichage des infos réseau.
        
        Args:
            dictargs : dict généré par la méthode get_network_infos du composant réseau associé
        """
        if self.type_app == AppTypes.APP_CLIENT:
            # données
            svrdict = dictargs["server"]
            svr_add = self._format_NET_address(svrdict["address"])
            server_status = str(svrdict["server_status"])
            clt_status = str(svrdict["connection_status"])
            cltdict = dictargs["client"]
            clt_read_add = self._format_NET_address(cltdict["read_address"])
            # publication :
            surf_send = self.skin.get_image("net", "send_" + clt_status)
            self.picto_send.load_surface(surf_send)
            surf_receive = self.skin.get_image("net", "receive_" + server_status)
            self.picto_receive.load_surface(surf_receive)
            txt = (
                "Serveur ("
                + svr_add
                + " | statut : "
                + self._format_status(server_status)
                + ")\n"
            )
            txt += (
                "Client  ("
                + clt_read_add
                + " | statut : "
                + self._format_status(clt_status)
                + ")"
            )
            self.txt_net.text = txt

    def _format_status(self, status):
        """
        Formate le code de statut issu de CustomRequestHelper
        """
        out = ""
        if status == CustomRequestHelper.STATUS_SHUTDOWN:
            out = "fermé"
        elif status == CustomRequestHelper.STATUS_DISCONNECTED:
            out = "déconnecté"
        elif status == CustomRequestHelper.STATUS_ERROR_CONNECTION:
            out = "en erreur"
        elif status == CustomRequestHelper.STATUS_UNDEFINED:
            out = "indéfini"
        elif status == CustomRequestHelper.STATUS_CONNECTED:
            out = "connecté"
        elif status == CustomRequestHelper.STATUS_REJECTED:
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
