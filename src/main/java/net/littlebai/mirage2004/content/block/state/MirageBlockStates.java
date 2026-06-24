package net.littlebai.mirage2004.content.block.state;

import net.minecraft.util.StringRepresentable;
import net.minecraft.world.level.block.state.properties.EnumProperty;

/** Shared custom block-state properties for the mod's connecting special blocks. */
public final class MirageBlockStates {
    private MirageBlockStates() {
    }

    /**
     * Vertical connection position (ported from yuushya). Serializes as {@code pos}
     * so the generated blockstate keys read {@code pos=top} etc.
     */
    public static final EnumProperty<VerticalPosition> POS_VERTICAL =
            EnumProperty.create("pos", VerticalPosition.class);

    /**
     * Horizontal connection position (ported from yuushya {@code LineBlock}). Serializes
     * as {@code pos_h} — a key distinct from {@link #POS_VERTICAL}'s {@code pos} so a block
     * can carry BOTH (the framed window uses {@code facing}, {@code pos}, {@code pos_h}).
     * {@code LEFT} = "I am the left member, my right (east-side) neighbour connects".
     */
    public static final EnumProperty<HorizontalPosition> POS_HORIZON =
            EnumProperty.create("pos_h", HorizontalPosition.class);

    public enum VerticalPosition implements StringRepresentable {
        TOP("top"),
        MIDDLE("middle"),
        BOTTOM("bottom"),
        NONE("none");

        private final String name;

        VerticalPosition(String name) {
            this.name = name;
        }

        @Override
        public String getSerializedName() {
            return this.name;
        }
    }

    public enum HorizontalPosition implements StringRepresentable {
        LEFT("left"),
        MIDDLE("middle"),
        RIGHT("right"),
        NONE("none");

        private final String name;

        HorizontalPosition(String name) {
            this.name = name;
        }

        @Override
        public String getSerializedName() {
            return this.name;
        }
    }
}
