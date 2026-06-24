package net.littlebai.mirage2004.content.spec;

import java.util.List;

public record MaterialFamilySpec(
        String id,
        String preset,
        String zhName,
        String enName,
        String category,
        String renderType,
        String baseTexture,
        List<String> commonShapes,
        List<String> specialShapes,
        List<String> colors,
        BlockPropertySpec blockProps) {
}
