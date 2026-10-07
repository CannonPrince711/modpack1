#!/usr/bin/env python3
"""
One-shot: fold the registry-verified pins captured on 2026-10-07 into pack/mods.lock.json.

This exists because the first draft of the lockfile was written from project *pages*
(versions, loaders, MC versions — all correct) while the exact download URL, filename and
hash of each file can only come from the registry API. Eleven pins moved as a result, two
project ids were wrong, one dependency was wrong (Alex's Mobs needs Citadel, not GeckoLib)
and one pinned version turned out not to be listed as a 1.20.1 release at all.

Run once:  python3 tools/apply_verified_pins.py
Idempotent: re-running with the same data changes nothing.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "pack/mods.lock.json"
SRC = "GET /v2/project/{id}/version?loaders=[\"forge\"]&game_versions=[\"1.20.1\"]&version_type=release"

# slug -> (version, filename, project_id, url, sha1, sha512, size, per-page)
PINS = {
    "create": ("mc1.20.1-6.0.8", "create-1.20.1-6.0.8.jar", "LNytGWDc",
               "https://cdn.modrinth.com/data/LNytGWDc/versions/8amzvn9x/create-1.20.1-6.0.8.jar",
               "b13d912b9247a38d66d11598c121442585a1c1e9",
               "5b51f5d31437d9bfbf221b67459abd87260d284874e1e23b7ed1d522b23a48059a3b1d2c1c541428da35dc6be15561b4f3c7f36aac6df3a0e8db6a278f6b0316",
               19170905, "https://modrinth.com/mod/create/version/8amzvn9x"),
    "farmers-delight": ("1.20.1-1.3.4", "FarmersDelight-1.20.1-1.3.4.jar", "R2OftAxM",
                        "https://cdn.modrinth.com/data/R2OftAxM/versions/SiIpcZzM/FarmersDelight-1.20.1-1.3.4.jar",
                        "26f615fd35f652021f5b0f1cba68afa7d578fe15",
                        "932ae0ab95fa0755bb5a79fbf1d1e31d0e86f3c0f5186796ed06973a3019a618ee8c66a4eae5b901909aed6232abb2bd3b1ff0e1905f74fc70644fada94a80b5",
                        3311051, "https://modrinth.com/mod/farmers-delight/version/SiIpcZzM"),
    "alexs-mobs": ("1.22.9", "alexsmobs-1.22.9.jar", "2cMuAZAp",
                   "https://cdn.modrinth.com/data/2cMuAZAp/versions/XoIASRVU/alexsmobs-1.22.9.jar",
                   "dbf93d2f1da19e16739e91e8ea0fc6f4bc2f228f",
                   "b50280057926d750f9ffbf6a8df36deb37529356895f6bf59f25d272ecf69afccec65ec1a5c3a8bfad24f9475c15b93c5ec4666447b1fce26a90c41445bbfb04",
                   26350793, "https://modrinth.com/mod/alexs-mobs/version/XoIASRVU"),
    "citadel": ("2.6.3", "citadel-2.6.3-1.20.1.jar", "jJfV67b1",
                "https://cdn.modrinth.com/data/jJfV67b1/versions/lTAAe4sZ/citadel-2.6.3-1.20.1.jar",
                "fb0b1fa96ce28e4be77b38ad95d83c3da7ec8316",
                "42e3fa0ddefb1ebdbba4242d81caede834cd0bbd96e4e90b12b2157a5b07c68b625f64046de1f9e1ad4d6056d3536e17207be5f4b24960582052d713b13f22c0",
                3185275, "https://modrinth.com/mod/citadel/version/lTAAe4sZ"),
    "ars-nouveau": ("4.12.7", "ars_nouveau-1.20.1-4.12.7-all.jar", "TKB6INcv",
                    "https://cdn.modrinth.com/data/TKB6INcv/versions/Hw2aD01e/ars_nouveau-1.20.1-4.12.7-all.jar",
                    "6c23a97d771ea7ad43bee9bd71d2f2a1f2084170",
                    "f3e3abf260fb3ef4c5b6b7324c055802135f82f4c550986f4e93b1a186c9b495cd8b6396ed89ab088b95e6176c0b9e290ccc69a528c521cd1bff19935ac36836",
                    12430237, "https://modrinth.com/mod/ars-nouveau/version/Hw2aD01e"),
    "corail-tombstone": ("forge-1.20.1-9.1.5", "tombstone-1.20.1-9.1.5.jar", "YT5K34AB",
                         "https://cdn.modrinth.com/data/YT5K34AB/versions/nTAliy2r/tombstone-1.20.1-9.1.5.jar",
                         "0d9cb76b6162c672a7aca40771e5749a97ebb451",
                         "57283c5dce944a4eaec4240a0d2bb33d5c6f009a5b6a7a7334f48c286aa17ecd794e7025ff87e61b5555ce29667eb2ad336d92e4235d1384e0172b485e23338a",
                         2560746, "https://modrinth.com/mod/corail-tombstone/version/nTAliy2r"),
    "yungs-extras": ("1.20-Forge-4.0.3", "YungsExtras-1.20-Forge-4.0.3.jar", "ZYgyPyfq",
                     "https://cdn.modrinth.com/data/ZYgyPyfq/versions/h4m8J7w8/YungsExtras-1.20-Forge-4.0.3.jar",
                     "4b2e632353a95c16a080c2e64c426480a139fbd6",
                     "2c70e8e2c8e6161139bd19d302e225f7c12dc44f9cbdd63f4a548645fe923eb16de930abe2d2f8a89bee99f31d77798b7352bbd33f3642560cad18d86d372d4f",
                     200341, "https://modrinth.com/mod/yungs-extras/version/h4m8J7w8"),
    "yungs-api": ("1.20-Forge-4.0.6", "YungsApi-1.20-Forge-4.0.6.jar", "Ua7DFN59",
                  "https://cdn.modrinth.com/data/Ua7DFN59/versions/PJOYAmAs/YungsApi-1.20-Forge-4.0.6.jar",
                  "af584b690f5646c6032002b58abc4591beed3833",
                  "7d83d94a90e55a712f6508485c044ff202916e9b9b9166b75177cb8f2eb919543bbbe1547d11c41cfd4763820f934235f47c0b26dd9e89bc1030954afa9fb889",
                  370524, "https://modrinth.com/mod/yungs-api/version/PJOYAmAs"),
    "sophisticated-backpacks": ("1.20.1-3.26.9.2194", "sophisticatedbackpacks-1.20.1-3.26.9.2194.jar", "TyCTlI4b",
                                "https://cdn.modrinth.com/data/TyCTlI4b/versions/nSVHlIzZ/sophisticatedbackpacks-1.20.1-3.26.9.2194.jar",
                                "315a8151c0e89c71ae165e33bcfcfccc762a1766",
                                "6d78f290fd4acb5e856da8e7f105d626fbb8d416439b2676f89f4239b56f3c146c1bd9df2a2119a07df24904bc4a598eeb8c17389424f75d18845564f01b9c98",
                                1215727, "https://modrinth.com/mod/sophisticated-backpacks/version/nSVHlIzZ"),
    "sophisticated-core": ("1.20.1-1.5.6.2378", "sophisticatedcore-1.20.1-1.5.6.2378.jar", "nmoqTijg",
                           "https://cdn.modrinth.com/data/nmoqTijg/versions/yIBA2SnN/sophisticatedcore-1.20.1-1.5.6.2378.jar",
                           "6b43a36241c8f9ad777efd83a7ea2268af23230a",
                           "6a2246e61f0180368bb93ce0992209bef887f37b640a0ddec771b00b0dcdbc299ae0399675163a8f75297f7e6205d8bed8bb12e76ed5bbbd9c5c0eda3805bf1a",
                           1758791, "https://modrinth.com/mod/sophisticated-core/version/yIBA2SnN"),
    "paragliders": ("20.1.3", "Paraglider-forge-20.1.3.jar", "esqWA0aQ",
                    "https://cdn.modrinth.com/data/esqWA0aQ/versions/nudKlXXT/Paraglider-forge-20.1.3.jar",
                    "51fdf94686fc847515e6de8a6c9fd4dab3466ea5",
                    "81212fb4b3a0cf7af4ce8df2f9bab0c0f05527bd7c022ae65dbe97032e06083401d81bc03c3b41f04651140a0261196e2cb14a0431b9b8d096e18de8129340a1",
                    589055, "https://modrinth.com/mod/paragliders/version/nudKlXXT"),
    "emi": ("1.1.24+1.20.1+forge", "emi-1.1.24+1.20.1+forge.jar", "fRiHVvU7",
            "https://cdn.modrinth.com/data/fRiHVvU7/versions/Axuu9I9R/emi-1.1.24%2B1.20.1%2Bforge.jar",
            "ea320200878e4a49196760234a22da763671520a",
            "02743be3476b7dc5668cedbcc5a6d384e9806981833926a83fed76a2800c44da33576e86308c058250718c128d58076f1b62bc53d200464326ace70a43229c8b",
            1121750, "https://modrinth.com/mod/emi/version/Axuu9I9R"),
    "xaeros-minimap": ("forge-1.20.1-26.5.0", "xaerominimap-forge-1.20.1-26.5.0.jar", "1bokaNcj",
                       "https://cdn.modrinth.com/data/1bokaNcj/versions/Juh6inLY/xaerominimap-forge-1.20.1-26.5.0.jar",
                       "718a4339f6dad3a56b6e7243e62febfb643b7151",
                       "913b1c428b049b9b0376e75edc7ab49bc3df605cf81a4c326b91241314d64c81420df0fc946cd6bd8a9a13f7a45b842d7b86008f32a0cf27d0d3cb278a5e5204",
                       2195399, "https://modrinth.com/mod/xaeros-minimap/version/Juh6inLY"),
    "embeddium": ("0.3.31+mc1.20.1", "embeddium-0.3.31+mc1.20.1.jar", "sk9rgfiA",
                  "https://cdn.modrinth.com/data/sk9rgfiA/versions/UTbfe5d1/embeddium-0.3.31%2Bmc1.20.1.jar",
                  "bb2fa8f3e493af16af9160d049f96c614a1faf2f",
                  "ffbf2da4685260a4d5c14c621708bd20722563f084f042d3dfb0a7b87f048e39299648c854a93939129da0d23a15a91ec628560d601e76074b08e275f6e132e9",
                  1320675, "https://modrinth.com/mod/embeddium/version/UTbfe5d1"),
    "oculus": ("1.20.1-1.8.0", "oculus-mc1.20.1-1.8.0.jar", "GchcoXML",
               "https://cdn.modrinth.com/data/GchcoXML/versions/iQ1SwGc3/oculus-mc1.20.1-1.8.0.jar",
               "984f774e71790deaec674c7587bd24e0711871b2",
               "1bb4ac77400d6684347988ed298a692c2cb15cf7923693607eb8739b171a20fef7412259e9e157111d9ce21779badab386029956f7d2283a9e611722a373e9d5",
               2851119, "https://modrinth.com/mod/oculus/version/iQ1SwGc3"),
    "modernfix": ("5.27.83+mc1.20.1", "modernfix-forge-5.27.83+mc1.20.1.jar", "nmDcB62a",
                  "https://cdn.modrinth.com/data/nmDcB62a/versions/jAZ7Ge3d/modernfix-forge-5.27.83%2Bmc1.20.1.jar",
                  "24109106b51846d387aa00c06d1445c35410c31c",
                  "2987d43ab991c31c94e53d16fe0694dd29a405fc7cdf6be69f5bf5b3d6a06a5d1b82ba8f5d8ecb4df45e592c649e39bc69787caa62b3417b5548392793be6e55",
                  1003230, "https://modrinth.com/mod/modernfix/version/jAZ7Ge3d"),
    "ambientsounds": ("6.3.8", "AmbientSounds_FORGE_v6.3.8_mc1.20.1.jar", "fM515JnW",
                      "https://cdn.modrinth.com/data/fM515JnW/versions/AuLdtrBY/AmbientSounds_FORGE_v6.3.8_mc1.20.1.jar",
                      "87ea0cd8ec56763185ee0db09eec7c676969e4da",
                      "150acb106bcb5cb7c74ede40f92cd7f597cc5f735104633b9a068179b05f5488d844af00fde98195a9cb8091f8055011a65126a67d96a8a2af95515a4ae42e55",
                      53429226, "https://modrinth.com/mod/ambientsounds/version/AuLdtrBY"),
    "creativecore": ("2.12.38", "CreativeCore_FORGE_v2.12.38_mc1.20.1.jar", "OsZiaDHq",
                     "https://cdn.modrinth.com/data/OsZiaDHq/versions/J9tluyYl/CreativeCore_FORGE_v2.12.38_mc1.20.1.jar",
                     "1004b6ae4e494039e28b14f2ba3ebe6b182487a8",
                     "fb4460c6c808369bd8a2191413e2f59126ff6113ff266f40a8c872b9d412b7a804a66c8f8de58af48581c649cd23d59ae1b183af8031d532d5bbd595c3187f04",
                     1144069, "https://modrinth.com/mod/creativecore/version/J9tluyYl"),
    "paxi": ("1.20-Forge-4.0", "Paxi-1.20-Forge-4.0.jar", "CU0PAyzb",
             "https://cdn.modrinth.com/data/CU0PAyzb/versions/C7buFh0l/Paxi-1.20-Forge-4.0.jar",
             "a3a7008e07a27b3c831af7e4c82fbbc10a4da328",
             "50ed8c99981b9860c846a18cda215d388b67019b76a172833fa4e4b52cbd122eb8e49e594e5789790f95af06e0a98dcf2433b001b1f559b3e7071d2e6b7c1dd7",
             96892, "https://modrinth.com/mod/paxi/version/C7buFh0l"),
    "architectury": ("9.2.14+forge", "architectury-9.2.14-forge.jar", "lhGA9TYQ",
                     "https://cdn.modrinth.com/data/lhGA9TYQ/versions/1MKTLiiG/architectury-9.2.14-forge.jar",
                     "a52918a500ff421180a1cbd1a0cabee712134ec4",
                     "cf67f2050cafa00f0bee42e6d7bef77fdb808ac4f71742f7b4d6d5c1e6ffb49561a5a252f332d2b78a9767bdb5faa284611790dba303fbdc736ae36d794f61c7",
                     580602, "https://modrinth.com/mod/architectury-api/version/1MKTLiiG"),
}

# notes that must accompany a re-pin, so the reasoning is not lost
REPIN_NOTES = {
    "farmers-delight": "RE-PINNED 1.2.11a -> 1.3.4 after querying the registry. 1.3.4 is the current 1.20.1 release (Aug 2026) and the 1.3.0 line added a native EMI plugin, which is this pack's recipe viewer. The original justification for 1.2.11a (a Create-contraption block-entity fix) is subsumed by the newer line.",
    "corail-tombstone": "RE-PINNED 9.1.4 -> 9.1.5. The author's own file banner reads 'Latest: 9.1.5 - Recommended: 9.1.5' in both entries, and an author recommendation outranks a download-count heuristic. The earlier 9.1.4 justification cited a CurseForge download figure that does not hold on Modrinth.",
    "modernfix": "RE-PINNED 5.26.1 -> 5.27.83. 5.26.1+mc1.20.1 is NOT returned by the registry as a 1.20.1 release, so a resolver filtering on release+Minecraft+loader would never find it; the earlier claim that it was 'the Modrinth-listed Release' came from a search snippet and was wrong. 5.27.83 is the most-downloaded release in the active 5.27 line (432,024).",
    "alexs-mobs": "Project id corrected to 2cMuAZAp (the id first written down was not this project). Declared required dependency is Citadel (jJfV67b1), NOT GeckoLib: GeckoLib was removed from the pack as a result.",
    "oculus": "Project id corrected to GchcoXML. The jar name is confirmed as oculus-mc1.20.1-1.8.0.jar, not the 'Oculus-...' form first inferred, and the file declares Embeddium (sk9rgfiA) as a required dependency — which is why shipping any other renderer crashes.",
    "ars-nouveau": "The published Forge file is the '-all' jar (ars_nouveau-1.20.1-4.12.7-all.jar). The plain-jar filename written in the first draft is not the Forge download.",
    "create": "The Modrinth version_number is 'mc1.20.1-6.0.8' while the jar is 'create-1.20.1-6.0.8.jar'. Both are recorded, because a resolver that matches on version_number needs the former and a mods/ folder needs the latter.",
    "xaeros-minimap": "RE-PINNED 25.2.0_Forge_1.20 -> forge-1.20.1-26.5.0. The project changed its file naming scheme; 25.x names no longer match the author's current releases. 26.5.0 has 309,788 downloads.",
    "emi": "RE-PINNED 1.1.22 -> 1.1.24. The newer release's headline fixes are crash fixes ('inconsistent crashes due to mixin order'); 1.65M downloads.",
    "ambientsounds": "RE-PINNED 6.1.4 -> 6.3.8. 6.1.4 was chosen from a page listing; the API's current line for 1.20.1 is 6.3.x and 6.3.8 has 1.67M downloads. 6.3.9 exists but was 5 days old with 22K downloads at capture.",
    "creativecore": "RE-PINNED 2.12.32 -> 2.12.38, kept in the same generation as AmbientSounds 6.3.8 (both are the same author's coordinated releases; 2.12.37/6.3.6 fixed the same reloader-thread bug together).",
    "sophisticated-backpacks": "RE-PINNED 3.23.1.1184 -> 3.26.9.2194: published 8 minutes before Sophisticated Core 1.5.6.2378 on the same day, i.e. a coordinated pair. The changelog also carries a Create-contraption fix ('backpacks not restoring correctly after Create contraption disassembly'), which matters for this pack.",
    "sophisticated-core": "RE-PINNED 1.2.39.938 -> 1.5.6.2378 as the matching half of the coordinated Backpacks release. A required library is safer matched to its dependent than chosen by download count.",
    "citadel": "ADDED. Required by Alex's Mobs. Changelog headline: server-side memory leak in world data loading — relevant to a pack with a custom dimension.",
}


def main() -> int:
    data = json.loads(LOCK.read_text(encoding="utf-8"))
    mods = {m["slug"]: m for m in data["mods"]}

    # 1. GeckoLib out: nothing in the pack uses it once Alex's Mobs' real dependency is known
    data["mods"] = [m for m in data["mods"] if m["slug"] != "geckolib"]
    mods.pop("geckolib", None)

    # 2. Citadel in, slotted next to Alex's Mobs
    if "citadel" not in mods:
        citadel = {
            "slug": "citadel", "name": "Citadel", "version": "2.6.3",
            "filename": "citadel-2.6.3-1.20.1.jar",
            "source": {"kind": "modrinth", "project": "jJfV67b1",
                       "page": "https://modrinth.com/mod/citadel/version/lTAAe4sZ"},
            "environment": "both", "deps": [],
            "purpose": "Required library for Alex's Mobs; its 2026 release fixes a server-side "
                       "memory leak in world-data loading, which is exactly the kind of leak a "
                       "pack with its own dimension should not ship.",
            "license": "GPL-3.0-only (project page; verify)",
            "verification": {"status": "official-page-verified", "sources": [
                "https://api.modrinth.com/v2/project/citadel/version (forge, 1.20.1, release)"]},
        }
        idx = [i for i, m in enumerate(data["mods"]) if m["slug"] == "alexs-mobs"][0]
        data["mods"].insert(idx + 1, citadel)
        mods["citadel"] = citadel

    # 3. apply every verified pin
    for slug, (ver, fname, proj, url, sha1, sha512, size, page) in PINS.items():
        m = mods.get(slug)
        if not m:
            raise SystemExit(f"lockfile has no '{slug}'")
        m["version"] = ver
        m["filename"] = fname
        m["source"]["kind"] = "modrinth"
        m["source"]["project"] = proj
        m["source"]["page"] = page
        m["pins"] = {"url": url, "sha1": sha1, "sha512": sha512, "size": size}
        m["verification"]["status"] = "official-page-verified"
        src = f"https://api.modrinth.com/v2/project/{proj}/version (filtered: forge, 1.20.1, release)"
        if src not in m["verification"]["sources"]:
            m["verification"]["sources"].append(src)
        extra = f"Registry-verified 2026-10-07: {SRC.format(id=proj)}. sha1 {sha1}."
        if slug in REPIN_NOTES:
            extra += " " + REPIN_NOTES[slug]
        m["verification"]["note"] = (m["verification"].get("note", "") + " " + extra).strip()

    # 4. Alex's Mobs' dependency is Citadel
    for m in data["mods"]:
        if m["slug"] == "alexs-mobs":
            m["deps"] = ["citadel"]

    # 5. record the outcome in the rejections list
    data["considered_and_rejected"] = [r for r in data["considered_and_rejected"]
                                       if r["mod"] != "GeckoLib"]
    data["considered_and_rejected"].insert(0, {
        "mod": "GeckoLib",
        "reason": "Was in the first draft on the assumption that Alex's Mobs needs it. The "
                  "registry shows Alex's Mobs' required dependency is Citadel, and nothing else "
                  "in the pack uses GeckoLib. Removed rather than kept as insurance."})

    LOCK.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"applied {len(PINS)} verified pins; {len(data['mods'])} mods in the lockfile")
    pinned = sum(1 for m in data["mods"] if m.get("pins"))
    print(f"  {pinned} with publisher URL + sha1 + sha512")
    print(f"  {len(data['mods']) - pinned} without (CurseForge-only FTB libraries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
