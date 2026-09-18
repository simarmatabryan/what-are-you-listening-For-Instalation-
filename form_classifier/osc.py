from pythonosc.udp_client import SimpleUDPClient


class MaxOSC:
    def __init__(self, host="127.0.0.1", port=8000):
        self.host = host
        self.port = port
        self.client = SimpleUDPClient(host, port)

    def send_state(self, state):
        state = str(state).strip().upper()

        mapping = {
            "LOW": "Low",
            "MIDDLE": "Middle",
            "HIGH": "High",
            "STOP": "Stop",
        }

        if state not in mapping:
            raise ValueError(f"State tidak valid: {state}")

        value = mapping[state]

        self.client.send_message(
            "/screen_time",
            value
        )

        print(
            f"OSC → /screen_time {value} "
            f"→ {self.host}:{self.port}"
        )

        return value

    def send_category(
        self,
        category,
        total=0,
        new_response=False
    ):
        value = self.send_state(category)

        return {
            "/screen_time/category": value,
            "/screen_time/total": total,
        }

    def stop(self):
        return self.send_state("STOP")