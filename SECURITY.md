# Security

`hotkeyconfig` installs dependencies and uses a **global keyboard hook**, which is a sensitive
area. These are the project's commitments.

## The listener is NOT a keylogger

- It only reacts to the **`F13` to `F24` combos configured** in your `profile.yaml`.
- It does **not** record, store or transmit your normal keystrokes.
- It makes **no** network calls. There is no telemetry.
- All the code is open source and auditable (`hotkeyconfig/runtime.py`, `actions.py`).

## Updates

The updater (`hotkeyconfig/updater.py`) is the only component that uses the network:

- It only talks to **GitHub over HTTPS** (the release API and the release assets). Any other host
  is rejected.
- The downloaded installer's **SHA256 is verified against the published `SHA256SUMS.txt`** before
  anything is executed.
- It never updates silently on its own: the app shows a banner and you decide.

## Legitimate, verified dependencies

- **Default path is pure Python**: flashing goes over **native HID** (`hidapi`), with no Rust and no
  external binaries. The protocol is ported byte for byte (and therefore auditable) from ch57x, and
  is written only to the `MI_00` programming interface.
- **Python dependencies**: minimal and from the official **PyPI** only (`PyYAML`, `keyboard`,
  `pystray`, `Pillow`, `hidapi`, `pywebview`, `pywin32`).
- **`ch57x-keyboard-tool`** (OPTIONAL backend): a well known public repo (MIT, by `kriomant`). If
  used, install from **crates.io** with `--locked` and audit with `cargo audit`.
- **Auditing**: `pip-audit` (Python) and `cargo audit` (ch57x tree) must pass with no known
  vulnerabilities before publishing.

```bash
pip-audit                 # Python dependencies
cargo audit               # dependencies of ch57x-keyboard-tool
```

### Audit status (2026-06-21)

- **`pip-audit`**: no known vulnerabilities in the Python dependencies.
- **`cargo audit`** over the `ch57x-keyboard-tool` 1.7.0 tree (105 crates): 3 advisories, **all of
  them in transitive dependencies of that tool**, none in this project's code:
  - `RUSTSEC-2026-0009` (`time`, medium 6.8): stack exhaustion DoS when **parsing untrusted time
    strings**. Does not apply to our usage: we only hand it YAML we generated ourselves, and the
    tool runs locally on demand.
  - `RUSTSEC-2024-0370` (`proc-macro-error`): unmaintained build crate.
  - `RUSTSEC-2023-0075` (`unsafe-libyaml`): misaligned write, only on **32/16 bit** platforms (does
    not affect Windows x64).
- Conclusion: `ch57x-keyboard-tool` is legitimate (a known MIT repo) and free of backdoors; the
  advisories are low risk and live in its upstream tree. Worth reporting upstream or updating when
  they publish a version with `time>=0.3.47`.

## No secrets in the repository

- API keys and private paths are never committed.
- Your real `config/profile.yaml` is in `.gitignore`; only `config/profile.example.yaml` is
  published.

## Running your scripts

`run` actions execute **what you define** in your own `profile.yaml`, locally and under your
control. The app does **not** download or evaluate code from external sources.

## Reporting a vulnerability

Open a private issue or contact the maintainer. Please do not publish exploitable details until a
patch exists.
