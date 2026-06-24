package net.littlebai.mirage2004.content.block;

import java.util.Map;

import com.mojang.serialization.MapCodec;

import net.minecraft.core.Direction;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.phys.shapes.VoxelShape;

import net.littlebai.mirage2004.content.shape.ModShapes;

/** Thin vertical facing panel mounted on the block's facing side. */
public class ExteriorWallBlock extends AbstractHorizontalShapeBlock {
    public static final MapCodec<ExteriorWallBlock> CODEC = simpleCodec(ExteriorWallBlock::new);

    public ExteriorWallBlock(BlockBehaviour.Properties properties) {
        super(properties);
    }

    @Override
    public MapCodec<ExteriorWallBlock> codec() {
        return CODEC;
    }

    @Override
    protected Map<Direction, VoxelShape> shapes() {
        return ModShapes.EXTERIOR_WALL;
    }
}
