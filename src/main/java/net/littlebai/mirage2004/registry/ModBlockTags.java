package net.littlebai.mirage2004.registry;

import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.tags.TagKey;
import net.minecraft.world.level.block.Block;

import net.littlebai.mirage2004.Mirage2004;

/** Mod-owned block tags. Tag membership is supplied by the generated data files. */
public final class ModBlockTags {
    /**
     * Blocks the security grille must NOT connect to horizontally. Covers glass CUBES
     * (#minecraft:impermeable + this mod's glass blocks); glass PANES and iron bars are
     * excluded separately in {@link net.littlebai.mirage2004.content.block.SecurityGrilleBlock}
     * via an {@code instanceof IronBarsBlock} check.
     */
    public static final TagKey<Block> GRILLE_NO_CONNECT =
            TagKey.create(Registries.BLOCK, Identifier.parse(Mirage2004.MODID + ":grille_no_connect"));

    private ModBlockTags() {
    }
}
