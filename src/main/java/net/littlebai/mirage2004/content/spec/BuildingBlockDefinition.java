package net.littlebai.mirage2004.content.spec;

public record BuildingBlockDefinition(
        String id,
        String baseId,
        String familyId,
        String preset,
        String colorId,
        String shape,
        String zhName,
        String enName,
        String category,
        String renderType,
        String texturePath,
        String sound,
        double hardness,
        double resistance,
        String mapColor,
        String kit,
        String modelPrefix,
        String collision,
        String connectsBy,
        String frameTexturePath,
        String glassTexturePath) {
    public boolean isShape(String expectedShape) {
        return shape.equals(expectedShape);
    }

    /** A special-shape block (kit-driven, hand-authored model) vs a common shape. */
    public boolean isSpecial() {
        return !kit.isEmpty();
    }
}
