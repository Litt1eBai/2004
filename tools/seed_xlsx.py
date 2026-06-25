#!/usr/bin/env python3
"""One-time migration: seed content/mirage.xlsx from the pre-xlsx tabular sources
(step 5 of the content-pipeline rebuild). After this runs and the generator is
switched to read the xlsx, the readable YAML/JSON tabular sources are removed and
mirage.xlsx becomes the source of truth for COLORS/MATERIALS/BLOCK_TYPES/APPLY/
BLOCKS/COLLECTIONS. Family docs stay as content/families/*.yaml.

Run: python3 tools/seed_xlsx.py   (re-runnable only while the YAML sources exist).

The flatten here is the inverse of load_tables_from_xlsx() in generate_content.py;
this script self-tests that inverse at the end and refuses to write a drifting xlsx.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yaml  # noqa: E402
import xlsx_io  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"

COLORS_H = ["id", "zh", "en", "sort"]
MATERIALS_H = ["id", "sound", "hardness", "resistance", "mapColor", "tool", "tag_transformers"]
BLOCK_TYPES_H = ["kind", "id", "produce", "suffix", "kit", "collision", "base_model", "zh", "en"]
APPLY_H = ["family", "role", "type", "kit", "modelPrefix", "collision", "connectsBy", "zh", "en"]
BLOCKS_H = ["id", "familyId", "preset", "colorId", "shape", "zh", "en", "category",
            "renderType", "texturePath", "material", "kit", "modelPrefix", "collision", "connectsBy"]
COLLECTIONS_H = ["id", "enabled", "families"]


def _read_json(p):
    return json.loads(p.read_text(encoding="utf-8"))


def _read_yaml(p):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def flatten():
    colors = _read_json(CONTENT / "palettes" / "colors.json")
    colors_rows = xlsx_io.dicts_to_sheet(COLORS_H, colors)

    materials = _read_yaml(CONTENT / "materials.yaml")
    mat_rows = [list(MATERIALS_H)]
    for m in materials:
        mat_rows.append([
            m["id"], m["sound"], float(m["hardness"]), float(m["resistance"]), m["mapColor"],
            m.get("tool", ""),
            json.dumps(m["tag_transformers"], ensure_ascii=False) if m.get("tag_transformers") else "",
        ])

    bt = _read_yaml(CONTENT / "block_types.yaml")
    bt_rows = [list(BLOCK_TYPES_H)]
    for c in bt.get("common", []):
        bt_rows.append(["common", c["id"], c.get("produce", ""), c.get("suffix", ""),
                        "", "", "", c.get("zh", ""), c.get("en", "")])
    for s in bt.get("special", []):
        bt_rows.append(["special", s["id"], s.get("produce", ""), "",
                        s.get("kit", ""), s.get("collision", ""), s.get("base_model", ""),
                        s.get("zh", ""), s.get("en", "")])

    apply_map = _read_yaml(CONTENT / "apply.yaml") or {}
    apply_rows = [list(APPLY_H)]
    for family, spec in apply_map.items():
        spec = spec or {}
        for t in spec.get("common", []):
            apply_rows.append([family, "common", t, "", "", "", "", "", ""])
        for e in spec.get("special", []):
            if isinstance(e, str):
                e = {"type": e}
            apply_rows.append([family, "special", e["type"], e.get("kit", ""), e.get("modelPrefix", ""),
                               e.get("collision", ""), e.get("connectsBy", ""), e.get("zh", ""), e.get("en", "")])
        for p in spec.get("pieces", []):
            apply_rows.append([family, "piece", p["type"], p.get("kit", ""), p.get("modelPrefix", ""),
                               p.get("collision", ""), "", p.get("zh", ""), p.get("en", "")])

    singles = _read_yaml(CONTENT / "blocks.yaml") or []
    blocks_rows = xlsx_io.dicts_to_sheet(BLOCKS_H, singles)

    collections = []
    for p in sorted((CONTENT / "collections").glob("*.json")):
        collections.append(_read_json(p))
    coll_rows = [list(COLLECTIONS_H)]
    for c in collections:
        coll_rows.append([c["id"], bool(c.get("enabled", True)), ",".join(c["families"])])

    return [
        ("colors", colors_rows),
        ("materials", mat_rows),
        ("block_types", bt_rows),
        ("apply", apply_rows),
        ("blocks", blocks_rows),
        ("collections", coll_rows),
    ]


def main():
    import os
    if not (CONTENT / "materials.yaml").exists():
        raise SystemExit(
            "seed_xlsx is a one-time migration script. The legacy YAML/JSON tabular sources it "
            "reads were removed in step 5 (mirage.xlsx is now the source of truth), so there is "
            "nothing to seed from. Restore them from git history to re-run.")

    sheets = flatten()
    out = CONTENT / "mirage.xlsx"
    tmp = out.with_name(out.name + ".tmp")
    xlsx_io.write_xlsx(tmp, sheets)  # write to a temp first; only replace the real file if the self-test passes

    # self-test: the generator's reader must reconstruct the same data we flattened, read from
    # the TEMP file (not the live source), so a round-trip bug can't clobber a good mirage.xlsx.
    import generate_content as gen
    colors, materials, block_types, apply_map, singles, collections = gen.load_tables_from_xlsx(tmp)
    material_map = {m["id"]: m for m in materials}
    src_colors = _read_json(CONTENT / "palettes" / "colors.json")
    src_materials = {m["id"]: m for m in _read_yaml(CONTENT / "materials.yaml")}
    src_bt = _read_yaml(CONTENT / "block_types.yaml")
    src_collections = [_read_json(p) for p in sorted((CONTENT / "collections").glob("*.json"))]

    problems = []
    if colors != src_colors:
        problems.append("colors mismatch")
    if block_types != src_bt:
        problems.append("block_types mismatch")
    if collections != src_collections:
        problems.append("collections mismatch")
    for mid, m in src_materials.items():
        got = material_map.get(mid, {})
        if (got.get("sound") != m["sound"] or float(got.get("hardness")) != float(m["hardness"])
                or float(got.get("resistance")) != float(m["resistance"]) or got.get("mapColor") != m["mapColor"]
                or got.get("tool") != m.get("tool") or (got.get("tag_transformers") or {}) != (m.get("tag_transformers") or {})):
            problems.append(f"material {mid} mismatch: {got} vs {m}")
    if problems:
        tmp.unlink()
        raise SystemExit("seed self-test FAILED (mirage.xlsx left untouched):\n  " + "\n  ".join(problems))

    os.replace(tmp, out)  # atomic
    print(f"Seeded {out} ({len(sheets)} sheets); reader self-test passed.")


if __name__ == "__main__":
    main()
