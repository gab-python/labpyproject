#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
**Prototype de "moteur de publication"  Pygame**.

.. note::

   Compatibilité: pygame 1.9 (SDL 1.2) et pygame 2 (SDL 2)

.. admonition:: portage sur pygame 2
   
   Les développeurs de Pygame annoncent une rétro compatibilité quasi complète avec la version 2. 
   Pour ce package une seule modification a été nécessaire: caster une valeur en pygame.Color ne 
   renvoit plus une ValueError mais un TypeError.
   

.. admonition:: Application concrète

    Les objets du module widgets constituent les briques graphiques de base de l'interface pygame du jeu **labpyrinthe**, voir :
    
    * Root du jeu: :doc:`labpyproject.apps.labpyrinthe.gui.GUIPygame`
    * Eléments d'interface :doc:`labpyproject.apps.labpyrinthe.gui.skinPygame`   
"""
