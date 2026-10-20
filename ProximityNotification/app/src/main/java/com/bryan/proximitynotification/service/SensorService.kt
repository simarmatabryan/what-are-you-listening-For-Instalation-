package com.bryan.proximitynotification.service

import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.media.MediaPlayer
import android.os.Build
import android.os.IBinder
import android.os.VibrationEffect
import android.os.Vibrator
import android.util.Log
import com.bryan.proximitynotification.model.SensorStatus
import com.bryan.proximitynotification.network.OscConfig
import com.bryan.proximitynotification.network.OscSender
import com.bryan.proximitynotification.notification.NotificationHelper
import com.bryan.proximitynotification.util.Constants
import java.util.Timer
import java.util.TimerTask

class SensorService : Service(), SensorEventListener {
    private val TAG = "OSC_PROXIMITY"
    private var currentStatus = SensorStatus.UNKNOWN
    private var lastValue = -1f

    private var proximitySensor: Sensor? = null
    private var lightSensor: Sensor? = null
    private lateinit var sensorManager: SensorManager
    private lateinit var notificationManager: NotificationManager
    
    private lateinit var pythonOscSender: OscSender
    private lateinit var maxDirectSender: OscSender
    
    private var mediaPlayer: MediaPlayer? = null
    private var keepAliveTimer: Timer? = null

    override fun onCreate() {
        super.onCreate()
        notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        
        proximitySensor = sensorManager.getDefaultSensor(Sensor.TYPE_PROXIMITY)
        lightSensor = sensorManager.getDefaultSensor(Sensor.TYPE_LIGHT)

        NotificationHelper.createChannel(this)
        
        // Sender 1: Ke Python (Port 8011)
        pythonOscSender = OscSender(OscConfig.MAC_HOST, OscConfig.PYTHON_PORT)
        
        // Sender 2: Langsung ke Max Proximity (Port 8001) - SESUAI GAMBAR
        maxDirectSender = OscSender(OscConfig.MAC_HOST, OscConfig.MAX_PROX_PORT)
        
        startKeepAlive()
    }

    override fun onSensorChanged(event: SensorEvent?) {
        if (event == null || event.values.isEmpty()) return

        val isNear: Boolean = if (event.sensor.type == Sensor.TYPE_PROXIMITY) {
            event.values[0] < event.sensor.maximumRange
        } else if (event.sensor.type == Sensor.TYPE_LIGHT) {
            event.values[0] < 20f
        } else {
            false
        }

        val valToSend = if (isNear) 0f else 5f
        if (valToSend == lastValue) return
        lastValue = valToSend

        val newStatus = if (isNear) SensorStatus.NEAR else SensorStatus.FAR
        currentStatus = newStatus

        // KIRIM OSC KE SEMUA PORT
        pythonOscSender.sendProximity(valToSend)
        maxDirectSender.sendProximity(valToSend)
        
        Log.i(TAG, "SEND OSC: $valToSend to Port ${OscConfig.PYTHON_PORT} & ${OscConfig.MAX_PROX_PORT}")

        if (isNear) {
            vibratePhone()
            spamNotifications()
            playAlertSound()
            launchLockscreen()
        } else {
            stopAlertSound()
        }

        updateNotification()
        broadcastStatus(newStatus)
    }

    private fun vibratePhone() {
        val vibrator = getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            vibrator.vibrate(VibrationEffect.createOneShot(200, VibrationEffect.DEFAULT_AMPLITUDE))
        } else {
            @Suppress("DEPRECATION")
            vibrator.vibrate(200)
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    private fun startKeepAlive() {
        keepAliveTimer?.cancel()
        keepAliveTimer = Timer()
        keepAliveTimer?.schedule(object : TimerTask() {
            override fun run() {
                val valToSend = if (currentStatus == SensorStatus.NEAR) 0f else 5f
                pythonOscSender.sendProximity(valToSend)
                maxDirectSender.sendProximity(valToSend)
            }
        }, 1000, 1000)
    }

    private fun launchLockscreen() {
        val intent = Intent(this, com.bryan.proximitynotification.MainActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_REORDER_TO_FRONT or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        }
        startActivity(intent)
    }

    private fun playAlertSound() {
        try {
            var resId = resources.getIdentifier("samsung", "raw", packageName)
            if (resId == 0) resId = resources.getIdentifier("max_msp_alert", "raw", packageName)
            mediaPlayer?.release()
            if (resId != 0) {
                mediaPlayer = MediaPlayer.create(this, resId)
                mediaPlayer?.isLooping = true
                mediaPlayer?.start()
            }
        } catch (e: Exception) { e.printStackTrace() }
    }

    private fun stopAlertSound() {
        try { mediaPlayer?.stop() } catch (_: Exception) {}
        mediaPlayer?.release()
        mediaPlayer = null
    }

    override fun onDestroy() {
        keepAliveTimer?.cancel()
        stopAlertSound()
        sensorManager.unregisterListener(this)
        pythonOscSender.close()
        maxDirectSender.close()
        super.onDestroy()
    }

    private fun spamNotifications() {
        for (i in 2..5) {
            val notification = NotificationHelper.buildNotification(this, SensorStatus.NEAR, i)
            notificationManager.notify(i, notification)
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        updateNotification()
        proximitySensor?.let { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI) }
        lightSensor?.let { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI) }
        return START_STICKY
    }

    private fun updateNotification() {
        val notification = NotificationHelper.buildNotification(this, currentStatus)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(1, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        } else {
            startForeground(1, notification)
        }
    }

    private fun broadcastStatus(status: SensorStatus) {
        val broadcastIntent = Intent(Constants.ACTION_PROXIMITY_STATUS_CHANGED).apply {
            putExtra(Constants.EXTRA_PROXIMITY_STATUS, status.name)
        }
        sendBroadcast(broadcastIntent)
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
