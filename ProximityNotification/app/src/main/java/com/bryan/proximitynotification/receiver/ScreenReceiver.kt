package com.bryan.proximitynotification.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.bryan.proximitynotification.service.SensorService

class ScreenReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context?, intent: Intent?) {
        if (context == null || intent == null) return

        val screenAction = intent.action
        val serviceIntent = Intent(context, SensorService::class.java)

        when (screenAction) {
            Intent.ACTION_SCREEN_ON -> {
                context.startForegroundService(serviceIntent)
            }
            Intent.ACTION_SCREEN_OFF -> {
                context.stopService(serviceIntent)
            }
        }
    }
}
