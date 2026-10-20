package com.bryan.proximitynotification

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast

import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.ContextCompat

import com.bryan.proximitynotification.model.SensorStatus
import com.bryan.proximitynotification.service.SensorService
import com.bryan.proximitynotification.theme.ProximityNotificationTheme
import com.bryan.proximitynotification.ui.LockscreenUI
import com.bryan.proximitynotification.util.Constants


class MainActivity : ComponentActivity() {

    private var currentStatus by mutableStateOf(
        SensorStatus.UNKNOWN
    )

    private var serviceEnabled by mutableStateOf(false)

    private lateinit var statusReceiver: BroadcastReceiver


    private val requestPermissionLauncher =
        registerForActivityResult(
            ActivityResultContracts.RequestPermission()
        ) { isGranted ->

            if (isGranted) {
                Toast.makeText(
                    this,
                    "Izin notifikasi diberikan",
                    Toast.LENGTH_SHORT
                ).show()
            } else {
                Toast.makeText(
                    this,
                    "Izin notifikasi ditolak",
                    Toast.LENGTH_LONG
                ).show()
            }
        }


    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)


        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {

            setShowWhenLocked(true)
            setTurnScreenOn(true)

        } else {

            window.addFlags(
                android.view.WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                        android.view.WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
            )
        }


        checkNotificationPermission()


        statusReceiver =
            object : BroadcastReceiver() {

                override fun onReceive(
                    context: Context?,
                    intent: Intent?
                ) {

                    val statusName =
                        intent?.getStringExtra(
                            Constants.EXTRA_PROXIMITY_STATUS
                        )

                    if (statusName != null) {

                        try {

                            currentStatus =
                                SensorStatus.valueOf(statusName)

                            serviceEnabled = true

                        } catch (e: Exception) {

                            e.printStackTrace()
                        }
                    }
                }
            }


        ContextCompat.registerReceiver(
            this,
            statusReceiver,
            IntentFilter(
                Constants.ACTION_PROXIMITY_STATUS_CHANGED
            ),
            ContextCompat.RECEIVER_NOT_EXPORTED
        )


        setContent {

            ProximityNotificationTheme {

                LockscreenUI(

                    status = currentStatus,

                    onStartService = {
                        startSensorService()
                    },

                    running = serviceEnabled
                )
            }
        }
    }


    private fun startSensorService() {

        if (serviceEnabled) {
            return
        }

        val intent =
            Intent(
                this,
                SensorService::class.java
            )

        ContextCompat.startForegroundService(
            this,
            intent
        )

        serviceEnabled = true

        Toast.makeText(
            this,
            "Proximity Sensor Aktif",
            Toast.LENGTH_SHORT
        ).show()
    }


    private fun checkNotificationPermission() {

        if (
            Build.VERSION.SDK_INT >=
            Build.VERSION_CODES.TIRAMISU
        ) {

            if (
                ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.POST_NOTIFICATIONS
                ) != PackageManager.PERMISSION_GRANTED
            ) {

                requestPermissionLauncher.launch(
                    Manifest.permission.POST_NOTIFICATIONS
                )
            }
        }
    }


    override fun onDestroy() {

        try {
            unregisterReceiver(statusReceiver)
        } catch (_: Exception) {
        }

        super.onDestroy()
    }
}