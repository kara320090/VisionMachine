package org.visionmachine.agriclinic

import kotlin.math.abs
import kotlin.math.max

/** Pillow RGB BICUBIC resize + torchvision CenterCrop, without a full resized bitmap.
 * Source rows are EXIF-oriented by the caller. Intermediate channels round to 8 bit,
 * matching Pillow's separable fixed-point filter rather than Android's bilinear scaler.
 */
object RgbPreprocessor {
    private const val CROP_SIZE = 224
    private const val ROW_CHANNELS = CROP_SIZE * 3
    private const val FRACTION_BITS = 22
    private const val ROUNDING_OFFSET = 1L shl (FRACTION_BITS - 1)

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
            val w = values[i] / sum * (1 shl FRACTION_BITS)
            (w + if (w < 0) -.5 else .5).toInt()
        })
    }
    fun cropRgb(width: Int, height: Int, readRow: (Int, IntArray) -> Unit): ByteArray {
        require(width > 0 && height > 0)
        val rw = if (width <= height) 256 else (256L * width / height).toInt()
        val rh = if (height <= width) 256 else (256L * height / width).toInt()
        // Python round() uses ties to even.
        val left = Math.rint((rw - CROP_SIZE) / 2.0).toInt()
        val top = Math.rint((rh - CROP_SIZE) / 2.0).toInt()
        val horizontal = Array(CROP_SIZE) { filter(width, rw, it + left) }
        val vertical = Array(CROP_SIZE) { filter(height, rh, it + top) }
        // Each vertical filter needs a contiguous span. Spans advance as output rows advance,
        // so a cache as wide as the largest span retains their overlapping source rows.
        val rows = Array(vertical.maxOf { it.weights.size }) { ByteArray(ROW_CHANNELS) }
        val sourceRows = IntArray(rows.size) { -1 }
        val input = IntArray(width)
        val sums = LongArray(ROW_CHANNELS)
        val result = ByteArray(CROP_SIZE * ROW_CHANNELS)
        for (y in vertical.indices) {
            val filter = vertical[y]
            sums.fill(ROUNDING_OFFSET)
            for (tap in filter.weights.indices) {
                val sourceY = filter.first + tap
                val slot = sourceY % rows.size
                val row = rows[slot]
                if (sourceRows[slot] != sourceY) {
                    readRow(sourceY, input)
                    filterRow(input, horizontal, row)
                    sourceRows[slot] = sourceY
                }
                val weight = filter.weights[tap].toLong()
                for (channel in row.indices) {
                    sums[channel] += (row[channel].toInt() and 255) * weight
                }
            }
            for (channel in sums.indices) {
                result[y * ROW_CHANNELS + channel] = quantize(sums[channel])
            }
        }
        return result
    }

    private fun filterRow(input: IntArray, filters: Array<Filter>, output: ByteArray) {
        for (x in filters.indices) {
            val filter = filters[x]
            var red = ROUNDING_OFFSET
            var green = ROUNDING_OFFSET
            var blue = ROUNDING_OFFSET
            for (tap in filter.weights.indices) {
                val rgb = input[filter.first + tap]
                val weight = filter.weights[tap].toLong()
                red += ((rgb ushr 16) and 255) * weight
                green += ((rgb ushr 8) and 255) * weight
                blue += (rgb and 255) * weight
            }
            val offset = x * 3
            output[offset] = quantize(red)
            output[offset + 1] = quantize(green)
            output[offset + 2] = quantize(blue)
        }
    }

    private fun quantize(value: Long): Byte = (value shr FRACTION_BITS).coerceIn(0, 255).toByte()
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
