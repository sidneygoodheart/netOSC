import asyncio
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

LISTEN_IP = "127.0.0.1"
LISTEN_PORT = 9000      # mirror listens here

TARGET_IP = "127.0.0.1"
TARGET_PORT = 8000     # send back to tester via netOSC client

osc_out = SimpleUDPClient(TARGET_IP, TARGET_PORT)


async def osc_handler(address, *args):
    osc_out.send_message(address, args)


def osc_handler_sync(address, *args):
    asyncio.get_running_loop().create_task(
        osc_handler(address, *args)
    )


async def main():
    dispatcher = Dispatcher()
    dispatcher.set_default_handler(osc_handler_sync)

    server = AsyncIOOSCUDPServer(
        (LISTEN_IP, LISTEN_PORT),
        dispatcher,
        asyncio.get_running_loop()
    )

    transport, _ = await server.create_serve_endpoint()
    print(f"OSC mirror listening on {LISTEN_IP}:{LISTEN_PORT}")

    await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
