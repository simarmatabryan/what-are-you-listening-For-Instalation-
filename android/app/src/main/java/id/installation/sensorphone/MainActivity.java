package id.installation.sensorphone;

import android.app.Activity;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.MotionEvent;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.net.InetAddress;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Reads only phone sensors and sends OSC control data. It has no audio assets or playback. */
public final class MainActivity extends Activity implements SensorEventListener {
    private SensorManager sensors;
    private Sensor proximitySensor;
    private UdpOsc osc;
    private EditText host;
    private TextView status;
    private float proximity = 0f;
    private boolean touch = false;
    private long heldSince = 0L;
    private final ExecutorService sender = Executors.newSingleThreadExecutor();
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable publish = new Runnable() {
        @Override public void run() {
            boolean candidate = touch && proximity >= .8f;
            if (candidate && heldSince == 0L) heldSince = SystemClock.elapsedRealtime();
            if (!candidate) heldSince = 0L;
            boolean held = candidate && SystemClock.elapsedRealtime() - heldSince >= 600L;
            if (osc != null) {
                final UdpOsc target = osc;
                final float sentProximity = proximity;
                final boolean sentTouch = touch;
                final boolean sentHeld = held;
                sender.submit(() -> {
                    try {
                        target.sendFloat("/sensor/proximity", sentProximity);
                        target.sendInt("/sensor/touch", sentTouch ? 1 : 0);
                        target.sendInt("/sensor/held", sentHeld ? 1 : 0);
                        handler.post(() -> status.setText(String.format(Locale.US,
                                "Connected · proximity %.2f · %s", sentProximity,
                                sentHeld ? "HELD" : (sentTouch ? "TOUCH" : "IDLE"))));
                    } catch (Exception error) {
                        handler.post(() -> status.setText("Send error: " + error.getMessage()));
                    }
                });
            }
            handler.postDelayed(this, 100L);
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        sensors = (SensorManager) getSystemService(SENSOR_SERVICE);
        proximitySensor = sensors.getDefaultSensor(Sensor.TYPE_PROXIMITY);
        LinearLayout layout = new LinearLayout(this);
        layout.setPadding(32, 48, 32, 32);
        layout.setOrientation(LinearLayout.VERTICAL);
        TextView title = new TextView(this);
        title.setText("Sensor Bridge → Python → Max/MSP\nPython OSC port: 8001");
        title.setTextSize(20f);
        host = new EditText(this);
        host.setSingleLine(true);
        host.setHint("IP komputer Python, contoh 192.168.1.10");
        host.setText(getPreferences(MODE_PRIVATE).getString("host", "192.168.1.10"));
        Button connect = new Button(this);
        connect.setText("Connect sensor");
        status = new TextView(this);
        status.setText(proximitySensor == null ? "Proximity sensor tidak tersedia" : "Disconnected");
        status.setTextSize(16f);
        layout.addView(title);
        layout.addView(host);
        layout.addView(connect);
        layout.addView(status);
        setContentView(layout);
        connect.setOnClickListener(view -> connectSensor());
        layout.setOnTouchListener((view, event) -> updateTouch(event));
    }

    private void connectSensor() {
        try {
            InetAddress address = InetAddress.getByName(host.getText().toString().trim());
            osc = new UdpOsc(address, 8001);
            getPreferences(MODE_PRIVATE).edit().putString("host", host.getText().toString().trim()).apply();
            status.setText("Connected to " + address.getHostAddress() + ":8001");
        } catch (Exception error) {
            status.setText("Connection error: " + error.getMessage());
        }
    }

    private boolean updateTouch(MotionEvent event) {
        if (event.getActionMasked() == MotionEvent.ACTION_DOWN) touch = true;
        if (event.getActionMasked() == MotionEvent.ACTION_UP || event.getActionMasked() == MotionEvent.ACTION_CANCEL) touch = false;
        return true;
    }

    @Override protected void onResume() {
        super.onResume();
        if (proximitySensor != null) sensors.registerListener(this, proximitySensor, SensorManager.SENSOR_DELAY_NORMAL);
        handler.post(publish);
    }
    @Override protected void onPause() {
        touch = false; heldSince = 0L;
        sensors.unregisterListener(this);
        handler.removeCallbacks(publish);
        if (osc != null) osc.close();
        osc = null;
        super.onPause();
    }
    @Override protected void onDestroy() {
        sender.shutdownNow();
        super.onDestroy();
    }
    @Override public void onSensorChanged(SensorEvent event) {
        float maximum = event.sensor.getMaximumRange();
        proximity = maximum > 0 ? Math.max(0f, Math.min(1f, 1f - event.values[0] / maximum)) : 0f;
    }
    @Override public void onAccuracyChanged(Sensor sensor, int accuracy) { }
}
