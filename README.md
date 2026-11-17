# Spotlight AI Search

A compact, frosted-glass Google AI search popup for **Omarchy with Hyprland's Lua configuration**.

Type a question, complete it with Google's suggestions, and press Enter to open Google AI Mode in the same Brave app window. The search panel expands to fit suggestions, then grows into a reading window for the answer.

## Controls

| Shortcut | Action |
| --- | --- |
| Alt+Space | Show or hide the current search |
| Super+Alt+Space | Close only the popup and open a fresh search |
| Up / Down | Choose a suggestion |
| Tab | Complete the selected or first suggestion |
| Enter | Search in Google AI Mode |
| Escape | Dismiss suggestions |

Super+Alt+Space replaces Omarchy's default Apps-menu binding while installed. Existing default actions return when the managed module is removed. If you had your own conflicting custom binding, review the saved bindings backup after uninstalling.

## Requirements

- Omarchy using `~/.config/hypr/bindings.lua` and the `o` helpers.
- Hyprland with the Lua API (`hl`), version 0.55 or newer. Developed on 0.56.
- Brave with a **Default** browser profile. Other browsers and profiles are not currently supported by the automatic installer.
- Python 3.10 or newer and systemd user services.
- Internet access and Google AI Mode availability for your account/region.
- Desktop blur enabled for the frosted effect. Normal Brave search settings are not modified.

This is not a GNOME/KDE launcher, a native Wayland layer-shell app, or a general Hyprland configuration installer. The launcher is a small web page inside Brave app mode; the window treatment comes from Hyprland.

## Install

From a checkout of this project:

```sh
python3 install.py --dry-run
python3 install.py
```

No sudo, API key, Python packages, or browser extension is required. The installer uses XDG configuration/data directories, backs up `bindings.lua`, and adds a clearly marked module import. It validates the Hyprland configuration before starting the service. Failed activation restores the previous managed files and bindings.

The default loopback port is **18476**. To choose another unprivileged port:

```sh
python3 install.py --port 18500
```

`--no-start` writes the files without enabling the service or reloading Hyprland. This is useful for reviewing a deployment; it still requires the listed dependencies. Re-running the installer is supported while installed files are unmodified. It refuses to overwrite local edits or an unowned installation directory.

Installed files:

```text
$XDG_DATA_HOME/spotlight-ai-search/          # defaults to ~/.local/share/
$XDG_CONFIG_HOME/hypr/spotlight-ai-search.lua
$XDG_CONFIG_HOME/systemd/user/spotlight-ai-search.service
```

Generated runtime settings and ownership receipts live in the installation directory, not in the source checkout.

## Uninstall

Run from the checkout:

```sh
python3 uninstall.py
```

The uninstaller stops/disables its service, removes its exact bindings block, and removes only owned, unchanged files. It preserves edited and unrelated files. Bindings backups remain beside `bindings.lua`. `--no-services` skips service commands and the compositor reload for an offline/staged removal.

## Manual use and troubleshooting

To try the search page without installing the window integration:

```sh
python3 app/server.py --port 18476
```

Open `http://127.0.0.1:18476/spotlight-ai` in a browser. Submit opens Google AI Mode. Automatic sizing, glass treatment, and desktop shortcuts require the supplied Omarchy integration. The Lua template can be adapted manually for other Hyprland setups; plain Hyprland does not supply Omarchy's `o` helper.

Service diagnostics:

```sh
systemctl --user status spotlight-ai-search.service
journalctl --user -u spotlight-ai-search.service
hyprctl configerrors
```

If the port is occupied, select a different port at installation. The source uses a distinct service name, URL path, and popup window class so it can coexist with other local applications. Existing unrelated Brave windows are never closed by fresh start.

Google's autocomplete endpoint and the AI Mode URL parameters (`udm=50`, `aep=11`) are not a supported public integration API and may change. The latter follows Chromium's AI entry URL. This project does not hide or automatically accept Google's confirmation dialogs. Availability and response speed are controlled by Google. If suggestions fail, you can still submit a typed query.

## Privacy

- The source contains no account identifiers, API keys, browser profiles, cookies, screenshots, chat transcripts, search history, or personal Hyprland configuration.
- Partial queries are sent to Google's autocomplete service as you type. Selected/submitted queries go to Google AI Mode.
- The local server listens only on `127.0.0.1` and does not log request URLs or queries. Its short autocomplete cache is in memory only.
- Brave uses your existing Default profile and its Google sign-in. Google's and Brave's normal account/history settings still apply. This is **not private browsing**.

## Development

Everything uses Python's standard library and plain HTML/CSS/JavaScript:

```sh
python3 -m unittest discover -s tests -v
node --check app/app.js       # optional JavaScript syntax check
```

Tests use temporary installation directories, an ephemeral loopback port, and mocked external requests. They do not alter the real desktop, start installed services, open Brave, or contact Google.

```text
app/                       # search UI, autocomplete service, scoped launcher
integration/hyprland.lua.in # portable window/shortcut template
install.py                 # user-local setup
uninstall.py               # conservative removal
project_setup.py           # shared installation logic
tests/                     # backend, launcher, and install lifecycle tests
```

## License

MIT. See [LICENSE](LICENSE). This is an independent project, not affiliated with Apple, Google, Brave, or Omarchy.
