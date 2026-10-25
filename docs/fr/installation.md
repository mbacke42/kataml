# Installation

KataML ne demande aucun droit administrateur et ne modifie pas le système : tout
s'installe dans un dossier de l'utilisateur. Il existe trois modes d'installation, du plus
simple au plus souple.

## 1. Version portable (rien à installer)

Chaque [version publiée](https://gitlab.com/fredbl/kataml/-/releases) fournit deux
paquets qui embarquent Python, pandas et scikit-learn.

=== "Linux"

    1. Téléchargez `KataML-<version>-x86_64.AppImage`.
    2. Rendez-le exécutable, puis lancez-le :
       ```bash
       chmod +x KataML-*-x86_64.AppImage
       ./KataML-*-x86_64.AppImage
       ```
    3. Le navigateur s'ouvre sur l'interface. Les données sont rangées dans
       `kataml-workspace/`, **à côté du fichier AppImage**.

    !!! note "« FUSE » manquant"
        Sur certaines distributions récentes, une AppImage a besoin de la bibliothèque
        `libfuse2`. À défaut, lancez-la avec `--appimage-extract-and-run`.

=== "Windows"

    1. Téléchargez `KataML-<version>-windows-x64.zip` et dézippez-le.
    2. Double-cliquez sur **`KataML.bat`**. Une fenêtre noire (le serveur) s'ouvre,
       puis le navigateur.
    3. Les données sont rangées dans le dossier `workspace/`, à côté du lanceur. Le
       dossier complet peut être déplacé ou copié sur une clé USB.

    !!! note "SmartScreen"
        Le paquet n'est pas signé : Windows peut afficher « Windows a protégé votre
        ordinateur ». Cliquez sur **Informations complémentaires**, puis **Exécuter quand
        même**.

## 2. Avec uv (recommandé pour les postes de travail)

[uv](https://docs.astral.sh/uv/) installe Python et les dépendances sans droits
administrateur :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh        # installe uv (une seule fois)
uv tool install git+https://gitlab.com/fredbl/kataml.git
kataml
```

La commande `kataml` est placée dans `~/.local/bin`. L'espace de travail par défaut est
`~/kataml`. Mise à jour et désinstallation :

```bash
uv tool upgrade kataml
uv tool uninstall kataml
```

Pour essayer sans installer : `uvx --from git+https://gitlab.com/fredbl/kataml.git kataml`.

## 3. Depuis le dépôt (développement)

```bash
git clone https://gitlab.com/fredbl/kataml.git
cd kataml
./kataml.sh        # Windows : kataml.bat
```

Au premier lancement, uv crée `.venv/` dans le dossier et y installe les dépendances.
L'espace de travail est alors `workspace/`, à côté du code.

## Options de lancement

| Option | Effet |
|---|---|
| `--port 9000` | port HTTP (par défaut 8765 ; le suivant libre est pris si besoin) |
| `--no-browser` | ne pas ouvrir le navigateur automatiquement |
| `--workspace DOSSIER` | dossier de travail (données, workflows, rapports, blocs) |
| `--host 0.0.0.0` | rendre l'interface accessible depuis le réseau (voir ci-dessous) |
| `--version` | afficher la version |
| `--jobs N` | cœurs utilisés par la validation croisée, la recherche d'hyperparamètres, les courbes et les permutations (`-1` = tous, par défaut ; `1` = un seul) |
| `--cache-mb N` | taille maximale du cache des résultats, en Mo (1024 par défaut) |

La variable d'environnement `KATAML_WORKSPACE` fixe aussi le dossier de travail,
`KATAML_CACHE_MB` la taille maximale du cache des résultats (1024 Mo par défaut) et
`KATAML_N_JOBS` le nombre de cœurs.

!!! tip "Gros jeux de données"
    Au-delà de 10 000 lignes, les calculs répétés (validation croisée, recherche
    d'hyperparamètres, courbes, importance par permutation) se répartissent sur tous les
    cœurs du processeur. Chaque cœur reçoit une copie des données : en cas de mémoire
    insuffisante, limitez-les (`--jobs 4`). Avec beaucoup de nœuds sur une grosse table,
    agrandissez le cache (`--cache-mb 4096`) pour que les résultats déjà calculés ne soient
    pas recalculés.

!!! warning "Sécurité"
    Par défaut, KataML n'écoute que sur la machine locale (`127.0.0.1`) et chaque requête
    doit porter un jeton aléatoire généré au démarrage. Le nœud « Script Python » et les
    blocs personnalisés exécutent du code Python : n'utilisez `--host 0.0.0.0` que sur un
    réseau de confiance.

## Quitter

Le bouton **⏻** en haut à droite arrête le serveur. On peut aussi fermer la fenêtre du
terminal (ou faire ++ctrl+c++). Le dernier workflow est conservé par le navigateur et
restauré au prochain lancement ; les résultats déjà calculés sont relus depuis le cache.
