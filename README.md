Mirage2004
==========

Content flow
============

Author editable inputs live under `content/`:

- `content/palettes/*.json`: color palette definitions
- `content/families/*.json`: material family definitions
- `content/collections/*.json`: enabled family sets
- `content/base_lang/*.json`: hand-written base localization keys

These inputs describe mod-internal content structure only. They do not describe how textures are generated.
Each family also carries a code-owned `preset` that tells the runtime what kind of system it belongs to, such as solid materials, glass systems, future window-frame systems, or future infrastructure systems. Families also distinguish between `commonShapes` for ordinary block variants and `specialShapes` for future system-specific parts.

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
