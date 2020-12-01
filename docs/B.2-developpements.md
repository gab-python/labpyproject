# B.2- Développements

Dans ce premier projet significatif en python, je me suis rapproché de mes anciennes habitudes en actionscript. Le code est essentiellement objet. Il utilise massivement la composition ainsi que les classes statiques et (grande force de python) l’héritage multiple.

Pour standardiser le code j’ai fait appel à [**Black**](https://github.com/psf/black) « The Uncompromising Code Formatter », dans son paramétrage par défaut.

Pour obtenir quelques métriques j’ai utilisé [**Sonarqube**](https://www.sonarqube.org/):

Métrique | Projet | Code générique (core) | Code du jeu (apps.labpyrinthe)
-------- | ------ | --------------------- | ------------------------------
Total (lignes) | 43 117 | 12 424 | 30 682
Code (lignes) | 26 981 | 7 020 | 19 953
Commentaires (lignes) | 14 284 | 4 737 | 9 545
Commentaires (%) | 34.6% | 40.3 % | 32.4 %
Classes | 146 | 54 | 92
Fonctions (méthodes) | 1 946 | 675 | 1 271
Fichiers (modules) | 84 | 17 | 66

Remarques: Par curiosité j’ai analysé le code du projet avec **Sonarqube**, là encore dans son paramétrage par défaut. Le code passe la « quality gate » avec :
-	la note A en Reliability, Security et Maintainability
-	0% de couverture du code (tests unitaires absents)
-	573 « code smell » dont une très grande partie relève de conventions de nommage. Parmi les autres causes : trop grand nombre de paramètres pour des fonctions, Cognitive complexity to reduce
-	17 Security Hotspots : liés à l’utilisation 
  -	d’arguments en ligne de commande
  -	d’expressions régulières
  -	d’adresse IP littérales
  -	de l’entrée standard
  -	du générateur pseudorandom
