#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
import shutil

# Codegen always emits LF, on every platform. Python text-mode writes translate
# "\n" -> os.linesep (CRLF on Windows), which makes Windows gradle builds churn every
# generated file against the LF copies committed from Linux. Patch write_text at the
# single chokepoint so all call sites stay LF without per-call newline= args.
_write_text_orig = Path.write_text
def _write_text_lf(self, data, encoding=None, errors=None, newline="\n"):
    return _write_text_orig(self, data, encoding=encoding, errors=errors, newline=newline)
Path.write_text = _write_text_lf


ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"
GENERATED_JAVA_DIR = ROOT / "src" / "generated" / "java" / "net" / "littlebai" / "mirage2004" / "generated"
GENERATED_RES_DIR = ROOT / "src" / "generated" / "resources" / "assets" / "mirage2004"
GENERATED_DATA_DIR = ROOT / "src" / "generated" / "resources" / "data"
GENERATED_MANIFEST_DIR = ROOT / "src" / "generated" / "resources" / "mirage2004"
MANAGED_JAVA_FILES = [
    "GeneratedPalette.java",
    "GeneratedFamilies.java",
    "GeneratedCollections.java",
    "GeneratedBlockCatalog.java",
    "GeneratedSpecialShapes.java",
]
MANAGED_RESOURCE_DIRS = [
    "lang",
    "blockstates",
    "models",
    "items",
]
MANAGED_MANIFEST_FILES = [
    "content_manifest.json",
]
SHAPE_SUFFIXES = {
    "cube": "",
    "slab": "_slab",
    "stairs": "_stairs",
    "wall": "_wall",
    "pane": "_pane",
    "grille": "",
    "slope": "_slope",
    "triangle_wall": "_triangle_wall",
}
SHAPE_ZH_NAMES = {
    "cube": "",
    "slab": "半砖",
    "stairs": "楼梯",
    "wall": "墙",
    "pane": "窗格",
    "grille": "",
    "slope": "斜坡",
    "triangle_wall": "三角墙",
}
SHAPE_EN_NAMES = {
    "cube": "",
    "slab": " Slab",
    "stairs": " Stairs",
    "wall": " Wall",
    "pane": " Pane",
    "grille": "",
    "slope": " Slope",
    "triangle_wall": " Triangle Wall",
}
SUPPORTED_GENERATED_SHAPES = {"cube", "slab", "stairs", "wall", "pane", "grille", "slope", "triangle_wall"}
# Maps a family renderType to the NeoForge model `render_type` field. "solid" is
# intentionally absent: solid is the chunk-render default and needs no field.
RENDER_TYPE_MODEL = {
    "cutout": "minecraft:cutout",
    "cutout_mipped": "minecraft:cutout_mipped",
    "translucent": "minecraft:translucent",
}
SUPPORTED_GENERATED_PRESETS = {
    "solid_material",
    "glass_system",
    "window_frame_system",
    "window_glass_system",
    "framed_window_system",
    "security_grille",
    "utility_pole",
    "cable_system",
}
# Special-shape kits (A2). `static` (FACING-only) and `pole` (vertical connect)
# are implemented; `framed_window` (1x1 centered, 2D same-type connect) is the
# single-block framed-window line (v1.md §2.1); `prefab_window` (door-style 2-tall
# column, FACING+HALF+OPEN) is the prefab balcony window line (v1.md §2.2);
# `rail` / `pole_line` land when their families exist.
SUPPORTED_KITS = {"static", "pole", "framed_window", "framed_window_slope", "prefab_window"}
# Collision modes a special shape may declare. The VoxelShape box-string DSL is a
# planned later A2 step; for now only full / none.
SUPPORTED_SPECIAL_COLLISION = {"full", "none"}
# Display-name fragments per special shape (zh/en). Override per-shape via the
# specialShapes object's optional zh/en fields.
SPECIAL_SHAPE_ZH = {
    "window_frame": "窗框",
    "window_frame_cross": "十字窗框",
    "window_frame_corner": "转角窗框",
    "window_panel": "窗扇",
    "grille_panel": "防盗网",
    "grille_cap": "防盗网帽",
    "grille_arch": "拱形防盗网",
    "grille_cage": "笼式防盗网",
    "grille_box": "环框防盗笼",
    "pole": "杆",
    "pole_arm": "横担",
    "pole_base": "杆基",
    "wire": "电线",
}
SPECIAL_SHAPE_EN = {
    "window_frame": "Window Frame",
    "window_frame_cross": "Cross Window Frame",
    "window_frame_corner": "Corner Window Frame",
    "window_panel": "Window Panel",
    "grille_panel": "Security Grille Panel",
    "grille_cap": "Security Grille Cap",
    "grille_arch": "Security Grille Arch",
    "grille_cage": "Security Grille Cage",
    "grille_box": "Security Grille Box",
    "pole": "Pole",
    "pole_arm": "Pole Arm",
    "pole_base": "Pole Base",
    "wire": "Wire",
}


def is_framed_window_family(family: dict) -> bool:
    """The single-block framed-window line (v1.md §2.1, FramedWindowBlock): a 1x1
    centered frame+glass that 2D-connects to same-id, same-facing neighbours. Detected
    by the `framed_window_system` preset; carries `colorPairs` (two-color) + `pieces`
    instead of the cartesian `colors` x `commonShapes`/`specialShapes` expansion."""
    return family.get("preset") == "framed_window_system"


def normalize_special_shape(entry) -> dict:
    """Accept a bare shape string (migration form) or an object; return a
    normalized special-shape dict. Bare string -> static kit, modelPrefix = shape."""
    if isinstance(entry, str):
        entry = {"shape": entry}
    if "shape" not in entry:
        raise SystemExit(f"specialShapes entry missing 'shape': {entry}")
    shape = entry["shape"]
    return {
        "shape": shape,
        "kit": entry.get("kit", "static"),
        "modelPrefix": entry.get("modelPrefix", shape),
        "collision": entry.get("collision", "full"),
        "connectsBy": entry.get("connectsBy", ""),
        "zh": entry.get("zh"),
        "en": entry.get("en"),
    }


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def java_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("\"", "\\\"")
    return f"\"{escaped}\""


def shape_list_java(values: list[str]) -> str:
    return "List.of(" + ", ".join(java_string(value) for value in values) + ")"


def java_constant(value: str) -> str:
    normalized = value.upper().replace("-", "_")
    return "".join(character if character.isalnum() or character == "_" else "_" for character in normalized)


def ensure_unique(items: list[dict], key: str, label: str):
    seen = set()
    for item in items:
        value = item[key]
        if value in seen:
            raise SystemExit(f"Duplicate {label} id: {value}")
        seen.add(value)


def reset_generated_outputs():
    GENERATED_JAVA_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_RES_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

    # Generated block tags merge into vanilla tags (#minecraft:walls/slabs/stairs,
    # mineable/pickaxe); the whole tags/block subtree is fully owned here.
    generated_block_tag_dir = GENERATED_DATA_DIR / "minecraft" / "tags" / "block"
    if generated_block_tag_dir.exists():
        shutil.rmtree(generated_block_tag_dir)

    # Generated loot tables are fully owned here (one per block); wipe before rewrite.
    generated_loot_dir = GENERATED_DATA_DIR / "mirage2004" / "loot_table"
    if generated_loot_dir.exists():
        shutil.rmtree(generated_loot_dir)

    # Mod-owned block tags (e.g. grille_no_connect) are fully regenerated each run.
    generated_mirage_tag_dir = GENERATED_DATA_DIR / "mirage2004" / "tags" / "block"
    if generated_mirage_tag_dir.exists():
        shutil.rmtree(generated_mirage_tag_dir)

    for file_name in MANAGED_JAVA_FILES:
        path = GENERATED_JAVA_DIR / file_name
        if path.exists():
            path.unlink()

    for directory_name in MANAGED_RESOURCE_DIRS:
        path = GENERATED_RES_DIR / directory_name
        if path.exists():
            shutil.rmtree(path)

    for file_name in MANAGED_MANIFEST_FILES:
        path = GENERATED_MANIFEST_DIR / file_name
        if path.exists():
            path.unlink()


def load_content():
    colors = read_json(CONTENT_DIR / "palettes" / "colors.json")
    color_map = {entry["id"]: entry for entry in colors}

    families = []
    for path in sorted((CONTENT_DIR / "families").glob("*.json")):
        families.append(read_json(path))

    collections = []
    for path in sorted((CONTENT_DIR / "collections").glob("*.json")):
        collections.append(read_json(path))

    base_en = read_json(CONTENT_DIR / "base_lang" / "en_us.json")
    base_zh = read_json(CONTENT_DIR / "base_lang" / "zh_cn.json")

    return colors, color_map, families, collections, base_en, base_zh


def validate_framed_window_family(family: dict, known_colors: set[str]):
    """Schema + palette guardrail for a framed-window family. Requires frameTexture,
    glassTexture, a non-empty colorPairs list of [frameColor, glassColor] palette ids,
    and a non-empty pieces list. Fails loudly if a colorPairs id is not in the palette."""
    for required in ("frameTexture", "glassTexture"):
        if required not in family:
            raise SystemExit(
                f"Framed-window family '{family['id']}' must declare '{required}'."
            )
    color_pairs = family.get("colorPairs", [])
    if not color_pairs:
        raise SystemExit(
            f"Framed-window family '{family['id']}' must declare a non-empty colorPairs list."
        )
    for pair in color_pairs:
        if not isinstance(pair, list) or len(pair) != 2:
            raise SystemExit(
                f"Framed-window family '{family['id']}' colorPairs entry must be "
                f"[frameColor, glassColor]: {pair}"
            )
        for color_id in pair:
            if color_id not in known_colors:
                raise SystemExit(
                    f"Framed-window family '{family['id']}' references unknown palette "
                    f"color '{color_id}' in colorPairs {pair}."
                )
    pieces = family.get("pieces", [])
    if not pieces:
        raise SystemExit(
            f"Framed-window family '{family['id']}' must declare a non-empty pieces list."
        )
    for piece in pieces:
        if "modelPrefix" not in piece:
            raise SystemExit(
                f"Framed-window family '{family['id']}' piece missing 'modelPrefix': {piece}"
            )
        collision = piece.get("collision", "full")
        if collision not in SUPPORTED_SPECIAL_COLLISION:
            voxel_shape_to_java(collision)


def validate_content(colors: list[dict], families: list[dict], collections: list[dict]):
    ensure_unique(colors, "id", "color")
    ensure_unique(families, "id", "family")
    ensure_unique(collections, "id", "collection")

    known_colors = {color["id"] for color in colors}
    family_ids = {family["id"] for family in families}

    enabled_family_ids = []
    for collection in collections:
        if collection.get("enabled", True):
            for family_id in collection["families"]:
                if family_id not in enabled_family_ids:
                    enabled_family_ids.append(family_id)

    for family in families:
        # Framed-window families (single-block §2.1) declare colorPairs + pieces instead
        # of the cartesian colors x shapes expansion; validate that shape and skip the
        # common/special-shape path entirely.
        if is_framed_window_family(family):
            validate_framed_window_family(family, known_colors)
            continue
        common_shapes = family.get("commonShapes", family.get("shapes", []))
        special_shapes = family.get("specialShapes", [])
        if not common_shapes and not special_shapes:
            raise SystemExit(
                f"Family '{family['id']}' must declare commonShapes or specialShapes."
            )
        unsupported_common_shapes = [shape for shape in common_shapes if shape not in SUPPORTED_GENERATED_SHAPES]
        if unsupported_common_shapes:
            raise SystemExit(
                f"Family '{family['id']}' uses unsupported commonShapes {unsupported_common_shapes}. "
                f"Supported generated shapes: {sorted(SUPPORTED_GENERATED_SHAPES)}"
            )
        if not isinstance(special_shapes, list):
            raise SystemExit(f"Family '{family['id']}' specialShapes must be a list")
        for raw_special in special_shapes:
            special = normalize_special_shape(raw_special)
            if special["kit"] not in SUPPORTED_KITS:
                raise SystemExit(
                    f"Family '{family['id']}' special shape '{special['shape']}' uses unsupported kit "
                    f"'{special['kit']}'. Supported kits: {sorted(SUPPORTED_KITS)}"
                )
            if special["collision"] not in SUPPORTED_SPECIAL_COLLISION:
                # Not full/none → must be a valid box-string collision DSL; parse to verify syntax.
                voxel_shape_to_java(special["collision"])
        # slab (type=double model) and stairs (StairBlock base state) both reference the
        # cube block id. Without a cube variant they produce missing models / a runtime NPE.
        cube_dependent_shapes = [shape for shape in ("slab", "stairs") if shape in common_shapes]
        if cube_dependent_shapes and "cube" not in common_shapes:
            raise SystemExit(
                f"Family '{family['id']}' declares {cube_dependent_shapes} but no 'cube' shape. "
                "slab and stairs depend on the cube block; add 'cube' to commonShapes."
            )

        # randomVariants > 1 makes the cube blockstate list N models so the client
        # picks one per block position (grass-block style). Only the cube shape uses it.
        random_variants = family.get("randomVariants", 1)
        if not isinstance(random_variants, int) or random_variants < 1:
            raise SystemExit(f"Family '{family['id']}' randomVariants must be a positive integer.")
        if random_variants > 1 and "cube" not in common_shapes:
            raise SystemExit(
                f"Family '{family['id']}' sets randomVariants={random_variants} but has no 'cube' shape."
            )

        for color_id in family["colors"]:
            if color_id not in known_colors:
                raise SystemExit(f"Family '{family['id']}' references unknown color '{color_id}'")
        if family["id"] in enabled_family_ids:
            if family["preset"] not in SUPPORTED_GENERATED_PRESETS:
                raise SystemExit(
                    f"Enabled family '{family['id']}' uses unsupported preset '{family['preset']}'. "
                    f"Supported presets: {sorted(SUPPORTED_GENERATED_PRESETS)}"
                )

    for collection in collections:
        for family_id in collection["families"]:
            if family_id not in family_ids:
                raise SystemExit(f"Collection '{collection['id']}' references unknown family '{family_id}'")


def resolve_enabled_families(families: list[dict], collections: list[dict]) -> list[dict]:
    enabled_family_ids = []
    for collection in collections:
        if not collection.get("enabled", True):
            continue
        for family_id in collection["families"]:
            if family_id not in enabled_family_ids:
                enabled_family_ids.append(family_id)

    if not enabled_family_ids:
        raise SystemExit("No enabled families found in content/collections")

    family_map = {family["id"]: family for family in families}
    return [family_map[family_id] for family_id in enabled_family_ids]


def build_framed_window_blocks(color_map: dict[str, dict], family: dict) -> list[dict]:
    """Expand a framed-window family into one block per (colorPair, piece). Each block
    is kit='framed_window' (FramedWindowBlock), carries the two-color frame/glass texture
    paths, renderType='translucent' (the multipart forces cutout/translucent per child).
    id = {family}_{frame}_{glass}_{pieceModelPrefix}."""
    blocks = []
    block_props = family["blockProps"]
    frame_texture = family["frameTexture"]
    glass_texture = family["glassTexture"]
    for frame_color, glass_color in family["colorPairs"]:
        frame = color_map[frame_color]
        glass = color_map[glass_color]
        for piece in family["pieces"]:
            model_prefix = piece["modelPrefix"]
            # The kit field dispatches the blockstate writer + the Java block class:
            # `framed_window` (single-block §2.1) vs `prefab_window` (prefab 2-tall §2.2).
            # Default to framed_window so the existing single-block families stay unchanged.
            piece_kit = piece.get("kit", "framed_window")
            piece_zh = piece.get("zh", "")
            piece_en = piece.get("en", "")
            block_id = f"{family['id']}_{frame_color}_{glass_color}_{model_prefix}"
            zh_name = f"{frame['zh']}框{glass['zh']}玻璃{family['zh']}{piece_zh}"
            en_name = f"{frame['en']} Frame {glass['en']} Glass {family['en']}{(' ' + piece_en) if piece_en else ''}"
            blocks.append(
                {
                    "id": block_id,
                    "baseId": f"{family['id']}_{frame_color}_{glass_color}",
                    "familyId": family["id"],
                    "preset": family["preset"],
                    "colorId": frame_color,
                    "shape": model_prefix,
                    "zhName": zh_name,
                    "enName": en_name,
                    "category": family["category"],
                    "renderType": "translucent",
                    # framed_window has no single primary sprite -- its visual is the two-color
                    # frame/glassTexturePath pair, read directly by the multipart writer. Leave
                    # texturePath empty so it never carries a misleading "this is THE texture" value.
                    "texturePath": "",
                    "sound": block_props["sound"],
                    "hardness": block_props["hardness"],
                    "resistance": block_props["resistance"],
                    "mapColor": block_props["mapColor"],
                    "kit": piece_kit,
                    "modelPrefix": model_prefix,
                    "collision": piece.get("collision", "full"),
                    "connectsBy": "",
                    "frameTexturePath": f"{frame_texture}_{frame_color}",
                    "glassTexturePath": f"{glass_texture}_{glass_color}",
                }
            )
    return blocks


def build_block_catalog(color_map: dict[str, dict], families: list[dict]) -> list[dict]:
    blocks = []
    for family in families:
        if is_framed_window_family(family):
            blocks.extend(build_framed_window_blocks(color_map, family))
            continue
        block_props = family["blockProps"]
        for color_id in family["colors"]:
            color = color_map[color_id]
            texture_path = f"{family['baseTexture']}_{color_id}"
            slope_face_path = f"{family.get('slopeFace', family['baseTexture'])}_{color_id}"
            base_id = f"{family['id']}_{color_id}"
            base_zh_name = f"{color['zh']}{family['zh']}"
            base_en_name = f"{color['en']} {family['en']}"
            for shape in family.get("commonShapes", family.get("shapes", [])):
                blocks.append(
                    {
                        "id": f"{base_id}{SHAPE_SUFFIXES[shape]}",
                        "baseId": base_id,
                        "familyId": family["id"],
                        "preset": family["preset"],
                        "colorId": color_id,
                        "shape": shape,
                        "zhName": f"{base_zh_name}{SHAPE_ZH_NAMES[shape]}",
                        "enName": f"{base_en_name}{SHAPE_EN_NAMES[shape]}",
                        "category": family["category"],
                        "renderType": family["renderType"],
                        "texturePath": texture_path,
                        "sound": block_props["sound"],
                        "hardness": block_props["hardness"],
                        "resistance": block_props["resistance"],
                        "mapColor": block_props["mapColor"],
                        "kit": "",
                        "modelPrefix": "",
                        "collision": "full",
                        "connectsBy": "",
                        "randomVariants": family.get("randomVariants", 1),
                        "slopeFace": slope_face_path,
                    }
                )
            for raw_special in family.get("specialShapes", []):
                special = normalize_special_shape(raw_special)
                shape = special["shape"]
                zh_fragment = special["zh"] or SPECIAL_SHAPE_ZH.get(shape, shape)
                en_fragment = special["en"] or SPECIAL_SHAPE_EN.get(shape, shape.replace("_", " ").title())
                blocks.append(
                    {
                        "id": f"{base_id}_{shape}",
                        "baseId": base_id,
                        "familyId": family["id"],
                        "preset": family["preset"],
                        "colorId": color_id,
                        "shape": shape,
                        "zhName": f"{base_zh_name}{zh_fragment}",
                        "enName": f"{base_en_name} {en_fragment}",
                        "category": family["category"],
                        "renderType": family["renderType"],
                        "texturePath": texture_path,
                        "sound": block_props["sound"],
                        "hardness": block_props["hardness"],
                        "resistance": block_props["resistance"],
                        "mapColor": block_props["mapColor"],
                        "kit": special["kit"],
                        "modelPrefix": special["modelPrefix"],
                        "collision": special["collision"],
                        "connectsBy": special["connectsBy"],
                    }
                )
    return blocks


def write_generated_palette(colors: list[dict]):
    body = ",\n".join(
        f"            new ColorPaletteEntry({java_string(color['id'])}, {java_string(color['zh'])}, {java_string(color['en'])}, {color['sort']})"
        for color in colors
    )
    content = f"""package net.littlebai.mirage2004.generated;

import java.util.List;

import net.littlebai.mirage2004.content.spec.ColorPaletteEntry;

// Generated by tools/generate_content.py. Do not edit by hand.
public final class GeneratedPalette {{
    public static final List<ColorPaletteEntry> COLORS = List.of(
{body});

    private GeneratedPalette() {{
    }}
}}
"""
    (GENERATED_JAVA_DIR / "GeneratedPalette.java").write_text(content, encoding="utf-8")


def write_generated_families(families: list[dict]):
    entries = []
    for family in families:
        props = family["blockProps"]
        entries.append(
            "            new MaterialFamilySpec(\n"
            f"                    {java_string(family['id'])},\n"
            f"                    {java_string(family['preset'])},\n"
            f"                    {java_string(family['zh'])},\n"
            f"                    {java_string(family['en'])},\n"
            f"                    {java_string(family['category'])},\n"
            f"                    {java_string(family['renderType'])},\n"
            f"                    {java_string(family['baseTexture'])},\n"
            f"                    {shape_list_java(family.get('commonShapes', family.get('shapes', [])))},\n"
            f"                    {shape_list_java([normalize_special_shape(s)['shape'] for s in family.get('specialShapes', [])])},\n"
            f"                    {shape_list_java(family['colors'])},\n"
            f"                    new BlockPropertySpec({java_string(props['sound'])}, {props['hardness']}, {props['resistance']}, {java_string(props['mapColor'])}))"
        )
    body = ",\n".join(entries)
    content = f"""package net.littlebai.mirage2004.generated;

import java.util.List;

import net.littlebai.mirage2004.content.spec.BlockPropertySpec;
import net.littlebai.mirage2004.content.spec.MaterialFamilySpec;

// Generated by tools/generate_content.py. Do not edit by hand.
public final class GeneratedFamilies {{
    public static final List<MaterialFamilySpec> FAMILIES = List.of(
{body});

    private GeneratedFamilies() {{
    }}
}}
"""
    (GENERATED_JAVA_DIR / "GeneratedFamilies.java").write_text(content, encoding="utf-8")


def write_generated_collections(collections: list[dict]):
    constants = []
    for collection in collections:
        constants.append(
            f"""    public static final ContentCollectionSpec {java_constant(collection['id'])} = new ContentCollectionSpec(
            {java_string(collection['id'])},
            {str(collection.get('enabled', True)).lower()},
            {shape_list_java(collection['families'])});"""
        )
    collection_refs = ", ".join(java_constant(collection["id"]) for collection in collections)
    content = f"""package net.littlebai.mirage2004.generated;

import java.util.List;

import net.littlebai.mirage2004.content.spec.ContentCollectionSpec;

// Generated by tools/generate_content.py. Do not edit by hand.
public final class GeneratedCollections {{
{chr(10).join(constants)}

    public static final List<ContentCollectionSpec> COLLECTIONS = List.of({collection_refs});

    private GeneratedCollections() {{
    }}
}}
"""
    (GENERATED_JAVA_DIR / "GeneratedCollections.java").write_text(content, encoding="utf-8")


def write_generated_block_catalog(blocks: list[dict]):
    entries = []
    for block in blocks:
        entries.append(
            "            new BuildingBlockDefinition(\n"
            f"                    {java_string(block['id'])},\n"
            f"                    {java_string(block['baseId'])},\n"
            f"                    {java_string(block['familyId'])},\n"
            f"                    {java_string(block['preset'])},\n"
            f"                    {java_string(block['colorId'])},\n"
            f"                    {java_string(block['shape'])},\n"
            f"                    {java_string(block['zhName'])},\n"
            f"                    {java_string(block['enName'])},\n"
            f"                    {java_string(block['category'])},\n"
            f"                    {java_string(block['renderType'])},\n"
            f"                    {java_string(block['texturePath'])},\n"
            f"                    {java_string(block['sound'])},\n"
            f"                    {block['hardness']},\n"
            f"                    {block['resistance']},\n"
            f"                    {java_string(block['mapColor'])},\n"
            f"                    {java_string(block['kit'])},\n"
            f"                    {java_string(block['modelPrefix'])},\n"
            f"                    {java_string(block['collision'])},\n"
            f"                    {java_string(block['connectsBy'])},\n"
            f"                    {java_string(block.get('frameTexturePath', ''))},\n"
            f"                    {java_string(block.get('glassTexturePath', ''))})"
        )
    body = ",\n".join(entries)
    content = f"""package net.littlebai.mirage2004.generated;

import java.util.List;

import net.littlebai.mirage2004.content.spec.BuildingBlockDefinition;

// Generated by tools/generate_content.py. Do not edit by hand.
public final class GeneratedBlockCatalog {{
    public static final List<BuildingBlockDefinition> BLOCKS = List.of(
{body});

    private GeneratedBlockCatalog() {{
    }}
}}
"""
    (GENERATED_JAVA_DIR / "GeneratedBlockCatalog.java").write_text(content, encoding="utf-8")


# --- VoxelShape collision box-string DSL (borrowed from Kiwi UnbakedShapeCodec) ---
# Grammar: `(x1,y1,z1,x2,y2,z2)` boxes in 1/16 units; multiple boxes union; `or(A,B)`
# / `and(A,B)` recursive. Emits a Java VoxelShape expression (NORTH-authored).
_BOX_RE = re.compile(
    r"\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)"
)
_BOOLEAN_OPS = {"or": "BooleanOp.OR", "and": "BooleanOp.AND"}


def is_box_string_collision(collision: str) -> bool:
    return collision not in ("full", "none")


def _split_top_comma(inner: str) -> tuple[str, str]:
    depth = 0
    for index, char in enumerate(inner):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            return inner[:index], inner[index + 1:]
    raise SystemExit(f"Collision boolean op needs exactly one top-level comma: {inner}")


def voxel_shape_to_java(collision: str) -> str:
    return _voxel_expr(collision.replace(" ", "").lower())


def _voxel_expr(spec: str) -> str:
    if not spec:
        raise SystemExit("Empty collision shape string")
    for op_name, java_op in _BOOLEAN_OPS.items():
        if spec.startswith(op_name + "(") and spec.endswith(")"):
            left, right = _split_top_comma(spec[len(op_name) + 1:-1])
            return f"Shapes.join({_voxel_expr(left)}, {_voxel_expr(right)}, {java_op})"
    boxes = _BOX_RE.findall(spec)
    if not boxes or _BOX_RE.sub("", spec):
        raise SystemExit(f"Invalid collision shape string: {spec}")
    box_exprs = [f"Block.box({', '.join(box)})" for box in boxes]
    if len(box_exprs) == 1:
        return box_exprs[0]
    return "Shapes.or(" + ", ".join(box_exprs) + ")"


def write_generated_special_shapes(blocks: list[dict]):
    """Emit data-driven collision shapes for special blocks whose `collision` is a
    box-string. Keyed by block id; each NORTH shape is rotated to all 4 facings.
    Blocks with collision full/none get no entry (the block falls back to a full cube)."""
    entries = []
    for block in blocks:
        if not block["kit"] or not is_box_string_collision(block["collision"]):
            continue
        expr = voxel_shape_to_java(block["collision"])
        entries.append(
            f"            Map.entry({java_string(block['id'])}, Shapes.rotateHorizontal({expr}))"
        )
    map_init = ("Map.ofEntries(\n" + ",\n".join(entries) + ")") if entries else "Map.of()"
    # Only import BooleanOp when an or/and combinator is actually emitted.
    boolean_op_import = "import net.minecraft.world.phys.shapes.BooleanOp;\n" if "BooleanOp." in map_init else ""
    content = f"""package net.littlebai.mirage2004.generated;

import java.util.Map;

import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.block.Block;
{boolean_op_import}import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

// Generated by tools/generate_content.py. Do not edit by hand.
// Data-driven collision shapes from the `collision` box-string DSL. Keyed by block id;
// each value is the NORTH-authored shape rotated to all four horizontal facings.
public final class GeneratedSpecialShapes {{
    public static final Map<String, Map<Direction, VoxelShape>> SHAPES = {map_init};

    public static VoxelShape get(Block block, Direction facing, VoxelShape fallback) {{
        Map<Direction, VoxelShape> shapes = SHAPES.get(BuiltInRegistries.BLOCK.getKey(block).getPath());
        return shapes == null ? fallback : shapes.get(facing);
    }}

    private GeneratedSpecialShapes() {{
    }}
}}
"""
    (GENERATED_JAVA_DIR / "GeneratedSpecialShapes.java").write_text(content, encoding="utf-8")


def write_lang_files(base_en: dict, base_zh: dict, blocks: list[dict]):
    en = dict(base_en)
    zh = dict(base_zh)
    for block in blocks:
        en[f"block.mirage2004.{block['id']}"] = block["enName"]
        en[f"item.mirage2004.{block['id']}"] = block["enName"]
        zh[f"block.mirage2004.{block['id']}"] = block["zhName"]
        zh[f"item.mirage2004.{block['id']}"] = block["zhName"]

    lang_dir = GENERATED_RES_DIR / "lang"
    lang_dir.mkdir(parents=True, exist_ok=True)
    (lang_dir / "en_us.json").write_text(json.dumps(en, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (lang_dir / "zh_cn.json").write_text(json.dumps(zh, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def texture_sprite(texture_path: str, block: dict) -> str | dict:
    sprite = f"mirage2004:block/{texture_path}"
    if block["renderType"] == "translucent":
        return {"force_translucent": True, "sprite": sprite}
    return sprite


def texture_reference(block: dict) -> str | dict:
    return texture_sprite(block["texturePath"], block)


def apply_render_type(model: dict, block: dict) -> dict:
    """Inject the NeoForge `render_type` model field for non-solid blocks.

    Without this, cutout and translucent blocks render on the solid chunk layer:
    glass becomes opaque and cutout holes render as black. Item models inherit
    the field through their `parent` block model, so only block models need it.
    """
    render_type = RENDER_TYPE_MODEL.get(block["renderType"])
    if render_type is not None:
        model["render_type"] = render_type
    return model


def write_cube_resources(block: dict, blockstate_dir: Path, block_model_dir: Path, item_model_dir: Path):
    variant_count = block.get("randomVariants", 1) or 1

    def variant_model_id(index: int) -> str:
        return block["id"] if index == 0 else f"{block['id']}_{index}"

    def variant_texture_path(index: int) -> str:
        return block["texturePath"] if index == 0 else f"{block['texturePath']}_{index}"

    if variant_count > 1:
        # Array of models on the empty variant key: the client picks one
        # pseudo-randomly per block position (the vanilla grass-block mechanism).
        # Each variant is a cube_all model over its own texture.
        variant_value = [{"model": f"mirage2004:block/{variant_model_id(i)}"} for i in range(variant_count)]
        blockstate = {"variants": {"": variant_value}}
    else:
        blockstate = {"variants": {"": {"model": f"mirage2004:block/{block['id']}"}}}

    (blockstate_dir / f"{block['id']}.json").write_text(
        json.dumps(blockstate, indent=2) + "\n", encoding="utf-8"
    )

    for i in range(variant_count):
        block_model = apply_render_type(
            {"parent": "minecraft:block/cube_all", "textures": {"all": texture_sprite(variant_texture_path(i), block)}},
            block,
        )
        (block_model_dir / f"{variant_model_id(i)}.json").write_text(
            json.dumps(block_model, indent=2) + "\n", encoding="utf-8"
        )

    # Item model parents the base (variant 0) block model.
    (item_model_dir / f"{block['id']}.json").write_text(
        json.dumps({"parent": f"mirage2004:block/{block['id']}"}, indent=2) + "\n",
        encoding="utf-8",
    )


def write_slab_resources(block: dict, blockstate_dir: Path, block_model_dir: Path, item_model_dir: Path):
    texture = texture_reference(block)
    (blockstate_dir / f"{block['id']}.json").write_text(
        json.dumps(
            {
                "variants": {
                    "type=bottom": {"model": f"mirage2004:block/{block['id']}"},
                    "type=top": {"model": f"mirage2004:block/{block['id']}_top"},
                    "type=double": {"model": f"mirage2004:block/{block['baseId']}"},
                }
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    base_model = apply_render_type(
        {
            "parent": "minecraft:block/slab",
            "textures": {
                "bottom": texture,
                "top": texture,
                "side": texture,
            },
        },
        block,
    )
    top_model = apply_render_type(
        {
            "parent": "minecraft:block/slab_top",
            "textures": {
                "bottom": texture,
                "top": texture,
                "side": texture,
            },
        },
        block,
    )
    (block_model_dir / f"{block['id']}.json").write_text(json.dumps(base_model, indent=2) + "\n", encoding="utf-8")
    (block_model_dir / f"{block['id']}_top.json").write_text(json.dumps(top_model, indent=2) + "\n", encoding="utf-8")
    (item_model_dir / f"{block['id']}.json").write_text(
        json.dumps({"parent": f"mirage2004:block/{block['id']}"}, indent=2) + "\n",
        encoding="utf-8",
    )


def stair_variants(model_prefix: str) -> dict:
    variants = {}
    mappings = {
        ("east", "bottom", "inner_left"): {"model": f"{model_prefix}_inner", "uvlock": True, "y": 270},
        ("east", "bottom", "inner_right"): {"model": f"{model_prefix}_inner"},
        ("east", "bottom", "outer_left"): {"model": f"{model_prefix}_outer", "uvlock": True, "y": 270},
        ("east", "bottom", "outer_right"): {"model": f"{model_prefix}_outer"},
        ("east", "bottom", "straight"): {"model": model_prefix},
        ("east", "top", "inner_left"): {"model": f"{model_prefix}_inner", "uvlock": True, "x": 180},
        ("east", "top", "inner_right"): {"model": f"{model_prefix}_inner", "uvlock": True, "x": 180, "y": 90},
        ("east", "top", "outer_left"): {"model": f"{model_prefix}_outer", "uvlock": True, "x": 180},
        ("east", "top", "outer_right"): {"model": f"{model_prefix}_outer", "uvlock": True, "x": 180, "y": 90},
        ("east", "top", "straight"): {"model": model_prefix, "uvlock": True, "x": 180},
        ("north", "bottom", "inner_left"): {"model": f"{model_prefix}_inner", "uvlock": True, "y": 180},
        ("north", "bottom", "inner_right"): {"model": f"{model_prefix}_inner", "uvlock": True, "y": 270},
        ("north", "bottom", "outer_left"): {"model": f"{model_prefix}_outer", "uvlock": True, "y": 180},
        ("north", "bottom", "outer_right"): {"model": f"{model_prefix}_outer", "uvlock": True, "y": 270},
        ("north", "bottom", "straight"): {"model": model_prefix, "uvlock": True, "y": 270},
        ("north", "top", "inner_left"): {"model": f"{model_prefix}_inner", "uvlock": True, "x": 180, "y": 270},
        ("north", "top", "inner_right"): {"model": f"{model_prefix}_inner", "uvlock": True, "x": 180},
        ("north", "top", "outer_left"): {"model": f"{model_prefix}_outer", "uvlock": True, "x": 180, "y": 270},
        ("north", "top", "outer_right"): {"model": f"{model_prefix}_outer", "uvlock": True, "x": 180},
        ("north", "top", "straight"): {"model": model_prefix, "uvlock": True, "x": 180, "y": 270},
        ("south", "bottom", "inner_left"): {"model": f"{model_prefix}_inner"},
        ("south", "bottom", "inner_right"): {"model": f"{model_prefix}_inner", "uvlock": True, "y": 90},
        ("south", "bottom", "outer_left"): {"model": f"{model_prefix}_outer"},
        ("south", "bottom", "outer_right"): {"model": f"{model_prefix}_outer", "uvlock": True, "y": 90},
        ("south", "bottom", "straight"): {"model": model_prefix, "uvlock": True, "y": 90},
        ("south", "top", "inner_left"): {"model": f"{model_prefix}_inner", "uvlock": True, "x": 180, "y": 90},
        ("south", "top", "inner_right"): {"model": f"{model_prefix}_inner", "uvlock": True, "x": 180, "y": 180},
        ("south", "top", "outer_left"): {"model": f"{model_prefix}_outer", "uvlock": True, "x": 180, "y": 90},
        ("south", "top", "outer_right"): {"model": f"{model_prefix}_outer", "uvlock": True, "x": 180, "y": 180},
        ("south", "top", "straight"): {"model": model_prefix, "uvlock": True, "x": 180, "y": 90},
        ("west", "bottom", "inner_left"): {"model": f"{model_prefix}_inner", "uvlock": True, "y": 90},
        ("west", "bottom", "inner_right"): {"model": f"{model_prefix}_inner", "uvlock": True, "y": 180},
        ("west", "bottom", "outer_left"): {"model": f"{model_prefix}_outer", "uvlock": True, "y": 90},
        ("west", "bottom", "outer_right"): {"model": f"{model_prefix}_outer", "uvlock": True, "y": 180},
        ("west", "bottom", "straight"): {"model": model_prefix, "uvlock": True, "y": 180},
        ("west", "top", "inner_left"): {"model": f"{model_prefix}_inner", "uvlock": True, "x": 180, "y": 180},
        ("west", "top", "inner_right"): {"model": f"{model_prefix}_inner", "uvlock": True, "x": 180, "y": 270},
        ("west", "top", "outer_left"): {"model": f"{model_prefix}_outer", "uvlock": True, "x": 180, "y": 180},
        ("west", "top", "outer_right"): {"model": f"{model_prefix}_outer", "uvlock": True, "x": 180, "y": 270},
        ("west", "top", "straight"): {"model": model_prefix, "uvlock": True, "x": 180, "y": 180},
    }
    for key, value in mappings.items():
        facing, half, shape = key
        variants[f"facing={facing},half={half},shape={shape}"] = value
    return variants


def write_stairs_resources(block: dict, blockstate_dir: Path, block_model_dir: Path, item_model_dir: Path):
    texture = texture_reference(block)
    model_prefix = f"mirage2004:block/{block['id']}"
    (blockstate_dir / f"{block['id']}.json").write_text(
        json.dumps({"variants": stair_variants(model_prefix)}, indent=2) + "\n",
        encoding="utf-8",
    )
    textures = {
        "bottom": texture,
        "top": texture,
        "side": texture,
    }
    for suffix, parent in [("", "minecraft:block/stairs"), ("_inner", "minecraft:block/inner_stairs"), ("_outer", "minecraft:block/outer_stairs")]:
        (block_model_dir / f"{block['id']}{suffix}.json").write_text(
            json.dumps(apply_render_type({"parent": parent, "textures": textures}, block), indent=2) + "\n",
            encoding="utf-8",
        )
    (item_model_dir / f"{block['id']}.json").write_text(
        json.dumps({"parent": f"mirage2004:block/{block['id']}"}, indent=2) + "\n",
        encoding="utf-8",
    )


def write_wall_resources(block: dict, blockstate_dir: Path, block_model_dir: Path, item_model_dir: Path):
    texture = texture_reference(block)
    multipart = [
        {"when": {"up": "true"}, "apply": {"model": f"mirage2004:block/{block['id']}_post"}},
        {"when": {"north": "low"}, "apply": {"model": f"mirage2004:block/{block['id']}_side", "uvlock": True}},
        {"when": {"east": "low"}, "apply": {"model": f"mirage2004:block/{block['id']}_side", "uvlock": True, "y": 90}},
        {"when": {"south": "low"}, "apply": {"model": f"mirage2004:block/{block['id']}_side", "uvlock": True, "y": 180}},
        {"when": {"west": "low"}, "apply": {"model": f"mirage2004:block/{block['id']}_side", "uvlock": True, "y": 270}},
        {"when": {"north": "tall"}, "apply": {"model": f"mirage2004:block/{block['id']}_side_tall", "uvlock": True}},
        {"when": {"east": "tall"}, "apply": {"model": f"mirage2004:block/{block['id']}_side_tall", "uvlock": True, "y": 90}},
        {"when": {"south": "tall"}, "apply": {"model": f"mirage2004:block/{block['id']}_side_tall", "uvlock": True, "y": 180}},
        {"when": {"west": "tall"}, "apply": {"model": f"mirage2004:block/{block['id']}_side_tall", "uvlock": True, "y": 270}},
    ]
    (blockstate_dir / f"{block['id']}.json").write_text(json.dumps({"multipart": multipart}, indent=2) + "\n", encoding="utf-8")
    for suffix, parent in [
        ("_post", "minecraft:block/template_wall_post"),
        ("_side", "minecraft:block/template_wall_side"),
        ("_side_tall", "minecraft:block/template_wall_side_tall"),
        ("_inventory", "minecraft:block/wall_inventory"),
    ]:
        (block_model_dir / f"{block['id']}{suffix}.json").write_text(
            json.dumps(apply_render_type({"parent": parent, "textures": {"wall": texture}}, block), indent=2) + "\n",
            encoding="utf-8",
        )
    (item_model_dir / f"{block['id']}.json").write_text(
        json.dumps({"parent": f"mirage2004:block/{block['id']}_inventory"}, indent=2) + "\n",
        encoding="utf-8",
    )


def write_pane_resources(block: dict, blockstate_dir: Path, block_model_dir: Path, item_model_dir: Path):
    pane_texture = texture_reference(block)
    edge_texture = texture_reference(block)
    multipart = [
        {"apply": {"model": f"mirage2004:block/{block['id']}_post"}},
        {"when": {"north": "true"}, "apply": {"model": f"mirage2004:block/{block['id']}_side"}},
        {"when": {"east": "true"}, "apply": {"model": f"mirage2004:block/{block['id']}_side", "y": 90}},
        {"when": {"south": "true"}, "apply": {"model": f"mirage2004:block/{block['id']}_side_alt"}},
        {"when": {"west": "true"}, "apply": {"model": f"mirage2004:block/{block['id']}_side_alt", "y": 90}},
        {"when": {"north": "false"}, "apply": {"model": f"mirage2004:block/{block['id']}_noside"}},
        {"when": {"east": "false"}, "apply": {"model": f"mirage2004:block/{block['id']}_noside_alt"}},
        {"when": {"south": "false"}, "apply": {"model": f"mirage2004:block/{block['id']}_noside_alt", "y": 90}},
        {"when": {"west": "false"}, "apply": {"model": f"mirage2004:block/{block['id']}_noside", "y": 270}},
    ]
    (blockstate_dir / f"{block['id']}.json").write_text(json.dumps({"multipart": multipart}, indent=2) + "\n", encoding="utf-8")
    pane_models = {
        "_post": ("minecraft:block/template_glass_pane_post", {"pane": pane_texture, "edge": edge_texture}),
        "_side": ("minecraft:block/template_glass_pane_side", {"pane": pane_texture, "edge": edge_texture}),
        "_side_alt": ("minecraft:block/template_glass_pane_side_alt", {"pane": pane_texture, "edge": edge_texture}),
        "_noside": ("minecraft:block/template_glass_pane_noside", {"pane": pane_texture}),
        "_noside_alt": ("minecraft:block/template_glass_pane_noside_alt", {"pane": pane_texture}),
    }
    for suffix, (parent, textures) in pane_models.items():
        (block_model_dir / f"{block['id']}{suffix}.json").write_text(
            json.dumps(apply_render_type({"parent": parent, "textures": textures}, block), indent=2) + "\n",
            encoding="utf-8",
        )
    (item_model_dir / f"{block['id']}.json").write_text(
        json.dumps({"parent": "minecraft:item/generated", "textures": {"layer0": f"mirage2004:block/{block['texturePath']}"}}, indent=2) + "\n",
        encoding="utf-8",
    )


def write_grille_resources(block: dict, blockstate_dir: Path, block_model_dir: Path, item_model_dir: Path):
    """Security grille (防盗窗): iron-bars-style connecting pane backed by SecurityGrilleBlock,
    with auto TOP/BOTTOM frame caps. Post/arms reuse the vanilla glass-pane piece templates;
    the caps are per-color children of the hand-authored special/grille_cap_arm_{top,bottom}
    bases -- a notched cap (two strips at x4.5-7 and x9-11.5 that clear the x7-9 pane band so
    the cap is never coplanar with the pane's top/bottom faces), applied via multipart so the
    pieces tile along a run (framed at every capped end: open air or wall, not grille)."""
    pane_texture = texture_reference(block)
    edge_texture = texture_reference(block)
    bid = block["id"]
    multipart = [
        {"apply": {"model": f"mirage2004:block/{bid}_post"}},
        {"when": {"north": "true"}, "apply": {"model": f"mirage2004:block/{bid}_side"}},
        {"when": {"east": "true"}, "apply": {"model": f"mirage2004:block/{bid}_side", "y": 90}},
        {"when": {"south": "true"}, "apply": {"model": f"mirage2004:block/{bid}_side_alt"}},
        {"when": {"west": "true"}, "apply": {"model": f"mirage2004:block/{bid}_side_alt", "y": 90}},
        {"when": {"north": "false"}, "apply": {"model": f"mirage2004:block/{bid}_noside"}},
        {"when": {"east": "false"}, "apply": {"model": f"mirage2004:block/{bid}_noside_alt"}},
        {"when": {"south": "false"}, "apply": {"model": f"mirage2004:block/{bid}_noside_alt", "y": 90}},
        {"when": {"west": "false"}, "apply": {"model": f"mirage2004:block/{bid}_noside", "y": 270}},
    ]
    # Top/bottom frame caps: a notched cap (two strips clearing the pane band) toward each
    # horizontal connection, shown where the run is capped. Multipart; pieces tile along a run.
    for prop, arm_suffix in (("top", "_cap_arm_top"), ("bottom", "_cap_arm_bottom")):
        for facing, y in (("north", 0), ("east", 90), ("south", 180), ("west", 270)):
            apply = {"model": f"mirage2004:block/{bid}{arm_suffix}"}
            if y:
                apply["y"] = y
            multipart.append({"when": {prop: "true", facing: "true"}, "apply": apply})
    (blockstate_dir / f"{bid}.json").write_text(json.dumps({"multipart": multipart}, indent=2) + "\n", encoding="utf-8")

    pane_models = {
        "_post": ("minecraft:block/template_glass_pane_post", {"pane": pane_texture, "edge": edge_texture}),
        "_side": ("minecraft:block/template_glass_pane_side", {"pane": pane_texture, "edge": edge_texture}),
        "_side_alt": ("minecraft:block/template_glass_pane_side_alt", {"pane": pane_texture, "edge": edge_texture}),
        "_noside": ("minecraft:block/template_glass_pane_noside", {"pane": pane_texture}),
        "_noside_alt": ("minecraft:block/template_glass_pane_noside_alt", {"pane": pane_texture}),
    }
    for suffix, (parent, textures) in pane_models.items():
        (block_model_dir / f"{bid}{suffix}.json").write_text(
            json.dumps(apply_render_type({"parent": parent, "textures": textures}, block), indent=2) + "\n",
            encoding="utf-8",
        )
    cap_bases = {
        "_cap_arm_top": "special/grille_cap_arm_top",
        "_cap_arm_bottom": "special/grille_cap_arm_bottom",
    }
    for suffix, base in cap_bases.items():
        # Two slots: #all = vertical (立面) face texture, #top = horizontal (顶面) face texture.
        model = {"parent": f"mirage2004:block/{base}", "textures": {
            "all": f"mirage2004:block/{block['texturePath']}",
            "top": f"mirage2004:block/{block['texturePath']}_top",
        }}
        (block_model_dir / f"{bid}{suffix}.json").write_text(
            json.dumps(apply_render_type(model, block), indent=2) + "\n", encoding="utf-8",
        )
    (item_model_dir / f"{bid}.json").write_text(
        json.dumps({"parent": "minecraft:item/generated", "textures": {"layer0": f"mirage2004:block/{block['texturePath']}"}}, indent=2) + "\n",
        encoding="utf-8",
    )


def write_item_definition_files(blocks: list[dict]):
    item_definition_dir = GENERATED_RES_DIR / "items"
    item_definition_dir.mkdir(parents=True, exist_ok=True)

    for block in blocks:
        item_definition = {
            "model": {
                "type": "minecraft:model",
                "model": f"mirage2004:item/{block['id']}",
            }
        }
        (item_definition_dir / f"{block['id']}.json").write_text(
            json.dumps(item_definition, indent=2) + "\n",
            encoding="utf-8",
        )


def write_slope_resources(block: dict, blockstate_dir: Path, block_model_dir: Path, item_model_dir: Path):
    """Smooth wedge (三角块) via the custom `mirage2004:slope` geometry loader — renders
    through the vanilla pipeline (AO/light/cull). The block model just names the loader
    + the family texture; the geometry is built in Java (SlopeGeometry). Blockstate
    rotates the NORTH-authored wedge by facing (SlopeGeometry applies the modelState)."""
    model = f"mirage2004:block/{block['id']}"
    block_model = {
        "loader": "mirage2004:slope",
        "textures": {
            # particle = base face: the slope/triangle parent (block/block) has no
            # particle slot, so without this break/step particles fall back to the
            # missing-texture (magenta/black) sprite. #all mirrors vanilla cube_all.
            "particle": "#all",
            "all": f"mirage2004:block/{block['texturePath']}",
            "slope": f"mirage2004:block/{block.get('slopeFace', block['texturePath'])}",
        },
    }
    (block_model_dir / f"{block['id']}.json").write_text(json.dumps(block_model, indent=2) + "\n", encoding="utf-8")
    # facing (y-rotation) x half (top = x:180, like stairs).
    variants = {}
    for facing, y in (("north", 0), ("east", 90), ("south", 180), ("west", 270)):
        for half, x in (("bottom", 0), ("top", 180)):
            variant = {"model": model}
            if x:
                variant["x"] = x
            if y:
                variant["y"] = y
            variants[f"facing={facing},half={half}"] = variant
    (blockstate_dir / f"{block['id']}.json").write_text(
        json.dumps({"variants": variants}, indent=2) + "\n", encoding="utf-8"
    )
    (item_model_dir / f"{block['id']}.json").write_text(
        json.dumps({"parent": model}, indent=2) + "\n", encoding="utf-8"
    )


def write_triangle_wall_resources(block: dict, blockstate_dir: Path, block_model_dir: Path, item_model_dir: Path):
    """Vertical corner-cut wall (三角墙) via the custom mirage2004:triangle_wall geometry
    loader. Facing-only (4 variants); full-height, so no half."""
    model = f"mirage2004:block/{block['id']}"
    block_model = {
        "loader": "mirage2004:triangle_wall",
        "textures": {
            # particle = base face (see write_slope_resources): without it, break/step
            # particles fall back to the missing-texture sprite. #all mirrors cube_all.
            "particle": "#all",
            "all": f"mirage2004:block/{block['texturePath']}",
            "slope": f"mirage2004:block/{block.get('slopeFace', block['texturePath'])}",
        },
    }
    (block_model_dir / f"{block['id']}.json").write_text(json.dumps(block_model, indent=2) + "\n", encoding="utf-8")
    variants = {}
    for facing, y in (("north", 0), ("east", 90), ("south", 180), ("west", 270)):
        variant = {"model": model}
        if y:
            variant["y"] = y
        variants[f"facing={facing}"] = variant
    (blockstate_dir / f"{block['id']}.json").write_text(
        json.dumps({"variants": variants}, indent=2) + "\n", encoding="utf-8"
    )
    (item_model_dir / f"{block['id']}.json").write_text(
        json.dumps({"parent": model}, indent=2) + "\n", encoding="utf-8"
    )


_FACING_Y = (("north", 0), ("east", 90), ("south", 180), ("west", 270))


def write_special_resources(block: dict, blockstate_dir: Path, block_model_dir: Path, item_model_dir: Path):
    """Special-shape block resources. The GEOMETRY is a shared hand-authored base model
    per shape (`special/<modelPrefix>[_<pos>]`, textured via the `#all` slot) — authored
    ONCE and reused across all colors. The generator emits a per-color CHILD model that
    parents the base and overrides the texture (exactly like vanilla cube_all), plus the
    blockstate + item model. Missing base model -> purple; missing blockstate variant key
    -> hard load error."""
    kit = block["kit"]
    if kit == "static":
        _write_static_special_resources(block, blockstate_dir, block_model_dir, item_model_dir)
    elif kit == "pole":
        _write_pole_special_resources(block, blockstate_dir, block_model_dir, item_model_dir)
    elif kit == "framed_window":
        _write_framed_window_resources(block, blockstate_dir, block_model_dir, item_model_dir)
    elif kit == "framed_window_slope":
        _write_framed_window_slope_resources(block, blockstate_dir, block_model_dir, item_model_dir)
    elif kit == "prefab_window":
        _write_prefab_window_resources(block, blockstate_dir, block_model_dir, item_model_dir)
    else:
        raise SystemExit(f"Unsupported special kit in resource writer: {kit}")


def _special_child_model(block: dict, block_model_dir: Path, suffix: str) -> str:
    """Per-color child model: parents the shared base `special/<modelPrefix><suffix>` and
    overrides its `all` texture with the family's per-color texture. Returns the child id."""
    base = f"mirage2004:block/special/{block['modelPrefix']}{suffix}"
    child_id = f"{block['id']}{suffix}"
    (block_model_dir / f"{child_id}.json").write_text(
        json.dumps({"parent": base, "textures": {"all": f"mirage2004:block/{block['texturePath']}"}}, indent=2) + "\n",
        encoding="utf-8",
    )
    return f"mirage2004:block/{child_id}"


def _write_static_special_resources(block: dict, blockstate_dir: Path, block_model_dir: Path, item_model_dir: Path):
    """static kit: HORIZONTAL_FACING, one shared base model rotated by facing."""
    model = _special_child_model(block, block_model_dir, "")
    variants = {}
    for facing, y in _FACING_Y:
        variant = {"model": model}
        if y:
            variant["y"] = y
        variants[f"facing={facing}"] = variant
    (blockstate_dir / f"{block['id']}.json").write_text(
        json.dumps({"variants": variants}, indent=2) + "\n", encoding="utf-8"
    )
    (item_model_dir / f"{block['id']}.json").write_text(
        json.dumps({"parent": model}, indent=2) + "\n", encoding="utf-8"
    )


def _write_pole_special_resources(block: dict, blockstate_dir: Path, block_model_dir: Path, item_model_dir: Path):
    """pole kit: HORIZONTAL_FACING x POS_VERTICAL (16 states) -> 4 shared base models
    (_top/_middle/_bottom/_none) rotated by facing. Item model = the standalone _none form."""
    models = {pos: _special_child_model(block, block_model_dir, f"_{pos}") for pos in ("top", "middle", "bottom", "none")}
    variants = {}
    for facing, y in _FACING_Y:
        for pos in ("top", "middle", "bottom", "none"):
            variant = {"model": models[pos]}
            if y:
                variant["y"] = y
            variants[f"facing={facing},pos={pos}"] = variant
    (blockstate_dir / f"{block['id']}.json").write_text(
        json.dumps({"variants": variants}, indent=2) + "\n", encoding="utf-8"
    )
    (item_model_dir / f"{block['id']}.json").write_text(
        json.dumps({"parent": models["none"]}, indent=2) + "\n", encoding="utf-8"
    )


# --- Framed window (FramedWindowBlock, v1.md §2.1) -- yuushya pole_line model ------------
# Connection state = POS_HORIZON (pos_h: left/middle/right/none) x POS_VERTICAL (pos:
# top/middle/bottom/none) x FACING(4). The frame is connection-dependent, so the generator
# COMPOSES one frame model per (pos_h, pos) = 16 models, each with the rails that should be
# present for that state; the glass is state-independent (always a full-cell pane), so it is
# one model reused across all states. Multipart applies frame_<pos_h>_<pos> + glass per
# facing (y-rot). Rails carry no per-state cull (the box itself differs per model), so they
# never leave a junction gap.
_FRAMED_WINDOW_POS_H = ("left", "middle", "right", "none")
_FRAMED_WINDOW_POS = ("top", "middle", "bottom", "none")


def _frame_box(x1, y1, z1, x2, y2, z2, slot="#frame"):
    """One axis-aligned frame box with `slot` (default #frame) on all six faces, standard
    16x16 UVs sampled from the box footprint so the frame sprite tiles consistently."""
    return {
        "from": [x1, y1, z1],
        "to": [x2, y2, z2],
        "faces": {
            "north": {"uv": [16 - x2, 16 - y2, 16 - x1, 16 - y1], "texture": slot},
            "south": {"uv": [x1, 16 - y2, x2, 16 - y1], "texture": slot},
            "west": {"uv": [z1, 16 - y2, z2, 16 - y1], "texture": slot},
            "east": {"uv": [16 - z2, 16 - y2, 16 - z1, 16 - y1], "texture": slot},
            "up": {"uv": [x1, z1, x2, z2], "texture": slot},
            "down": {"uv": [x1, 16 - z2, x2, 16 - z1], "texture": slot},
        },
    }


def _compose_frame_elements(pos_h: str, pos: str, slot="#frame") -> list[dict]:
    """The 16-state frame composition rule (SINGLE_BLOCK_WINDOW_DESIGN.md v2 §2). A rail is
    PRESENT on a framed (unconnected) side and absent on a connected side:
        left  rail iff pos_h in {none, left}    right rail iff pos_h in {none, right}
        top   rail iff pos   in {none, top}     bottom rail iff pos in {none, bottom}
    Vertical rails are always full height (0..16). Horizontal rails span to the cell edge on
    a CONNECTED side (Lx=0 / Rx=16) and stop at the vertical rail on a framed side
    (Lx=2 / Rx=14), so a connected junction is continuous and a framed junction meets its
    own corner. none_none = all four rails (isolated); middle_middle = no rails (interior)."""
    left_present = pos_h in ("none", "left")
    right_present = pos_h in ("none", "right")
    top_present = pos in ("none", "top")
    bottom_present = pos in ("none", "bottom")
    lx = 2 if left_present else 0
    rx = 14 if right_present else 16
    elements = []
    if left_present:
        elements.append(_frame_box(0, 0, 7, 2, 16, 9, slot))
    if right_present:
        elements.append(_frame_box(14, 0, 7, 16, 16, 9, slot))
    if top_present:
        elements.append(_frame_box(lx, 14, 7, rx, 16, 9, slot))
    if bottom_present:
        elements.append(_frame_box(lx, 0, 7, rx, 2, 9, slot))
    return elements


def _glass_elements(slot="#glass") -> list[dict]:
    """The state-independent glass pane: a full-cell box [0,0,7.5]->[16,16,8.5] so connected
    neighbours' panes meet at the cell border (no gap; on a framed side the rail covers the
    edge). #glass = the mod glass (玻璃组), translucent + force_translucent."""
    return [
        {
            "from": [0, 0, 7.5],
            "to": [16, 16, 8.5],
            "faces": {
                "north": {"uv": [0, 0, 16, 16], "texture": slot},
                "south": {"uv": [0, 0, 16, 16], "texture": slot},
                "west": {"uv": [7.5, 0, 8.5, 16], "texture": slot},
                "east": {"uv": [7.5, 0, 8.5, 16], "texture": slot},
                "up": {"uv": [0, 7.5, 16, 8.5], "texture": slot},
                "down": {"uv": [0, 7.5, 16, 8.5], "texture": slot},
            },
        }
    ]


def _write_framed_window_resources(block: dict, blockstate_dir: Path, block_model_dir: Path, item_model_dir: Path):
    """framed_window kit (FramedWindowBlock): 1x1 centered frame+glass, port of yuushya
    PoleLineBlock. State = FACING(4) x POS_HORIZON(pos_h, 4) x POS_VERTICAL(pos, 4) = 64.

    Emits, per block id:
      - 16 COMPOSED frame models (frame_<pos_h>_<pos>): the rails present for that connection
        state, texture #frame = the frame color, render_type cutout.
      - 1 GLASS model (glass): full-cell pane, texture #glass = the mod glass, render_type
        translucent + force_translucent (state-independent, reused across all 16 states).
      - a MULTIPART blockstate that applies frame_<pos_h>_<pos> + glass per facing (y-rot).
      - an item model = the isolated none_none frame + glass (the standalone full-frame look).
    """
    frame_texture = f"mirage2004:block/{block['frameTexturePath']}"
    glass_texture = f"mirage2004:block/{block['glassTexturePath']}"

    # 16 composed frame models (one per pos_h x pos).
    frame_model_ids = {}
    for pos_h in _FRAMED_WINDOW_POS_H:
        for pos in _FRAMED_WINDOW_POS:
            model_id = f"{block['id']}_frame_{pos_h}_{pos}"
            model = {
                "parent": "minecraft:block/block",
                "render_type": "minecraft:cutout",
                "textures": {"frame": frame_texture, "particle": frame_texture},
                "elements": _compose_frame_elements(pos_h, pos),
            }
            (block_model_dir / f"{model_id}.json").write_text(
                json.dumps(model, indent=2) + "\n", encoding="utf-8"
            )
            frame_model_ids[(pos_h, pos)] = f"mirage2004:block/{model_id}"

    # 1 glass model (state-independent, full-cell, translucent).
    glass_model_id = f"{block['id']}_glass"
    glass_model = {
        "parent": "minecraft:block/block",
        "render_type": "minecraft:translucent",
        "textures": {
            "glass": {"force_translucent": True, "sprite": glass_texture},
            "particle": glass_texture,
        },
        "elements": _glass_elements(),
    }
    (block_model_dir / f"{glass_model_id}.json").write_text(
        json.dumps(glass_model, indent=2) + "\n", encoding="utf-8"
    )
    glass_model_ref = f"mirage2004:block/{glass_model_id}"

    # Multipart blockstate: per (facing, pos_h, pos) apply the matching frame model; per
    # facing apply the glass. y-rot per facing (N0/E90/S180/W270).
    multipart = []
    for facing, y in _FACING_Y:
        glass_apply = {"model": glass_model_ref}
        if y:
            glass_apply["y"] = y
        multipart.append({"when": {"facing": facing}, "apply": glass_apply})
        for pos_h in _FRAMED_WINDOW_POS_H:
            for pos in _FRAMED_WINDOW_POS:
                frame_apply = {"model": frame_model_ids[(pos_h, pos)]}
                if y:
                    frame_apply["y"] = y
                multipart.append(
                    {"when": {"facing": facing, "pos_h": pos_h, "pos": pos}, "apply": frame_apply}
                )

    (blockstate_dir / f"{block['id']}.json").write_text(
        json.dumps({"multipart": multipart}, indent=2) + "\n", encoding="utf-8"
    )

    # Item model = the isolated (none_none) full frame + the glass pane, combined.
    item_model_id = f"{block['id']}_inventory"
    item_model = {
        "parent": "minecraft:block/block",
        "render_type": "minecraft:cutout",
        "textures": {
            "frame": frame_texture,
            "glass": {"force_translucent": True, "sprite": glass_texture},
            "particle": frame_texture,
        },
        "elements": _compose_frame_elements("none", "none") + _glass_elements(),
    }
    (block_model_dir / f"{item_model_id}.json").write_text(
        json.dumps(item_model, indent=2) + "\n", encoding="utf-8"
    )
    (item_model_dir / f"{block['id']}.json").write_text(
        json.dumps({"parent": f"mirage2004:block/{item_model_id}"}, indent=2) + "\n", encoding="utf-8"
    )


# --- Framed window SLOPE (FacingSpecialBlock) -- diagonal (45deg-Y) single-block window ---
# The flat single-block window's frame+glass, ROTATED 45deg about the vertical (Y) axis in the
# MODEL (blockstate only allows 90deg steps), for diagonal/chamfered walls. FACING-only, NO
# connection, ONE variant. Two hand-authored bases live under src/main special/:
#   framed_window_slope_frame (4 rails, #all, cutout) + framed_window_slope_glass (full pane,
#   #all, translucent) -- EACH element carries rotation {angle:45, axis:y, origin:[8,8,8],
# rescale:true}. The generator emits per-color child models (parent base, override #all) and a
# FACING-only multipart (y-rot 0/90/180/270 -> the 4 diagonal orientations).


# The 45deg-Y rotation applied to EVERY slope element. rescale:true scales the box by sqrt(2)
# so a 16px panel spans the cell diagonal (~22.6px) = the author's "stretch to ~22px".
_SLOPE_ROTATION = {"angle": 45, "axis": "y", "origin": [8, 8, 8], "rescale": True}


def _slope_frame_elements(slot="#all") -> list[dict]:
    """The 4 frame rails of the diagonal window (same Z7-9 centered rails as the flat single-block
    window), each carrying the 45deg-Y rotation about the cell centre. Used to author the item
    composite; the hand-authored base model (special/framed_window_slope_frame) is the source of
    truth for the in-world rails and must stay byte-identical to these boxes + rotation."""
    rails = [
        _frame_box(0, 0, 7, 2, 16, 9, slot),    # left
        _frame_box(14, 0, 7, 16, 16, 9, slot),  # right
        _frame_box(2, 14, 7, 14, 16, 9, slot),  # top
        _frame_box(2, 0, 7, 14, 2, 9, slot),    # bottom
    ]
    for rail in rails:
        rail["rotation"] = dict(_SLOPE_ROTATION)
    return rails


def _slope_glass_elements(slot="#all") -> list[dict]:
    """The full diagonal glass pane (Z7.5-8.5), carrying the same 45deg-Y rotation. Source of
    truth for the in-world glass is special/framed_window_slope_glass; keep them identical."""
    element = {
        "from": [2, 2, 7.5],
        "to": [14, 14, 8.5],
        "rotation": dict(_SLOPE_ROTATION),
        "faces": {
            "north": {"uv": [2, 2, 14, 14], "texture": slot},
            "south": {"uv": [2, 2, 14, 14], "texture": slot},
            "west": {"uv": [7.5, 2, 8.5, 14], "texture": slot},
            "east": {"uv": [7.5, 2, 8.5, 14], "texture": slot},
            "up": {"uv": [2, 7.5, 14, 8.5], "texture": slot},
            "down": {"uv": [2, 7.5, 14, 8.5], "texture": slot},
        },
    }
    return [element]


def _slope_layer_child(block: dict, block_model_dir: Path, layer: str, texture: str, translucent: bool) -> str:
    """Per-color child model for one framed_window_slope layer (frame|glass). Parents the shared
    hand-authored base `special/framed_window_slope_<layer>` (which carries the 45deg-Y rotation
    on every element) and overrides its `#all` slot with the family per-color texture, forcing the
    render type per layer (frame=cutout, glass=translucent). Glass uses force_translucent so it
    sorts on the translucent layer only."""
    base = f"mirage2004:block/special/{block['modelPrefix']}_{layer}"
    child_id = f"{block['id']}_{layer}"
    if translucent:
        all_slot = {"force_translucent": True, "sprite": texture}
        render_type = "minecraft:translucent"
    else:
        all_slot = texture
        render_type = "minecraft:cutout"
    model = {
        "parent": base,
        "render_type": render_type,
        "textures": {"all": all_slot, "particle": texture},
    }
    (block_model_dir / f"{child_id}.json").write_text(
        json.dumps(model, indent=2) + "\n", encoding="utf-8"
    )
    return f"mirage2004:block/{child_id}"


def _write_framed_window_slope_resources(block: dict, blockstate_dir: Path, block_model_dir: Path, item_model_dir: Path):
    """framed_window_slope kit (FacingSpecialBlock): diagonal single-block window, the flat
    window's frame+glass rotated 45deg about Y in the MODEL. State = FACING(4) only -- NO
    connection (no pos/pos_h), ONE variant.

    Emits, per block id:
      - 2 per-color child models: frame (cutout) + glass (translucent), each parenting the shared
        45deg-rotated base and overriding #all with the color texture.
      - a FACING-only MULTIPART blockstate: per facing apply BOTH the frame and the glass child,
        y-rot per facing (N0/E90/S180/W270) -> the 4 diagonal orientations.
      - an item model = the frame+glass composite (the standalone diagonal window thumbnail).
    """
    frame_texture = f"mirage2004:block/{block['frameTexturePath']}"
    glass_texture = f"mirage2004:block/{block['glassTexturePath']}"

    frame_model = _slope_layer_child(block, block_model_dir, "frame", frame_texture, translucent=False)
    glass_model = _slope_layer_child(block, block_model_dir, "glass", glass_texture, translucent=True)

    # FACING-only multipart: per facing apply BOTH layers, y-rot per facing. No connection keys.
    multipart = []
    for facing, y in _FACING_Y:
        for model_ref in (frame_model, glass_model):
            apply = {"model": model_ref}
            if y:
                apply["y"] = y
            multipart.append({"when": {"facing": facing}, "apply": apply})

    (blockstate_dir / f"{block['id']}.json").write_text(
        json.dumps({"multipart": multipart}, indent=2) + "\n", encoding="utf-8"
    )

    # Item model = the frame+glass composite (a single model inlines both element sets; a model
    # can have only one parent, so the rotated geometry is authored here via the _slope_*_elements
    # helpers, which mirror the two hand-authored bases). Both element sets carry the 45deg-Y
    # rotation, so the inventory thumbnail shows the diagonal window too.
    item_model_id = f"{block['id']}_inventory"
    item_model = {
        "parent": "minecraft:block/block",
        "render_type": "minecraft:cutout",
        "textures": {
            "frame": frame_texture,
            "glass": {"force_translucent": True, "sprite": glass_texture},
            "particle": frame_texture,
        },
        "elements": _slope_frame_elements(slot="frame") + _slope_glass_elements(slot="glass"),
    }
    (block_model_dir / f"{item_model_id}.json").write_text(
        json.dumps(item_model, indent=2) + "\n", encoding="utf-8"
    )
    (item_model_dir / f"{block['id']}.json").write_text(
        json.dumps({"parent": f"mirage2004:block/{item_model_id}"}, indent=2) + "\n", encoding="utf-8"
    )


# --- Prefab window (PrefabWindowBlock, v1.md §2.2) -- door-style 2-tall column ------------
# State = FACING(4) x HALF(lower/upper) x OPEN(true/false) = 16. The geometry is FIXED per
# (modelPrefix, half): a hand-authored frame base (special/<prefix>_frame_<half>, #all=frame,
# cutout) + a hand-authored glass base (special/<prefix>_glass_<half>, #all=mod glass,
# translucent), authored ONCE and reused across all colorPairs. The generator emits per-color
# child models that parent the bases and override #all, then a MULTIPART blockstate keyed on
# `facing + half` ONLY (open is ignored, so both open values render identically in v1).
_PREFAB_WINDOW_HALVES = ("lower", "upper")


def _prefab_layer_child(block: dict, block_model_dir: Path, layer: str, half: str, texture: str, translucent: bool) -> str:
    """Per-color child model for one prefab layer (frame|glass) x half. Parents the shared
    base `special/<modelPrefix>_<layer>_<half>` and overrides its `#all` slot with the family
    per-color texture, forcing the render type per layer (frame=cutout, glass=translucent).
    Glass uses force_translucent so it sorts on the translucent layer only."""
    base = f"mirage2004:block/special/{block['modelPrefix']}_{layer}_{half}"
    child_id = f"{block['id']}_{layer}_{half}"
    if translucent:
        all_slot = {"force_translucent": True, "sprite": texture}
        render_type = "minecraft:translucent"
    else:
        all_slot = texture
        render_type = "minecraft:cutout"
    model = {
        "parent": base,
        "render_type": render_type,
        "textures": {"all": all_slot, "particle": texture},
    }
    (block_model_dir / f"{child_id}.json").write_text(
        json.dumps(model, indent=2) + "\n", encoding="utf-8"
    )
    return f"mirage2004:block/{child_id}"


def _write_prefab_window_resources(block: dict, blockstate_dir: Path, block_model_dir: Path, item_model_dir: Path):
    """prefab_window kit (PrefabWindowBlock): door-style 2-tall column, flush to the exterior.

    Emits, per block id:
      - 4 child models: frame_lower/frame_upper (cutout) + glass_lower/glass_upper (translucent),
        each parenting the hand-authored base and overriding #all with the color texture.
      - a MULTIPART blockstate keyed on facing + half ONLY (open ignored): per (facing, half)
        apply the frame child + the glass child, y-rot per facing (N0/E90/S180/W270).
      - an item model = the LOWER-half composite (frame_lower over glass_lower), the natural
        thumbnail for the dropped block item.
    """
    frame_texture = f"mirage2004:block/{block['frameTexturePath']}"
    glass_texture = f"mirage2004:block/{block['glassTexturePath']}"

    # 4 per-color child models (frame/glass x lower/upper).
    frame_models = {}
    glass_models = {}
    for half in _PREFAB_WINDOW_HALVES:
        frame_models[half] = _prefab_layer_child(block, block_model_dir, "frame", half, frame_texture, translucent=False)
        glass_models[half] = _prefab_layer_child(block, block_model_dir, "glass", half, glass_texture, translucent=True)

    # Multipart blockstate: per (facing, half) apply BOTH the frame and the glass child. The
    # `when` ignores `open`, so OPEN=true|false render the same closed model in v1.
    multipart = []
    for facing, y in _FACING_Y:
        for half in _PREFAB_WINDOW_HALVES:
            for model_ref in (frame_models[half], glass_models[half]):
                apply = {"model": model_ref}
                if y:
                    apply["y"] = y
                multipart.append({"when": {"facing": facing, "half": half}, "apply": apply})

    (blockstate_dir / f"{block['id']}.json").write_text(
        json.dumps({"multipart": multipart}, indent=2) + "\n", encoding="utf-8"
    )

    # Item model = the LOWER-half composite (frame over glass), via a small parent that pulls
    # both base elements together with the two-color textures.
    item_model_id = f"{block['id']}_inventory"
    item_model = {
        "parent": f"mirage2004:block/special/{block['modelPrefix']}_item",
        "render_type": "minecraft:cutout",
        "textures": {
            "frame": frame_texture,
            "glass": {"force_translucent": True, "sprite": glass_texture},
            "particle": frame_texture,
        },
    }
    (block_model_dir / f"{item_model_id}.json").write_text(
        json.dumps(item_model, indent=2) + "\n", encoding="utf-8"
    )
    (item_model_dir / f"{block['id']}.json").write_text(
        json.dumps({"parent": f"mirage2004:block/{item_model_id}"}, indent=2) + "\n", encoding="utf-8"
    )


def write_model_files(blocks: list[dict]):
    blockstate_dir = GENERATED_RES_DIR / "blockstates"
    block_model_dir = GENERATED_RES_DIR / "models" / "block"
    item_model_dir = GENERATED_RES_DIR / "models" / "item"
    for directory in [blockstate_dir, block_model_dir, item_model_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    for block in blocks:
        if block["kit"]:
            write_special_resources(block, blockstate_dir, block_model_dir, item_model_dir)
            continue
        match block["shape"]:
            case "cube":
                write_cube_resources(block, blockstate_dir, block_model_dir, item_model_dir)
            case "slab":
                write_slab_resources(block, blockstate_dir, block_model_dir, item_model_dir)
            case "stairs":
                write_stairs_resources(block, blockstate_dir, block_model_dir, item_model_dir)
            case "wall":
                write_wall_resources(block, blockstate_dir, block_model_dir, item_model_dir)
            case "pane":
                write_pane_resources(block, blockstate_dir, block_model_dir, item_model_dir)
            case "grille":
                write_grille_resources(block, blockstate_dir, block_model_dir, item_model_dir)
            case "slope":
                write_slope_resources(block, blockstate_dir, block_model_dir, item_model_dir)
            case "triangle_wall":
                write_triangle_wall_resources(block, blockstate_dir, block_model_dir, item_model_dir)
            case _:
                raise SystemExit(f"Unsupported generated shape: {block['shape']}")

    write_item_definition_files(blocks)


def write_block_tag_files(blocks: list[dict]):
    """Emit vanilla-merging block tags (all replace:false). Walls/slabs/stairs must
    be listed or vanilla connection/behavior silently fails. mineable/pickaxe sets
    mining SPEED only (drops are gated by the loot tables, not this tag). Glass
    (sound == 'glass') is intentionally excluded from mineable/pickaxe, matching
    vanilla. Each tag is skipped individually when it has no members."""
    tag_dir = GENERATED_DATA_DIR / "minecraft" / "tags" / "block"

    tag_values = {
        "walls.json": [block["id"] for block in blocks if block["shape"] == "wall"],
        "slabs.json": [block["id"] for block in blocks if block["shape"] == "slab"],
        "stairs.json": [block["id"] for block in blocks if block["shape"] == "stairs"],
        "mineable/pickaxe.json": [block["id"] for block in blocks if block["sound"] == "stone"],
    }

    for rel_path, block_ids in tag_values.items():
        if not block_ids:
            continue
        path = tag_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"replace": False, "values": [f"mirage2004:{block_id}" for block_id in block_ids]},
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )


def build_loot_table(block: dict) -> dict:
    """Vanilla-shaped block loot table for one block (random_sequence inner segment
    is plural `blocks/` even though the data dir is singular `loot_table` — both
    verified against 26.1.2 vanilla).

    - prefab_window -> door-style half=lower condition so ONLY the lower half drops (the
                       block is two real cells; without this, breaking both double-drops)
    - slab  -> double-slab pattern (set_count 2 when type=double), mirrors brick_slab
    - glass -> silk-touch-only, drops nothing otherwise, mirrors vanilla glass
    - else  -> self drop gated by survives_explosion, mirrors bricks
    """
    block_id = block["id"]
    name = f"mirage2004:{block_id}"
    random_sequence = f"mirage2004:blocks/{block_id}"

    if block.get("kit") == "prefab_window":
        # Door-style: only the LOWER half drops (mirrors vanilla door loot). The UPPER drops
        # nothing; combined with PrefabWindowBlock.playerWillDestroy, every break path yields
        # exactly one item (or zero in creative).
        return {
            "type": "minecraft:block",
            "pools": [
                {
                    "bonus_rolls": 0.0,
                    "conditions": [{"condition": "minecraft:survives_explosion"}],
                    "entries": [
                        {
                            "type": "minecraft:item",
                            "name": name,
                            "conditions": [
                                {
                                    "condition": "minecraft:block_state_property",
                                    "block": name,
                                    "properties": {"half": "lower"},
                                }
                            ],
                        }
                    ],
                    "rolls": 1.0,
                }
            ],
            "random_sequence": random_sequence,
        }

    if block["shape"] == "slab":
        return {
            "type": "minecraft:block",
            "pools": [
                {
                    "bonus_rolls": 0.0,
                    "entries": [
                        {
                            "type": "minecraft:item",
                            "functions": [
                                {
                                    "add": False,
                                    "conditions": [
                                        {
                                            "block": name,
                                            "condition": "minecraft:block_state_property",
                                            "properties": {"type": "double"},
                                        }
                                    ],
                                    "count": 2.0,
                                    "function": "minecraft:set_count",
                                },
                                {"function": "minecraft:explosion_decay"},
                            ],
                            "name": name,
                        }
                    ],
                    "rolls": 1.0,
                }
            ],
            "random_sequence": random_sequence,
        }

    if block["sound"] == "glass":
        condition = {
            "condition": "minecraft:match_tool",
            "predicate": {
                "predicates": {
                    "minecraft:enchantments": [
                        {"enchantments": "minecraft:silk_touch", "levels": {"min": 1}}
                    ]
                }
            },
        }
    else:
        condition = {"condition": "minecraft:survives_explosion"}

    return {
        "type": "minecraft:block",
        "pools": [
            {
                "bonus_rolls": 0.0,
                "conditions": [condition],
                "entries": [{"type": "minecraft:item", "name": name}],
                "rolls": 1.0,
            }
        ],
        "random_sequence": random_sequence,
    }


def write_loot_table_files(blocks: list[dict]):
    """One loot table per block at data/mirage2004/loot_table/blocks/<id>.json.
    Without these, blocks resolve a missing table and drop nothing when mined.
    Driven by shape/sound only, so it is color-independent."""
    loot_dir = GENERATED_DATA_DIR / "mirage2004" / "loot_table" / "blocks"
    loot_dir.mkdir(parents=True, exist_ok=True)
    for block in blocks:
        (loot_dir / f"{block['id']}.json").write_text(
            json.dumps(build_loot_table(block), indent=2) + "\n",
            encoding="utf-8",
        )


def write_manifest(colors: list[dict], families: list[dict], collections: list[dict], blocks: list[dict]):
    manifest = {
        "colors": colors,
        "families": families,
        "collections": collections,
        "blocks": blocks,
    }
    GENERATED_MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    (GENERATED_MANIFEST_DIR / "content_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_grille_connect_tag(blocks: list[dict]):
    """Emit mirage2004:grille_no_connect — the block tag SecurityGrilleBlock refuses to
    connect to (glass CUBES). Glass panes / iron bars are excluded in Java via instanceof,
    so this tag only needs the cube forms: vanilla glass via #minecraft:impermeable plus
    this mod's glass-cube blocks (glass_system / window_glass_system presets)."""
    glass_cube_ids = [
        block["id"]
        for block in blocks
        if block["shape"] == "cube" and block["preset"] in ("glass_system", "window_glass_system")
    ]
    if not glass_cube_ids:
        return
    values = ["#minecraft:impermeable"] + [f"mirage2004:{block_id}" for block_id in glass_cube_ids]
    tag_dir = GENERATED_DATA_DIR / "mirage2004" / "tags" / "block"
    tag_dir.mkdir(parents=True, exist_ok=True)
    (tag_dir / "grille_no_connect.json").write_text(
        json.dumps({"replace": False, "values": values}, indent=2) + "\n", encoding="utf-8"
    )


def main():
    reset_generated_outputs()
    colors, color_map, families, collections, base_en, base_zh = load_content()
    validate_content(colors, families, collections)
    enabled_families = resolve_enabled_families(families, collections)
    blocks = build_block_catalog(color_map, enabled_families)
    write_generated_palette(colors)
    write_generated_families(enabled_families)
    write_generated_collections(collections)
    write_generated_block_catalog(blocks)
    write_generated_special_shapes(blocks)
    write_lang_files(base_en, base_zh, blocks)
    write_model_files(blocks)
    write_block_tag_files(blocks)
    write_grille_connect_tag(blocks)
    write_loot_table_files(blocks)
    write_manifest(colors, enabled_families, collections, blocks)
    print(f"Generated {len(blocks)} block definitions from {len(enabled_families)} enabled families.")


if __name__ == "__main__":
    main()
