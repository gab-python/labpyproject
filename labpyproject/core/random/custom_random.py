#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Centralisation des choix (pseudos) aléatoires dans un helper statique. 
Privilégie l'usage de secrets à celui de random.
"""
# imports
import secrets
import random

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["CustomRandom"]
# Classe
class CustomRandom:
    """
    Helper statique centralisant les fonctions aléatoires
    """

    def choice(cls, l):
        """
        Retourne un élément choisit aléatoirement dans la liste l.
        
        Args:
            l (list)
            
        Returns:
            object
        """
        if isinstance(l, set):
            l = list(l)
        return secrets.choice(l)

    choice = classmethod(choice)

    def randrange(cls, a, b):
        """
        Retourne un entier aléatoire n tel que a<= n <b
        
        Args:
            a (int), b(int)
            
        Returns:
            int
        """
        return secrets.choice(range(a, b))

    randrange = classmethod(randrange)

    def sample(cls, l, k):
        """
        Retourne un échantillon de k éléments pris dans l.
        
        Args:
            l (list)
            k (int)
        
        Returns:
            list
        """
        return random.sample(l, k)

    sample = classmethod(sample)

    def shuffle(cls, l):
        """
        Mélange les éléments de la liste l.
        
        Args:
            l (list)
            
        Returns:
            list
        """
        if isinstance(l, set):
            l = list(l)
        return random.shuffle(l)

    shuffle = classmethod(shuffle)
