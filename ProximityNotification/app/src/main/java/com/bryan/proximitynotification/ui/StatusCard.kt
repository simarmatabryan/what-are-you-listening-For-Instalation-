package com.bryan.proximitynotification.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.Card
import androidx.compose.material.MaterialTheme
import androidx.compose.material.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.bryan.proximitynotification.model.SensorStatus

@Composable
fun StatusCard(status: SensorStatus) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colors.surface),
        elevation = 8.dp
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Text(
                text = "Status Sensor",
                style = MaterialTheme.typography.h5,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = when (status) {
                    SensorStatus.NEAR -> "Dekat"
                    SensorStatus.FAR -> "Jauh"
                    SensorStatus.UNKNOWN -> "Menunggu data ..."
                },
                style = MaterialTheme.typography.body1,
                modifier = Modifier.padding(top = 12.dp)
            )
        }
    }
}
