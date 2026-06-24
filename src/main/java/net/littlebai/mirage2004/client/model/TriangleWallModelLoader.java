package net.littlebai.mirage2004.client.model;

import com.google.gson.JsonDeserializationContext;
import com.google.gson.JsonObject;

import net.minecraft.client.resources.model.sprite.TextureSlots;
import net.neoforged.neoforge.client.model.UnbakedModelLoader;

/**
 * Loader for {@code {"loader": "mirage2004:triangle_wall", "textures": {"all": "..."}}}.
 * Registered via {@code ModelEvent.RegisterLoaders}.
 */
public final class TriangleWallModelLoader implements UnbakedModelLoader<TriangleWallUnbakedModel> {
    public static final TriangleWallModelLoader INSTANCE = new TriangleWallModelLoader();

    private TriangleWallModelLoader() {
    }

    @Override
    public TriangleWallUnbakedModel read(JsonObject json, JsonDeserializationContext context) {
        TextureSlots.Data slots = json.has("textures")
                ? TextureSlots.parseTextureMap(json.getAsJsonObject("textures"))
                : TextureSlots.Data.EMPTY;
        return new TriangleWallUnbakedModel(slots);
    }
}
