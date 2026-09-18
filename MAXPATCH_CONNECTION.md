# Max/MSP connection found in `Maxpatch.zip`

The supplied patch `What are you listening_max.maxpat` already listens on UDP port **8000**:

```text
udpreceive 8000
  -> OSC-route /screen_time
  -> route Low Middle High
```

The Python configuration is therefore:

```json
{
  "osc_enabled": true,
  "max_host": "127.0.0.1",
  "max_port": 8000
}
```

Start the Max patch first, then run:

```sh
python3 main.py watch
```

The current patch is case-sensitive and expects `Low`, `Middle`, and `High`; the Python OSC adapter sends those exact symbols. The flags and response count are also sent for the controller contract, but the supplied patch's visible route currently consumes `/screen_time` category messages.

This is a local UDP connection. Max must run on the same computer for `127.0.0.1`; use the Max computer's LAN address in `max_host` if Python runs elsewhere. UDP has no delivery acknowledgement. A successful send means Python handed the packet to the local network socket; Max's `udpreceive` must be running to receive it.

The patch's audio files remain owned by Max/MSP. Python does not open or play them.
