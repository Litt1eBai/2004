package net.littlebai.mirage2004.client.model;

import net.minecraft.client.resources.model.UnbakedModel;
import net.minecraft.client.resources.model.geometry.UnbakedGeometry;
import net.minecraft.client.resources.model.sprite.TextureSlots;
import net.minecraft.resources.Identifier;

/**
 * Custom unbaked block model delegating geometry to {@link TriangleWallGeometry}.
 * Parents {@code minecraft:block/block} for standard block-item display transforms.
 */
public record TriangleWallUnbakedModel(TextureSlots.Data textureSlots) implements UnbakedModel {
    private static final UnbakedGeometry GEOMETRY = new TriangleWallGeometry();

    @Override
    public UnbakedGeometry geometry() {
        return GEOMETRY;
    }

    @Override
    public Identifier parent() {
        return Identifier.parse("minecraft:block/block");
    }
}
