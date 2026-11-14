package org.visionmachine.agriclinic

import android.content.Context
import android.util.AtomicFile
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

data class RgbRecord(val name:String,val normal:Float,val abnormal:Float,val millis:Long,val sha256:String,val timestamp:String,val model:String,
    val cropCode:String?=null,val sourceCaptureId:String?=null,val sensorRecordId:String?=null,val sensorAssessmentJson:String?=null,val compositeJson:String?=null,
    val executionProvider:String?=null,val serverInspectionId:String?=null) {
    val label get()=if(abnormal>=.5f) "이상 의심" else "정상 쪽"
    fun json()=JSONObject().put("name",name).put("normal",normal.toDouble()).put("abnormal",abnormal.toDouble()).put("millis",millis).put("sha256",sha256).put("timestamp",timestamp).put("model",model)
        .put("crop_code",cropCode?:JSONObject.NULL).put("source_photo_id",sourceCaptureId?:JSONObject.NULL)
        .put("sensor_record_id",sensorRecordId?:JSONObject.NULL).put("sensor_assessment_json",sensorAssessmentJson?:JSONObject.NULL).put("composite_json",compositeJson?:JSONObject.NULL)
        .put("execution_provider",executionProvider?:JSONObject.NULL).put("server_inspection_id",serverInspectionId?:JSONObject.NULL)
}
class RgbHistory(context:Context) {
    private val file=AtomicFile(File(context.filesDir,"rgb_history.json"))
    fun read():List<RgbRecord> {
        if(!file.baseFile.exists()) return emptyList()
        val a=JSONArray(file.openRead().bufferedReader().use { it.readText() })
        return (0 until a.length()).map { i -> val o=a.getJSONObject(i)
            fun optional(key:String)=o.optString(key).takeUnless {o.isNull(key)||it.isBlank()}
            RgbRecord(o.getString("name"),o.getDouble("normal").toFloat(),o.getDouble("abnormal").toFloat(),o.getLong("millis"),o.getString("sha256"),o.getString("timestamp"),o.getString("model"),
                optional("crop_code"),optional("source_photo_id"),optional("sensor_record_id"),optional("sensor_assessment_json"),optional("composite_json"),optional("execution_provider"),optional("server_inspection_id")) }
    }
    fun write(rows:List<RgbRecord>) {
        val a=JSONArray();rows.takeLast(200).forEach { a.put(it.json()) }
        val out=file.startWrite()
        try { out.write(a.toString().toByteArray(Charsets.UTF_8));file.finishWrite(out) }
        catch(e:Exception) {file.failWrite(out);throw e}
    }
    companion object {
        private fun cell(s:String):String {
            // Untrusted filenames must remain text when CSV is opened in a spreadsheet.
            val safe=if(s.trimStart().firstOrNull() in listOf('=','+','-','@','\t','\r')) "'$s" else s
            return "\"${safe.replace("\"","\"\"")}\""
        }
        fun csv(rows:List<RgbRecord>):String="\uFEFFfilename,label,normal,abnormal,elapsed_ms,input_sha256,timestamp,model_version,crop_code,source_photo_id,sensor_record_id,sensor_assessment_json,composite_json,execution_provider,server_inspection_id\r\n"+
            rows.joinToString("") { r -> listOf(cell(r.name),cell(r.label),r.normal.toString(),r.abnormal.toString(),r.millis.toString(),cell(r.sha256),cell(r.timestamp),cell(r.model),
                cell(r.cropCode.orEmpty()),cell(r.sourceCaptureId.orEmpty()),cell(r.sensorRecordId.orEmpty()),cell(r.sensorAssessmentJson.orEmpty()),cell(r.compositeJson.orEmpty()),cell(r.executionProvider.orEmpty()),cell(r.serverInspectionId.orEmpty())).joinToString(",")+"\r\n" }
    }
}
