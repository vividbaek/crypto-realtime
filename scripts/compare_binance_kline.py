#!/usr/bin/env python3
"""
Kafka binance-kline 토픽에서 Binance 1분봉만 읽어서 테이블로 출력.
Spark kline Job 대신 가벼운 컨슈머로, 터미널 3에서 preprocess(우리 1분봉)와 나란히 비교용.

실행: python3 scripts/compare_binance_kline.py
(프로젝트 루트에서, venv 활성화 후)
"""
import json
import sys
from datetime import datetime, timezone

try:
    from kafka import KafkaConsumer
except ImportError:
    print("kafka-python 필요: pip install kafka-python")
    sys.exit(1)

BOOTSTRAP = "localhost:9092"
TOPIC = "binance-kline"


def main():
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP,
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    print(f"📥 {TOPIC} 구독 중 (Binance 1분봉, 봉 닫힐 때만 출력). Ctrl+C 종료.\n")
    try:
        for msg in consumer:
            data = msg.value
            if not data or "data" not in data:
                continue
            payload = data.get("data", {})
            k = payload.get("k", {})
            if not k:
                continue
            # 봉이 닫힐 때만 출력 (우리 1분봉과 같은 시점으로 비교)
            if not k.get("x", False):
                continue
            t_ms = int(k.get("t", 0))
            window_start = datetime.fromtimestamp(t_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            row = {
                "window_start": window_start,
                "symbol": k.get("s", ""),
                "open": float(k.get("o", 0)),
                "high": float(k.get("h", 0)),
                "low": float(k.get("l", 0)),
                "close": float(k.get("c", 0)),
                "volume": float(k.get("v", 0)),
                "trades": int(k.get("n", 0)),
            }
            print(
                f"[Binance 1m] {row['window_start']} | "
                f"O:{row['open']} H:{row['high']} L:{row['low']} C:{row['close']} | "
                f"V:{row['volume']} n:{row['trades']}"
            )
    except KeyboardInterrupt:
        print("\n종료.")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
