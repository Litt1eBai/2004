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
 * Vertical corner-cut wall: a full-height right-triangular prism. NORTH-authored with
 * the right angle at x=0,z=0; legs along the front wall (z=0) and left wall (x=0); the
 * vertical diagonal face runs from (x=16,z=0) to (x=0,z=16). Top/bottom are triangles
 * (degenerate quads). Renders through the vanilla pipeline (proper BakedNormals).
 *
 * <p>The axis-aligned faces are UV-locked (UVs recomputed from each vertex's world
 * position) so the directional tile grid stays world-oriented and tiles seamlessly with
 * cubes for every facing. The vertical diagonal face uses a separate ("slope") texture so
 * a ~23px-wide tile covers the 16*sqrt(2)~22.6 diagonal without stretching — mirrors
 * {@link SlopeGeometry}.
 *
 * <p>TODO(render): like {@link SlopeGeometry}, the non-axis-aligned diagonal face's AO
 * isn't perfect next to neighbours; acceptable for now.
 */
public final class TriangleWallGeometry implements UnbakedGeometry {
    private static final String SLOT_ALL = "all";
    private static final String SLOT_SLOPE = "slope";
    private final Vector3fc center = new Vector3f(0.5F, 0.5F, 0.5F);

    @Override
    public QuadCollection bake(TextureSlots textures, ModelBaker baker, ModelState state, ModelDebugName name) {
        Material.Baked baseMaterial = baker.materials().resolveSlot(textures, SLOT_ALL, name);
        TextureAtlasSprite baseSprite = baseMaterial.sprite();
        BakedQuad.MaterialInfo baseInfo = materialInfo(baseMaterial);

        Material.Baked slopeMaterial = baker.materials().resolveSlot(textures, SLOT_SLOPE, name);
        TextureAtlasSprite slopeSprite = slopeMaterial.sprite();
        BakedQuad.MaterialInfo slopeInfo = materialInfo(slopeMaterial);

        Matrix4fc matrix = state.transformation().getMatrix();

        QuadCollection.Builder builder = new QuadCollection.Builder();

        // Axis-aligned faces — UV-locked (UVs from world position) so the directional grid stays
        // world-oriented and aligns with cubes across all four facings.
        // Front wall (model NORTH, z=0) and left wall (model WEST, x=0).
        addLockedQuad(builder, state, matrix, baseSprite, baseInfo, Direction.NORTH,
                v(0, 0, 0), v(0, 16, 0), v(16, 16, 0), v(16, 0, 0));
        addLockedQuad(builder, state, matrix, baseSprite, baseInfo, Direction.WEST,
                v(0, 0, 0), v(0, 0, 16), v(0, 16, 16), v(0, 16, 0));
        // Top (model UP) and bottom (model DOWN) triangles.
        addLockedTri(builder, state, matrix, baseSprite, baseInfo, Direction.UP,
                v(0, 16, 0), v(0, 16, 16), v(16, 16, 0));
        addLockedTri(builder, state, matrix, baseSprite, baseInfo, Direction.DOWN,
                v(0, 0, 0), v(16, 0, 0), v(0, 0, 16));

        // Vertical diagonal face from (x16,z0) to (x0,z16): NON-axis face, so it keeps a custom
        // mapping — the "slope" texture's WIDTH (u) runs ALONG the 16*sqrt2~22.6 diagonal and its
        // HEIGHT (v) down the 16 wall height, so a ~23px-wide texture shows undistorted tiles. No cull.
        builder.addUnculledFace(quad(slopeSprite, slopeInfo, matrix, Direction.SOUTH,
                v(16, 0, 0), v(16, 16, 0), v(0, 16, 16), v(0, 0, 16),
                uv(0, 16), uv(0, 0), uv(16, 0), uv(16, 16)));

        return builder.build();
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

    private static BakedQuad.MaterialInfo materialInfo(Material.Baked material) {
        Transparency transparency = material.forceTranslucent()
                ? Transparency.TRANSLUCENT
                : material.sprite().contents().computeTransparency(0.0F, 0.0F, 1.0F, 1.0F);
        return BakedQuad.MaterialInfo.of(material, transparency, -1, true, 0, true);
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

    private BakedQuad quad(TextureAtlasSprite sprite, BakedQuad.MaterialInfo info, Matrix4fc matrix, Direction dir,
            float[] p0, float[] p1, float[] p2, float[] p3, float[] uv0, float[] uv1, float[] uv2, float[] uv3) {
        Vector3fc q0 = pos(p0, matrix);
        Vector3fc q1 = pos(p1, matrix);
        Vector3fc q2 = pos(p2, matrix);
        Vector3fc q3 = pos(p3, matrix);
        return new BakedQuad(q0, q1, q2, q3,
                packUv(sprite, uv0), packUv(sprite, uv1), packUv(sprite, uv2), packUv(sprite, uv3),
                dir, info,
                BakedNormals.of(BakedNormals.computeQuadNormal(q0, q1, q2, q3)),
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
        return UVPair.pack(sprite.getU(uv[0] / 16.0F), sprite.getV(uv[1] / 16.0F));
    }
}
