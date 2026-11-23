package org.visionmachine.agriclinic
import org.junit.Test
import org.junit.Assert.*
import java.security.MessageDigest
class RgbPreprocessorTest {
    @Test fun matchesPillowGoldenRgbForSmallLargePortraitAndLandscape() {
        val cases=listOf(
            Triple(71,53,"c38cc40c1f2dffa6e14291de4f98f8265e9823bbf297f8184987b6c171bbc9bc"),
            Triple(53,71,"0f154700878a80a927b8a555be822967024a48d88231fb8b646c638f3c9ad819"),
            Triple(7,35,"771964a81f3234102ca73d05f1bca1a97db9d16d1fa18989a6555a450e7df49b"),
            Triple(256,256,"7cfacf8b6b0eb0cb8798654284fa94551335f5fad5de817e6514b0159a1e9f13"),
            Triple(1001,601,"4e50448eec58bba4321e4a013caa2091160ee7217d88620b9bcf2d441eed74b1"),
            Triple(601,1001,"cc5cf2937ad9f1c689cbd0caf7061084e711c62bfd6794f183688f5537b27fd4"),
            Triple(3000,4000,"fd4589c8787702fb5c8e013bfc323a87d2a6659554656d4917b37d58be147405"),
            Triple(4001,3001,"a9b9215ffdf3fd5e8ee2434a876a5eb10b76c6c77db0914b02f5af7947867ef6")
        )
        for((w,h,expected) in cases) {
            val readRows = BooleanArray(h)
            val rgb = RgbPreprocessor.cropRgb(w, h) { y, row ->
                assertFalse("${w}x${h} source row $y was read twice", readRows[y])
                readRows[y] = true
                for (x in row.indices) {
                    row[x] = 0xff000000.toInt() or (((x * 13 + y * 7) % 256) shl 16) or
                        (((x * 3 + y * 19) % 256) shl 8) or ((x * 29 + y * 5) % 256)
                }
            }
            val actual=MessageDigest.getInstance("SHA-256").digest(rgb).joinToString(""){"%02x".format(it)}
            assertEquals("${w}x${h}",expected,actual)
            val x=RgbPreprocessor.normalize(rgb)
            assertEquals(150528,x.size)
            assertTrue(x.all {it.isFinite()})
        }
    }
}
