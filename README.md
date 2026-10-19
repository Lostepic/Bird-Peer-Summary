# BIRD Peer Summary

**A clearer view of your BGP sessions, straight from the terminal.**

`bps` turns BIRD's protocol output into a readable peer summary: session health, neighbour addresses and ASNs, route counts, state timestamps and useful connection errors. It is a single Python script with **no third-party Python dependencies** and makes **one read-only `birdc` query per snapshot**.

[Installation](#installation) · [Usage](#usage) · [Updating BPS](#updating-bps) · [Options](#options) · [Troubleshooting](#troubleshooting)

## At a glance

```text
BIRD / Peer summary
3 peers  /  1 up  /  2 down

NAME         PEER                 STATE          IN  OUT  DETAIL
-----------  -------------------  ------  ---------  ---  ----------------------------------------------------
upstream v4  192.0.2.1 AS64501    UP      1,200,000    5  Example transit
ix v6        2001:db8::1 AS64502  ACTIVE          0    0  Socket: Connection refused | retry 4.500/5 | Exampl…
disabled     -                    DOWN            0    0  Administratively down | Maintenance

Updated 2026-10-19 13:29:16
```

Illustrative compact view. In wider terminals, the table also shows a separate ASN column, address-family channels and BIRD's state-start timestamp. Colours highlight session states; headings and secondary fields use subtle styling. The layout adapts to the terminal width.

- Find peers by name, ASN, neighbour IP or description.
- Isolate established sessions with `--up`, or investigate the rest with `--down`.
- Sort by state, name, ASN, imported routes or exported routes.
- Refresh live, or export JSON for your own scripts.
- Keep source addresses available with `--details`.

BPS does not reload BIRD, change configuration or reset sessions. Every query uses `birdc -r` restricted mode, as described in the [BIRD remote control guide](https://bird.network.cz/doc/bird-4.html).

## Requirements

- A Linux/BSD host running BIRD, with `birdc` installed.
- Python **3.8 or newer**.
- Permission to access BIRD's control socket.
- Bash and the standard `install` utility for the installer.

The project has previously been tested with **BIRD 2.17.x, 2.18.x and 3.3.x**. The current automated suite uses synthetic protocol output; changes should also be verified against a live daemon before production rollout.

## Installation

On Debian/Ubuntu, install Git and Python if needed, then clone and install:

```bash
sudo apt install git python3 -y
git clone https://github.com/Lostepic/Bird-Peer-Summary.git
cd Bird-Peer-Summary
sudo bash install.sh
bps --version
bps
```

The installer creates `/usr/local/bin/bird-peer-summary` and the `bps` alias. BIRD and `birdc` must already be installed separately.

For a custom directory or command name:

```bash
sudo PREFIX=/usr/local/bin TARGET_NAME=bird-peers bash install.sh
```

For an install under your own account:

```bash
PREFIX="$HOME/.local/bin" bash install.sh
```

Make sure that directory is in your `PATH`.

## Usage

```bash
bps                              # Default peer summary
bps --compact                    # Fewer columns
bps --details                    # Include source addresses and full details
bps --down                       # Sessions that are not established
bps --up --sort imported          # Established peers, busiest first
bps --match AS64501               # Search an ASN
bps --match 2001:db8::1           # Search a neighbour address
bps --match transit               # Search a name or description
bps --watch 5                     # Live view with a five-second interval
bps --down --watch 5              # Watch sessions needing attention
bps --compact --no-color          # Plain text
```

The default detail column shows descriptions for established peers and puts connection errors first for other peers. `--details` includes the full detail summary, including source addresses for established sessions.

### Keeping it lightweight

A normal `bps` run queries BIRD once and exits. Watch mode queries once per refresh, then sleeps for the requested interval; `bps --watch 5` is a sensible starting point for a live view. There are no background services or third-party Python packages. Press **Ctrl+C** to stop watching.

### Custom BIRD installations

```bash
bps --socket /run/bird/bird6.ctl
bps --birdc /usr/local/sbin/birdc --timeout 5
BIRDC=/usr/local/sbin/birdc bps
```

`--birdc` takes precedence over `BIRDC`. An invalid explicit path reports an error instead of silently using another executable.

### JSON output

```bash
bps --json > peers.json
bps --json --down
bps --json --watch 5 >> peers.jsonl
```

A single run produces a formatted JSON object. Watch mode emits one complete JSON object per line, suitable for collecting snapshots.

| Field | Contents |
| --- | --- |
| `generated_at` | Local timestamp with UTC offset |
| `summary` | `total`, `up` and `down` counts for the filtered result |
| `peers` | Array of matching peers; empty when nothing matches |

Each peer includes its original `name`, `pretty_name`, `neighbor`, `neighbor_as`, description, channels, `since` timestamp and detail fields. `state` is BIRD's protocol state, `bgp_state` is its reported BGP state, and `session_state` is the normalised state used for filtering. `imported`, `exported` and `preferred` are integers. `neighbor_as` remains a string because some sessions do not expose it.

## Updating BPS

To install the latest version, open your original clone, pull the latest changes and rerun the installer:

```bash
cd /path/to/Bird-Peer-Summary
git pull --ff-only origin main
sudo bash install.sh
bps --version
```

Replace `/path/to/Bird-Peer-Summary` with the directory where you cloned this repository. **Pulling alone does not update the installed command**: rerun the installer to copy the new script into place. No BIRD restart or configuration reload is needed. Stop and restart any running `bps --watch` process to use the new version.

If you originally used a custom install directory or command name, use the same settings when updating:

```bash
sudo PREFIX=/usr/local/bin TARGET_NAME=bird-peers bash install.sh
bird-peers --version
```

For an install under your own account:

```bash
PREFIX="$HOME/.local/bin" bash install.sh
bps --version
```

If you no longer have the clone, clone the repository again and follow the installation steps. If Git reports local modifications or divergent history, resolve or save those changes before pulling; `--ff-only` avoids creating an unexpected merge.

To check which installed command you are running:

```bash
command -v bps
bps --version
```

## Options

| Option | Purpose |
| --- | --- |
| `--up` | Show BGP `Established` sessions only |
| `--down` | Show all other sessions, including disabled peers |
| `--match TEXT` | Case-insensitive search of names, ASNs, IPs and descriptions |
| `--sort FIELD` | `state` (default), `name`, `asn`, `imported` or `exported` |
| `--compact` | Use fewer columns |
| `--details` | Include source addresses and full details |
| `--watch SECONDS` | Refresh repeatedly; accepts positive fractional seconds |
| `--json` | JSON snapshot, or newline-delimited JSON with `--watch` |
| `--no-color` | Disable ANSI styling |
| `--socket PATH`, `-s PATH` | Select the BIRD control socket |
| `--birdc PATH` | Select the `birdc` executable |
| `--timeout SECONDS` | Query timeout; default `10`, accepts positive fractions |
| `--version` | Print the BPS version without querying BIRD |
| `--help`, `-h` | Show command help |

State sorting puts established peers first. Route-count sorting is largest first; name and ASN sorting are ascending. `--up` and `--down` cannot be combined.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `Could not find birdc` | Install `birdc`, or set `--birdc /path/to/birdc` or `BIRDC` |
| Socket connection or permission error | Confirm BIRD is running, select the correct `--socket` and use an account allowed to access it |
| Query timeout | Check daemon health; use `--timeout SECONDS` if necessary |
| No matching peers | Remove filters and check `birdc -r show protocols all` for BGP instances |
| Old version after updating | Rerun the installer and check `command -v bps` for another installation earlier in `PATH` |

- Imported/exported/preferred counts are summed across a peer's channels; they are BIRD's route counters, not counts of unique prefixes across all peers.
- `SINCE` preserves BIRD's state-start timestamp. Its format depends on the daemon configuration.
- Redirected output contains no colour or screen-clearing codes. `NO_COLOR` and `TERM=dumb` are respected.
- Watch mode stops on query failure with an error rather than presenting an old snapshot as fresh data.
- Exit codes: **0** for success (including no matches), **1** for query/executable/timeout errors, **2** for invalid arguments.

## Development

Run the regression suite without BIRD or extra Python packages:

```bash
python3 -m unittest discover -s tests -v
bash -n install.sh
```

The fixture covers IPv4/IPv6, multiple channels, disabled sessions, connection errors and non-BGP protocols. Tests cover parsing, filtering, sorting, query construction, timeouts, JSON, watch output and terminal rendering. GitHub Actions runs tests on Python 3.8, 3.12 and 3.14, and checks installation and command aliases on Linux.

## Licence

[MIT](LICENSE) — Aaran Perry.
