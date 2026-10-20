package com.bryan.proximitynotification.ui

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.Card
import androidx.compose.material.Icon
import androidx.compose.material.Text
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Settings
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.bryan.proximitynotification.model.SensorStatus
import com.bryan.proximitynotification.network.OscConfig
import com.bryan.proximitynotification.network.OscSender
import kotlinx.coroutines.delay
import java.text.SimpleDateFormat
import java.util.*
import kotlin.random.Random

@Composable
fun LockscreenUI(
    status: SensorStatus,
    onStartService: () -> Unit,
    running: Boolean
) {
    val isNear = status == SensorStatus.NEAR
    var bubbleCount by remember { mutableStateOf(0) }
    val bubbles = remember { mutableStateListOf<Int>() }
    var intensity by remember { mutableStateOf(0f) }
    var currentTime by remember { mutableStateOf(Calendar.getInstance().time) }
    
    LaunchedEffect(Unit) {
        while (true) {
            currentTime = Calendar.getInstance().time
            delay(1000)
        }
    }

    LaunchedEffect(isNear) {
        if (isNear) {
            var currentDelay = 800L
            while (true) {
                val batchSize = (1 + (intensity * 5)).toInt()
                repeat(batchSize) {
                    bubbles.add(0, bubbleCount++)
                }
                if (bubbles.size > 40) {
                    repeat(batchSize) { if (bubbles.isNotEmpty()) bubbles.removeAt(bubbles.size - 1) }
                }
                if (intensity < 1f) intensity += 0.08f
                delay(currentDelay)
                currentDelay = (800L * (1f - (intensity * 0.95f))).toLong().coerceAtLeast(20)
            }
        } else {
            bubbles.clear()
            intensity = 0f
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        // PERTANDA SENSOR: Hijau=Aktif, Merah=Mendeteksi
        Box(
            modifier = Modifier
                .padding(12.dp)
                .size(8.dp)
                .clip(CircleShape)
                .background(if (running) (if (isNear) Color.Red else Color.Green) else Color.Gray)
                .align(Alignment.TopStart)
        )

        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(if (isNear) Color.Red.copy(alpha = 0.05f + (intensity * 0.2f)) else Color.Transparent)
        )

        Column(
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(60.dp))
            Icon(
                imageVector = Icons.Default.Lock,
                contentDescription = null,
                tint = Color.White.copy(alpha = 0.7f),
                modifier = Modifier.size(20.dp)
            )
            
            Spacer(modifier = Modifier.height(16.dp))
            GlitchyTime(time = currentTime, isGlitching = isNear, intensity = intensity)
            Text(
                text = SimpleDateFormat("EEEE, d MMMM", Locale("id", "ID")).format(currentTime),
                color = Color.White,
                fontSize = 18.sp,
                fontFamily = FontFamily.SansSerif,
                fontWeight = FontWeight.Normal
            )

            Spacer(modifier = Modifier.height(40.dp))
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .padding(horizontal = 20.dp)
            ) {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    items(bubbles) { id ->
                        NotificationBubble(id, intensity)
                    }
                }
            }
            
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 40.dp, start = 40.dp, end = 40.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Bottom
            ) {
                Box(modifier = Modifier.size(50.dp).clip(CircleShape).background(Color.White.copy(alpha = 0.2f)).clickable { onStartService() }, contentAlignment = Alignment.Center) {
                    Icon(Icons.Default.Call, null, tint = Color.White)
                }
                Box(modifier = Modifier.size(50.dp).clip(CircleShape).background(Color.White.copy(alpha = 0.2f)), contentAlignment = Alignment.Center) {
                    Icon(Icons.Default.Settings, null, tint = Color.White)
                }
            }
        }

        // Overlay tombol start service
        if (!running) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color.Transparent)
                    .padding(bottom = 100.dp),
                contentAlignment = Alignment.BottomCenter
            ) {
                androidx.compose.material.Button(
                    onClick = onStartService,
                    colors = androidx.compose.material.ButtonDefaults.buttonColors(backgroundColor = Color.White.copy(alpha = 0.1f)),
                    shape = RoundedCornerShape(20.dp),
                    elevation = null
                ) {
                    Text("Usap ke atas untuk membuka", color = Color.White.copy(alpha = 0.5f), fontSize = 14.sp)
                }
            }
        }
    }
}

@Composable
fun GlitchyTime(time: Date, isGlitching: Boolean, intensity: Float) {
    val timeFormat = SimpleDateFormat("HH:mm", Locale.getDefault())
    var fastTimeMillis by remember { mutableStateOf(time.time) }
    LaunchedEffect(isGlitching, intensity) {
        if (isGlitching) {
            while (true) {
                val speed = (1 + (intensity * 300)).toLong()
                fastTimeMillis += (60000 * speed)
                delay(40)
            }
        } else {
            fastTimeMillis = Calendar.getInstance().timeInMillis
        }
    }
    val displayTime = if (isGlitching) Date(fastTimeMillis) else time
    val timeString = timeFormat.format(displayTime)
    val infiniteTransition = rememberInfiniteTransition()
    val shake by infiniteTransition.animateFloat(
        initialValue = -intensity * 4f,
        targetValue = intensity * 4f,
        animationSpec = infiniteRepeatable(
            animation = tween(40, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        )
    )
    Text(
        text = timeString,
        color = Color.White,
        fontSize = 82.sp,
        fontFamily = FontFamily.SansSerif,
        fontWeight = if (isGlitching) FontWeight.Bold else FontWeight.Light,
        modifier = Modifier.offset(x = shake.dp)
    )
}

@Composable
fun NotificationBubble(id: Int, intensity: Float) {
    val newsHeadlines = listOf(
        "PERINGATAN: Kebocoran Data Terdeteksi",
        "Sistem Mengalami Kegagalan Kritis",
        "Akses Ilegal Terdeteksi di Lokasi Anda",
        "Baterai Melemah: Kerusakan Perangkat Lunak",
        "Layanan Lokasi Dimanipulasi Pihak Ketiga",
        "Ancaman Terdeteksi: Segera Jauhkan Perangkat",
        "Koneksi Tidak Aman: Data Anda Sedang Disadap",
        "Suhu Perangkat Sangat Tinggi (Bahaya)",
        "Kesalahan Sistem FATAL: 0x880293",
        "Penyimpanan Terinfeksi Virus Berbahaya"
    )
    val headline = newsHeadlines[id % newsHeadlines.size]
    val randomX = remember(id) { Random.nextInt(-60, 60) }
    val currentX = randomX * intensity
    val randomRotation = remember(id) { Random.nextInt(-25, 25) }
    val currentRotation = randomRotation * intensity
    val randomScale = remember(id) { 0.8f + Random.nextFloat() * 0.4f }
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp)
            .offset(x = currentX.dp)
            .graphicsLayer(
                rotationZ = currentRotation,
                scaleX = if (intensity > 0.5f) randomScale else 1f,
                scaleY = if (intensity > 0.5f) randomScale else 1f
            ),
        shape = RoundedCornerShape(24.dp),
        backgroundColor = Color.White.copy(alpha = 0.9f),
        elevation = 0.dp
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .clip(CircleShape)
                    .background(Color(0xFFD32F2F)),
                contentAlignment = Alignment.Center
            ) {
                Text("⚠️", fontSize = 18.sp)
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column {
                Text(text = headline, fontSize = 13.sp, fontWeight = FontWeight.Bold, color = Color.Black)
                Text(text = "Berita Terbaru • Baru Saja", fontSize = 11.sp, color = Color.DarkGray)
            }
        }
    }
}
