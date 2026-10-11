# Studio Optimuscle – procédure

Vidéos animées « Opti coach » : Opti, le coach en sweat orange, explique un conseil musculation,
dans le style des carrousels du jour 3. Il bouge, fait des gestes et des bulles, et sa bouche suit la voix.

## Fichiers
- `coach_template.html` : décor, personnage et moteur d'animation (ne pas modifier sans raison).
- `build.py` : fabrique la vidéo à partir d'un script JSON (voir `exemple_courbatures.json`).
- `musique.mp3` : musique de fond (piste générée par vidIQ pour Optimuscle).

## Écrire un script (JSON)
- 5 à 6 scènes, de 35 à 45 s au total. Scène 1 = accroche, scène 2 = idée reçue ou problème, scènes 3 à 5 = numérotées 1, 2, 3, dernière scène = appel à l'action.
- Pour chaque scène : `items` (les textes à l'écran), `geste` (cross, explain, shrug, pointUL, pointUp, wag, count, wave, thumbs, hips), `bulle` (court, facultatif) et `voix` (le texte dit par la voix off, tutoiement).
- Types de texte : `big`, `big grad`, `mid`, `mid out`, `sub`, `pill`, `num`, `chk`, `card` (+ `lab`), `card ex` (+ `lab`). `**gras**` et `|` pour un retour à la ligne. `in` = moment d'apparition (s) dans la scène.

## Règles de contenu (obligatoires)
- Cible : jeunes de 15 à 25 ans, débutants ou qui stagnent. Ton cash et direct, tutoiement, phrases courtes.
- Sujets : conseils débutant, erreurs à éviter, mythes à démonter.
- Interdit : résultat chiffré garanti, « sans effort », conseil médical (renvoyer vers un médecin en cas de douleur), produits dopants, moqueries sur le physique, faux témoignages, produits à vendre ou liens.
- Fin : « Enregistre ce post… » ou « Abonne-toi @optimuscle20… ».

## Fabriquer
1. Contrôle visuel rapide : `python3 build.py script.json sortie.mp4 --test 2,10,25`, puis regarder les captures.
2. Avec voix off, une voix par scène dans l'ordre : `python3 build.py script.json sortie.mp4 --voix v1.mp3 v2.mp3 …`
3. Sans voix (musique seule) : `python3 build.py script.json sortie.mp4`
Un rendu prend environ 1 minute pour 10 secondes de vidéo.

## Publier (après la validation de Bilal, jamais avant)
- La vidéo va dans `videos/AAAA-MM-JJ_sujet.mp4` de ce dépôt.
- Son lien public : `https://raw.githubusercontent.com/bilouxxpro-design/optimuscle-medias/main/videos/<fichier>`
- Le post est proposé sur Telegram (boutons Valider / Modifier / Refuser) par le workflow n8n « Posts : proposer et mettre à jour ».
- Il n'est programmé dans Metricool qu'une fois au statut VALIDE.
