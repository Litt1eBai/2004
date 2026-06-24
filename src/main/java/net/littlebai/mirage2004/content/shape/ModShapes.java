package net.littlebai.mirage2004.content.shape;

import java.util.Map;

import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

/**
 * Central, allocation-free holder of named VoxelShapes for the mod's non-cube
 * blocks. Each base shape is authored as if {@code FACING = NORTH} (-Z) and
 * rotated to all four horizontal directions via vanilla
 * {@link Shapes#rotateHorizontal(VoxelShape)} (the same idiom vanilla
 * {@code LadderBlock}/{@code StairBlock} use). The blockstate {@code y} rotation
 * the generator emits (NORTH=0 / EAST=90 / SOUTH=180 / WEST=270) MUST stay in
 * lockstep with this NORTH-authored convention, or collision desyncs from visuals.
 *
 * <p>All dimensions are in 1/16 block (pixel) units; {@link Block#box} divides by
 * 16 internally. Sizes here are placeholders pending author sign-off.
 */
public final class ModShapes {
    private ModShapes() {
    }

    /** Vertical corner prism (triangle footprint, full height) — for a future corner block. */
    public static final Map<Direction, VoxelShape> TRIANGLE_WALL =
            Shapes.rotateHorizontal(sideTriangleBase());

    /**
     * Stepped ramp collision matching the smooth wedge (三角块): low at the front (z=0)
     * rising to full height at the back (z=16) — a "sideways stair". NORTH-authored to
     * match {@code SlopeGeometry} so visual and collision rotate in lockstep by facing.
     */
    public static final Map<Direction, VoxelShape> SLOPE_BOTTOM =
            Shapes.rotateHorizontal(rampBase());

    /** Top (ceiling) ramp = the bottom ramp rotated 180° about X (y→16-y, z→16-z) — for HALF=top. */
    public static final Map<Direction, VoxelShape> SLOPE_TOP =
            Shapes.rotateHorizontal(rampTopBase());

    private static VoxelShape sideTriangleBase() {
        return Shapes.or(
                Block.box(0.0, 0.0, 0.0, 16.0, 16.0, 4.0),
                Block.box(0.0, 0.0, 4.0, 12.0, 16.0, 8.0),
                Block.box(0.0, 0.0, 8.0, 8.0, 16.0, 12.0),
                Block.box(0.0, 0.0, 12.0, 4.0, 16.0, 16.0));
    }

    private static VoxelShape rampBase() {
        return Shapes.or(
                Block.box(0.0, 0.0, 0.0, 16.0, 4.0, 4.0),
                Block.box(0.0, 0.0, 4.0, 16.0, 8.0, 8.0),
                Block.box(0.0, 0.0, 8.0, 16.0, 12.0, 12.0),
                Block.box(0.0, 0.0, 12.0, 16.0, 16.0, 16.0));
    }

    private static VoxelShape rampTopBase() {
        return Shapes.or(
                Block.box(0.0, 12.0, 12.0, 16.0, 16.0, 16.0),
                Block.box(0.0, 8.0, 8.0, 16.0, 16.0, 12.0),
                Block.box(0.0, 4.0, 4.0, 16.0, 16.0, 8.0),
                Block.box(0.0, 0.0, 0.0, 16.0, 16.0, 4.0));
    }
}
