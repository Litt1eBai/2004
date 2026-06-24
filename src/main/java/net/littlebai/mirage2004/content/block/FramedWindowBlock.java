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
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

import net.littlebai.mirage2004.content.block.state.MirageBlockStates;
import net.littlebai.mirage2004.content.block.state.MirageBlockStates.HorizontalPosition;
import net.littlebai.mirage2004.content.block.state.MirageBlockStates.VerticalPosition;
import net.littlebai.mirage2004.generated.GeneratedSpecialShapes;

/**
 * The {@code framed_window} kit (single-block 带框窗, v1.md §2.1): a 1x1, centered
 * (frame Z7-9, glass Z7.5-8.5) frame+glass block that connects to same-id, same-facing
 * neighbours so a wall of them tiles into one window grid.
 *
 * <p>This is a port of yuushya's {@code PoleLineBlock}: {@code FACING} +
 * {@link MirageBlockStates#POS_HORIZON} (yuushya {@code LineBlock.getPositionOfFace} —
 * the horizontal axis ⟂ facing) + {@link MirageBlockStates#POS_VERTICAL} (yuushya
 * {@code PoleBlock.getPositionOfPole} — the vertical axis). 4 × 4 × 4 = 64 states. The
 * generator composes one frame model per {@code (pos_h, pos)} so junctions have no gap.
 *
 * <p>Three byte-identical variants ({@code framed_window_1/2/3}) give the builder seam
 * control: connection fuses only the SAME block id (and same facing), so alternating
 * numbers keeps a border. Fixed (no open); no support requirement; single-block loot.
 */
public class FramedWindowBlock extends Block {
    public static final MapCodec<FramedWindowBlock> CODEC = simpleCodec(FramedWindowBlock::new);
    public static final EnumProperty<Direction> FACING = HorizontalDirectionalBlock.FACING;
    public static final EnumProperty<HorizontalPosition> POS_HORIZON = MirageBlockStates.POS_HORIZON;
    public static final EnumProperty<VerticalPosition> POS_VERTICAL = MirageBlockStates.POS_VERTICAL;

    public FramedWindowBlock(BlockBehaviour.Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any()
                .setValue(FACING, Direction.NORTH)
                .setValue(POS_HORIZON, HorizontalPosition.NONE)
                .setValue(POS_VERTICAL, VerticalPosition.NONE));
    }

    @Override
    public MapCodec<FramedWindowBlock> codec() {
        return CODEC;
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(FACING, POS_HORIZON, POS_VERTICAL);
    }

    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        // Mirrors yuushya PoleLineBlock.getStateForPlacement: click on a top/bottom face ->
        // face the way the player looks; click on a side -> face that side's opposite (so the
        // frame plane sits against the wall). Then resolve both connection axes.
        Direction facing = context.getClickedFace().getAxis() == Direction.Axis.Y
                ? context.getHorizontalDirection()
                : context.getClickedFace().getOpposite();
        BlockState state = this.defaultBlockState().setValue(FACING, facing);
        return state
                .setValue(POS_HORIZON, positionOfFace(state, context.getLevel(), context.getClickedPos()))
                .setValue(POS_VERTICAL, positionOfPole(state, context.getLevel(), context.getClickedPos()));
    }

    @Override
    protected BlockState updateShape(BlockState state, LevelReader level, ScheduledTickAccess ticks, BlockPos pos,
            Direction direction, BlockPos neighbourPos, BlockState neighbourState, RandomSource random) {
        // Any neighbour change can flip a connection: recompute BOTH axes (yuushya
        // PoleLineBlock.updateShape recomputes pos_h + pos unconditionally).
        return state
                .setValue(POS_HORIZON, positionOfFace(state, level, pos))
                .setValue(POS_VERTICAL, positionOfPole(state, level, pos));
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

    /**
     * Horizontal connection on the axis ⟂ FACING (ported verbatim from yuushya
     * {@code LineBlock.getPositionOfFace}). {@code LEFT} = the EAST/RIGHT neighbour
     * connects; {@code RIGHT} = the WEST/LEFT neighbour connects; the WEST/EAST and
     * NORTH/SOUTH branches flip left/right because facing reverses the screen-left axis.
     */
    private static HorizontalPosition positionOfFace(BlockState state, LevelReader level, BlockPos pos) {
        Direction facing = state.getValue(FACING);
        switch (facing.getAxis()) {
            case X -> {
                boolean north = connects(state, level.getBlockState(pos.north()));
                boolean south = connects(state, level.getBlockState(pos.south()));
                if (north && south) {
                    return HorizontalPosition.MIDDLE;
                }
                switch (facing) {
                    case WEST -> {
                        if (north) return HorizontalPosition.LEFT;
                        if (south) return HorizontalPosition.RIGHT;
                    }
                    case EAST -> {
                        if (north) return HorizontalPosition.RIGHT;
                        if (south) return HorizontalPosition.LEFT;
                    }
                    default -> {
                    }
                }
            }
            case Z -> {
                boolean west = connects(state, level.getBlockState(pos.west()));
                boolean east = connects(state, level.getBlockState(pos.east()));
                if (west && east) {
                    return HorizontalPosition.MIDDLE;
                }
                switch (facing) {
                    case NORTH -> {
                        if (west) return HorizontalPosition.RIGHT;
                        if (east) return HorizontalPosition.LEFT;
                    }
                    case SOUTH -> {
                        if (west) return HorizontalPosition.LEFT;
                        if (east) return HorizontalPosition.RIGHT;
                    }
                    default -> {
                    }
                }
            }
            default -> {
            }
        }
        return HorizontalPosition.NONE;
    }

    /**
     * Vertical connection (ported from yuushya {@code PoleBlock.getPositionOfPole}; same as
     * {@link PoleBlock}'s {@code positionOf}). {@code BOTTOM} = only-above connects,
     * {@code TOP} = only-below connects, {@code MIDDLE} = both, {@code NONE} = neither.
     */
    private static VerticalPosition positionOfPole(BlockState state, LevelReader level, BlockPos pos) {
        boolean up = connects(state, level.getBlockState(pos.above()));
        boolean down = connects(state, level.getBlockState(pos.below()));
        if (up) {
            return down ? VerticalPosition.MIDDLE : VerticalPosition.BOTTOM;
        }
        return down ? VerticalPosition.TOP : VerticalPosition.NONE;
    }

    /** Same block id AND same facing -> connect (so framed_window_1 never fuses to _2). */
    private static boolean connects(BlockState self, BlockState neighbour) {
        return neighbour.is(self.getBlock()) && neighbour.getValue(FACING) == self.getValue(FACING);
    }
}
