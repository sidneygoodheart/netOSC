import asyncio
import csv
import json
import time
import base64
from pathlib import Path

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

#
# The tester replays a fixed dataset of OSC messages cyclically at a configurable rate.
# For each message, the round-trip time is measured upon reception of the reflected message.
#

# =========================================================
# Configuration
# =========================================================

DATASET_FILE = "netosc_test_dataset.jsonl"
OUTPUT_FILE = "rtt_results.csv"

MESSAGES_PER_SECOND = 50
DURATION_SECONDS = 30

SEND_IP = "127.0.0.1"
SEND_PORT = 9000      # netOSC client A listens here

RECV_IP = "127.0.0.1"
RECV_PORT = 8000      # tester receives replies here

# =========================================================
# Load dataset
# =========================================================

def load_dataset(path: str):
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

results = []

async def recv_handler(address, seq_id, send_ts, payload):
    recv_ts = time.time()
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
# Sender
# =========================================================

async def sender(dataset, messages_per_second, duration_seconds):
    osc_out = SimpleUDPClient(SEND_IP, SEND_PORT)

    interval = 1.0 / messages_per_second
    max_messages = int(messages_per_second * duration_seconds)
    dataset_len = len(dataset)

    print(f"Sending {max_messages} messages at {messages_per_second} msg/s")

    for i in range(max_messages):
        seq, topic, payload = dataset[i % dataset_len]
        ts = time.time()
        osc_out.send_message(topic, (seq, ts, payload))
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

    # Allow late packets to arrive
    await asyncio.sleep(2)

    recv_transport.close()

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["seq_id", "topic", "rtt_seconds"])
        writer.writerows(results)

    print(f"Wrote {len(results)} RTT samples to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
