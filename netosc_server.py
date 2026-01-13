import asyncio
import json
from collections import defaultdict

import websockets

# Config
HOST = "127.0.0.1"
PORT = 8765


# Global state
clients = {}  # client_id -> websocket
subscriptions = defaultdict(list)  # client_id -> [topics]
published_topics = defaultdict(set)  # client_id -> set(addresses)


# Topic matching
def topic_matches(address: str, pattern: str) -> bool:
    if pattern == "/*":
        return True
    if pattern.endswith("*"):
        return address.startswith(pattern[:-1])
    return address == pattern


# State broadcast
async def broadcast_state():
    state_msg = {
        "type": "state",
        "clients": {
            cid: sorted(list(topics))
            for cid, topics in published_topics.items()
        }
    }

    message = json.dumps(state_msg)

    for ws in clients.values():
        await ws.send(message)

# =========================================================
# Message handling
# =========================================================

async def handle_subscribe(client_id, data):
    topics = data.get("topics", [])
    subscriptions[client_id] = topics
    print(f"[SUBSCRIBE] {client_id} → {topics}")

async def handle_osc(client_id, data):
    address = data["address"]
    args = data["args"]

    published_topics[client_id].add(address)

    print(f"[OSC IN] {client_id} | {address} {args}")

    # Relay to interested clients
    for target_id, target_ws in clients.items():
        if target_id == client_id:
            continue

        for pattern in subscriptions.get(target_id, []):
            if topic_matches(address, pattern):
                msg = {
                    "type": "osc",
                    "address": address,
                    "args": args
                }
                await target_ws.send(json.dumps(msg))
                break

    await broadcast_state()

# =========================================================
# Client lifecycle
# =========================================================

async def handle_client(ws):
    client_id = None

    try:
        async for message in ws:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "subscribe":
                client_id = data["client_id"]
                clients[client_id] = ws
                await handle_subscribe(client_id, data)
                await broadcast_state()

            elif msg_type == "osc":
                if client_id is None:
                    client_id = data["client_id"]
                    clients[client_id] = ws

                await handle_osc(client_id, data)

            else:
                print(f"[WARN] Unknown message type: {msg_type}")

    except websockets.exceptions.ConnectionClosed:
        pass

    finally:
        if client_id:
            print(f"[DISCONNECT] {client_id}")
            clients.pop(client_id, None)
            subscriptions.pop(client_id, None)
            published_topics.pop(client_id, None)
            await broadcast_state()

# =========================================================
# Main
# =========================================================

async def main():
    print(f"Starting netOSC server on {HOST}:{PORT}")
    async with websockets.serve(handle_client, HOST, PORT):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
