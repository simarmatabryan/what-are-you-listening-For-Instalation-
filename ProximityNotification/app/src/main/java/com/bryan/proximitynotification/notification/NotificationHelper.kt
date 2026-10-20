package com.bryan.proximitynotification.notification

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.bryan.proximitynotification.MainActivity
import com.bryan.proximitynotification.R
import com.bryan.proximitynotification.model.SensorStatus

object NotificationHelper {
    const val CHANNEL_ID = "proximity_notification_channel"
    private const val CHANNEL_NAME = "Proximity Sensor"
    private const val NOTIFICATION_ID = 1

    fun createChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (manager.getNotificationChannel(CHANNEL_ID) == null) {
                val channel = NotificationChannel(
                    CHANNEL_ID,
                    CHANNEL_NAME,
                    NotificationManager.IMPORTANCE_HIGH
                ).apply {
                    description = "Notifikasi status sensor jarak"
                    enableVibration(true)
                    lockscreenVisibility = Notification.VISIBILITY_PUBLIC
                }
                manager.createNotificationChannel(channel)
            }
        }
    }

    fun buildNotification(context: Context, status: SensorStatus, id: Int = NOTIFICATION_ID): Notification {
        val launchIntent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            context,
            0,
            launchIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val contentTitle = if (status == SensorStatus.NEAR) "⚠️ PERINGATAN: TERLALU DEKAT! ⚠️" else "Proximity Sensor Aktif"
        val contentText = when (status) {
            SensorStatus.NEAR -> "Seseorang sangat dekat dengan perangkat Anda!"
            SensorStatus.FAR -> "Jarak aman terdeteksi."
            SensorStatus.UNKNOWN -> "Menunggu data sensor..."
        }

        return NotificationCompat.Builder(context, CHANNEL_ID)
            .setContentTitle(contentTitle)
            .setContentText(contentText)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentIntent(pendingIntent)
            .setFullScreenIntent(pendingIntent, true) // Tambahkan Full Screen Intent agar otomatis muncul
            .setOngoing(status == SensorStatus.NEAR)
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setVibrate(longArrayOf(0, 500, 100, 500, 100, 500))
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setGroup("proximity_group")
            .setGroupSummary(id == NOTIFICATION_ID)
            .build()
    }
}
