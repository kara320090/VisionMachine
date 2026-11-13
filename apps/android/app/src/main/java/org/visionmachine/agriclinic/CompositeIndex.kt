package org.visionmachine.agriclinic

import org.json.JSONObject

/** User-weighted display index. No probability calibration or trained fusion is claimed. */
object CompositeIndex {
    fun weighted(photoOutput: Double, sensorDeviation: Double, sensorWeight: Double): Double {
        require(photoOutput.isFinite() && photoOutput in 0.0..1.0 && sensorDeviation.isFinite() && sensorDeviation in 0.0..100.0)
        require(sensorWeight.isFinite() && sensorWeight in 0.0..1.0)
        return photoOutput * 100 * (1 - sensorWeight) + sensorDeviation * sensorWeight
    }
    fun attach(record: RgbRecord, sensorWeight: Float): RgbRecord {
        val raw = record.sensorAssessmentJson ?: return record.copy(compositeJson = null)
        val sensor = JSONObject(raw)
        if (record.sourceCaptureId == null || record.sensorRecordId == null || sensor.isNull("deviation_score") ||
            sensor.getJSONObject("profile").getString("crop") != record.cropCode) return record.copy(compositeJson = null)
        val score = weighted(record.abnormal.toDouble(), sensor.getDouble("deviation_score"), sensorWeight.toDouble())
        val json = JSONObject().put("method", "user-weighted-index-v1").put("photo_output", record.abnormal.toDouble())
            .put("sensor_deviation", sensor.getDouble("deviation_score")).put("sensor_weight", sensorWeight.toDouble())
            .put("photo_weight", 1 - sensorWeight.toDouble()).put("index", score).put("sensor_metrics_used", sensor.getInt("scored_count"))
            .put("sensor_metrics_available", sensor.getInt("available_metric_count")).put("sensor_record_id", record.sensorRecordId)
            .put("source_photo_id", record.sourceCaptureId)
        return record.copy(compositeJson = json.toString())
    }
}
