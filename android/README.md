# Samsung A51 sensor sender

This is a small native Android app for the Samsung A51. It reads the phone's proximity sensor and screen touch, then sends OSC UDP control packets to the Python computer. It does not contain any audio and does not play Max/MSP files.

## Build and install

Open this `android/` folder in Android Studio. Use Android SDK 35 and JDK 17. Build and install the `app` module on the Samsung A51. The device serial shown by ADB should be `RR8NA0E20XY` when USB debugging is enabled.

The computer and phone must be on the same Wi-Fi. In the app, enter the computer's LAN IP, not `127.0.0.1`; `127.0.0.1` on the phone means the phone itself. Press **Connect sensor**. Python must already be running:

```sh
python3 main.py sensor --sensor-host 0.0.0.0 --sensor-port 8001 --category HIGH
```

The app sends `/sensor/proximity`, `/sensor/touch`, and `/sensor/held` at 10 Hz to the computer's UDP 8001. Python sends control and trigger OSC to Max/MSP UDP 8000.

## Physical behavior

The Android proximity sensor is normalized using its maximum range. Many phones report only near/far, so intermediate levels depend on the device sensor. Touch is screen touch while the app is active. `HELD` is generated after touch + proximity >= 0.8 for 600 ms, and Python independently debounces it as a second safety layer. When the app is backgrounded, it stops sending and Python should be treated as disconnected.

The app intentionally has no WebView, UI notification cards, audio player, or audio assets. It is only the hardware sensor sender.
