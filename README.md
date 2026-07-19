# bps

`bps` is a small read-only wrapper around `birdc` that gives you a cleaner BGP peer summary than `birdc show protocols` on its own.

It is aimed at the annoying middle ground where you do not want a whole dashboard, but you also do not want to keep drilling into every peer one by one.

It shows, per BGP session:

- peer name
- neighbour IP
- neighbour ASN
- state
- imported route count
- exported route count
- when the current state started
- a short detail summary pulled from BIRD itself

It does **not** change BIRD config, touch sessions, reload anything, or write to the daemon. It only reads `birdc` output.

## What it supports

`bps` is written against the `birdc` output format used by modern BIRD installs and has been tested against:

- BIRD 2.17.x
- BIRD 2.18.x
- BIRD 3.3.x

If your `birdc` binary lives somewhere unusual, set `BIRDC` before running it:

```bash
BIRDC=/usr/local/sbin/birdc ./bps
```

## Features

- compact summary view for all BGP peers
- colourised states in a real terminal
- `--up` filter for established sessions only
- `--match` filter for quick peer searches
- `--watch` live refresh mode
- `--no-color` for logging or copy/paste

## Install

Clone the repo and run the installer:

```bash
apt install git -y
git clone https://github.com/Lostepic/Bird-Peer-Summary.git
cd Bird-Peer-Summary
chmod +x install.sh
sudo ./install.sh
```

That installs:

- `/usr/local/bin/bird-peer-summary`
- `/usr/local/bin/bps`

If you want a different prefix:

```bash
sudo PREFIX=/usr/bin ./install.sh
```

If you want a different command name as well:

```bash
sudo PREFIX=/usr/local/bin TARGET_NAME=bird-peers ./install.sh
```

## Usage

Default view:

```bash
bps
```

Compact view:

```bash
bps --compact
```

Only established peers:

```bash
bps --up
```

Filter to a specific peer or ASN string:

```bash
bps --match 47272
bps --match linx
bps --match apple
```

Live view refreshing every second:

```bash
bps --watch 1
```

Live compact view:

```bash
bps --watch 1 --compact
```

Plain text output with no ANSI colour:

```bash
bps --compact --no-color
```

## Example output

```text
BGP peer summary | total 13 | up 13 | down 0 | generated 2026-05-29 12:51:08

NAME              PEER                         STATE       IN      OUT  DETAIL
----------------  ---------------------------  -----  -------  -------  ------
apple 1 v4        206.55.196.100 AS714         UP        1311        1  Apple IPv4 - 1 | src 206.55.196.34
linx nova rs1 v4  206.55.196.230 AS8714        UP        9814        1  LINX NoVA RS1 IPv4 | src 206.55.196.34
xenyth v4         74.119.149.130 AS835         UP     1039467        1  Upstream Xenyth IPv4 | src 74.119.149.131
```

## Notes

- The imported/exported numbers come from BIRD's per-channel route counters.
- For down peers, the detail column will show the last useful error BIRD exposes, plus retry/connect timing where available.
- The `Since` field in the full view is BIRD's own state-start timestamp, so the exact format depends on what BIRD prints on that host.

## Why this exists

`birdc show protocols` is fine when you already know which peer you care about.

It is less fun when you just want a quick operational view of everything at once.

That is all this is trying to fix.
