package net.littlebai.mirage2004.content.block;

import java.util.Map;

import com.mojang.serialization.MapCodec;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.EnumProperty;
import net.minecraft.world.level.block.state.properties.Half;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;

import net.littlebai.mirage2004.content.shape.ModShapes;

/**
 * Corner ramp wedge. Like {@code StairBlock}, it carries a {@link Half} (top/bottom)
 * so it can be placed on the floor or inverted on the ceiling, chosen by where the
 * player clicks. Visual is the smooth {@code mirage2004:slope} custom geometry; the
 * blockstate supplies facing (y) and half (x=180 for top) rotations.
 */
public class SlopeBlock extends AbstractHorizontalShapeBlock {
    public static final MapCodec<SlopeBlock> CODEC = simpleCodec(SlopeBlock::new);
    public static final EnumProperty<Half> HALF = BlockStateProperties.HALF;

    public SlopeBlock(BlockBehaviour.Properties properties) {
        super(properties);
        this.registerDefaultState(this.defaultBlockState().setValue(HALF, Half.BOTTOM));
    }

    @Override
    public MapCodec<SlopeBlock> codec() {
        return CODEC;
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(FACING, HALF);
    }

    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        Direction clicked = context.getClickedFace();
        Half half = clicked != Direction.DOWN
                && (clicked == Direction.UP || !(context.getClickLocation().y - context.getClickedPos().getY() > 0.5))
                ? Half.BOTTOM
                : Half.TOP;
        return this.defaultBlockState()
                .setValue(FACING, context.getHorizontalDirection().getOpposite())
                .setValue(HALF, half);
    }

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        Map<Direction, VoxelShape> map = state.getValue(HALF) == Half.TOP
                ? ModShapes.SLOPE_TOP
                : ModShapes.SLOPE_BOTTOM;
        return map.get(state.getValue(FACING));
    }

    @Override
    protected Map<Direction, VoxelShape> shapes() {
        // Unused (getShape above selects by HALF); required by the base class.
        return ModShapes.SLOPE_BOTTOM;
    }
}
