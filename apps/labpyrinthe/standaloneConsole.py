#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de lancement du jeu Labpyrinthe en version standalone console.

::

    from labpyproject.apps.labpyrinthe.app.application import AppManager
    
    if __name__ == '__main__':
        # Création du composant applicatif paramétré en standalone
        # L'AppManager prendra en charge le lancement de la GUI console dans un thread secondaire
        AppMngr = AppManager(AppManager.APP_STANDALONE)

"""
# import
from labpyproject.apps.labpyrinthe.app.application import AppManager

# script
if __name__ == "__main__":
    # Création du composant applicatif paramétré en standalone
    # L'AppManager prendra en charge le lancement de la GUI console dans un thread secondaire
    AppMngr = AppManager(AppManager.APP_STANDALONE)
