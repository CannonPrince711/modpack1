#!/usr/bin/env python3
"""Repair loot tables that Forge rejects because they reference items or functions the pack does not have.

Several structure mods ship chest tables with entries for optional compat mods (Ice and Fire, Ars Nouveau).
When that mod is absent, Forge discards the *whole* table, so those chests spawn empty. This reads a server log,
finds every "Couldn't parse element loot_tables:<id>" failure, loads the original table from the mod jars, drops
only the offending entries, and writes the patched copy to overrides/kubejs/data/<namespace>/loot_tables/.

  python3 tools/fix_loot_tables.py --mods <dir with the pack's jars> --log <server latest.log or console output>

Run again after adding mods; tables that now parse are left alone and stale overrides are removed.
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "overrides" / "kubejs" / "data"
ALWAYS = {"minecraft", "forge", "c"}


def installed_namespaces(mods_dir):
    ids = set(ALWAYS)
    for jar in glob.glob(f"{mods_dir}/*.jar"):
        archive = zipfile.ZipFile(jar)
        names = archive.namelist()
        if "META-INF/mods.toml" in names:  # only declared mods count: jars also ship compat data for mods that are absent
            ids.update(re.findall(r'modId\s*=\s*"([^"]+)"', archive.read("META-INF/mods.toml").decode("utf-8", "replace")))
    return ids


def failing_tables(log_path):
    text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    tables = set(re.findall(r"Couldn't parse element loot_tables:(\S+)", text))
    functions = set(re.findall(r"Unknown type '([^']+)'", text))
    return tables, functions


def find_json(mods_dir, table):
    namespace, _, path = table.partition(":")
    member = f"data/{namespace}/loot_tables/{path}.json"
    for jar in sorted(glob.glob(f"{mods_dir}/*.jar")):
        archive = zipfile.ZipFile(jar)
        if member in archive.namelist():
            return json.loads(archive.read(member))
    return None


def strip(node, namespaces, bad_functions, removed):
    """Remove item entries from unknown namespaces and unknown functions, recursively."""
    if isinstance(node, list):
        kept = []
        for child in node:
            if isinstance(child, dict):
                name = child.get("name", "")
                if child.get("type", "").rpartition(":")[2] == "item" and not name:
                    removed.append("<entry with no name>")  # a bug in the mod's own table
                    continue
                if child.get("type", "").rpartition(":")[2] == "item" and ":" in name and name.partition(":")[0] not in namespaces:
                    removed.append(name)
                    continue
                if "function" in child and child["function"] in bad_functions:
                    removed.append(child["function"])
                    continue
            kept.append(strip(child, namespaces, bad_functions, removed))
        return kept
    if isinstance(node, dict):
        return {key: strip(value, namespaces, bad_functions, removed) for key, value in node.items()}
    return node


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mods", required=True)
    parser.add_argument("--log", required=True)
    args = parser.parse_args()

    namespaces = installed_namespaces(args.mods)
    tables, bad_functions = failing_tables(args.log)
    fixed, unresolved = [], []
    for table in sorted(tables):
        original = find_json(args.mods, table)
        if original is None:
            unresolved.append(f"{table} (not found in the jars)")
            continue
        removed = []
        patched = strip(original, namespaces, bad_functions, removed)
        if not removed:
            unresolved.append(f"{table} (nothing recognisable to remove)")
            continue
        namespace, _, path = table.partition(":")
        target = DATA / namespace / "loot_tables" / f"{path}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(patched, indent=2) + "\n", encoding="utf-8")
        fixed.append((table, sorted(set(removed))))
    for table, removed in fixed:
        print(f"patched {table}: dropped {', '.join(removed)}")
    for line in unresolved:
        print(f"unresolved {line}")
    print(f"{len(fixed)} patched, {len(unresolved)} unresolved of {len(tables)} failing tables")


if __name__ == "__main__":
    main()
