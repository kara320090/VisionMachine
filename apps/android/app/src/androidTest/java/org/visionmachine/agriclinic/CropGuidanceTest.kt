package org.visionmachine.agriclinic

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.util.UUID

class CropGuidanceTest {
    private fun record(value: Double, mode: String = "real"): RgbRecord {
        val packet = syntheticExtendedSensorPacket(UUID.randomUUID()).put("mode", mode)
        packet.getJSONObject("readings").put("air_temp_c", value)
        val profile = SensorProfile("basil", mapOf("air_temp_c" to ReferenceBand(20.0, 30.0, 2.0)), applied = true)
        val assessment = SensorScoring.assess(packet, profile).toString()
        return RgbRecord("synthetic", .8f, .2f, 1, "hash", "test", "test", "basil", "photo", "sensor", assessment)
    }

    @Test fun allSupportedCropsHaveConditionalActionsAndHistoricalAliasesAreHandled() {
        for (crop in listOf("basil", "bok_choy", "cucumber", "kale", "lettuce", "pepper", "rosemary", "tomato")) {
            val checks = fieldChecks(crop)
            assertTrue(crop, checks.size >= 2)
            assertTrue(checks.all { it.cause.isNotBlank() && it.verify.isNotBlank() && it.action.isNotBlank() && it.source.startsWith("https://") })
        }
        assertEquals(fieldChecks("tomato"), fieldChecks("cherry_tomato"))
        assertTrue(fieldChecks(null).isEmpty())
        assertTrue(fieldChecks("eggplant").isEmpty())
    }

    @Test fun guidanceUsesLinkedScoredValuesAndHonorsToleranceInBothDirections() {
        val high = record(35.0)
        assertTrue(sensorFindings(high).single().evidence.contains("높음"))
        assertTrue(sensorFindings(record(17.0)).single().evidence.contains("낮음"))
        for (value in listOf(18.0, 20.0, 26.0, 32.0)) assertTrue(sensorFindings(record(value)).isEmpty())
        assertTrue(sensorFindings(record(35.0, "mock")).isEmpty())
        assertTrue(sensorFindings(high.copy(sensorRecordId = null)).isEmpty())
        assertTrue(sensorFindings(high.copy(cropCode = "lettuce")).isEmpty())
        assertTrue(sensorFindings(high.copy(sensorAssessmentJson = null)).isEmpty())
        val raw = JSONObject(high.sensorAssessmentJson!!)
        raw.getJSONArray("details").getJSONObject(0).put("status", "QUALITY_OR_CONDITIONS")
        assertTrue(sensorFindings(high.copy(sensorAssessmentJson = raw.toString())).isEmpty())
    }
}
