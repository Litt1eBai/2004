package net.littlebai.mirage2004;

import net.neoforged.neoforge.common.ModConfigSpec;

// Empty-but-real config spec. Kept (rather than removed) because
// Mirage2004Client registers an IConfigScreenFactory and Mirage2004 registers
// this SPEC; the config screen renders empty until real options are added.
public class Config {
    private static final ModConfigSpec.Builder BUILDER = new ModConfigSpec.Builder();

    static final ModConfigSpec SPEC = BUILDER.build();

    private Config() {
    }
}
