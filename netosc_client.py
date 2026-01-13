import asyncio
import json
import uuid
import socket

import websockets
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

# =========================================================
# Configuration
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
known_clients = {}

exit_event = asyncio.Event()
reconnect_event = asyncio.Event()

# =========================================================
# OSC → WebSocket
# =========================================================

async def osc_handler(address, *args):
    if ws_connection is None:
        print("OSC received but WebSocket not connected")
        return

    msg = {
        "type": "osc",
        "client_id": CLIENT_ID,
        "address": address,
        "args": args
    }

    print(f"OSC → WS | {address} {args}")
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
# WebSocket → OSC
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

# =========================================================
# Subscriptions
# =========================================================

async def send_subscriptions():
    if ws_connection is None:
        return

    msg = {
        "type": "subscribe",
        "client_id": CLIENT_ID,
        "topics": SUBSCRIBE_TOPICS
    }

    print(f"Sending subscriptions: {SUBSCRIBE_TOPICS}")
    await ws_connection.send(json.dumps(msg))

# =========================================================
# WebSocket connection loop (with reconnect)
# =========================================================

async def connection_loop():
    global ws_connection

    backoff = 2

    while not exit_event.is_set():
        try:
            print(f"Connecting to broker: {BROKER_URL}")
            async with websockets.connect(
                BROKER_URL,
                family=socket.AF_INET,
            ) as ws:
                ws_connection = ws
                print("WebSocket connected")

                await send_subscriptions()
                backoff = 2  # reset after success

                async for message in ws:
                    await handle_server_message(message)

        except Exception as e:
            ws_connection = None
            print(f"WebSocket disconnected: {e}")

            if exit_event.is_set():
                break

            print(f"Reconnecting in {backoff}s...")
            try:
                await asyncio.wait_for(
                    reconnect_event.wait(),
                    timeout=backoff
                )
            except asyncio.TimeoutError:
                pass

            reconnect_event.clear()
            backoff = min(backoff * 2, 30)

def print_status():
    print("Status:")
    print(f"  Broker: {BROKER_URL}")
    print(f"  Connected: {'yes' if ws_connection else 'no'}")
    print(f"  Subscriptions: {SUBSCRIBE_TOPICS}")
    print(f"  Known clients: {len(known_clients)}")


def print_known_clients():
    if not known_clients:
        print("No known clients")
        return

    print("Known clients:")
    for cid, topics in known_clients.items():
        print(f"  {cid}")
        for t in topics:
            print(f"    - {t}")

# =========================================================
# Command line input loop
# =========================================================

async def command_loop():
    loop = asyncio.get_running_loop()

    print("Commands:")
    print("  -r            reconnect")
    print("  -x            exit")
    print("  -t <topics>   set topics (comma-separated)")
    print("  -s            status")
    print("  -l            list known clients")
    print()

    while not exit_event.is_set():
        cmd = await loop.run_in_executor(None, input, "> ")
        cmd = cmd.strip()

        if cmd == "-x":
            print("Exiting...")
            exit_event.set()
            reconnect_event.set()
            break

        elif cmd == "-r":
            print("Forcing reconnect")
            reconnect_event.set()

        elif cmd == "-s":
            print_status()

        elif cmd == "-l":
            print_known_clients()

        elif cmd.startswith("-t"):
            parts = cmd.split(maxsplit=1)
            if len(parts) != 2:
                print("Usage: -t /foo,/bar/*")
                continue

            topics = [t.strip() for t in parts[1].split(",") if t.strip()]
            if not topics:
                print("No topics provided")
                continue

            SUBSCRIBE_TOPICS.clear()
            SUBSCRIBE_TOPICS.extend(topics)
            print(f"Updated topics: {SUBSCRIBE_TOPICS}")
            await send_subscriptions()

        else:
            print("Unknown command")


# =========================================================
# Main
# =========================================================

async def main():
    osc_transport = await start_osc_server()

    tasks = [
        asyncio.create_task(connection_loop()),
        asyncio.create_task(command_loop()),
    ]

    await exit_event.wait()

    for t in tasks:
        t.cancel()

    osc_transport.close()
    print("Client shut down")


if __name__ == "__main__":
    asyncio.run(main())
