package net.littlebai.mirage2004.content.block;

import javax.annotation.Nullable;

import com.mojang.serialization.MapCodec;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.util.RandomSource;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.ScheduledTickAccess;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.HorizontalDirectionalBlock;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.level.block.state.properties.DoubleBlockHalf;
import net.minecraft.world.level.block.state.properties.EnumProperty;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

import net.littlebai.mirage2004.generated.GeneratedSpecialShapes;

/**
 * The {@code prefab_window} kit (prefab balcony window, v1.md §2.2 / FRAMED_WINDOW_DESIGN.md):
 * a door-style 2-tall column. {@code FACING} + {@code HALF}(LOWER/UPPER) + {@code OPEN}
 * registered UNIFORMLY = 16 states. v1 NEVER toggles {@code OPEN} (right-click is a no-op)
 * and the multipart blockstate ignores {@code open}, so both values render the closed model;
 * {@code OPEN} is pre-wired so v2 adds opening with no state migration.
 *
 * <p>This is a custom {@link Block}, NOT a {@code DoorBlock} subclass: it has no support-block
 * requirement (a window floats in a wall opening), no redstone, no hinge. It COPIES the door
 * two-tall mechanics — place the partner above, break-either removes both, drop only from the
 * lower half — but does not inherit them. The bottom-half drop helper is copied from
 * vanilla's {@code DoublePlantBlock.preventDropFromBottomPart} (which is {@code protected
 * static} in another package, so it cannot be called).
 *
 * <p>The balcony 2×2 is two EXPLICIT pieces ({@code balcony_left} + {@code balcony_right})
 * placed side by side — not auto-connection, not an atomic multiblock. The shared centre
 * mullion is baked into the left piece (left draws its right-edge mullion; right omits its
 * left mullion) so the 2-wide pair shows one seam mullion.
 */
public class PrefabWindowBlock extends Block {
    public static final MapCodec<PrefabWindowBlock> CODEC = simpleCodec(PrefabWindowBlock::new);
    public static final EnumProperty<Direction> FACING = HorizontalDirectionalBlock.FACING;
    public static final EnumProperty<DoubleBlockHalf> HALF = BlockStateProperties.DOUBLE_BLOCK_HALF;
    public static final BooleanProperty OPEN = BlockStateProperties.OPEN;

    public PrefabWindowBlock(BlockBehaviour.Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any()
                .setValue(FACING, Direction.NORTH)
                .setValue(HALF, DoubleBlockHalf.LOWER)
                .setValue(OPEN, Boolean.FALSE));
    }

    @Override
    public MapCodec<PrefabWindowBlock> codec() {
        return CODEC;
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(FACING, HALF, OPEN);
    }

    /**
     * PLACE — need room for the UPPER cell only; NO support check (a window floats in a wall
     * opening). FACING = the player's horizontal look opposite (so the exterior plane sits
     * against the wall, matching the single-block line); HALF = LOWER; OPEN = false.
     */
    @Override
    @Nullable
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        BlockPos pos = context.getClickedPos();
        Level level = context.getLevel();
        if (pos.getY() >= level.getMaxY() || !level.getBlockState(pos.above()).canBeReplaced(context)) {
            return null;
        }
        return this.defaultBlockState()
                .setValue(FACING, context.getHorizontalDirection().getOpposite())
                .setValue(HALF, DoubleBlockHalf.LOWER)
                .setValue(OPEN, Boolean.FALSE);
    }

    /** Door pattern (DoorBlock.setPlacedBy): stamp the UPPER half one cell up. */
    @Override
    public void setPlacedBy(Level level, BlockPos pos, BlockState state, @Nullable LivingEntity by, ItemStack itemStack) {
        level.setBlock(pos.above(), state.setValue(HALF, DoubleBlockHalf.UPPER), 3);
    }

    /**
     * BREAK-BOTH — when the partner cell along the vertical axis changes and is no longer this
     * block's OTHER half, self-destruct (mirrors DoorBlock.updateShape). No support check, so
     * horizontal neighbour changes never remove the window.
     */
    @Override
    protected BlockState updateShape(BlockState state, LevelReader level, ScheduledTickAccess ticks, BlockPos pos,
            Direction direction, BlockPos neighbourPos, BlockState neighbourState, RandomSource random) {
        if (direction.getAxis().isVertical()) {
            DoubleBlockHalf half = state.getValue(HALF);
            boolean facingUp = direction == Direction.UP;
            boolean towardPartner = (half == DoubleBlockHalf.LOWER) == facingUp;
            if (towardPartner
                    && !(neighbourState.is(this) && neighbourState.getValue(HALF) != half)) {
                return Blocks.AIR.defaultBlockState();
            }
        }
        return super.updateShape(state, level, ticks, pos, direction, neighbourPos, neighbourState, random);
    }

    /**
     * DROP-ONCE — our own copy of {@code DoublePlantBlock.preventDropFromBottomPart} (it is
     * {@code protected static} in a different package, so we cannot call it). In the creative /
     * wrong-tool case, breaking the UPPER half removes the matching LOWER half with
     * {@code UPDATE_SUPPRESS_DROPS} so nothing drops there. Combined with the {@code half=lower}
     * loot condition, every survival break path yields exactly one item (or zero in creative).
     */
    @Override
    public BlockState playerWillDestroy(Level level, BlockPos pos, BlockState state, Player player) {
        if (!level.isClientSide()
                && (player.isCreative() || !player.hasCorrectToolForDrops(state, level, pos))
                && state.getValue(HALF) == DoubleBlockHalf.UPPER) {
            BlockPos below = pos.below();
            BlockState belowState = level.getBlockState(below);
            if (belowState.is(this) && belowState.getValue(HALF) == DoubleBlockHalf.LOWER) {
                // UPDATE_ALL | UPDATE_SUPPRESS_DROPS (35): remove the lower half without dropping.
                level.setBlock(below, Blocks.AIR.defaultBlockState(), 35);
                level.levelEvent(player, 2001, below, Block.getId(belowState)); // break particles
            }
        }
        return super.playerWillDestroy(level, pos, state, player);
    }

    /** v1: right-click is a no-op (the window is FIXED). v2 wires OPEN toggling here. */
    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {
        return InteractionResult.PASS;
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
}
