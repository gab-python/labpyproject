#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de lancement du jeu Labpyrinthe en version client console.

::

    from labpyproject.apps.labpyrinthe.app.application import AppManager
    
    if __name__ == '__main__':
        # Création du composant applicatif paramétré en client
        # L'AppManager prendra en charge le lancement de la GUI console dans un thread secondaire
        AppMngr = AppManager(AppManager.APP_CLIENT)
        
"""
# imports
from labpyproject.apps.labpyrinthe.app.application import AppManager

# script
if __name__ == "__main__":
    # Création du composant applicatif paramétré en client
    # L'AppManager prendra en charge le lancement de la GUI console dans un thread secondaire
    AppMngr = AppManager(AppManager.APP_CLIENT)
