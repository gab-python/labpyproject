#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Typage statique des applications (client, serveur, standalone).
"""
class AppTypes:
    """
    Helper portant le typage statique des applications (client, serveur, standalone).
    
    .. note::
       Séparé de AppManager pour résoudre des problèmes de références circulaires à l'import.
    """

    # types d'application :
    APP_SERVER = "APP_SERVER"  #: marque une application de type serveur
    APP_CLIENT = "APP_CLIENT"  #: marque une application de type client
    APP_STANDALONE = "APP_STANDALONE"  #: marque une application de type standalone
    # définition du type
    SET_APPTYPE = (
        "SET_APPTYPE"  
    ) #: identifie une information de définition de type d'application
