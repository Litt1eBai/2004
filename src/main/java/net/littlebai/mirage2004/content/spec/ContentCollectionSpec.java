package net.littlebai.mirage2004.content.spec;

import java.util.List;

public record ContentCollectionSpec(String id, boolean enabled, List<String> families) {
}
