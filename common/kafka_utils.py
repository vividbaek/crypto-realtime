from kafka import KafkaProducer
import json
import logging

logger = logging.getLogger(__name__)

class KafkaProducerWrapper:
    _instance = None  # 싱글톤

    def __new__(cls, bootstrap_servers="localhost:9092"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.producer = KafkaProducer(
                bootstrap_servers=[bootstrap_servers], # 카프카 서버 주소
                value_serializer=lambda v: json.dumps(v).encode('utf-8'), # 값 직렬화 dict -> json string -> bytes (바이트로 변환)
                key_serializer=lambda k: k.encode('utf-8') if k else None, # 키 직렬화 str -> bytes (바이트로 변환)
                batch_size=32768, # 배치 크기 (네트워크 효율 높임)
                linger_ms=10, # 대기 시간 (메시지가 도착하면 10ms 기다린 후 모아서 전송, 0이면 즉시 전송 (배치 효과없음))
                compression_type='gzip', # 압축 타입
                acks='all', #모든 복제본이 메시지를 받았는지 확인 (all - 가장 안전(데이터 손실 x), 1- 리더만 확인 (빠르지만 손실 가능), 0 - 확인 안함 (가장 빠르지만 위험))
                retries=3, # 재시도 횟수
            )
            logger.info(f"Kafka Producer 생성: {bootstrap_servers}")
        return cls._instance

    def send(self, topic: str, value: dict, key: str = None):
        return self.producer.send(topic=topic, value=value, key=key)

    def flush(self):
        self.producer.flush()

    def close(self):
        self.producer.close()