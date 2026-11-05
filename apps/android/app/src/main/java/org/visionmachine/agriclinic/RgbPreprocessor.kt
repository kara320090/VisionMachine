package org.visionmachine.agriclinic

import kotlin.math.abs
import kotlin.math.max

/** Pillow RGB BICUBIC resize + torchvision CenterCrop, without a full resized bitmap.
 * Source rows are EXIF-oriented by the caller. Intermediate channels round to 8 bit,
 * matching Pillow's separable fixed-point filter rather than Android's bilinear scaler.
 */
object RgbPreprocessor {
    private data class Filter(val first: Int, val weights: IntArray)
    private fun cubic(x0: Double): Double {
        val x = abs(x0)
        return when { x < 1 -> ((1.5 * x - 2.5) * x) * x + 1
            x < 2 -> (((-.5 * x + 2.5) * x - 4) * x) + 2
            else -> 0.0 }
    }
    private fun filter(input: Int, output: Int, index: Int): Filter {
        val scale = input.toDouble() / output
        val fs = max(1.0, scale)
        val center = (index + .5) * scale
        val first = max(0, (center - 2 * fs + .5).toInt())
        val last = minOf(input, (center + 2 * fs + .5).toInt())
        val values = DoubleArray(last - first) { cubic((it + first - center + .5) / fs) }
        val sum = values.sum()
        return Filter(first, IntArray(values.size) { i ->
            val w = values[i] / sum * (1 shl 22)
            (w + if (w < 0) -.5 else .5).toInt()
        })
    }
    fun cropRgb(width: Int, height: Int, readRow: (Int, IntArray) -> Unit): ByteArray {
        require(width > 0 && height > 0)
        val rw = if (width <= height) 256 else (256L * width / height).toInt()
        val rh = if (height <= width) 256 else (256L * height / width).toInt()
        // Python round() uses ties to even.
        val left = Math.rint((rw - 224) / 2.0).toInt()
        val top = Math.rint((rh - 224) / 2.0).toInt()
        val xf = Array(224) { filter(width, rw, it + left) }
        val yf = Array(224) { filter(height, rh, it + top) }
        val rows = arrayOfNulls<ByteArray>(height)
        val input = IntArray(width)
        val needed = yf.flatMap { f -> f.weights.indices.map { it + f.first } }.toSet()
        for (y in needed) {
            readRow(y, input)
            val out = ByteArray(224 * 3)
            for (x in 0 until 224) {
                val f = xf[x]
                for (c in 0..2) {
                    var acc = 1L shl 21
                    for (i in f.weights.indices) {
                        val value = (input[f.first + i] ushr (16 - 8 * c)) and 255
                        acc += value.toLong() * f.weights[i]
                    }
                    out[x * 3 + c] = (acc shr 22).coerceIn(0,255).toByte()
                }
            }
            rows[y] = out
        }
        val result = ByteArray(224 * 224 * 3)
        for (y in 0 until 224) {
            val f = yf[y]
            for (i in 0 until 224 * 3) {
                var acc = 1L shl 21
                for (k in f.weights.indices) acc += (rows[f.first + k]!![i].toInt() and 255).toLong() * f.weights[k]
                result[y * 224 * 3 + i] = (acc shr 22).coerceIn(0,255).toByte()
            }
        }
        return result
    }
    fun normalize(rgb: ByteArray): FloatArray {
        require(rgb.size == 224 * 224 * 3)
        val mean = floatArrayOf(.485f,.456f,.406f)
        val std = floatArrayOf(.229f,.224f,.225f)
        return FloatArray(3 * 224 * 224) { i ->
            val c = i / (224 * 224)
            ((rgb[(i % (224 * 224)) * 3 + c].toInt() and 255) / 255f - mean[c]) / std[c]
        }
    }
}
