package com.bryan.proximitynotification.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.Button
import androidx.compose.material.MaterialTheme
import androidx.compose.material.Surface
import androidx.compose.material.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.bryan.proximitynotification.model.SensorStatus

import androidx.compose.ui.platform.LocalContext
import android.content.Intent
import com.bryan.proximitynotification.util.Constants

@Composable
fun HomeScreen(
    status: SensorStatus,
    running: Boolean,
    onStartService: () -> Unit,
    onStopService: () -> Unit
) {
    val context = LocalContext.current
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colors.background
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            StatusCard(status = status)
            Spacer(modifier = Modifier.height(24.dp))
            Button(onClick = onStartService, enabled = !running) {
                Text(text = "Mulai Sensor")
            }
            Spacer(modifier = Modifier.height(12.dp))
            Button(onClick = onStopService, enabled = running) {
                Text(text = "Hentikan Sensor")
            }
            
            Spacer(modifier = Modifier.height(32.dp))
            Text(text = "Mode Debug", style = MaterialTheme.typography.caption)
            Button(
                onClick = { 
                    // Simulasi status NEAR untuk tes
                    val intent = Intent(com.bryan.proximitynotification.util.Constants.ACTION_PROXIMITY_STATUS_CHANGED).apply {
                        putExtra(com.bryan.proximitynotification.util.Constants.EXTRA_PROXIMITY_STATUS, com.bryan.proximitynotification.model.SensorStatus.NEAR.name)
                        setPackage(context.packageName)
                    }
                    context.sendBroadcast(intent)
                },
                modifier = Modifier.padding(top = 8.dp)
            ) {
                Text(text = "Tes Tampilan Lockscreen (NEAR)")
            }
        }
    }
}
