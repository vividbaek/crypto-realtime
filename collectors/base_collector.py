# collectors/base_collector.py
import asyncio
from common.config import Config
from common.kafka_utils import KafkaProducerWrapper
import websockets
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime
from utils.binance_stream_enum import BinanceStreamType

class BaseBinanceCollector(ABC):
    def __init__(self, symbol: str, streams: list):
        self.symbol = symbol.lower()
        self.streams = streams
        self.base_url = "wss://fstream.binance.com/stream?streams="
        self.url = f"{self.base_url}{'/'.join([f'{self.symbol}@{s.value if isinstance(s, BinanceStreamType) else s}' for s in streams])}"
        
        # 메트릭 관리
        self.total_count = 0
        self.sec_count = 0
        self.start_time = None
        self.last_report_time = None
        self.printed_samples = 0
        self.running = True  # 종료 플래그 추가
        self.kafka = KafkaProducerWrapper(Config.KAFKA_BOOTSTRAP_SERVERS)


    @abstractmethod
    async def process_data(self, stream_name: str, payload: dict):
        """하위 클래스에서 데이터 정제 및 카프카 전송 로직 구현"""
        pass
    
    async def _send_to_kafka(self, stream_name: str, payload: dict):
        """Kafka로 메시지 전송"""
        topic = Config.get_topic(stream_name)
        message = {
            "symbol": self.symbol.upper(),
            "stream": stream_name,
            "data": payload,
            "ts": int(time.time() * 1000)
        }
        self.kafka.send(topic=topic, value=message, key=self.symbol.upper())


    async def start(self):
        self.start_time = time.time()
        self.last_report_time = self.start_time
        print(f"🚀 {self.__class__.__name__} 시작 | 구독: {self.streams}")

        try:
            async with websockets.connect(self.url) as ws:
                while self.running:
                    try:
                        # 타임아웃을 두어 주기적으로 종료 플래그 확인
                        msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        self.total_count += 1
                        self.sec_count += 1
                        
                        try:
                            data = json.loads(msg)
                            stream_name = data.get("stream", "unknown")
                            payload = data.get("data", {})
                            
                            # 데이터 샘플 출력 (초반 5개만)
                            if self.printed_samples < 5:
                                print(f"\n📥 [{datetime.now().strftime('%H:%M:%S')}] {stream_name} 샘플 데이터 확인")
                                self.printed_samples += 1

                            # 실질적인 데이터 처리 로직 호출
                            await self.process_data(stream_name, payload)
                            
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON 파싱 에러: {e}")
                        except Exception as e:
                            print(f"❌ 데이터 처리 에러: {e}")

                        # TPS 리포팅
                        await self._report_metrics()
                        
                    except asyncio.TimeoutError:
                        # 타임아웃은 정상 (종료 플래그 확인용)
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        print("\n⚠️ 웹소켓 연결이 끊어졌습니다.")
                        break

        except KeyboardInterrupt:
            print("\n🛑 중단 요청 수신")
            self.running = False
        except asyncio.CancelledError:
            # 정상적인 취소 처리
            print("\n🛑 작업 취소됨")
            self.running = False
        except Exception as e:
            print(f"\n❌ 예상치 못한 에러: {e}")
        finally:
            self._final_report()

    async def _report_metrics(self):
        now = time.time()
        if now - self.last_report_time >= 1.0:
            tps = self.sec_count / (now - self.last_report_time)
            print(f"⏱️ TPS: {tps:.2f} msgs/sec | 누적: {self.total_count:,}", end='\r')
            self.sec_count = 0
            self.last_report_time = now

    def _final_report(self):
        if self.start_time:
            duration = time.time() - self.start_time
            avg_tps = self.total_count / duration if duration > 0 else 0
            print(f"\n📊 종료 리포트 | 평균 TPS: {avg_tps:.2f} | 총 메시지: {self.total_count:,}")