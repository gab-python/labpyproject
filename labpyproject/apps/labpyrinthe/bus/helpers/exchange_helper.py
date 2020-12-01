#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExchangeHelper: créateur d'objets d'échanges.
"""
# imports
from labpyproject.core.app import app_components as appcomp

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["ExchangeHelper"]
# classe
class ExchangeHelper:
    """
    Helper statique prenant en charge la création d'objets d'échange entre composantes
    de l'application
    """

    def createNETObj(cls, typeexchange, dictargs):
        """
        Création d'un objet d'échange avec le réseau
        
        Args:
            typeexchange (str)
            dictargs (dict)
        
        Returns:
            NETExchangeObject
        """
        obj = appcomp.NETExchangeObject(typeexchange)
        dictref = obj.dictargs
        for k, v in dictargs.items():
            if not cls._xInsertDict(v, dictref):
                dictref[k] = v
        return obj

    createNETObj = classmethod(createNETObj)

    def createGUIObj(cls, typeexchange, dictargs):
        """
        Création d'un objet d'échange avec la GUI
        
        Args:
            typeexchange (str)
            dictargs (dict)
        
        Returns:
            GUIExchangeObject
        """
        obj = appcomp.GUIExchangeObject(typeexchange, dictargs)
        return obj

    createGUIObj = classmethod(createGUIObj)

    def _xInsertDict(cls, elt, dictref):
        """
        "Applatit" récursivement les dicts
        """
        if type(elt) is dict:
            for k, v in elt.items():
                if not cls._xInsertDict(v, dictref):
                    dictref[k] = v
            return True
        return False

    _xInsertDict = classmethod(_xInsertDict)
