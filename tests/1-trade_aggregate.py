import asyncio
import websockets
import json
import time
from datetime import datetime

async def trade_aggtrade_test():
    streams = ["btcusdt@trade", "btcus햣 ㅑㅜㅜrade"]  # Trade + Aggregate Trade
    url = f"wss://fstream.binance.com/stream?streams={'/'.join(streams)}"

    total_count = 0
    sec_count = 0
    start_time = time.time()
    last_report_time = start_time
    printed_samples = 0

    print("🚀 Trade / Aggregate Trade 테스트 시작")
    print(f"구독: {streams}")

    try:
        async with websockets.connect(url) as ws:
            while True:
                msg = await ws.recv()
                total_count += 1
                sec_count += 1

                try:
                    data = json.loads(msg)
                    stream_name = data.get("stream", "unknown")
                    payload = data.get("data", {})

                    if printed_samples < 10:
                        print(f"\n📥 [{datetime.now().strftime('%H:%M:%S')}] {stream_name}")
                        print(json.dumps(payload, indent=2)[:500])
                        printed_samples += 1
                    else:
                        print(f"📊 {stream_name} | 가격: {payload.get('p', 'N/A')} | 수량: {payload.get('q', 'N/A')}", end='\r')
                except:
                    pass

                now = time.time()
                if now - last_report_time >= 1.0:
                    tps = sec_count / (now - last_report_time)
                    print(f"\n⏱️ TPS: {tps:.2f} msgs/sec | 누적: {total_count:,}")
                    sec_count = 0
                    last_report_time = now

    except KeyboardInterrupt:
        print("\n🛑 중단")
    finally:
        duration = time.time() - start_time
        avg_tps = total_count / duration if duration > 0 else 0
        print(f"\n📊 평균 TPS: {avg_tps:.2f} | 총 메시지: {total_count:,}")

asyncio.run(trade_aggtrade_test())