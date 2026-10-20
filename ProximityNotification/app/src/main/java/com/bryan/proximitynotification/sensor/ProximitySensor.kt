package com.bryan.proximitynotification.sensor

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import com.bryan.proximitynotification.model.SensorStatus

class ProximitySensor(
    context: Context,
    private val onSensorUpdate: (SensorStatus, Float) -> Unit
) {
    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val proximitySensor: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_PROXIMITY)
    private val lightSensor: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_LIGHT)

    private var lastValue = 5.0f

    private val listener = object : SensorEventListener {
        override fun onSensorChanged(event: SensorEvent) {
            var currentMappedValue = lastValue

            when (event.sensor.type) {
                Sensor.TYPE_PROXIMITY -> {
                    val distance = event.values.firstOrNull() ?: return
                    // 0.0 = NEAR, 5.0 = FAR
                    currentMappedValue = if (distance < (proximitySensor?.maximumRange ?: 5f)) 0.0f else 5.0f
                }
                Sensor.TYPE_LIGHT -> {
                    val lux = event.values.firstOrNull() ?: return
                    // Terang (50+ lux) = 5.0 (Far), Gelap (0 lux) = 0.0 (Near)
                    currentMappedValue = (lux / 10f).coerceIn(0f, 5f)
                }
            }

            if (Math.abs(currentMappedValue - lastValue) > 0.05f) {
                lastValue = currentMappedValue
                // NEAR jika nilai <= 1.0f (Sesuai protokol Python)
                val status = if (currentMappedValue <= 1.0f) SensorStatus.NEAR else SensorStatus.FAR
                onSensorUpdate(status, currentMappedValue)
            }
        }

        override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
    }

    fun start() {
        proximitySensor?.let { sensorManager.registerListener(listener, it, SensorManager.SENSOR_DELAY_UI) }
        lightSensor?.let { sensorManager.registerListener(listener, it, SensorManager.SENSOR_DELAY_UI) }
    }

    fun stop() {
        sensorManager.unregisterListener(listener)
    }
}
