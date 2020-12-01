# B.1- Contexte

Ce projet est le résultat d’une démarche d’auto formation. Ancien développeur web, spécialisé dans la technologie **Flash/Flex**, je reviens au développement après cinq ans consacrés à de toutes autres activités. Pour ce retour aux sources, j’ai choisis un langage de haut niveau, plus puissant que ceux que j’avais pratiqués jusque-là : **Python**.

L’idée d’un jeu de labyrinthe vient du mini projet du MOOC **« Apprenez à programmer en python » d’[OpenClassrooms](https://openclassrooms.com/fr/)**. N’apprenant jamais aussi bien qu’en faisant, j’ai étendu le cahier des charges initial de ce projet, en me fixant les objectifs suivants :
-	Proposer en plus du mode console, une interface graphique riche (ce qui m’a permis de renouer avec mon ancien métier de développeur d’interfaces).
- Augmenter la complexité du jeu (via six types de bots, les mines et bonus, les lancers de grenade…) de telle sorte qu’il puisse constituer un terrain d’entrainement pour une intelligence artificielle (cet aspect fera peut être l’objet d’une V2 de ce projet dans l’avenir).
-	Traiter un certain nombre de problématiques de façon générique tout en utilisant le moins possible de librairies externes à la distribution Python standard.
-	Sortir franchement de ma « zone de confort » en me confrontant aux problématiques de build (voir B.3 et B.4), afin de proposer des exécutables optimisés sur plusieurs plate formes.

Remarque: Vis-à-vis du cahier des charges initial, j’ai néanmoins introduit une régression : l’absence de tests unitaires. Etant habitué à développer en « trace-debug » (débogage par points d’arrêts manuels et affichage de traces dans la console), le naturel est revenu au galop. Par ailleurs le mode démo (partie automatique avec uniquement des bots), a permis de faire tourner le jeu intensivement tout au long de son développement.

Ayant beaucoup appris au travers de forums tels que [**stackoverflow**](https://stackoverflow.com/), il m’est apparu naturel de partager le résultat de ce travail, en souhaitant, qu’il soit d’une quelconque aide pour d’autres.

Les solutions présentées dans la suite de ce document ne sont pas forcément les plus pertinentes et ne sont de toute façon pas exhaustives (plate forme OS X non traitée par exemple). Si vous souhaitez enrichir le contenu de ce projet, n’hésitez pas à y apporter des commentaires.

De même les fonctionnalités du jeu pourraient être étendues :
- Habillage sonore
- Habillage graphique différent
- Enchainement de niveaux, nouvelle case de type trou pour redescendre au niveau précédent
- De nouvelles actions : pousser un joueur d’un nombre de cases n dans une direction (jusqu’à une mine par exemple)
- Doter les joueurs de plusieurs vies
- …

N’hésitez pas à vous emparer des sources et à les améliorer.
