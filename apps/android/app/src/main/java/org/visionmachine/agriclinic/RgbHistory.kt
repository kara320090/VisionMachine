package org.visionmachine.agriclinic

import android.content.Context
import android.util.AtomicFile
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

data class RgbRecord(val name:String,val normal:Float,val abnormal:Float,val millis:Long,val sha256:String,val timestamp:String,val model:String) {
    val label get()=if(abnormal>=.5f) "이상 의심" else "정상 쪽"
    fun json()=JSONObject().put("name",name).put("normal",normal.toDouble()).put("abnormal",abnormal.toDouble()).put("millis",millis).put("sha256",sha256).put("timestamp",timestamp).put("model",model)
}
class RgbHistory(context:Context) {
    private val file=AtomicFile(File(context.filesDir,"rgb_history.json"))
    fun read():List<RgbRecord> {
        if(!file.baseFile.exists()) return emptyList()
        val a=JSONArray(file.openRead().bufferedReader().use { it.readText() })
        return (0 until a.length()).map { i -> val o=a.getJSONObject(i);RgbRecord(o.getString("name"),o.getDouble("normal").toFloat(),o.getDouble("abnormal").toFloat(),o.getLong("millis"),o.getString("sha256"),o.getString("timestamp"),o.getString("model")) }
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
        fun csv(rows:List<RgbRecord>):String="\uFEFFfilename,label,normal,abnormal,elapsed_ms,input_sha256,timestamp,model_version\r\n"+
            rows.joinToString("") { r -> listOf(cell(r.name),cell(r.label),r.normal.toString(),r.abnormal.toString(),r.millis.toString(),cell(r.sha256),cell(r.timestamp),cell(r.model)).joinToString(",")+"\r\n" }
    }
}
