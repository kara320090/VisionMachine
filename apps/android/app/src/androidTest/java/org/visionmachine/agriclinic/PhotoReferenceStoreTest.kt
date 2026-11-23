package org.visionmachine.agriclinic

import android.content.Context
import android.content.ContextWrapper
import android.content.SharedPreferences
import android.net.Uri
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.io.Closeable
import java.util.UUID
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PhotoReferenceStoreTest {
    @Test fun eightRegistrationsMatchSingleWritesWithOnePreferenceCommit() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val initial = (0 until 500).map(::sample)
        val existing = initial.last()
        val registrations = listOf(PhotoReferenceStore.Registration(existing.uri, "lettuce")) +
            (500 until 507).map(::sample)

        StoreFixture(context).use { sequential ->
            StoreFixture(context).use { grouped ->
                sequential.store.putAll(initial)
                grouped.store.putAll(initial)
                sequential.resetCounts()
                grouped.resetCounts()

                val direct = registrations.map { (uri, crop, capture) ->
                    sequential.store.put(uri, crop, capture)
                }
                val batch = grouped.store.putAll(registrations)

                assertEquals(8, sequential.reads)
                assertEquals(8, sequential.commits)
                assertEquals(1, grouped.reads)
                assertEquals(1, grouped.commits)
                assertEquals(direct, batch)
                assertEquals(existing.capture!!.inspectionId, batch.first().inspectionId)
                assertEquals("lettuce", batch.first().cropCode)

                val saved = grouped.store.all()
                assertEquals(sequential.store.all(), saved)
                val expectedIds = initial.drop(7).dropLast(1).map { it.capture!!.inspectionId } +
                    batch.map { it.inspectionId }
                assertEquals(500, saved.size)
                assertEquals(expectedIds, saved.map { it.inspectionId })
            }
        }
    }

    @Test fun repeatedUriReusesIdAndMovesToNewestPosition() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        StoreFixture(context).use { fixture ->
            assertTrue(fixture.store.putAll(emptyList()).isEmpty())
            assertEquals(0, fixture.reads)
            assertEquals(0, fixture.commits)

            val duplicate = Uri.parse("content://synthetic.test/duplicate")
            val first = PhotoReferenceStore.Registration(duplicate, "basil")
            val other = sample(1)
            val updated = first.copy(crop = "lettuce")
            val added = fixture.store.putAll(listOf(first, other, updated))

            assertEquals(1, fixture.reads)
            assertEquals(1, fixture.commits)
            assertEquals(added.first().inspectionId, added.last().inspectionId)
            assertEquals("lettuce", added.last().cropCode)
            assertEquals(listOf(added[1], added.last()), fixture.store.all())
        }
    }

    private fun sample(index: Int): PhotoReferenceStore.Registration {
        val uri = Uri.parse("content://synthetic.test/photo-$index")
        val record = CaptureRecord("synthetic-$index", "synthetic-subject", "synthetic-batch", "basil",
            uri.toString(), "2026-01-01T00:00:00Z")
        return PhotoReferenceStore.Registration(uri, record.cropCode, record)
    }

    private class StoreFixture(private val context: Context) : Closeable {
        private val name = "test-photo-references-${UUID.randomUUID()}"
        private val backing = context.getSharedPreferences(name, Context.MODE_PRIVATE)
        var reads = 0
            private set
        var commits = 0
            private set

        private val counting = object : SharedPreferences by backing {
            override fun getString(key: String, defValue: String?): String? {
                reads++
                return backing.getString(key, defValue)
            }

            override fun edit(): SharedPreferences.Editor {
                val editor = backing.edit()
                return object : SharedPreferences.Editor by editor {
                    override fun putString(key: String, value: String?): SharedPreferences.Editor {
                        editor.putString(key, value)
                        return this
                    }

                    override fun commit(): Boolean {
                        commits++
                        return editor.commit()
                    }
                }
            }
        }
        val store = PhotoReferenceStore(object : ContextWrapper(context) {
            override fun getSharedPreferences(name: String, mode: Int): SharedPreferences = counting
        })

        fun resetCounts() {
            reads = 0
            commits = 0
        }

        override fun close() {
            context.deleteSharedPreferences(name)
        }
    }
}
