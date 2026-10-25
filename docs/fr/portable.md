# Versions portables

Les versions portables permettent d'utiliser KataML **sans rien installer** : une salle
de TP sans droits administrateur, une clé USB, un poste verrouillé. Elles sont publiées
à chaque version sur la [page des releases](https://gitlab.com/fredbl/kataml/-/releases).

| Paquet | Contenu | Espace de travail |
|---|---|---|
| `KataML-<version>-x86_64.AppImage` (Linux) | un fichier exécutable unique | `kataml-workspace/` à côté du fichier |
| `KataML-<version>-windows-x64.zip` (Windows 10/11) | un dossier avec `KataML.bat` | `workspace/` dans le dossier |

Chaque paquet embarque un Python complet, scikit-learn, pandas, numpy, scipy et KataML :
il ne dépend d'aucun Python installé sur la machine et ne modifie rien en dehors de son
dossier. L'utilisation est décrite dans [Installation](installation.md#1-version-portable-rien-a-installer).

## Espace de travail

Tout ce que vous produisez (workflows, données importées, rapports, blocs personnalisés,
cache) est rangé dans l'espace de travail, **à côté** de l'application. Pour passer à une
nouvelle version, remplacez l'application et gardez le dossier. Pour transporter votre
travail, copiez l'application et son dossier ensemble.

Si l'emplacement n'est pas inscriptible (application posée dans un dossier système, clé
en lecture seule), KataML utilise `~/kataml` à la place et l'indique au démarrage.

## Fabrication

Les deux paquets sont construits **depuis Linux**, par l'intégration continue GitLab, à
chaque tag de version (`vX.Y.Z`) :

1. un Python relocalisable ([python-build-standalone](https://github.com/astral-sh/python-build-standalone),
   celui qu'utilise uv) est téléchargé pour chaque plateforme, en version figée ;
2. les *wheels* officielles de KataML et de ses dépendances sont installées dedans
   (`uv pip install --target --python-platform`), sans compilation ;
3. le tout est nettoyé (tests, en-têtes), précompilé en `.pyc` et empaqueté :
   AppImage (avec `appimagetool`) ou zip ;
4. un **test de fumée** lance chaque paquet Linux, exécute un workflow, génère un
   rapport et vérifie l'annulation d'un calcul.

Pour construire localement :

```bash
uv run --no-project python tools/build_portable.py --target all --smoke-test
```

Les paquets sont écrits dans `dist/` ; les téléchargements sont mis en cache dans
`.build-cache/`.
