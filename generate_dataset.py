import json
import random
import base64

NUM_MESSAGES = 10000
OUTPUT_FILE = "netosc_test_dataset.jsonl"

TOPICS = [
    "/foo",
    "/bar",
    "/baz",
    "/foo/x",
    "/foo/y",
    "/random"
]

PAYLOAD_SIZES = [8, 32, 128, 512, 1024]
PAYLOAD_TYPES = ["int", "float", "string", "blob"]

random.seed(42)  # critical for reproducibility


def generate_payload():
    kind = random.choice(PAYLOAD_TYPES)

    if kind == "int":
        value = random.randint(0, 100000)
        return kind, value, None

    if kind == "float":
        value = random.random()
        return kind, value, None

    if kind == "string":
        size = random.choice(PAYLOAD_SIZES)
        value = "x" * size
        return kind, value, size

    if kind == "blob":
        size = random.choice(PAYLOAD_SIZES)
        raw = bytes(random.getrandbits(8) for _ in range(size))
        value = base64.b64encode(raw).decode("ascii")
        return kind, value, size


with open(OUTPUT_FILE, "w") as f:
    for seq in range(NUM_MESSAGES):
        topic = random.choice(TOPICS)
        payload_type, payload, size = generate_payload()

        record = {
            "seq": seq,
            "topic": topic,
            "payload_type": payload_type,
            "payload": payload,
            "payload_size": size
        }

        f.write(json.dumps(record) + "\n")

print(f"Wrote {NUM_MESSAGES} messages to {OUTPUT_FILE}")
