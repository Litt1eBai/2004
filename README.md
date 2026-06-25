Mirage2004
==========

Content flow
============

Author editable inputs live under `content/`:

- `content/families/*.yaml`: material family definitions — colour axes + `material` only (YAML; the generator needs PyYAML)
- `content/mirage.xlsx`: the tabular sources, one sheet each — `colors`, `materials` (physics + `tool`/`tag_transformers`), `block_types` (the shape catalog: common cube/slab/stairs/wall/… + special kit-driven shapes), `apply` (assigns block_types to families, with per-cell collision/kit overrides; framed windows use `piece` rows), `blocks` (one-off "single" blocks), `collections` (enabled family sets). Read directly via the Python stdlib (no openpyxl); edit in any spreadsheet app.
- `content/base_lang/*.json`: hand-written base localization keys

These inputs describe mod-internal content structure only. They do not describe how textures are generated.
Each family also carries a code-owned `preset` that tells the runtime what kind of system it belongs to, such as solid materials, glass systems, window-frame systems, or infrastructure systems. A block is a family's `material` × colour-axes cartesian × the block_types assigned to it in the `apply` sheet, or a one-off row in the `blocks` sheet.

Generated outputs live under `src/generated/`:

- `src/generated/java/net/littlebai/mirage2004/generated`
- `src/generated/resources/assets/mirage2004`
- `src/generated/resources/mirage2004/content_manifest.json`

Run the generator with:

- `python3 tools/generate_content.py`
- or Gradle task `generateContent`
- on Windows/IDEA, if needed: `gradlew generateContent -PpythonCmd=python`

The generator owns those `src/generated/` outputs. When content specs are removed or renamed, regeneration clears stale generated Java, lang files, blockstates, and models before rewriting them.

Development notes
=================

- Runtime registration stays in native NeoForge `DeferredRegister`.
- `content/collections/*.json` controls which material families are enabled for generation. Collections can be checked in with `"enabled": false` to park future systems without forcing runtime support yet.
- The mod assumes static externally baked textures named as `<baseTexture>_<color>.png`.
- Current reference-driven targets include exterior `vertical_tile`, green `window_glass_panel`, and arched/cage-like `security_grille` variants.
- Minecraft reference sources are already extracted under `vendor/minecraft-patched-26.1.2.73-sources/`; use that directly instead of decompiling jars again.

References
==========

- NeoForge docs: https://docs.neoforged.net/
- Mojang mappings license: https://github.com/NeoForged/NeoForm/blob/main/Mojang.md
