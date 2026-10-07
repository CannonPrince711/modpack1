#!/bin/sh
# Saltglass — fetch and verify the server-side mods.
# Needs Python 3.8+ and network access to api.modrinth.com and edge.forgecdn.net.
set -e
cd "$(dirname "$0")"
python3 fetch_mods.py --resolve
python3 fetch_mods.py --download mods --server
echo 'mods/ is ready. Client-only jars were deliberately skipped.'
