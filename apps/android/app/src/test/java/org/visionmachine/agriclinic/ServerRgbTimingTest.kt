package org.visionmachine.agriclinic

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ServerRgbTimingTest {
    @Test fun readsQueueDurationWithOtherMetrics() {
        assertEquals(12.375, parseServerQueueMillis("cdn;dur=2, vm_queue;dur=12.375, vm_infer;dur=14")!!, 0.0)
        assertEquals(0.0, parseServerQueueMillis("vm_queue;dur=\"0\"")!!, 0.0)
    }

    @Test fun ignoresMissingOrInvalidQueueDuration() {
        for (header in listOf("", "vm_infer;dur=5", "vm_queue", "vm_queue;dur=-1",
            "vm_queue;dur=NaN", "vm_queue;dur=Infinity")) {
            assertNull(header, parseServerQueueMillis(header))
        }
    }
}
