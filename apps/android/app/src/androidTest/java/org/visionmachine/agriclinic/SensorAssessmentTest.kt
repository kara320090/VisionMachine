package org.visionmachine.agriclinic

import android.content.Context
import android.content.ContextWrapper
import android.content.SharedPreferences
import android.net.Uri
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.json.JSONArray
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.util.UUID

/** Synthetic packets exercise both wire modes; no physical measurement or calibration is claimed. */
@RunWith(AndroidJUnit4::class)
class SensorAssessmentTest {
    private fun packet()=syntheticExtendedSensorPacket(UUID.randomUUID()).put("mode","real")
    private fun profile(packet:JSONObject)=SensorProfile("basil",mapOf("air_temp_c" to ReferenceBand(20.0,30.0),
        "air_rh_pct" to ReferenceBand(40.0,60.0),"soil_raw" to ReferenceBand(1000.0,2000.0),
        "optical_sum" to ReferenceBand(100.0,500.0),"surface_air_delta_c" to ReferenceBand(0.0,5.0)),
        "synthetic comparison only","synthetic fixture",true,"synthetic-v1",SensorScoring.opticalConditions(packet),12)
    @Test fun allFourSensorModulesContributeWithTheirOwnUnits() {
        val packet=packet();val profile=profile(packet)
        assertEquals(0.0,SensorScoring.assess(packet,profile).getDouble("deviation_score"),1e-9)
        packet.getJSONObject("readings").put("air_rh_pct",80.0)
        val result=SensorScoring.assess(packet,profile)
        assertEquals(5,result.getInt("scored_count"))
        assertEquals(20.0,result.getDouble("deviation_score"),1e-9)
        assertEquals(100.0,result.getJSONArray("details").getJSONObject(1).getDouble("score"),1e-9)
    }
    @Test fun saturationMissingMockAndChangedExposureNeverProduceAnAggregate() {
        val base=packet();val profile=profile(base)
        val variants=listOf(
            JSONObject(base.toString()).also {it.getJSONObject("extensions").getJSONObject("optical").put("saturated",true);it.put("errors",JSONArray(listOf("as7341_saturated")))},
            JSONObject(base.toString()).also {it.getJSONObject("extensions").put("surface_temperature",JSONObject.NULL);it.put("errors",JSONArray(listOf("mlx90614_disconnected")))},
            JSONObject(base.toString()).put("mode","mock"),
            JSONObject(base.toString()).also {it.getJSONObject("extensions").getJSONObject("optical").put("gain_x",32)}
        )
        variants.forEach {assertTrue(SensorScoring.assess(it,profile).isNull("deviation_score"))}
        assertTrue(SensorScoring.assess(base,profile.copy(applied=false)).isNull("deviation_score"))
    }
    @Test fun profilesAndCompositeProvenanceSurviveStorageWithoutInventedDefaults() {
        val base=InstrumentationRegistry.getInstrumentation().targetContext
        val prefix="synthetic_profiles_${UUID.randomUUID()}_"
        val context=object:ContextWrapper(base) {
            override fun getSharedPreferences(name:String,mode:Int):SharedPreferences=super.getSharedPreferences(prefix+name,mode)
        }
        assertFalse(SensorProfileStore(context).get("basil").applied)
        assertTrue(SensorProfileStore(context).get("kale").bands.isEmpty())
        val packet=packet();val saved=SensorProfileStore(context).save(profile(packet))
        assertEquals(saved,SensorProfileStore(context).get("basil"))
        val assessment=SensorScoring.assess(packet,saved).toString()
        val result=CompositeIndex.attach(RgbRecord("synthetic.png",.2f,.8f,10,"0".repeat(64),"2026-01-01T00:00:00Z","synthetic",
            "basil",UUID.randomUUID().toString(),UUID.randomUUID().toString(),assessment),.5f)
        assertEquals(40.0,JSONObject(result.compositeJson!!).getDouble("index"),1e-5)
        assertTrue(RgbHistory.csv(listOf(result)).contains("user-weighted-index-v1"))
        assertNull(CompositeIndex.attach(result.copy(cropCode="lettuce"),.5f).compositeJson)
        assertNull(CompositeIndex.attach(result.copy(sensorAssessmentJson=null),.5f).compositeJson)
    }
    @Test fun galleryReferencesKeepUnknownExposureTimeAndExactPhotoIdentity() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val store=PhotoReferenceStore(context)
        val uri=Uri.parse("content://synthetic/${UUID.randomUUID()}")
        val first=store.put(uri,"basil")
        val second=store.put(uri,"lettuce")
        assertEquals(first.inspectionId,second.inspectionId)
        assertEquals("",second.capturedAt)
        assertEquals("unassigned",second.subjectId)
        assertEquals("lettuce",PhotoReferenceStore(context).all().first {it.inspectionId==first.inspectionId}.cropCode)
    }
}
