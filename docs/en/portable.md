# Portable builds

Portable builds let you use KataML **without installing anything**: a lab room without
administrator rights, a USB stick, a locked-down workstation. They are published with each
version on the [releases page](https://gitlab.com/fredbl/kataml/-/releases).

| Package | Content | Workspace |
|---|---|---|
| `KataML-<version>-x86_64.AppImage` (Linux) | a single executable file | `kataml-workspace/` next to the file |
| `KataML-<version>-windows-x64.zip` (Windows 10/11) | a folder with `KataML.bat` | `workspace/` in the folder |

Each package bundles a complete Python, scikit-learn, pandas, numpy, scipy and KataML: it
depends on no Python installed on the machine and changes nothing outside its folder. Usage
is described in [Installation](installation.md#1-portable-version-nothing-to-install).

## Workspace

Everything you produce (workflows, imported data, reports, custom blocks, cache) is stored
in the workspace, **next to** the application. To move to a new version, replace the
application and keep the folder. To carry your work around, copy the application and its
folder together.

If the location is not writable (application placed in a system folder, read-only stick),
KataML uses `~/kataml` instead and says so at startup.

## How they are built

Both packages are built **from Linux**, by GitLab continuous integration, on each version
tag (`vX.Y.Z`):

1. a relocatable Python ([python-build-standalone](https://github.com/astral-sh/python-build-standalone),
   the one uv uses) is downloaded for each platform, at a pinned version;
2. the official *wheels* of KataML and its dependencies are installed into it
   (`uv pip install --target --python-platform`), with no compilation;
3. everything is cleaned (tests, headers), precompiled to `.pyc` and packaged: AppImage
   (with `appimagetool`) or zip;
4. a **smoke test** launches the Linux package, runs a workflow, generates a report and
   checks the cancellation of a computation.

To build locally:

```bash
uv run --no-project python tools/build_portable.py --target all --smoke-test
```

Packages are written to `dist/`; downloads are cached in `.build-cache/`.
