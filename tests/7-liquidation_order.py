import asyncio
import websockets
import json
import time
from datetime import datetime

async def liquidation_test():
    streams = ["btcusdt@forceOrder"]  # Liquidation Order (청산 주문)
    url = f"wss://fstream.binance.com/stream?streams={'/'.join(streams)}"

    total_count = 0
    sec_count = 0
    start_time = time.time()
    last_report_time = start_time
    printed_samples = 0

    print("🚀 Liquidation Order 테스트 시작 (선물 전용)")
    print(f"구독: {streams}")
    print("💡 청산 발생 시 데이터 올 수 있음 - 시장 변동성 따라 빈도 다름!")

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
                    order = payload.get("o", {})  # 청산 주문 객체

                    if printed_samples < 10:
                        print(f"\n📥 [{datetime.now().strftime('%H:%M:%S')}] {stream_name}")
                        print(json.dumps(payload, indent=2))
                        printed_samples += 1
                    else:
                        side = order.get("S", "N/A")  # BUY/SELL
                        qty = order.get("q", "N/A")
                        price = order.get("p", "N/A")
                        print(f"📊 {stream_name} | 측면: {side} | 수량: {qty} | 가격: {price}", end='\r')
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
    asyncio.run(liquidation_test())