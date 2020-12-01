#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de lancement du jeu Labpyrinthe en version client Pygame.

::

    from labpyproject.apps.labpyrinthe.app.application import AppManager
    from labpyproject.apps.labpyrinthe.gui.GUIPygame import GUIPygame
    
    if __name__ == '__main__':   
        # 1. Création de la GUI graphique dans le thread principal
        GUIpg = GUIPygame()
        # 2. Création du composant applicatif paramétré en client
        AppMngr = AppManager(
            AppManager.APP_CLIENT,
            interface=AppManager.INTERFACE_PYGAME,
        )
        # 3. Lancement de la GUI (run thread)
        GUIpg.start_GUI()
        
"""
# imports
from labpyproject.apps.labpyrinthe.app.application import AppManager
from labpyproject.apps.labpyrinthe.gui.GUIPygame import GUIPygame

# script
if __name__ == "__main__":
    # 1. Création de la GUI graphique dans le thread principal
    GUIpg = GUIPygame()
    # 2. Création du composant applicatif paramétré en client
    AppMngr = AppManager(AppManager.APP_CLIENT, interface=AppManager.INTERFACE_PYGAME,)
    # 3. Lancement de la GUI (run thread)
    GUIpg.start_GUI()
