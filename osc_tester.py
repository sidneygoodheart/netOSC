import asyncio
import csv
import json
import time
import base64

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

# =========================================================
# Configuration
# =========================================================
MESSAGES_PER_SECOND = 500
DURATION_SECONDS = 30

DATASET_FILE = "netosc_test_dataset.jsonl"
OUTPUT_FILE = f"netOSC{MESSAGES_PER_SECOND}.csv"

# netOSC client A
SEND_IP = "127.0.0.1"
SEND_PORT = 9000      # netOSC client A listens here

# tester receives replies here
RECV_IP = "0.0.0.0"
RECV_PORT = 8000      # must match client A target port

# =========================================================
# Load dataset (NO timestamps inside)
# =========================================================

def load_dataset(path):
    dataset = []

    with open(path, "r") as f:
        for line in f:
            entry = json.loads(line)

            payload = entry["payload"]
            if entry["payload_type"] == "blob":
                payload = base64.b64decode(payload)

            dataset.append((
                entry["seq"],
                entry["topic"],
                payload
            ))

    return dataset

# =========================================================
# RTT measurement
# =========================================================

START_TIME = time.monotonic()

results = []

async def recv_handler(address, seq_id, send_ts, payload):
    recv_ts = time.monotonic() - START_TIME
    rtt = recv_ts - send_ts
    results.append((seq_id, address, rtt))


def recv_handler_sync(address, *args):
    asyncio.get_running_loop().create_task(
        recv_handler(address, *args)
    )


async def start_receiver():
    dispatcher = Dispatcher()
    dispatcher.set_default_handler(recv_handler_sync)

    server = AsyncIOOSCUDPServer(
        (RECV_IP, RECV_PORT),
        dispatcher,
        asyncio.get_running_loop()
    )

    transport, _ = await server.create_serve_endpoint()
    print(f"Tester listening on {RECV_IP}:{RECV_PORT}")
    return transport

# =========================================================
# Sender (cyclic replay, timestamp injected here)
# =========================================================

async def sender(dataset, messages_per_second, duration_seconds):
    osc_out = SimpleUDPClient(SEND_IP, SEND_PORT)

    interval = 1.0 / messages_per_second
    max_messages = int(messages_per_second * duration_seconds)
    dataset_len = len(dataset)

    print(f"Sending {max_messages} messages at {messages_per_second} msg/s")

    for i in range(max_messages):
        seq, topic, payload = dataset[i % dataset_len]

        send_ts = time.monotonic() - START_TIME
        osc_out.send_message(topic, (seq, send_ts, payload))

        await asyncio.sleep(interval)

# =========================================================
# Main
# =========================================================

async def main():
    dataset = load_dataset(DATASET_FILE)
    print(f"Loaded dataset with {len(dataset)} messages")

    recv_transport = await start_receiver()

    await sender(
        dataset,
        MESSAGES_PER_SECOND,
        DURATION_SECONDS
    )

    # allow late packets to arrive
    await asyncio.sleep(3)

    recv_transport.close()

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["seq_id", "topic", "rtt_seconds"])
        writer.writerows(results)

    sent = int(MESSAGES_PER_SECOND * DURATION_SECONDS)
    received = len(results)

    print(f"Sent: {sent}, Received: {received}")
    if sent > 0:
        print(f"Loss rate: {(sent - received) / sent:.2%}")

    print(f"Wrote {received} RTT samples to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
