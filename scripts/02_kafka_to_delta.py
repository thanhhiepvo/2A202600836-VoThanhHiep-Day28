# scripts/02_kafka_to_delta.py
"""Consume Kafka topic and save to Delta Lake (parquet) — Integration 2."""
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from kafka import KafkaConsumer

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DELTA_PATH = Path(__file__).resolve().parent.parent / "delta-lake" / "raw"


def consume_and_save():
    consumer = KafkaConsumer(
        "data.raw",
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset="earliest",
        consumer_timeout_ms=5000,
        value_deserializer=lambda m: json.loads(m.decode()),
    )
    records = [msg.value for msg in consumer]
    print(f"Consumed {len(records)} records from Kafka")

    if not records:
        print("No records to save")
        return

    DELTA_PATH.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records)
    outfile = DELTA_PATH / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
    df.to_parquet(outfile)
    print(f"Integration 2 OK: Saved {len(df)} records to {outfile}")


if __name__ == "__main__":
    consume_and_save()
