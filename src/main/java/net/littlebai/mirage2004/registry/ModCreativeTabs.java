package net.littlebai.mirage2004.registry;

import java.util.Set;

import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.CreativeModeTabs;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

import net.littlebai.mirage2004.Mirage2004;
import net.littlebai.mirage2004.generated.GeneratedBlockCatalog;

public final class ModCreativeTabs {
    private static final Set<String> WINDOW_CATEGORIES = Set.of("windows");
    private static final Set<String> INFRASTRUCTURE_CATEGORIES = Set.of("infrastructure");

    public static final DeferredRegister<CreativeModeTab> CREATIVE_MODE_TABS =
            DeferredRegister.create(Registries.CREATIVE_MODE_TAB, Mirage2004.MODID);

    public static final DeferredHolder<CreativeModeTab, CreativeModeTab> MATERIALS_TAB =
            CREATIVE_MODE_TABS.register(
                    "materials",
                    () -> CreativeModeTab.builder()
                            .title(Component.translatable("itemGroup.mirage2004.materials"))
                            .withTabsBefore(CreativeModeTabs.BUILDING_BLOCKS)
                            .icon(() -> ModItems.require("small_tile_white").get().getDefaultInstance())
                            .displayItems((parameters, output) -> GeneratedBlockCatalog.BLOCKS.stream()
                                    .filter(definition -> !WINDOW_CATEGORIES.contains(definition.category()))
                                    .filter(definition -> !INFRASTRUCTURE_CATEGORIES.contains(definition.category()))
                                    .forEach(definition -> output.accept(ModItems.require(definition.id()).get())))
                            .build());

    public static final DeferredHolder<CreativeModeTab, CreativeModeTab> WINDOWS_TAB =
            CREATIVE_MODE_TABS.register(
                    "windows",
                    () -> CreativeModeTab.builder()
                            .title(Component.translatable("itemGroup.mirage2004.windows"))
                            .withTabsBefore(MATERIALS_TAB.getKey())
                            .icon(() -> ModItems.require("curtain_glass_blue").get().getDefaultInstance())
                            .displayItems((parameters, output) -> GeneratedBlockCatalog.BLOCKS.stream()
                                    .filter(definition -> WINDOW_CATEGORIES.contains(definition.category()))
                                    .forEach(definition -> output.accept(ModItems.require(definition.id()).get())))
                            .build());

    public static final DeferredHolder<CreativeModeTab, CreativeModeTab> INFRASTRUCTURE_TAB =
            CREATIVE_MODE_TABS.register(
                    "infrastructure",
                    () -> CreativeModeTab.builder()
                            .title(Component.translatable("itemGroup.mirage2004.infrastructure"))
                            .withTabsBefore(WINDOWS_TAB.getKey())
                            .icon(() -> ModItems.require("small_tile_white").get().getDefaultInstance())
                            .displayItems((parameters, output) -> GeneratedBlockCatalog.BLOCKS.stream()
                                    .filter(definition -> INFRASTRUCTURE_CATEGORIES.contains(definition.category()))
                                    .forEach(definition -> output.accept(ModItems.require(definition.id()).get())))
                            .build());

    private ModCreativeTabs() {
    }

    public static void register(IEventBus modEventBus) {
        CREATIVE_MODE_TABS.register(modEventBus);
    }
}
