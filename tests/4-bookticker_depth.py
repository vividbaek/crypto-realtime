import asyncio
import websockets
import json
import time
from datetime import datetime

async def book_depth_test():
    streams = ["btcusdt@bookTicker", "btcusdt@depth@100ms"]  # BookTicker + Depth 100ms
    url = f"wss://fstream.binance.com/stream?streams={'/'.join(streams)}"

    total_count = 0
    sec_count = 0
    start_time = time.time()
    last_report_time = start_time
    printed_samples = 0

    print("🚀 Book Ticker / Depth 테스트 시작")
    print(f"구독: {streams}")
    print("💡 Depth는 고빈도라 TPS 높을 수 있음!")

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
                        print(json.dumps(payload, indent=2)[:800])  # 자세히 출력
                        printed_samples += 1
                    else:
                        if "bookTicker" in stream_name:
                            bid_price = payload.get("b", "N/A")
                            bid_qty = payload.get("B", "N/A")
                            ask_price = payload.get("a", "N/A")
                            ask_qty = payload.get("A", "N/A")
                            print(f"📊 {stream_name} | Bid: {bid_price} ({bid_qty}) | Ask: {ask_price} ({ask_qty})", end='\r')
                        else:  # Depth
                            bid_update = payload.get("b", [])
                            ask_update = payload.get("a", [])
                            print(f"📊 {stream_name} | Bid 업데이트: {len(bid_update)} | Ask 업데이트: {len(ask_update)}", end='\r')
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

if __name__ == "__main__":
    asyncio.run(book_depth_test())