# Notes de version

## 1.0.0 — 2026-10-08

- Nouvelle palette violette, icônes vectorielles, écran Explorer et navigation simplifiée.
- Thèmes clair et sombre appliqués aux cartes et aux fenêtres secondaires ; thème conservé après redémarrage.
- Bibliothèque avec grille qui s'adapte à la largeur de la fenêtre et ouverture directe du manga sélectionné.
- Démarrage immédiat, sans animation de chargement artificielle ; journal d'activité accessible avec Ctrl+L.
- Réponses de détails obsolètes ignorées lorsqu'un autre manga est sélectionné.
- Conservation des threads actifs jusqu'à leur fin et fermeture qui attend l'arrêt des tâches sans détruire leurs objets.
- File de téléchargement limitée à deux tâches, doublons actifs filtrés, annulation distincte de l'échec et relance sécurisée.
- Images vérifiées et enregistrées par remplacement atomique ; pages réussies comptées séparément des échecs.
- Export refusé quand des pages ou des chapitres d'un tome manquent ; images conservées en cas d'échec.
- Exports atomiques pour conserver les fichiers précédents en cas d'erreur ; métadonnées XML échappées et navigation EPUB ajoutée.
- Correspondance du titre vérifiée avant un basculement de téléchargement vers une autre source.
- Lecteur avec quatre chargements simultanés, cache partagé entre les modes et affichage des erreurs de pages.
- Historique de lecture mis à jour après lecture de la dernière page, sans marquer les chapitres qui n'ont pas chargé.
- Paramètres validés et sauvegardés en une seule opération ; changements de domaines pris en compte sans redémarrage.
- Vérification des sources en arrière-plan et suppression des badges « ONLINE » non vérifiés.
- Données personnelles stockées dans le dossier utilisateur, migration des anciens fichiers et configuration d'exemple sans chemin personnel.
- Comparaison des versions corrigée pour les versions abrégées et les préversions.
- Filtrage des chapitres bonus par mots complets et suppression des limites figées pour certaines séries en cours.
- 28 tests automatisés, versions de dépendances enregistrées et compilation portable avec test de démarrage.
- Workflow de tests et de compilation Windows / Linux avec archives téléchargeables.

La compilation Linux a été vérifiée localement. La validation Windows dépend du résultat du workflow GitHub. L'accès aux chapitres et l'exactitude des métadonnées externes restent dépendants des sources.
