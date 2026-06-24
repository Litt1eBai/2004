package net.littlebai.mirage2004.content.block;

import java.util.Map;

import com.mojang.serialization.MapCodec;

import net.minecraft.core.Direction;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.phys.shapes.VoxelShape;

import net.littlebai.mirage2004.content.shape.ModShapes;

/**
 * Vertical corner-cut wall (三角墙): a full-height triangular prism with a vertical
 * diagonal face. Facing-only (top/bottom symmetric, no HALF). Visual is the
 * {@code mirage2004:triangle_wall} custom geometry; collision is the vertical triangle
 * prism {@link ModShapes#TRIANGLE_WALL}.
 */
public class TriangleWallBlock extends AbstractHorizontalShapeBlock {
    public static final MapCodec<TriangleWallBlock> CODEC = simpleCodec(TriangleWallBlock::new);

    public TriangleWallBlock(BlockBehaviour.Properties properties) {
        super(properties);
    }

    @Override
    public MapCodec<TriangleWallBlock> codec() {
        return CODEC;
    }

    @Override
    protected Map<Direction, VoxelShape> shapes() {
        return ModShapes.TRIANGLE_WALL;
    }
}
