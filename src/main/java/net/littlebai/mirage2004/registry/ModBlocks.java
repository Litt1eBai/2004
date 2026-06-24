package net.littlebai.mirage2004.registry;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.IronBarsBlock;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.SlabBlock;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.TransparentBlock;
import net.minecraft.world.level.block.WallBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.material.MapColor;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredBlock;
import net.neoforged.neoforge.registries.DeferredRegister;

import net.littlebai.mirage2004.Mirage2004;
import net.littlebai.mirage2004.content.block.TriangleWallBlock;
import net.littlebai.mirage2004.content.block.FacingSpecialBlock;
import net.littlebai.mirage2004.content.block.FramedWindowBlock;
import net.littlebai.mirage2004.content.block.PoleBlock;
import net.littlebai.mirage2004.content.block.PrefabWindowBlock;
import net.littlebai.mirage2004.content.block.SecurityGrilleBlock;
import net.littlebai.mirage2004.content.block.SlopeBlock;
import net.littlebai.mirage2004.content.spec.BuildingBlockDefinition;
import net.littlebai.mirage2004.generated.GeneratedBlockCatalog;

public final class ModBlocks {
    public static final DeferredRegister.Blocks BLOCKS = DeferredRegister.createBlocks(Mirage2004.MODID);
    public static final Map<String, DeferredBlock<? extends Block>> BLOCKS_BY_ID = new LinkedHashMap<>();

    static {
        for (BuildingBlockDefinition definition : GeneratedBlockCatalog.BLOCKS) {
            if (definition.isShape("cube")) {
                BLOCKS_BY_ID.put(definition.id(), registerCube(definition));
            }
        }

        for (BuildingBlockDefinition definition : GeneratedBlockCatalog.BLOCKS) {
            if (definition.isShape("cube") || definition.isSpecial()) {
                continue;
            }
            BLOCKS_BY_ID.put(definition.id(), registerDerived(definition));
        }

        for (BuildingBlockDefinition definition : GeneratedBlockCatalog.BLOCKS) {
            if (definition.isSpecial()) {
                BLOCKS_BY_ID.put(definition.id(), registerSpecial(definition));
            }
        }
    }

    private ModBlocks() {
    }

    public static DeferredBlock<? extends Block> require(String id) {
        return Objects.requireNonNull(BLOCKS_BY_ID.get(id), () -> "Unknown generated block id: " + id);
    }

    public static void register(IEventBus modEventBus) {
        BLOCKS.register(modEventBus);
    }

    private static DeferredBlock<? extends Block> registerDerived(BuildingBlockDefinition definition) {
        return switch (definition.shape()) {
            case "slab" -> BLOCKS.registerBlock(definition.id(), SlabBlock::new, properties -> applyProperties(properties, definition));
            case "stairs" -> BLOCKS.registerBlock(
                    definition.id(),
                    properties -> new StairBlock(require(definition.baseId()).get().defaultBlockState(), properties),
                    properties -> applyProperties(properties, definition));
            case "wall" -> BLOCKS.registerBlock(definition.id(), WallBlock::new, properties -> applyProperties(properties, definition));
            case "pane" -> BLOCKS.registerBlock(definition.id(), IronBarsBlock::new, properties -> applyProperties(properties, definition));
            case "grille" -> BLOCKS.registerBlock(definition.id(), SecurityGrilleBlock::new, properties -> applyProperties(properties, definition));
            case "slope" -> BLOCKS.registerBlock(definition.id(), SlopeBlock::new, properties -> applyProperties(properties, definition));
            case "triangle_wall" -> BLOCKS.registerBlock(definition.id(), TriangleWallBlock::new, properties -> applyProperties(properties, definition));
            default -> throw new IllegalArgumentException("Unsupported generated block shape: " + definition.shape());
        };
    }

    private static DeferredBlock<? extends Block> registerSpecial(BuildingBlockDefinition definition) {
        return switch (definition.kit()) {
            case "static" -> BLOCKS.registerBlock(definition.id(), FacingSpecialBlock::new, properties -> applySpecialProps(properties, definition));
            case "pole" -> BLOCKS.registerBlock(definition.id(), PoleBlock::new, properties -> applySpecialProps(properties, definition));
            case "framed_window" -> BLOCKS.registerBlock(definition.id(), FramedWindowBlock::new, properties -> applySpecialProps(properties, definition));
            // framed_window_slope: the flat framed window's frame+glass rotated 45deg about the
            // vertical (Y) axis in the MODEL -> a diagonal window for chamfered walls. FACING-only,
            // NO connection, so it reuses FacingSpecialBlock (collision via GeneratedSpecialShapes).
            case "framed_window_slope" -> BLOCKS.registerBlock(definition.id(), FacingSpecialBlock::new, properties -> applySpecialProps(properties, definition));
            case "prefab_window" -> BLOCKS.registerBlock(definition.id(), PrefabWindowBlock::new, properties -> applySpecialProps(properties, definition));
            default -> throw new IllegalArgumentException("Unsupported special kit: " + definition.kit());
        };
    }

    // Special blocks are partial cubes (frames/grilles/poles), so always disable
    // occlusion regardless of render type; collision=none drops collision entirely.
    private static BlockBehaviour.Properties applySpecialProps(BlockBehaviour.Properties properties, BuildingBlockDefinition definition) {
        properties = applyProperties(properties, definition).noOcclusion();
        if ("none".equals(definition.collision())) {
            properties = properties.noCollision();
        }
        return properties;
    }

    private static DeferredBlock<? extends Block> registerCube(BuildingBlockDefinition definition) {
        if (isGlassCube(definition)) {
            return BLOCKS.registerBlock(definition.id(), TransparentBlock::new, properties -> applyProperties(properties, definition));
        }
        return BLOCKS.registerSimpleBlock(definition.id(), properties -> applyProperties(properties, definition));
    }

    private static BlockBehaviour.Properties applyProperties(BlockBehaviour.Properties properties, BuildingBlockDefinition definition) {
        properties = properties
                .mapColor(resolveMapColor(definition.mapColor()))
                .strength((float) definition.hardness(), (float) definition.resistance())
                .sound(resolveSoundType(definition.sound()));
        // Any non-solid render type (cutout grilles/frames, translucent glass) must not
        // occlude neighbors, otherwise faces seen through holes/glass get culled to black.
        if (!"solid".equals(definition.renderType())) {
            properties = properties
                    .noOcclusion()
                    .isValidSpawn((state, level, pos, entityType) -> false)
                    .isRedstoneConductor((state, level, pos) -> false)
                    .isSuffocating((state, level, pos) -> false)
                    .isViewBlocking((state, level, pos) -> false);
        }
        return properties;
    }

    private static boolean isGlassCube(BuildingBlockDefinition definition) {
        return definition.isShape("cube")
                && ("glass_system".equals(definition.preset()) || "window_glass_system".equals(definition.preset()));
    }

    private static SoundType resolveSoundType(String sound) {
        return switch (sound) {
            case "glass" -> SoundType.GLASS;
            case "wood" -> SoundType.WOOD;
            case "metal" -> SoundType.METAL;
            default -> SoundType.STONE;
        };
    }

    private static MapColor resolveMapColor(String mapColor) {
        return switch (mapColor) {
            case "TERRACOTTA_WHITE" -> MapColor.TERRACOTTA_WHITE;
            case "SAND" -> MapColor.SAND;
            case "DIRT" -> MapColor.DIRT;
            case "COLOR_RED" -> MapColor.COLOR_RED;
            case "COLOR_LIGHT_BLUE" -> MapColor.COLOR_LIGHT_BLUE;
            default -> MapColor.STONE;
        };
    }
}
