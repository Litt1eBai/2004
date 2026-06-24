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
import net.minecraft.world.level.block.CrossCollisionBlock;
import net.minecraft.world.level.block.IronBarsBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.level.material.FluidState;
import net.minecraft.world.level.material.Fluids;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

import net.littlebai.mirage2004.registry.ModBlockTags;

/**
 * 防盗窗 (security grille). Iron-bars-style connecting lattice (extends
 * {@link CrossCollisionBlock}, NOT {@link IronBarsBlock} — its {@code attachsTo} is
 * {@code final}) with two deliberate deviations from vanilla bars:
 *
 * <ul>
 *   <li><b>Horizontal connection</b> joins ONLY complete (full-cube) blocks and other
 *       security grilles. It never joins iron bars or any glass pane (both are
 *       {@code instanceof IronBarsBlock}), nor any glass cube
 *       ({@code #mirage2004:grille_no_connect} = {@code #minecraft:impermeable} + this
 *       mod's glass blocks).</li>
 *   <li><b>Vertical caps</b> ({@link #TOP}/{@link #BOTTOM}) auto-show notched frame stubs (two
 *       strips clearing the pane band) toward each horizontal connection when the cell above/below
 *       is not another grille — walls
 *       and open air alike, so a run frames at every end. The caps are visual; the inherited
 *       full-height (collisionHeight=16) cross collision is the real anti-intrusion barrier.</li>
 * </ul>
 */
public class SecurityGrilleBlock extends CrossCollisionBlock {
    public static final MapCodec<SecurityGrilleBlock> CODEC = simpleCodec(SecurityGrilleBlock::new);
    public static final BooleanProperty TOP = BooleanProperty.create("top");
    public static final BooleanProperty BOTTOM = BlockStateProperties.BOTTOM;

    public SecurityGrilleBlock(BlockBehaviour.Properties properties) {
        super(2.0F, 16.0F, 2.0F, 16.0F, 16.0F, properties);
        this.registerDefaultState(this.stateDefinition.any()
                .setValue(NORTH, false)
                .setValue(EAST, false)
                .setValue(SOUTH, false)
                .setValue(WEST, false)
                .setValue(TOP, false)
                .setValue(BOTTOM, false)
                .setValue(WATERLOGGED, false));
    }

    @Override
    protected MapCodec<SecurityGrilleBlock> codec() {
        return CODEC;
    }

    // Same shapes as the parent, but TOP/BOTTOM (visual caps only) are excluded from the
    // per-state shape cache so it doesn't 4x for the cap permutations.
    @Override
    protected Function<BlockState, VoxelShape> makeShapes(
            float postWidth, float postHeight, float wallWidth, float wallBottom, float wallTop) {
        VoxelShape post = Block.column(postWidth, 0.0, postHeight);
        Map<Direction, VoxelShape> arms = Shapes.rotateHorizontal(Block.boxZ(wallWidth, wallBottom, wallTop, 0.0, 8.0));
        return this.getShapeForEachState(state -> {
            VoxelShape shape = post;
            for (Map.Entry<Direction, BooleanProperty> entry : PROPERTY_BY_DIRECTION.entrySet()) {
                if (state.getValue(entry.getValue())) {
                    shape = Shapes.or(shape, arms.get(entry.getKey()));
                }
            }
            return shape;
        }, WATERLOGGED, TOP, BOTTOM);
    }

    /** Horizontal: complete cubes + other grilles; never bars/panes or glass cubes. */
    private boolean connectsTo(BlockState neighbour, BlockGetter level, BlockPos neighbourPos) {
        if (neighbour.getBlock() instanceof SecurityGrilleBlock) {
            return true;
        }
        if (neighbour.getBlock() instanceof IronBarsBlock) {
            return false; // vanilla iron bars + all glass panes (extend IronBarsBlock)
        }
        if (neighbour.is(ModBlockTags.GRILLE_NO_CONNECT)) {
            return false; // glass cubes (#minecraft:impermeable + this mod's glass blocks)
        }
        return !isExceptionForConnection(neighbour) && neighbour.isCollisionShapeFullBlock(level, neighbourPos);
    }

    /** Vertical cap at the end of a run: shown unless continued by another grille. Walls and
     *  open air are treated alike (连墙状态和下面类似), so both ends get framed. */
    private boolean capAt(BlockState neighbour) {
        return !(neighbour.getBlock() instanceof SecurityGrilleBlock);
    }

    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        BlockGetter level = context.getLevel();
        BlockPos pos = context.getClickedPos();
        BlockPos north = pos.north();
        BlockPos south = pos.south();
        BlockPos west = pos.west();
        BlockPos east = pos.east();
        BlockPos above = pos.above();
        BlockPos below = pos.below();
        FluidState fluid = level.getFluidState(pos);
        return this.defaultBlockState()
                .setValue(NORTH, connectsTo(level.getBlockState(north), level, north))
                .setValue(SOUTH, connectsTo(level.getBlockState(south), level, south))
                .setValue(WEST, connectsTo(level.getBlockState(west), level, west))
                .setValue(EAST, connectsTo(level.getBlockState(east), level, east))
                .setValue(TOP, capAt(level.getBlockState(above)))
                .setValue(BOTTOM, capAt(level.getBlockState(below)))
                .setValue(WATERLOGGED, fluid.is(Fluids.WATER));
    }

    @Override
    protected BlockState updateShape(BlockState state, LevelReader level, ScheduledTickAccess ticks, BlockPos pos,
            Direction direction, BlockPos neighbourPos, BlockState neighbourState, RandomSource random) {
        if (state.getValue(WATERLOGGED)) {
            ticks.scheduleTick(pos, Fluids.WATER, Fluids.WATER.getTickDelay(level));
        }
        if (direction.getAxis().isHorizontal()) {
            return state.setValue(PROPERTY_BY_DIRECTION.get(direction), connectsTo(neighbourState, level, neighbourPos));
        }
        if (direction == Direction.UP) {
            return state.setValue(TOP, capAt(neighbourState));
        }
        if (direction == Direction.DOWN) {
            return state.setValue(BOTTOM, capAt(neighbourState));
        }
        return state;
    }

    // Like vanilla bars: nothing occludes through the cutout, so the visual shape is empty.
    @Override
    protected VoxelShape getVisualShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return Shapes.empty();
    }

    // Cull the shared faces between touching grilles (ported from IronBarsBlock, keyed on
    // our own block instead of BlockTags.BARS).
    @Override
    protected boolean skipRendering(BlockState state, BlockState neighbourState, Direction direction) {
        if (neighbourState.getBlock() instanceof SecurityGrilleBlock) {
            if (!direction.getAxis().isHorizontal()) {
                return true;
            }
            BooleanProperty here = PROPERTY_BY_DIRECTION.get(direction);
            BooleanProperty there = PROPERTY_BY_DIRECTION.get(direction.getOpposite());
            if (here != null && there != null && state.getValue(here) && neighbourState.getValue(there)) {
                return true;
            }
        }
        return super.skipRendering(state, neighbourState, direction);
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(NORTH, EAST, WEST, SOUTH, TOP, BOTTOM, WATERLOGGED);
    }
}
