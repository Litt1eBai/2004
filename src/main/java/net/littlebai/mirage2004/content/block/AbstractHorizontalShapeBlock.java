package net.littlebai.mirage2004.content.block;

import java.util.Map;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
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

/**
 * Base for free-standing horizontally-oriented shape blocks (exterior wall,
 * side triangle, quarter brick). Carries {@code HORIZONTAL_FACING}, faces the
 * placer, and resolves its outline/collision from a per-subclass
 * {@code NORTH}-authored {@link net.littlebai.mirage2004.content.shape.ModShapes}
 * map. Subclasses provide the shape map and a {@code codec()} (required because
 * {@code BlockBehaviour} declares it abstract).
 */
public abstract class AbstractHorizontalShapeBlock extends Block {
    public static final EnumProperty<Direction> FACING = HorizontalDirectionalBlock.FACING;

    protected AbstractHorizontalShapeBlock(BlockBehaviour.Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(FACING, Direction.NORTH));
    }

    /** The NORTH-authored, rotateHorizontal-expanded shape map for this block. */
    protected abstract Map<Direction, VoxelShape> shapes();

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return this.shapes().get(state.getValue(FACING));
    }

    // Partial solid (like StairBlock/SlabBlock): occlude light by the actual shape, not a
    // full cube, so neighbours/own faces in the empty region aren't over-darkened.
    @Override
    protected boolean useShapeForLightOcclusion(BlockState state) {
        return true;
    }

    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        return this.defaultBlockState().setValue(FACING, context.getHorizontalDirection().getOpposite());
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
        builder.add(FACING);
    }
}
