#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# imports
from labpyproject.apps.labpyrinthe.bus.model.core_matrix import LabHelper

# Evite l'ajout non désiré de certains imports à la doc sphinx
__all__ = ["CommandHelper"]
# classe
class CommandHelper:
    """
    Helper statique fournissant des services d'interprétation, 
    sérialisation/dé-sérialisation des commandes.
    
    .. note::
       Sérialisation/dé-sérialisation trop limitées, passer en XML (V2).
    """

    #-----> Interprétation des commandes
    def translate_cmd(cls, cmd):
        """
        Traduit la commande saisie par l'utilisateur en actions
        
        Args:
            cmd (str): 1 caractère ou plus 
                        (ex, avec les chars par défauts : "n", "e25", "ps", "mn")
        
        Returns:
            dict: {"action":, **args}
        """
        if isinstance(cmd, str) and len(cmd) > 0:
            firstchar = cmd[0].lower()
            # déplacements
            listchardir = [
                LabHelper.CHAR_TOP,
                LabHelper.CHAR_BOTTOM,
                LabHelper.CHAR_LEFT,
                LabHelper.CHAR_RIGHT,
            ]
            listdir = [LabHelper.TOP, LabHelper.BOTTOM, LabHelper.LEFT, LabHelper.RIGHT]
            if firstchar in listchardir:
                indice = listchardir.index(firstchar)
                direct = listdir[indice]
                action = LabHelper.ACTION_MOVE
                nb_pas = cmd[1:]
                if LabHelper.REGEXP_INT.match(nb_pas) and int(nb_pas) > 0:
                    pas = int(nb_pas)
                else:
                    pas = 1
                return {"action": action, "direct": direct, "pas": pas}
            elif firstchar == LabHelper.CHAR_PORTE:
                secchar = cmd[1:]
                if secchar in listchardir:
                    indice = listchardir.index(secchar)
                    direct = listdir[indice]
                    action = LabHelper.ACTION_CREATE_DOOR
                    return {"action": action, "direct": direct, "pas": None}
            elif firstchar == LabHelper.CHAR_MUR:
                secchar = cmd[1:]
                if secchar in listchardir:
                    indice = listchardir.index(secchar)
                    direct = listdir[indice]
                    action = LabHelper.ACTION_CREATE_WALL
                    return {"action": action, "direct": direct, "pas": None}
            elif firstchar == LabHelper.CHAR_KILL:
                secchar = cmd[1:]
                if secchar in listchardir:
                    indice = listchardir.index(secchar)
                    direct = listdir[indice]
                    action = LabHelper.ACTION_KILL
                    return {"action": action, "direct": direct, "pas": None}
            elif firstchar == LabHelper.CHAR_MINE:
                secchar = cmd[1]
                if secchar in listchardir:
                    indice = listchardir.index(secchar)
                    direct = listdir[indice]
                    action = LabHelper.ACTION_MINE
                    puiss = cmd[2:]
                    if LabHelper.REGEXP_INT.match(puiss) and int(puiss) > 0:
                        puissance = int(puiss)
                    else:
                        puissance = 1
                    return {
                        "action": action,
                        "direct": direct,
                        "pas": None,
                        "puissance": puissance,
                    }
            elif firstchar == LabHelper.CHAR_GRENADE:
                secchar = cmd[1]
                if secchar in listchardir:
                    indice = listchardir.index(secchar)
                    direct = listdir[indice]
                    action = LabHelper.ACTION_GRENADE
                    paramsg = cmd[2:].split("-")
                    nb_pas = paramsg[0]
                    puiss = paramsg[1]
                    if LabHelper.REGEXP_INT.match(nb_pas) and int(nb_pas) > 0:
                        pas = int(nb_pas)
                    else:
                        pas = 1
                    if LabHelper.REGEXP_INT.match(puiss) and int(puiss) > 0:
                        puissance = int(puiss)
                    else:
                        puissance = 1
                    return {
                        "action": action,
                        "direct": direct,
                        "pas": pas,
                        "puissance": puissance,
                    }
            elif firstchar == LabHelper.CHAR_HELP:
                action = LabHelper.ACTION_HELP
                return {"action": action, "direct": None, "pas": None}
            elif firstchar == LabHelper.CHAR_MENU:
                action = LabHelper.ACTION_MENU
                return {"action": action, "direct": None, "pas": None}
            elif firstchar == LabHelper.CHAR_QUIT:
                action = LabHelper.ACTION_QUIT
                return {"action": action, "direct": None, "pas": None}
            elif firstchar == LabHelper.CHAR_START:
                action = LabHelper.ACTION_START
                return {"action": action, "direct": None, "pas": None}
            elif firstchar == LabHelper.CHAR_RESET_QUEUE:
                action = LabHelper.ACTION_RESET_QUEUE
                return {"action": action, "direct": None, "pas": None}
        return {"action": None, "direct": None, "pas": None}

    translate_cmd = classmethod(translate_cmd)

    #-----> Sérialisation/désérialisation des commandes
    def format_game_cmd(cls, code_cmd, com_uid, kwargs):
        """
        Formate un message cmd + args lié au jeu
        
        Args:
            code_cmd (str): la commande
            com_uid (int): id unique de commande
            **kwargs : dict d'arguments à "applatir"
        
        Return:
            str
        
        .. note::    
           Devrait être récursif (cf xml en V2)
        """
        msg = "gamecmd=" + code_cmd
        msg += "&comuid=" + com_uid
        if kwargs != None:
            for key, val in kwargs.items():
                msg += "&" + str(key) + "=" + str(cls.format_cmd_sequence(val))
        return msg

    format_game_cmd = classmethod(format_game_cmd)

    def format_cmd_sequence(cls, seq):
        """
        Transforme une séquence en chaine
        
        Args:
            seq: itérable de type list, tuple ou dict
        """
        if type(seq) is list and len(seq) > 0:
            chaine = "["
            for val in seq:
                chaine += str(val) + ","
            chaine = chaine[0 : len(chaine) - 1] + "]"
            return chaine
        elif type(seq) is tuple and len(seq) > 0:
            chaine = "("
            for val in seq:
                chaine += str(val) + ","
            chaine = chaine[0 : len(chaine) - 1] + ")"
            return chaine
        elif type(seq) is dict and len(seq) > 0:
            chaine = "{"
            for k, v in seq.items():
                chaine += str(k) + ":" + str(v) + ","
            chaine = chaine[0 : len(chaine) - 1] + "}"
            return chaine
        else:
            return seq

    format_cmd_sequence = classmethod(format_cmd_sequence)

    def split_game_cmd(cls, msg):
        """
        Méthode réciproque de format_game_cmd
        
        Args:
            msg (str): chaine conforme à l'expression régulière LabHelper.REGEXP_GAME 
        """
        if msg != None and LabHelper.REGEXP_GAME.match(msg):
            listp = msg.split("&")
            kwargs = dict()
            cmd = None
            for p in listp:
                kv = p.split("=")
                if kv[0] == "gamecmd":
                    cmd = kv[1]
                else:
                    val = kv[1]
                    if len(kv) > 2:
                        val = p[len(kv[0]) + 1 :]
                    kwargs[kv[0]] = cls.split_cmd_sequence(val)
            if "comuid" not in kwargs.keys():
                kwargs["comuid"] = None
            return cmd, kwargs
        return None, None

    split_game_cmd = classmethod(split_game_cmd)

    def split_cmd_sequence(cls, chaine):
        """
        Réciproque de _format_cmd_sequence
        """
        if LabHelper.REGEXP_SEQ_LIST.match(chaine):
            chaine = chaine[1 : len(chaine) - 1]
            seq = chaine.split(",")
            return seq
        elif LabHelper.REGEXP_SEQ_TUPLE.match(chaine):
            chaine = chaine[1 : len(chaine) - 1]
            seq = chaine.split(",")
            return seq
        elif LabHelper.REGEXP_SEQ_DICT.match(chaine):
            chaine = chaine[1 : len(chaine) - 1]
            lw = chaine.split(",")
            seq = dict()
            for item in lw:
                k, v = item.split(":")
                seq[k] = v
            return seq
        else:
            return chaine

    split_cmd_sequence = classmethod(split_cmd_sequence)
