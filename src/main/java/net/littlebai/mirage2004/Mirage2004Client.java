package net.littlebai.mirage2004;

import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.repository.Pack;
import net.minecraft.server.packs.repository.PackSource;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.event.lifecycle.FMLClientSetupEvent;
import net.neoforged.neoforge.client.event.ModelEvent;
import net.neoforged.neoforge.client.gui.ConfigurationScreen;
import net.neoforged.neoforge.client.gui.IConfigScreenFactory;
import net.neoforged.neoforge.event.AddPackFindersEvent;

import net.littlebai.mirage2004.client.model.TriangleWallModelLoader;
import net.littlebai.mirage2004.client.model.SlopeModelLoader;

// This class will not load on dedicated servers. Accessing client side code from here is safe.
@Mod(value = Mirage2004.MODID, dist = Dist.CLIENT)
// You can use EventBusSubscriber to automatically register all static methods in the class annotated with @SubscribeEvent
@EventBusSubscriber(modid = Mirage2004.MODID, value = Dist.CLIENT)
public class Mirage2004Client {
    public Mirage2004Client(ModContainer container) {
        // Allows NeoForge to create a config screen for this mod's configs.
        // The config screen is accessed by going to the Mods screen > clicking on your mod > clicking on config.
        // Do not forget to add translations for your config options to the en_us.json file.
        container.registerExtensionPoint(IConfigScreenFactory.class, ConfigurationScreen::new);
    }

    @SubscribeEvent
    static void onClientSetup(FMLClientSetupEvent event) {
    }

    @SubscribeEvent
    static void registerModelLoaders(ModelEvent.RegisterLoaders event) {
        event.register(Identifier.parse(Mirage2004.MODID + ":slope"), SlopeModelLoader.INSTANCE);
        event.register(Identifier.parse(Mirage2004.MODID + ":triangle_wall"), TriangleWallModelLoader.INSTANCE);
    }

    // Bundled optional 32x HD resource pack (src/main/resources/hd_32x/). Disabled by
    // default; players enable it in Options > Resource Packs to override the 16x base.
    @SubscribeEvent
    static void addResourcePacks(AddPackFindersEvent event) {
        event.addPackFinders(
                Identifier.parse(Mirage2004.MODID + ":hd_32x"),
                PackType.CLIENT_RESOURCES,
                Component.literal("Mirage2004 32x HD"),
                PackSource.BUILT_IN,
                false,
                Pack.Position.TOP);
    }
}
