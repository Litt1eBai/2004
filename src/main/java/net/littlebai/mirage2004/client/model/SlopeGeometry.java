package net.littlebai.mirage2004.client.model;

import com.mojang.blaze3d.platform.Transparency;

import org.joml.Matrix4fc;
import org.joml.Vector3f;
import org.joml.Vector3fc;

import net.minecraft.client.model.geom.builders.UVPair;
import net.minecraft.client.renderer.block.dispatch.ModelState;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.client.resources.model.ModelBaker;
import net.minecraft.client.resources.model.ModelDebugName;
import net.minecraft.client.resources.model.geometry.BakedQuad;
import net.minecraft.client.resources.model.geometry.QuadCollection;
import net.minecraft.client.resources.model.geometry.UnbakedGeometry;
import net.minecraft.client.resources.model.sprite.Material;
import net.minecraft.client.resources.model.sprite.TextureSlots;
import net.minecraft.core.Direction;
import net.neoforged.neoforge.client.model.quad.BakedColors;
import net.neoforged.neoforge.client.model.quad.BakedNormals;

/**
 * Smooth right-triangular-prism (wedge) geometry, hand-built as {@link BakedQuad}s
 * so it renders through the exact vanilla pipeline (AO/light/cull) — unlike OBJ.
 * NORTH-authored: right angle at x=0,y=0; hypotenuse from (0,16) top-back to (16,0)
 * bottom-front; extruded full depth along Z. Triangle side faces are degenerate
 * quads (4th vertex repeats the 3rd). The blockstate y-rotation arrives via
 * {@link ModelState#transformation()} and is applied to every vertex here.
 *
 * <p>TODO(render): lighting/AO on the sloped face is not perfect next to neighbours
 * (the slope is a non-axis-aligned quad, which vanilla's AO engine doesn't handle
 * cleanly). Acceptable for now; revisit (per-quad AO tuning, or flat-light the slope).
 */
public final class SlopeGeometry implements UnbakedGeometry {
    private static final String SLOT_ALL = "all";
    private static final String SLOT_SLOPE = "slope";
    private final Vector3fc center = new Vector3f(0.5F, 0.5F, 0.5F);

    @Override
    public QuadCollection bake(TextureSlots textures, ModelBaker baker, ModelState state, ModelDebugName name) {
        // Floor / back wall / triangle sides use the base ("all") texture; the sloped
        // hypotenuse uses its own ("slope") texture so a grid material can be swapped for
        // horizontal courses that read cleanly as ramp treads on the slant. The generator
        // always emits both slots ("slope" defaults to the base texture).
        Material.Baked baseMaterial = baker.materials().resolveSlot(textures, SLOT_ALL, name);
        TextureAtlasSprite baseSprite = baseMaterial.sprite();
        BakedQuad.MaterialInfo baseInfo = materialInfo(baseMaterial);

        Material.Baked slopeMaterial = baker.materials().resolveSlot(textures, SLOT_SLOPE, name);
        TextureAtlasSprite slopeSprite = slopeMaterial.sprite();
        BakedQuad.MaterialInfo slopeInfo = materialInfo(slopeMaterial);

        Matrix4fc matrix = state.transformation().getMatrix();

        QuadCollection.Builder builder = new QuadCollection.Builder();

        // Ramp authored for FACING=north (blockstate y=0): extruded along X (full width), tall
        // edge at z=16 (SOUTH/back), slope rising front(z=0)→back(z=16). The blockstate rotates
        // the whole wedge (facing = y; half=top adds x:180). The base tile texture is DIRECTIONAL
        // (grout on each tile's right+bottom edge), so the axis-aligned faces are UV-LOCKED: their
        // UVs are recomputed from each vertex's WORLD position after the rotation, so the grid stays
        // world-oriented and tiles seamlessly with normal cubes for every facing AND the flipped
        // (top) variant — model-space UVs would otherwise reverse the grid when x:180 flips it.
        boolean inverted = rotate(state, Direction.UP) == Direction.DOWN;

        // Floor (model DOWN) and back wall (model SOUTH, z=16) — uvlocked full squares.
        addLockedQuad(builder, state, matrix, baseSprite, baseInfo, Direction.DOWN,
                v(0, 0, 0), v(16, 0, 0), v(16, 0, 16), v(0, 0, 16));
        addLockedQuad(builder, state, matrix, baseSprite, baseInfo, Direction.SOUTH,
                v(16, 0, 16), v(16, 16, 16), v(0, 16, 16), v(0, 0, 16));

        // Left/right triangle sides (model WEST/EAST) — uvlocked, diagonally clipped squares.
        addLockedTri(builder, state, matrix, baseSprite, baseInfo, Direction.WEST,
                v(0, 0, 0), v(0, 0, 16), v(0, 16, 16));
        addLockedTri(builder, state, matrix, baseSprite, baseInfo, Direction.EAST,
                v(16, 0, 16), v(16, 0, 0), v(16, 16, 16));

        // Slope (inclined hypotenuse, 16 x 16*sqrt2~22.6): NON-axis face, so it keeps a custom
        // mapping (not uvlock) — the slope texture's WIDTH (u) runs along the climb and its HEIGHT
        // (v) across the block width, so a ~23px-wide texture shows undistorted tiles. When inverted
        // (top half) the U is flipped to counter the x:180 so the directional grid keeps orientation.
        float[] s0, s1, s2, s3;
        if (inverted) {
            s0 = uv(0, 0); s1 = uv(0, 16); s2 = uv(16, 16); s3 = uv(16, 0);
        } else {
            s0 = uv(16, 0); s1 = uv(16, 16); s2 = uv(0, 16); s3 = uv(0, 0);
        }
        builder.addUnculledFace(quad(slopeSprite, slopeInfo, matrix, Direction.UP,
                v(0, 16, 16), v(16, 16, 16), v(16, 0, 0), v(0, 0, 0),
                s0, s1, s2, s3));

        return builder.build();
    }

    /** Vanilla per-vertex default UV for an axis-aligned face, from a WORLD position (0..16). */
    private static float[] worldUv(Direction worldDir, Vector3fc wp) {
        float x = wp.x() * 16.0F, y = wp.y() * 16.0F, z = wp.z() * 16.0F;
        return switch (worldDir) {
            case DOWN -> new float[] {x, 16.0F - z};
            case UP -> new float[] {x, z};
            case NORTH -> new float[] {16.0F - x, 16.0F - y};
            case SOUTH -> new float[] {x, 16.0F - y};
            case WEST -> new float[] {z, 16.0F - y};
            case EAST -> new float[] {16.0F - z, 16.0F - y};
        };
    }

    /** A uvlocked quad: positions are transformed to world space, UVs recomputed from them. */
    private void addLockedQuad(QuadCollection.Builder builder, ModelState state, Matrix4fc matrix,
            TextureAtlasSprite sprite, BakedQuad.MaterialInfo info, Direction modelDir,
            float[] p0, float[] p1, float[] p2, float[] p3) {
        Direction worldDir = rotate(state, modelDir);
        Vector3fc q0 = pos(p0, matrix), q1 = pos(p1, matrix), q2 = pos(p2, matrix), q3 = pos(p3, matrix);
        builder.addCulledFace(worldDir, new BakedQuad(q0, q1, q2, q3,
                packUv(sprite, worldUv(worldDir, q0)), packUv(sprite, worldUv(worldDir, q1)),
                packUv(sprite, worldUv(worldDir, q2)), packUv(sprite, worldUv(worldDir, q3)),
                worldDir, info,
                BakedNormals.of(BakedNormals.computeQuadNormal(q0, q1, q2, q3)), BakedColors.DEFAULT));
    }

    /** A uvlocked triangle (degenerate quad). */
    private void addLockedTri(QuadCollection.Builder builder, ModelState state, Matrix4fc matrix,
            TextureAtlasSprite sprite, BakedQuad.MaterialInfo info, Direction modelDir,
            float[] p0, float[] p1, float[] p2) {
        Direction worldDir = rotate(state, modelDir);
        Vector3fc q0 = pos(p0, matrix), q1 = pos(p1, matrix), q2 = pos(p2, matrix);
        builder.addCulledFace(worldDir, new BakedQuad(q0, q1, q2, q2,
                packUv(sprite, worldUv(worldDir, q0)), packUv(sprite, worldUv(worldDir, q1)),
                packUv(sprite, worldUv(worldDir, q2)), packUv(sprite, worldUv(worldDir, q2)),
                worldDir, info,
                BakedNormals.of(BakedNormals.computeQuadNormal(q0, q1, q2, q2)), BakedColors.DEFAULT));
    }

    private static BakedQuad.MaterialInfo materialInfo(Material.Baked material) {
        Transparency transparency = material.forceTranslucent()
                ? Transparency.TRANSLUCENT
                : material.sprite().contents().computeTransparency(0.0F, 0.0F, 1.0F, 1.0F);
        return BakedQuad.MaterialInfo.of(material, transparency, -1, true, 0, true);
    }

    private static Direction rotate(ModelState state, Direction dir) {
        return Direction.rotate(state.transformation().getMatrix(), dir);
    }

    private static float[] v(float x, float y, float z) {
        return new float[] {x, y, z};
    }

    private static float[] uv(float u, float vv) {
        return new float[] {u, vv};
    }

    private BakedQuad quad(TextureAtlasSprite sprite, BakedQuad.MaterialInfo info, Matrix4fc matrix, Direction dir,
            float[] p0, float[] p1, float[] p2, float[] p3, float[] uv0, float[] uv1, float[] uv2, float[] uv3) {
        Vector3fc q0 = pos(p0, matrix);
        Vector3fc q1 = pos(p1, matrix);
        Vector3fc q2 = pos(p2, matrix);
        Vector3fc q3 = pos(p3, matrix);
        return new BakedQuad(
                q0, q1, q2, q3,
                packUv(sprite, uv0), packUv(sprite, uv1), packUv(sprite, uv2), packUv(sprite, uv3),
                dir, info,
                BakedNormals.of(BakedNormals.computeQuadNormal(q0, q1, q2, q3)),
                BakedColors.DEFAULT);
    }

    private BakedQuad tri(TextureAtlasSprite sprite, BakedQuad.MaterialInfo info, Matrix4fc matrix, Direction dir,
            float[] p0, float[] p1, float[] p2, float[] uv0, float[] uv1, float[] uv2) {
        // Triangle = degenerate quad: repeat the last vertex.
        Vector3fc q0 = pos(p0, matrix);
        Vector3fc q1 = pos(p1, matrix);
        Vector3fc q2 = pos(p2, matrix);
        return new BakedQuad(
                q0, q1, q2, q2,
                packUv(sprite, uv0), packUv(sprite, uv1), packUv(sprite, uv2), packUv(sprite, uv2),
                dir, info,
                BakedNormals.of(BakedNormals.computeQuadNormal(q0, q1, q2, q2)),
                BakedColors.DEFAULT);
    }

    private Vector3fc pos(float[] p, Matrix4fc matrix) {
        Vector3f vec = new Vector3f(p[0] / 16.0F, p[1] / 16.0F, p[2] / 16.0F);
        vec.sub(center);
        matrix.transformPosition(vec);
        vec.add(center);
        return vec;
    }

    private static long packUv(TextureAtlasSprite sprite, float[] uv) {
        // sprite.getU/getV take a 0..1 offset (vanilla feeds uvPixels/16), so normalize.
        return UVPair.pack(sprite.getU(uv[0] / 16.0F), sprite.getV(uv[1] / 16.0F));
    }
}
