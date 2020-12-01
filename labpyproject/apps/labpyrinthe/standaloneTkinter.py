#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# imports
"""
Script de lancement du jeu Labpyrinthe en version standalone Tkinter.

::

    import labpyproject.apps.labpyrinthe.gui.GUITk as gui
    from labpyproject.apps.labpyrinthe.app.application import AppManager
    
    if __name__ == '__main__':
        # 1. Création de la GUI graphique dans le thread principal
        GTk = gui.GUITk()
        # 2. Création du composant applicatif paramétré en standalone
        AppMngr = AppManager(AppManager.APP_STANDALONE, interface=AppManager.INTERFACE_TK)
        # 3. Lancement de la GUI (run thread)
        GTk.mainloop()

"""
# imports
import labpyproject.apps.labpyrinthe.gui.GUITk as gui
from labpyproject.apps.labpyrinthe.app.application import AppManager

# script
if __name__ == "__main__":
    # 1. Création de la GUI graphique dans le thread principal
    GTk = gui.GUITk()
    # 2. Création du composant applicatif paramétré en standalone
    AppMngr = AppManager(AppManager.APP_STANDALONE, interface=AppManager.INTERFACE_TK)
    # 3. Lancement de la GUI (run thread)
    GTk.mainloop()
