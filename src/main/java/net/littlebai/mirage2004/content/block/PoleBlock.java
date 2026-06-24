package net.littlebai.mirage2004.content.block;

import com.mojang.serialization.MapCodec;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.util.RandomSource;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.ScheduledTickAccess;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.HorizontalDirectionalBlock;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.EnumProperty;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;

import net.minecraft.world.phys.shapes.Shapes;

import net.littlebai.mirage2004.content.block.state.MirageBlockStates;
import net.littlebai.mirage2004.content.block.state.MirageBlockStates.VerticalPosition;
import net.littlebai.mirage2004.generated.GeneratedSpecialShapes;

/**
 * The {@code pole} kit (ported from yuushya): a vertically-connecting post that
 * auto-selects a top/middle/bottom/none model from same-block, same-facing
 * neighbours above and below. Neighbour reflow is automatic — a vertical neighbour
 * change fires this block's {@link #updateShape} for that direction.
 */
public class PoleBlock extends Block {
    public static final MapCodec<PoleBlock> CODEC = simpleCodec(PoleBlock::new);
    public static final EnumProperty<Direction> FACING = HorizontalDirectionalBlock.FACING;
    public static final EnumProperty<VerticalPosition> POS = MirageBlockStates.POS_VERTICAL;

    public PoleBlock(BlockBehaviour.Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(FACING, Direction.NORTH).setValue(POS, VerticalPosition.NONE));
    }

    @Override
    public MapCodec<PoleBlock> codec() {
        return CODEC;
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(FACING, POS);
    }

    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        Direction facing = context.getClickedFace().getAxis() == Direction.Axis.Y
                ? context.getHorizontalDirection()
                : context.getClickedFace().getOpposite();
        BlockState state = this.defaultBlockState().setValue(FACING, facing);
        return state.setValue(POS, positionOf(state, context.getLevel(), context.getClickedPos()));
    }

    @Override
    protected BlockState updateShape(BlockState state, LevelReader level, ScheduledTickAccess ticks, BlockPos pos,
            Direction direction, BlockPos neighbourPos, BlockState neighbourState, RandomSource random) {
        if (direction.getAxis().isVertical()) {
            return state.setValue(POS, positionOf(state, level, pos));
        }
        return super.updateShape(state, level, ticks, pos, direction, neighbourPos, neighbourState, random);
    }

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return GeneratedSpecialShapes.get(this, state.getValue(FACING), Shapes.block());
    }

    @Override
    protected BlockState rotate(BlockState state, Rotation rotation) {
        return state.setValue(FACING, rotation.rotate(state.getValue(FACING)));
    }

    @Override
    protected BlockState mirror(BlockState state, Mirror mirror) {
        return state.rotate(mirror.getRotation(state.getValue(FACING)));
    }

    private static VerticalPosition positionOf(BlockState state, LevelReader level, BlockPos pos) {
        boolean up = connects(state, level.getBlockState(pos.above()));
        boolean down = connects(state, level.getBlockState(pos.below()));
        if (up) {
            return down ? VerticalPosition.MIDDLE : VerticalPosition.BOTTOM;
        }
        return down ? VerticalPosition.TOP : VerticalPosition.NONE;
    }

    private static boolean connects(BlockState self, BlockState neighbour) {
        return neighbour.is(self.getBlock()) && neighbour.getValue(FACING) == self.getValue(FACING);
    }
}
