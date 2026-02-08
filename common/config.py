import os

class Config:
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092") # 환경 변수가 있으면 사용, 없으면 기본값 사용용
    
    # Binance
    BINANCE_WS_URL = "wss://fstream.binance.com/stream"
    
    # 토픽 매핑 (스트림 이름을 토픽명이랑 매칭)
    TOPIC_MAP = {
        # "bookTicker": "binance-bookticker",
        "depth": "binance-depth",
        # "trade": "binance-trade",
        # "aggTrade": "binance-trade",
        # "kline": "binance-kline",
        # "ticker": "binance-ticker",
        # "miniTicker": "binance-ticker",
        # "fundingRate": "binance-fundingrate",
        # "forceOrder": "binance-liquidation",
        # "openInterest": "binance-openinterest",
    }
    
    @classmethod
    def get_topic(cls, stream_name: str) -> str:
        """스트림 이름으로 토픽명 반환"""
        for key, topic in cls.TOPIC_MAP.items():
            if key in stream_name:
                return topic
        return "binance-other"