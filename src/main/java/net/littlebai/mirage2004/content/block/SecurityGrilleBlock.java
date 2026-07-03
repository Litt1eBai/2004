package net.littlebai.mirage2004.content.block;

import com.mojang.serialization.MapCodec;

import java.util.Map;
import java.util.function.Function;

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
import net.minecraft.world.level.block.SimpleWaterloggedBlock;
import net.minecraft.world.level.block.SlabBlock;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.level.block.state.properties.EnumProperty;
import net.minecraft.world.level.material.FluidState;
import net.minecraft.world.level.material.Fluids;
import net.minecraft.world.level.pathfinder.PathComputationType;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

/**
 * Security grille as a mergeable thick panel. The grille body is always a flat panel; frame
 * properties only mark the outer border of a same-plane panel run.
 */
public class SecurityGrilleBlock extends Block implements SimpleWaterloggedBlock {
    public static final MapCodec<SecurityGrilleBlock> CODEC = simpleCodec(SecurityGrilleBlock::new);
    public static final EnumProperty<Direction> FACING = HorizontalDirectionalBlock.FACING;
    public static final BooleanProperty FRAME_TOP = BooleanProperty.create("frame_top");
    public static final BooleanProperty FRAME_BOTTOM = BooleanProperty.create("frame_bottom");
    public static final BooleanProperty FRAME_LEFT = BooleanProperty.create("frame_left");
    public static final BooleanProperty FRAME_RIGHT = BooleanProperty.create("frame_right");
    public static final BooleanProperty WATERLOGGED = BlockStateProperties.WATERLOGGED;

    private final Function<BlockState, VoxelShape> shapes;

    public SecurityGrilleBlock(BlockBehaviour.Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any()
                .setValue(FACING, Direction.NORTH)
                .setValue(FRAME_TOP, true)
                .setValue(FRAME_BOTTOM, true)
                .setValue(FRAME_LEFT, true)
                .setValue(FRAME_RIGHT, true)
                .setValue(WATERLOGGED, false));
        this.shapes = makeShapes();
    }

    @Override
    protected MapCodec<SecurityGrilleBlock> codec() {
        return CODEC;
    }

    private Function<BlockState, VoxelShape> makeShapes() {
        Map<Direction, VoxelShape> panels = Shapes.rotateHorizontal(Block.box(0.0, 0.0, 7.0, 16.0, 16.0, 9.0));
        Map<Direction, VoxelShape> topFrames = Shapes.rotateHorizontal(Block.box(0.0, 14.0, 4.0, 16.0, 16.0, 9.0));
        Map<Direction, VoxelShape> bottomFrames = Shapes.rotateHorizontal(Block.box(0.0, 0.0, 4.0, 16.0, 2.0, 9.0));
        Map<Direction, VoxelShape> leftFrames = Shapes.rotateHorizontal(Block.box(0.0, 0.0, 4.0, 2.0, 16.0, 9.0));
        Map<Direction, VoxelShape> rightFrames = Shapes.rotateHorizontal(Block.box(14.0, 0.0, 4.0, 16.0, 16.0, 9.0));
        return this.getShapeForEachState(state -> {
            Direction facing = state.getValue(FACING);
            VoxelShape shape = panels.get(facing);
            if (state.getValue(FRAME_TOP)) {
                shape = Shapes.or(shape, topFrames.get(facing));
            }
            if (state.getValue(FRAME_BOTTOM)) {
                shape = Shapes.or(shape, bottomFrames.get(facing));
            }
            if (state.getValue(FRAME_LEFT)) {
                shape = Shapes.or(shape, leftFrames.get(facing));
            }
            if (state.getValue(FRAME_RIGHT)) {
                shape = Shapes.or(shape, rightFrames.get(facing));
            }
            return shape.optimize();
        }, WATERLOGGED);
    }

    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        Direction facing = placementFacing(context);
        BlockState state = this.defaultBlockState()
                .setValue(FACING, facing)
                .setValue(WATERLOGGED, context.getLevel().getFluidState(context.getClickedPos()).is(Fluids.WATER));
        return applyFrameStates(state, context.getLevel(), context.getClickedPos());
    }

    private static Direction placementFacing(BlockPlaceContext context) {
        Direction clickedFace = context.getClickedFace();
        BlockState clickedNeighbour = context.getLevel().getBlockState(context.getClickedPos().relative(clickedFace.getOpposite()));
        if (clickedNeighbour.getBlock() instanceof SecurityGrilleBlock) {
            return clickedNeighbour.getValue(FACING);
        }
        if (clickedFace.getAxis().isHorizontal()) {
            return clickedFace.getOpposite();
        }
        return context.getHorizontalDirection().getOpposite();
    }

    @Override
    protected BlockState updateShape(BlockState state, LevelReader level, ScheduledTickAccess ticks, BlockPos pos,
            Direction direction, BlockPos neighbourPos, BlockState neighbourState, RandomSource random) {
        if (state.getValue(WATERLOGGED)) {
            ticks.scheduleTick(pos, Fluids.WATER, Fluids.WATER.getTickDelay(level));
        }
        if (affectsFrames(direction, state.getValue(FACING))) {
            return applyFrameStates(state, level, pos);
        }
        return state;
    }

    private static boolean affectsFrames(Direction direction, Direction facing) {
        return direction == Direction.UP
                || direction == Direction.DOWN
                || direction == facing
                || direction == leftOf(facing)
                || direction == rightOf(facing);
    }

    private static BlockState applyFrameStates(BlockState state, BlockGetter level, BlockPos pos) {
        Direction facing = state.getValue(FACING);
        Direction left = leftOf(facing);
        Direction right = rightOf(facing);
        // Frames only exist when mounted in front; an edge seals only where an adjacent grille
        // (run merge), full block, slab, or stairs already closes the border. Every input here is a
        // DIRECT neighbour of pos, so vanilla neighbour-shape updates keep the state consistent (no
        // diagonal dependency on a neighbour's own wall, which the old sameAttachedPanel could not).
        boolean mounted = mountedInFront(level, pos, facing);
        return state
                .setValue(FRAME_TOP, mounted && !sealsEdge(level, pos.above()))
                .setValue(FRAME_BOTTOM, mounted && !sealsEdge(level, pos.below()))
                .setValue(FRAME_LEFT, mounted && !sealsEdge(level, pos.relative(left)))
                .setValue(FRAME_RIGHT, mounted && !sealsEdge(level, pos.relative(right)));
    }

    /** Mounted on anything to hang against: any block in front except air and other grilles. */
    private static boolean mountedInFront(BlockGetter level, BlockPos pos, Direction facing) {
        BlockState front = level.getBlockState(pos.relative(facing));
        return !front.isAir() && !(front.getBlock() instanceof SecurityGrilleBlock);
    }

    /** An edge drops its frame where an adjacent grille, full block, slab, or stairs closes it. */
    private static boolean sealsEdge(BlockGetter level, BlockPos neighbourPos) {
        BlockState neighbour = level.getBlockState(neighbourPos);
        return neighbour.getBlock() instanceof SecurityGrilleBlock
                || neighbour.isCollisionShapeFullBlock(level, neighbourPos)
                || neighbour.getBlock() instanceof SlabBlock
                || neighbour.getBlock() instanceof StairBlock;
    }

    private static Direction leftOf(Direction facing) {
        return facing.getCounterClockWise();
    }

    private static Direction rightOf(Direction facing) {
        return facing.getClockWise();
    }

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return this.shapes.apply(state);
    }

    @Override
    protected VoxelShape getCollisionShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return this.shapes.apply(state);
    }

    @Override
    protected VoxelShape getVisualShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return Shapes.empty();
    }

    @Override
    protected FluidState getFluidState(BlockState state) {
        return state.getValue(WATERLOGGED) ? Fluids.WATER.getSource(false) : super.getFluidState(state);
    }

    @Override
    protected boolean propagatesSkylightDown(BlockState state) {
        return !state.getValue(WATERLOGGED);
    }

    @Override
    protected boolean isPathfindable(BlockState state, PathComputationType type) {
        return false;
    }

    @Override
    protected BlockState rotate(BlockState state, Rotation rotation) {
        return state.setValue(FACING, rotation.rotate(state.getValue(FACING)));
    }

    @Override
    protected BlockState mirror(BlockState state, Mirror mirror) {
        return state.rotate(mirror.getRotation(state.getValue(FACING)));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(FACING, FRAME_TOP, FRAME_BOTTOM, FRAME_LEFT, FRAME_RIGHT, WATERLOGGED);
    }
}
