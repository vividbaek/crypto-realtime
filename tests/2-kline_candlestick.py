import asyncio
import websockets
import json
import time
from datetime import datetime

async def kline_test():
    intervals = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
    streams = [f"btcusdt@kline_{i}" for i in intervals]
    url = f"wss://fstream.binance.com/stream?streams={'/'.join(streams)}"

    total_count = 0
    sec_count = 0
    start_time = time.time()
    last_report_time = start_time
    printed_samples = 0

    print("🚀 Kline/Candlestick 테스트 시작")
    print(f"구독 타임프레임: {len(intervals)}개 (1m ~ 1M)")
    print(f"구독 스트림 예시: {streams[:3]}... 등")

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
                    k = payload.get("k", {})  # Kline 데이터는 k 객체 안에 있음

                    if printed_samples < 10:
                        print(f"\n📥 [{datetime.now().strftime('%H:%M:%S')}] {stream_name}")
                        print(json.dumps(payload, indent=2)[:800])  # 조금 더 길게 출력
                        printed_samples += 1
                    else:
                        interval = k.get("i", "N/A")
                        close_price = k.get("c", "N/A")
                        volume = k.get("v", "N/A")
                        is_closed = "마감" if k.get("x", False) else "진행중"
                        print(f"📊 {stream_name} | 종가: {close_price} | 거래량: {volume} | 상태: {is_closed}", end='\r')
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
    asyncio.run(kline_test())