# collectors/aggtrade_collector.py
import asyncio
from collectors.base_collector import BaseBinanceCollector
from utils.binance_stream_enum import BinanceStreamType


class AggTradeCollector(BaseBinanceCollector):
    """
    Binance Aggregate Trade 데이터 수집기
    
    수집 데이터:
    - e: 이벤트 타입 (aggTrade)
    - s: 심볼 (BTCUSDT)
    - a: Aggregate trade ID
    - p: 체결 가격
    - q: 체결 수량
    - f: First trade ID
    - l: Last trade ID
    - T: 체결 시각
    - m: 매수자가 maker인지 여부
    """
    
    async def process_data(self, stream_name: str, payload: dict):
        """
        aggTrade 데이터를 Kafka로 전송
        
        Args:
            stream_name: 스트림 이름 (btcusdt@aggTrade)
            payload: Binance에서 전송한 원본 데이터
        """
        # 데이터를 그대로 Kafka로 전송 (Spark에서 파싱)
        await self._send_to_kafka(stream_name, payload)


# 실행 예시
if __name__ == "__main__":
    # BTC/USDT aggTrade 스트림 구독
    streams = [BinanceStreamType.AGG_TRADE]
    collector = AggTradeCollector("btcusdt", streams)
    
    print("=" * 60)
    print("🚀 Binance Aggregate Trade 수집기 시작")
    print("=" * 60)
    print(f"📊 수집 대상: BTCUSDT")
    print(f"📡 스트림: {streams[0].value}")
    print(f"⚡ 업데이트: 100ms마다")
    print("=" * 60)
    print()
    
    asyncio.run(collector.start())
