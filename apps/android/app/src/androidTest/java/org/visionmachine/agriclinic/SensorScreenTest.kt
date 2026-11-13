package org.visionmachine.agriclinic

import androidx.lifecycle.ViewModelProvider
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SensorScreenTest {
    @Test fun absentDeviceAndRecreationNeverShowAnInventedCurrentReading() {
        ActivityScenario.launch(SensorActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                val model=ViewModelProvider(activity)[SensorViewModel::class.java]
                assertNull(model.current)
                model.connect()
                assertEquals("DEVICE_NOT_FOUND",model.usb.code)
                assertFalse(model.usb.connected)
                assertFalse(model.busy)
            }
            scenario.recreate()
            scenario.onActivity { activity ->
                val model=ViewModelProvider(activity)[SensorViewModel::class.java]
                assertNull(model.current)
                assertFalse(model.usb.connected)
            }
        }
    }
}
