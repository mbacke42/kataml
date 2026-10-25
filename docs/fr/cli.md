# Ligne de commande

## Lancer l'interface

```bash
kataml [--port 8765] [--host 127.0.0.1] [--workspace DOSSIER] [--no-browser]
```

Voir [Installation › Options de lancement](installation.md#options-de-lancement). Depuis
le dépôt, `./kataml.sh` (ou `kataml.bat`) accepte les mêmes options.

## Exécuter un workflow sans interface

```bash
kataml run workflow.json [--rapport rapport.html] [--script script.py]
                           [--notebook notebook.ipynb] [--workspace DOSSIER]
                           [--lang fr|en] [-q]
```

| Option | Effet |
|---|---|
| `workflow.json` | le workflow à exécuter (enregistré ou exporté depuis l'interface) |
| `--rapport FICHIER` | génère le [rapport HTML](reports.md), avec les réglages enregistrés dans le workflow |
| `--script FICHIER` | exporte le script Python équivalent |
| `--notebook FICHIER` | exporte le notebook Jupyter |
| `--workspace DOSSIER` | espace de travail : données des Lecteurs CSV, cache, blocs personnalisés |
| `--lang en` | rapport en anglais |
| `-q`, `--quiet` | n'affiche que les erreurs |

Tous les nœuds sont exécutés dans l'ordre du graphe. Un nœud en échec est signalé, et
les nœuds qui en dépendent sont ignorés ; les autres branches continuent :

```text
Workflow « Classification des iris » : 14 nœuds, espace de travail /home/moi/kataml
  ✓ [ 1] Introduction  (cache)
  ✓ [ 2] Iris  (0.01 s)
  ✓ [ 5] 75 % / 25 %  (0.03 s)
  ✓ [ 7] Forêt aléatoire  (0.56 s)
  ✓ [11] CV 5 plis  (3.23 s)
  …
Terminé en 5.1 s
Rapport : rapport.html
```

Le **code de retour** vaut 0 si tout a réussi, 1 sinon : la commande s'intègre dans un
script, un `Makefile` ou une intégration continue.

Le cache disque est partagé avec l'interface : les nœuds déjà calculés (mêmes paramètres,
mêmes données) ne sont pas recalculés.

## Exemples d'usage

=== "Rapport hebdomadaire"

    Un workflow lit `ventes.csv` (dans `workspace/data`) ; une tâche planifiée remplace le
    fichier puis régénère le rapport :

    ```bash
    kataml run ventes.json --rapport "rapports/ventes-$(date +%F).html" -q
    ```

=== "Corriger des TP"

    Exécuter tous les workflows rendus et produire un rapport pour chacun :

    ```bash
    for f in rendus/*.json; do
      kataml run "$f" --rapport "${f%.json}.html" -q || echo "Échec : $f"
    done
    ```

=== "Passer au code"

    ```bash
    kataml run etude.json --script etude.py --notebook etude.ipynb
    python etude.py
    ```

## Variables d'environnement

| Variable | Effet |
|---|---|
| `KATAML_WORKSPACE` | espace de travail par défaut |
| `KATAML_CACHE_MB` | taille maximale du cache disque, en Mo (1024 par défaut) |
| `KATAML_NO_EXTENSIONS=1` | ne charge aucune extension installée (diagnostic) |
