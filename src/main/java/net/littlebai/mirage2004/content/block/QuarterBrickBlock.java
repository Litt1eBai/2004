package net.littlebai.mirage2004.content.block;

import java.util.Map;

import com.mojang.serialization.MapCodec;

import net.minecraft.core.Direction;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.phys.shapes.VoxelShape;

import net.littlebai.mirage2004.content.shape.ModShapes;

/** Low curb block (1/4 brick), for road edges / 马路牙子. */
public class QuarterBrickBlock extends AbstractHorizontalShapeBlock {
    public static final MapCodec<QuarterBrickBlock> CODEC = simpleCodec(QuarterBrickBlock::new);

    public QuarterBrickBlock(BlockBehaviour.Properties properties) {
        super(properties);
    }

    @Override
    public MapCodec<QuarterBrickBlock> codec() {
        return CODEC;
    }

    @Override
    protected Map<Direction, VoxelShape> shapes() {
        return ModShapes.QUARTER_BRICK;
    }
}
