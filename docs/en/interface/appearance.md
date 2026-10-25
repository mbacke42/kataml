# Appearance and themes

KataML can be customised at two levels: each user picks their preferences in the
interface, and a `theme.css` file can impose a house style on everyone (lab room, school,
company).

## The “Appearance” dialog

The palette button, at the top right, opens the **Appearance** dialog. Changes apply
immediately and are remembered by the browser.

![Appearance dialog](../../assets/screenshots/en/dialog-theme.png){ .shot }

| Setting | Choices |
|---|---|
| **Mode** | **Automatic** (follows the system's light / dark setting), **Light**, **Dark** |
| **Main colour** | **Default** (marked “A”), seven hues (teal, blue, green, indigo, orange, raspberry, slate) or a **custom** colour |
| **Canvas background** | **Dots**, **Grid** or **Plain** |

The main colour is used for primary buttons, the selection, links and active tabs.
The offered hues come in two versions, one per mode; a custom colour that is too dark is lightened automatically in dark mode. The text colour of buttons (white or
black) is chosen to keep good contrast. **Node family** and chart series colours do not
change: they carry meaning.

The moon / sun button, next to it, switches directly between light and dark. **Reset**
restores the original settings.

![Example: blue, dark mode, grid](../../assets/screenshots/en/theme-custom.png){ .shot }

**Reports** use the chosen main colour (they stay in light mode, for printing).

## The `theme.css` file

To go further, place a `theme.css` file at the root of the
[workspace](../concepts/workspace.md). It is loaded after KataML's stylesheet and can
redefine all its **CSS variables**. It applies to the interface and to generated reports,
including from the [command line](../cli.md). Reload the page after editing it.

```css
/* workspace/theme.css: a school's house style */
:root {
  --accent: #b91c1c;                 /* main colour (light mode) */
  --font: "Atkinson Hyperlegible", system-ui, sans-serif;
  --r: 4px; --r-sm: 3px; --r-lg: 6px; /* less rounded corners */
}
:root[data-theme="dark"] {
  --accent: #f87171;                 /* main colour (dark mode) */
}
```

In the Appearance dialog, the **Default** colour then becomes the one from `theme.css`; a
user can still pick another hue for themselves.

### Available variables

| Variables | Role |
|---|---|
| `--accent` | main colour; derived shades (`--accent-2`, `--accent-soft`, `--accent-ring`) are computed from it |
| `--on-accent` | text placed on the main colour |
| `--bg`, `--panel`, `--panel-2`, `--canvas`, `--canvas-dot` | backgrounds: page, panels, canvas, grid dots or lines |
| `--text`, `--text-2`, `--muted`, `--line`, `--line-strong` | text and borders |
| `--ok`, `--warn`, `--err`, `--run` | states: executed, warning, error, running |
| `--c-io`, `--c-manip`, `--c-view`, `--c-learner`, `--c-transformer`, `--c-score`, `--c-tune`… | node family colours |
| `--s1` … `--s8` | chart series |
| `--font`, `--mono` | interface and code fonts |
| `--r-sm`, `--r`, `--r-lg` | corner radii |

The full list is at the top of `kataml/static/css/app.css`. Dark-mode variables are
redefined under `:root[data-theme="dark"]`.

!!! tip "Fonts"
    KataML works offline and ships no web fonts: put in `--font` a font installed on the
    workstations, followed by a fallback (`system-ui`).
