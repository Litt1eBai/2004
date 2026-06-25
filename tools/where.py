#!/usr/bin/env python3
"""where.py — locate every source/output file for a block, family, or generator logic.

Answers the three recurring "where is X" questions:

  1. Where is a block's SOURCE?         python3 tools/where.py vertical_tile_white_stairs
  2. Where are its MODELS / TEXTURES?   python3 tools/where.py framed_window_1   (lists special models + textures)
  3. Where is the GENERATOR LOGIC?      python3 tools/where.py --logic framed_window
                                        (any block/family query also prints its writer fn + line)

Query matches block id OR family id as a substring, case-insensitive.
Paths printed repo-relative so `path:line` stays clickable. Read-only; never writes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
CONTENT = REPO / "content"
GEN = REPO / "src/generated/resources/assets/mirage2004"
GEN_DATA = REPO / "src/generated/resources/data/mirage2004"
MAIN = REPO / "src/main/resources/assets/mirage2004"
MANIFEST = REPO / "src/generated/resources/mirage2004/content_manifest.json"
GENERATOR = "tools/generate_content.py"

# preset/shape/kit -> (writer function, line in generate_content.py). Keep in sync with the dispatch
# in write_model_files (~L1597) and write_special_resources (~L1141).
SHAPE_WRITER = {
    "cube": ("write_cube_resources", 767),
    "slab": ("write_slab_resources", 805),
    "stairs": ("write_stairs_resources", 900),
    "wall": ("write_wall_resources", 923),
    "pane": ("write_pane_resources", 953),
    "grille": ("write_grille_resources", 986),
    "slope": ("write_slope_resources", 1065),
    "triangle_wall": ("write_triangle_wall_resources", 1101),
}
KIT_WRITER = {
    "static": ("_write_static_special_resources", 1167),
    "pole": ("_write_pole_special_resources", 1184),
    "framed_window": ("_write_framed_window_resources", 1279),
    "framed_window_slope": ("_write_framed_window_slope_resources", 1442),
    "prefab_window": ("_write_prefab_window_resources", 1530),
}
# kits whose geometry is hand-authored base models (clean) vs emitted procedurally (messy).
HAND_BASE_KITS = {"static", "pole"}
PROCEDURAL_KITS = {"framed_window", "framed_window_slope", "prefab_window"}
FROZEN_SHAPES = {"pane", "grille"}


def is_frozen(block: dict) -> bool:
    """Mirror of generate_content.is_frozen_geometry: geometry hand-authored in src/main,
    NOT generated. The generator emits only this block's data (item-def/loot/lang/tags/catalog)."""
    return bool(block.get("kit")) or block.get("shape") in FROZEN_SHAPES


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO))
    except ValueError:
        return str(p)


def mark(p: Path) -> str:
    return rel(p) + ("" if p.exists() else "   [MISSING]")


def load_manifest() -> dict:
    if not MANIFEST.exists():
        sys.exit(f"manifest not found: {rel(MANIFEST)}  (run python3 tools/generate_content.py first)")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def family_to_collections(manifest: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for col in manifest.get("collections", []):
        for fam in col.get("families", []):
            out.setdefault(fam, []).append(col["id"] + ("" if col.get("enabled", True) else " (disabled)"))
    return out


def writer_for(block: dict) -> tuple[str, int]:
    kit = block.get("kit") or ""
    if kit:
        return KIT_WRITER.get(kit, ("write_special_resources", 1133))
    return SHAPE_WRITER.get(block.get("shape", ""), ("write_model_files", 1586))


def special_base_models(block: dict) -> list[Path]:
    """Hand-authored base models a block parents into (static/pole/grille pattern)."""
    prefix = block.get("modelPrefix") or block.get("shape") or ""
    sp = MAIN / "models/block/special"
    if not sp.exists() or not prefix:
        return []
    return sorted(sp.glob(f"{prefix}*.json"))


def _family_spec(fam: str) -> dict:
    p = CONTENT / "families" / f"{fam}.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


def textures_for(block: dict) -> list[Path]:
    tdir = MAIN / "textures/block"
    # base names to resolve: per-block texturePath, plus family-level frame/glass bases
    # combined with the block's colour(s) — windows carry colorPair, not a single texture.
    bases: list[str] = []
    if block.get("texturePath"):
        bases.append(block["texturePath"])
    spec = _family_spec(block.get("familyId", ""))
    colors = [c for c in (block.get("colorId"), block.get("glassColorId")) if c]
    if not colors and block.get("id"):
        colors = []  # fall back to scanning below
    for tex_key in ("frameTexture", "glassTexture", "baseTexture"):
        tex = spec.get(tex_key)
        if not tex:
            continue
        for col in colors or [None]:
            bases.append(f"{tex}_{col}" if col else tex)

    found: list[Path] = []
    seen: set[str] = set()
    for base in bases:
        for suffix in ("", "_n", "_s"):
            p = tdir / f"{base}{suffix}.png"
            if p.exists() and str(p) not in seen:
                seen.add(str(p))
                found.append(p)
    # if nothing resolved, glob by the family texture stems so the user still gets pointers
    if not found:
        for tex_key in ("baseTexture", "frameTexture", "glassTexture"):
            tex = spec.get(tex_key)
            if tex:
                found.extend(sorted(tdir.glob(f"{tex}_*.png")))
        if not found and block.get("texturePath"):
            found.append(tdir / f"{block['texturePath']}.png")  # show expected (missing) path
    return found


def report_block(block: dict, fam_cols: dict[str, list[str]]):
    bid = block["id"]
    fam = block.get("familyId", "?")
    kit = block.get("kit") or ""
    shape = block.get("shape", "?")
    preset = block.get("preset", "?")
    fn, line = writer_for(block)

    print(f"\n=== {bid}   ({block.get('zhName','')} / {block.get('enName','')})")
    print(f"  family   : {fam}   preset={preset}  shape={shape}" + (f"  kit={kit}" if kit else ""))
    cols = fam_cols.get(fam, [])
    print(f"  enabled by collection: {', '.join(cols) if cols else '(none — orphaned?)'}")

    print("  SOURCE (edit here):")
    print(f"    family spec : {mark(CONTENT / 'families' / (fam + '.yaml'))}")
    for col in cols:
        cid = col.split(' ')[0]
        print(f"    collection  : {mark(CONTENT / 'collections' / (cid + '.json'))}")

    frozen = is_frozen(block)
    if frozen:
        print("  GENERATOR LOGIC : FROZEN — generator emits NO geometry for this block; only its")
        print("                    data (item-definition/loot/lang/tags/catalog). Geometry is hand-authored.")
    else:
        print(f"  GENERATOR LOGIC : {GENERATOR}:{line}   def {fn}(...)")

    bm = special_base_models(block)
    if bm:
        print("  HAND-AUTHORED base model(s) (open in Blockbench):")
        for p in bm:
            print(f"    {mark(p)}")

    print("  TEXTURES:")
    for p in textures_for(block):
        print(f"    {mark(p)}")

    if frozen:
        print("  HAND-AUTHORED GEOMETRY (frozen in src/main — edit here, Blockbench):")
        print(f"    blockstate : {mark(MAIN / 'blockstates' / f'{bid}.json')}")
        models = sorted((MAIN / "models/block").glob(f"{bid}*.json"))
        if len(models) <= 3:
            for p in models:
                print(f"    model      : {mark(p)}")
        else:
            print(f"    models     : {len(models)} files  {rel(MAIN / 'models/block')}/{bid}*.json")
        print(f"    item model : {mark(MAIN / 'models/item' / f'{bid}.json')}")
        print("  GENERATED DATA (regenerated — do not hand-edit):")
        print(f"    item def   : {mark(GEN / 'items' / f'{bid}.json')}")
        print(f"    loot table : {mark(GEN_DATA / 'loot_table/blocks' / f'{bid}.json')}")
    else:
        print("  GENERATED OUTPUT (do not hand-edit — regenerated):")
        print(f"    blockstate : {mark(GEN / 'blockstates' / f'{bid}.json')}")
        models = sorted((GEN / "models/block").glob(f"{bid}*.json"))
        if len(models) <= 3:
            for p in models:
                print(f"    model      : {rel(p)}")
        else:
            print(f"    models     : {len(models)} files  {rel(GEN / 'models/block')}/{bid}*.json")
        print(f"    item model : {mark(GEN / 'models/item' / f'{bid}.json')}")
        print(f"    loot table : {mark(GEN_DATA / 'loot_table/blocks' / f'{bid}.json')}")


def report_logic(term: str):
    print(f"\n=== generator logic matching '{term}'")
    hits = []
    for table, kind in ((SHAPE_WRITER, "shape"), (KIT_WRITER, "kit")):
        for key, (fn, line) in table.items():
            if term.lower() in key.lower() or term.lower() in fn.lower():
                tag = ""
                if kind == "kit" or key in FROZEN_SHAPES:
                    # All kits + pane/grille are now frozen: geometry hand-authored in src/main,
                    # the listed writer fn is UNREACHABLE (kept only until the provider rebuild deletes it).
                    tag = "  [FROZEN — geometry in src/main; writer fn is dead code]"
                hits.append((kind, key, fn, line, tag))
    if not hits:
        print("  (no match; known keys: " + ", ".join(sorted(SHAPE_WRITER) + sorted(KIT_WRITER)) + ")")
        return
    for kind, key, fn, line, tag in hits:
        print(f"  {kind}={key:20} -> {GENERATOR}:{line}  def {fn}(...){tag}")


def main():
    args = [a for a in sys.argv[1:]]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    if args[0] == "--logic":
        report_logic(args[1] if len(args) > 1 else "")
        return

    term = args[0].lower()
    manifest = load_manifest()
    fam_cols = family_to_collections(manifest)
    matches = [b for b in manifest["blocks"] if term in b["id"].lower() or term in b.get("familyId", "").lower()]
    if not matches:
        print(f"no block/family matches '{term}'.")
        fams = sorted({b.get("familyId", "") for b in manifest["blocks"]})
        print("known families: " + ", ".join(fams))
        return
    if len(matches) > 12:
        print(f"{len(matches)} blocks match '{term}'. Showing family-level summary "
              f"(narrow the query for full per-block detail):")
        by_fam: dict[str, int] = {}
        for b in matches:
            by_fam[b["familyId"]] = by_fam.get(b["familyId"], 0) + 1
        for fam, n in sorted(by_fam.items()):
            ex = next(b for b in matches if b["familyId"] == fam)
            fn, line = writer_for(ex)
            print(f"  {fam:24} {n:3} blocks   {GENERATOR}:{line} {fn}   src: {rel(CONTENT/'families'/(fam+'.json'))}")
        return
    for b in matches:
        report_block(b, fam_cols)


if __name__ == "__main__":
    main()
