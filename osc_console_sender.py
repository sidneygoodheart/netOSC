from pythonosc.udp_client import SimpleUDPClient

OSC_TARGET_IP = "127.0.0.1"
OSC_TARGET_PORT = 8000

client = SimpleUDPClient(OSC_TARGET_IP, OSC_TARGET_PORT)

print("OSC console sender")
print("Enter messages as: /path value")
print("Press Ctrl+C to quit")

while True:
    try:
        line = input("> ").strip()
        if not line:
            continue

        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            print("Invalid input. Use: /path value")
            continue

        address, value = parts

        # try to cast value to int or float if possible
        if value.isdigit():
            value = int(value)
        else:
            try:
                value = float(value)
            except ValueError:
                pass  # keep as string

        client.send_message(address, value)
        print(f"Sent OSC: {address} {value}")

    except KeyboardInterrupt:
        print("\nExiting")
        break
