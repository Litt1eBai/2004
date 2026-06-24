package net.littlebai.mirage2004.registry;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

import net.minecraft.world.item.BlockItem;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredItem;
import net.neoforged.neoforge.registries.DeferredRegister;

import net.littlebai.mirage2004.Mirage2004;
import net.littlebai.mirage2004.generated.GeneratedBlockCatalog;

public final class ModItems {
    public static final DeferredRegister.Items ITEMS = DeferredRegister.createItems(Mirage2004.MODID);
    public static final Map<String, DeferredItem<BlockItem>> ITEMS_BY_ID = new LinkedHashMap<>();

    static {
        GeneratedBlockCatalog.BLOCKS.forEach(definition -> {
            ITEMS_BY_ID.put(definition.id(), ITEMS.registerSimpleBlockItem(definition.id(), ModBlocks.require(definition.id())));
        });
    }

    private ModItems() {
    }

    public static DeferredItem<BlockItem> require(String id) {
        return Objects.requireNonNull(ITEMS_BY_ID.get(id), () -> "Unknown generated item id: " + id);
    }

    public static void register(IEventBus modEventBus) {
        ITEMS.register(modEventBus);
    }
}
