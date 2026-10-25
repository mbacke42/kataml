# Installation

KataML needs no administrator rights and does not modify the system: everything is
installed in a user folder. There are three installation modes, from the simplest to the
most flexible.

## 1. Portable version (nothing to install)

Each [published release](https://gitlab.com/fredbl/kataml/-/releases) provides two
packages that bundle Python, pandas and scikit-learn.

=== "Linux"

    1. Download `KataML-<version>-x86_64.AppImage`.
    2. Make it executable, then run it:
       ```bash
       chmod +x KataML-*-x86_64.AppImage
       ./KataML-*-x86_64.AppImage
       ```
    3. The browser opens on the interface. Data is stored in `kataml-workspace/`,
       **next to the AppImage file**.

    !!! note "Missing “FUSE”"
        On some recent distributions, an AppImage needs the `libfuse2` library. Without
        it, run it with `--appimage-extract-and-run`.

=== "Windows"

    1. Download `KataML-<version>-windows-x64.zip` and unzip it.
    2. Double-click **`KataML.bat`**. A black window (the server) opens, then the
       browser.
    3. Data is stored in the `workspace/` folder, next to the launcher. The whole folder
       can be moved or copied to a USB stick.

    !!! note "SmartScreen"
        The package is not signed: Windows may display “Windows protected your PC”.
        Click **More info**, then **Run anyway**.

## 2. With uv (recommended for workstations)

[uv](https://docs.astral.sh/uv/) installs Python and the dependencies without
administrator rights:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh        # installs uv (once)
uv tool install git+https://gitlab.com/fredbl/kataml.git
kataml
```

The `kataml` command is placed in `~/.local/bin`. The default workspace is
`~/kataml`. Upgrade and uninstall:

```bash
uv tool upgrade kataml
uv tool uninstall kataml
```

To try without installing: `uvx --from git+https://gitlab.com/fredbl/kataml.git kataml`.

## 3. From the repository (development)

```bash
git clone https://gitlab.com/fredbl/kataml.git
cd kataml
./kataml.sh        # Windows: kataml.bat
```

On first launch, uv creates `.venv/` in the folder and installs the dependencies there.
The workspace is then `workspace/`, next to the code.

## Launch options

| Option | Effect |
|---|---|
| `--port 9000` | HTTP port (8765 by default; the next free one is used if needed) |
| `--no-browser` | do not open the browser automatically |
| `--workspace FOLDER` | working folder (data, workflows, reports, blocks) |
| `--host 0.0.0.0` | make the interface reachable from the network (see below) |
| `--version` | show the version |
| `--jobs N` | cores used by cross-validation, hyperparameter search, curves and permutations (`-1` = all, default; `1` = one) |
| `--cache-mb N` | maximum size of the result cache, in MB (1024 by default) |

The `KATAML_WORKSPACE` environment variable also sets the working folder, and
`KATAML_CACHE_MB` the maximum size of the result cache (1024 MB by default) and
`KATAML_N_JOBS` the number of cores.

!!! tip "Large datasets"
    Above 10,000 rows, repeated computations (cross-validation, hyperparameter search,
    curves, permutation importance) are spread over all the processor cores. Each core gets
    a copy of the data: if memory runs short, limit them (`--jobs 4`). With many nodes on a
    large table, enlarge the cache (`--cache-mb 4096`) so that results already computed are
    not computed again.

!!! warning "Security"
    By default, KataML only listens on the local machine (`127.0.0.1`) and every request
    must carry a random token generated at startup. The “Python script” node and custom
    blocks execute Python code: only use `--host 0.0.0.0` on a trusted network.

## Quitting

The **⏻** button at the top right stops the server. You can also close the terminal
window (or press ++ctrl+c++). The last workflow is kept by the browser and restored at
next launch; results already computed are read back from the cache.
