#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitaires de gestion de fichiers.
"""
import os
import pickle


def get_file_list(dir_path):
    """
    Retourne la liste des fichiers présents dans le dossier dir_path.
    """
    with os.scandir(dir_path) as it_de:  # itérateur d'objets os.DirEntry
        l = []
        for entry in it_de:
            if entry.is_file():
                l.append(entry.name)
        return l


def load_text_file(file_path, splitlines=True):
    """
    Charge un fichier texte (carte) et retourne la liste des lignes du fichier.
    """
    if os.path.exists(file_path):  # précaution inutile
        with open(file_path, "r") as fichier:
            chaine = fichier.read()
            if splitlines:
                lignes = chaine.splitlines()
                return lignes
            else:
                return chaine


def load_obj_from_file(file_path):
    """
    Charge un fichier binaire et renvoit l'objet python associé ou bien None.
    """
    if os.path.exists(file_path):
        fichier = open(file_path, "rb")
        my_unpickler = pickle.Unpickler(fichier)
        obj = my_unpickler.load()
        fichier.close()
        return obj
    else:
        return None


def save_obj_in_file(file_path, obj):
    """
    Sérialise l'objet python et le sauve dans le fichier.
    """
    fichier = open(file_path, "wb")
    my_pickler = pickle.Pickler(fichier)
    my_pickler.dump(obj)
    fichier.close()
