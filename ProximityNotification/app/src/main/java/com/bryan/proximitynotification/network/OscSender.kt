package com.bryan.proximitynotification.network

import android.util.Log
import java.io.ByteArrayOutputStream
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.Executors

class OscSender(
    private val host: String,
    private val port: Int
) {
    private val TAG = "OSC_PROXIMITY"
    private val executor = Executors.newSingleThreadExecutor()
    private val socket = DatagramSocket()
    @Volatile private var closed = false

    private fun oscString(value: String): ByteArray {
        val raw = value.toByteArray(Charsets.UTF_8)
        val sizeWithNull = raw.size + 1
        val paddedSize = ((sizeWithNull + 3) / 4) * 4
        val output = ByteArray(paddedSize)
        System.arraycopy(raw, 0, output, 0, raw.size)
        return output
    }

    private fun createFloatMessage(address: String, value: Float): ByteArray {
        val output = ByteArrayOutputStream()
        output.write(oscString(address))
        output.write(oscString(",f"))
        val floatBytes = ByteBuffer.allocate(4).order(ByteOrder.BIG_ENDIAN).putFloat(value).array()
        output.write(floatBytes)
        return output.toByteArray()
    }

    fun sendProximity(value: Float) {
        if (closed) return
        executor.execute {
            if (closed) return@execute
            try {
                val data = createFloatMessage("/proximity", value)
                val destination = InetAddress.getByName(host)
                val packet = DatagramPacket(data, data.size, destination, port)
                socket.send(packet)
                Log.d(TAG, "OSC SENT -> /proximity $value -> $host:$port")
            } catch (e: Exception) {
                Log.e(TAG, "OSC ERROR -> /proximity $value -> $host:$port", e)
            }
        }
    }

    fun close() {
        if (closed) return
        closed = true
        try {
            socket.close()
        } catch (_: Exception) {}
        executor.shutdown()
    }
}
