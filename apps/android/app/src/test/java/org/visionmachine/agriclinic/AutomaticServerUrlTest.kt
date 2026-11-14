package org.visionmachine.agriclinic

import org.junit.Assert.*
import org.junit.Test

class AutomaticServerUrlTest {
    @Test fun automaticConnectionAcceptsOnlyHttpsBaseAddressesInRelease() {
        assertEquals("https://example.com", checkedAutomaticServerUrl(" https://example.com/ ", false))
        for (invalid in listOf("http://example.com", "http://100.74.204.80:8000", "https://user:password@example.com",
            "https://example.com/api", "https://example.com?key=value", "https://example.com#fragment", "https://example.com:99999")) {
            try { checkedAutomaticServerUrl(invalid, false); fail("Unsafe automatic endpoint accepted") }
            catch (_: IllegalArgumentException) {}
        }
    }
    @Test fun debugCleartextIsConfinedToEmulatorAndLoopback() {
        assertEquals("http://10.0.2.2:8000", checkedAutomaticServerUrl("http://10.0.2.2:8000", true))
        try { checkedAutomaticServerUrl("http://192.168.0.1", true); fail("LAN cleartext endpoint accepted") }
        catch (_: IllegalArgumentException) {}
    }
}
