package id.installation.sensorphone;

import java.io.ByteArrayOutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;

/** Minimal OSC 1.0 UDP encoder for one int or float argument. */
final class UdpOsc {
    private final InetAddress address;
    private final int port;
    private final DatagramSocket socket = new DatagramSocket();
    UdpOsc(InetAddress address, int port) throws java.net.SocketException { this.address = address; this.port = port; }

    void sendFloat(String path, float value) throws Exception { send(path, ",f", ByteBuffer.allocate(4).order(ByteOrder.BIG_ENDIAN).putFloat(value).array()); }
    void sendInt(String path, int value) throws Exception { send(path, ",i", ByteBuffer.allocate(4).order(ByteOrder.BIG_ENDIAN).putInt(value).array()); }

    private void send(String path, String type, byte[] argument) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        writePadded(out, path.getBytes("UTF-8"));
        writePadded(out, type.getBytes("UTF-8"));
        out.write(argument);
        byte[] data = out.toByteArray();
        socket.send(new DatagramPacket(data, data.length, address, port));
    }

    private static void writePadded(ByteArrayOutputStream out, byte[] value) {
        out.write(value, 0, value.length);
        out.write(0);
        while (out.size() % 4 != 0) out.write(0);
    }
    void close() { socket.close(); }
}
