package net.littlebai.mirage2004.client.model;

import net.minecraft.client.resources.model.UnbakedModel;
import net.minecraft.client.resources.model.geometry.UnbakedGeometry;
import net.minecraft.client.resources.model.sprite.TextureSlots;
import net.minecraft.resources.Identifier;

/**
 * Custom unbaked block model that delegates geometry to {@link SlopeGeometry}.
 * The record accessor {@code textureSlots()} satisfies {@link UnbakedModel}; the
 * texture is supplied per-block from the model JSON's {@code textures} block.
 * Parents {@code minecraft:block/block} to inherit the standard block-item display
 * transforms (so it renders as a properly-sized 3D block in hand/inventory).
 */
public record SlopeUnbakedModel(TextureSlots.Data textureSlots) implements UnbakedModel {
    private static final UnbakedGeometry GEOMETRY = new SlopeGeometry();

    @Override
    public UnbakedGeometry geometry() {
        return GEOMETRY;
    }

    @Override
    public Identifier parent() {
        return Identifier.parse("minecraft:block/block");
    }
}
