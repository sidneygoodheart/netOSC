import asyncio
import json
import uuid

import websockets
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

# =========================================================
# Hard-coded configuration (development)
# =========================================================

CLIENT_ID = str(uuid.uuid4())

BROKER_URL = "wss://dev.503e.foo/netOSC"

OSC_LISTEN_IP = "127.0.0.1"
OSC_LISTEN_PORT = 8000

OSC_TARGET_IP = "127.0.0.1"
OSC_TARGET_PORT = 9000

SUBSCRIBE_TOPICS = ["/*"]

# =========================================================
# Global state
# =========================================================

ws_connection = None
known_clients = {}  # read-only cache from server

# =========================================================
# OSC → WebSocket (pure relay)
# =========================================================

async def osc_handler(address, *args):
    if ws_connection is None:
        print("OSC received but WebSocket not connected")
        return

    print(f"OSC → WS  | {address} {args}")

    msg = {
        "type": "osc",
        "client_id": CLIENT_ID,
        "address": address,
        "args": args
    }

    await ws_connection.send(json.dumps(msg))

def osc_handler_sync(address, *args):
    asyncio.get_running_loop().create_task(
        osc_handler(address, *args)
    )

async def start_osc_server():
    dispatcher = Dispatcher()
    dispatcher.set_default_handler(osc_handler_sync)

    server = AsyncIOOSCUDPServer(
        (OSC_LISTEN_IP, OSC_LISTEN_PORT),
        dispatcher,
        asyncio.get_running_loop()
    )

    transport, _ = await server.create_serve_endpoint()
    print(f"OSC listening on {OSC_LISTEN_IP}:{OSC_LISTEN_PORT}")
    return transport

# =========================================================
# WebSocket → OSC (pure relay)
# =========================================================

osc_out_client = SimpleUDPClient(OSC_TARGET_IP, OSC_TARGET_PORT)


async def handle_server_message(message):
    global known_clients

    data = json.loads(message)

    if data["type"] == "osc":
        print(f"WS → OSC | {data['address']} {data['args']}")
        osc_out_client.send_message(
            data["address"],
            data["args"]
        )

    elif data["type"] == "state":
        known_clients = data["clients"]
        print(f"WS ← state | {known_clients}")

    else:
        print(f"Unknown message type: {data.get('type')}")

# =========================================================
# WebSocket connection + subscription
# =========================================================

async def send_subscriptions():
    print(f"Sending subscriptions: {SUBSCRIBE_TOPICS}")
    msg = {
        "type": "subscribe",
        "client_id": CLIENT_ID,
        "topics": SUBSCRIBE_TOPICS
    }
    await ws_connection.send(json.dumps(msg))


async def websocket_loop():
    global ws_connection

    print(f"Connecting to broker: {BROKER_URL}")
    async with websockets.connect(BROKER_URL) as ws:
        ws_connection = ws
        print("WebSocket connected")

        await send_subscriptions()

        async for message in ws:
            await handle_server_message(message)

# =========================================================
# Main
# =========================================================

async def main():
    osc_transport = await start_osc_server()
    ws_task = asyncio.create_task(websocket_loop())

    try:
        await ws_task
    finally:
        osc_transport.close()
        print("OSC server shut down")

if __name__ == "__main__":
    asyncio.run(main())
