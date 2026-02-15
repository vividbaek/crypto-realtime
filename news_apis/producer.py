#!/usr/bin/env python3
"""
실시간 뉴스 Kafka Producer
자동으로 뉴스 데이터를 Kafka와 Elasticsearch로 전송하여 Spark SQL에서 실시간 처리
"""
import json
import time
import random
from datetime import datetime
import requests

class RealTimeNewsProducer:
    def __init__(self):
        self.setup_producer()
        self.setup_elasticsearch()
        
    def setup_producer(self):
        """Kafka Producer 설정"""
        try:
            from kafka import KafkaProducer
            self.producer = KafkaProducer(
                bootstrap_servers=['localhost:9092'],
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                key_serializer=lambda x: str(x).encode('utf-8') if x else None
            )
            print("✅ Kafka Producer 연결 성공")
            self.kafka_enabled = True
        except Exception as e:
            print(f"❌ Kafka 연결 실패: {e}")
            print("💡 파일 모드로 진행...")
            self.producer = None
            self.kafka_enabled = False
    
    def setup_elasticsearch(self):
        """Elasticsearch 클라이언트 설정"""
        try:
            from elasticsearch import Elasticsearch
            # Elasticsearch 8.x 서버와 호환되도록 설정
            self.es = Elasticsearch(
                ['http://localhost:9200'],
                request_timeout=30,
                # 버전 8과의 호환성 설정
                headers={"Accept": "application/json", "Content-Type": "application/json"}
            )
            
            # 연결 테스트 (ping 대신 info 사용)
            info = self.es.info()
            if info:
                print(f"✅ Elasticsearch 연결 성공 (v{info.get('version', {}).get('number', 'unknown')})")
                self.es_enabled = True
                
                # 인덱스 생성 (이미 존재하면 무시)
                index_name = 'crypto-news'
                if not self.es.indices.exists(index=index_name):
                    # 인덱스 매핑 정의
                    mapping = {
                        "mappings": {
                            "properties": {
                                "id": {"type": "keyword"},
                                "source": {"type": "keyword"},
                                "title": {"type": "text"},
                                "description": {"type": "text"},
                                "body": {"type": "text"},  # 본문 필드 추가
                                "url": {"type": "keyword"},
                                "published_at": {"type": "date"},
                                "coins": {"type": "keyword"},
                                "sentiment": {"type": "keyword"},
                                "timestamp": {"type": "date"}
                            }
                        }
                    }
                    self.es.indices.create(index=index_name, body=mapping)
                    print(f"📊 Elasticsearch 인덱스 '{index_name}' 생성 완료")
                else:
                    print(f"📊 Elasticsearch 인덱스 '{index_name}' 이미 존재")
            else:
                print("❌ Elasticsearch 연결 실패")
                self.es_enabled = False
                
        except Exception as e:
            print(f"❌ Elasticsearch 연결 실패: {type(e).__name__}: {e}")
            print("💡 Elasticsearch 없이 진행...")
            self.es = None
            self.es_enabled = False
    
    def extract_coins(self, text):
        """텍스트에서 코인 추출"""
        if not text:
            return ['unknown']
        
        text_lower = text.lower()
        coins = []
        
        coin_keywords = {
            'bitcoin': ['bitcoin', 'btc'],
            'ethereum': ['ethereum', 'eth', 'ether'],
            'binance': ['binance', 'bnb'], 
            'cardano': ['cardano', 'ada'],
            'solana': ['solana', 'sol'],
            'polkadot': ['polkadot', 'dot'],
            'dogecoin': ['dogecoin', 'doge'],
            'ripple': ['ripple', 'xrp'],
            'chainlink': ['chainlink', 'link']
        }
        
        for coin, keywords in coin_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    coins.append(coin)
                    break
        
        return coins if coins else ['unknown']
    
    def get_coindesk_news(self):
        """CoinDesk API에서 실제 뉴스 가져오기"""
        api_key = "2c6101236127849e0eafee8acea90ccf9281c5bd7eeb02550bbf5f0bc013ae51"
        url = "https://api.coindesk.com/v1/news"
        
        headers = {
            'X-API-Key': api_key,
            'User-Agent': 'RealTimeNewsProducer/1.0'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('articles', [])[:3]
            else:
                print(f"CoinDesk API 오류: {response.status_code}")
                return []
        except Exception as e:
            print(f"CoinDesk 요청 실패: {e}")
            return []
    
    def generate_sample_news(self):
        """실시간 샘플 뉴스 생성"""
        sample_templates = [
            "{coin} 가격이 {direction} 추세를 보이고 있습니다",
            "{coin} 네트워크에서 대규모 {event}가 발생했습니다", 
            "{coin} 개발팀이 새로운 {feature}를 발표했습니다",
            "{coin}에 대한 기관 투자자들의 관심이 {direction}하고 있습니다",
            "{coin} 거래량이 전일 대비 {percent}% {direction}했습니다"
        ]
        
        # 본문 템플릿 추가
        body_templates = [
            "최근 {coin} 시장에서 주목할 만한 움직임이 포착되었습니다. 전문가들은 이번 {event}가 장기적으로 {coin}의 가격에 영향을 미칠 것으로 예상하고 있습니다. 글로벌 암호화폐 거래소들에서는 거래량이 크게 증가하면서 투자자들의 관심이 집중되고 있습니다.\n\n시장 분석가들은 \"{coin}의 기술적 지표가 강세를 보이고 있으며, 단기적으로 추가 상승 가능성이 있다\"고 평가했습니다. 특히 기관 투자자들의 진입이 본격화되면서 시장 전반에 긍정적인 영향을 주고 있습니다.\n\n한편, {coin} 개발팀은 최근 커뮤니티에 향후 로드맵을 공개하며 생태계 확장 계획을 발표했습니다. 이에 대해 업계 관계자들은 \"{coin}의 기술적 혁신이 블록체인 산업 전반에 새로운 기준을 제시할 것\"이라고 전망했습니다.",
            
            "{coin} 네트워크가 중요한 전환점을 맞이했습니다. 이번 {event}는 블록체인 커뮤니티에서 큰 주목을 받고 있으며, 다수의 개발자와 투자자들이 긍정적인 반응을 보이고 있습니다.\n\n업계 전문가 김철수 씨는 \"{coin}의 이번 업데이트는 확장성과 보안성 측면에서 상당한 개선을 가져올 것\"이라며 \"장기 투자자들에게 좋은 기회가 될 수 있다\"고 말했습니다.\n\n{coin}의 시가총액은 최근 몇 주간 꾸준한 상승세를 보이고 있으며, 주요 거래소에서의 거래량도 급증하고 있습니다. 전문가들은 이러한 추세가 당분간 지속될 것으로 전망하고 있습니다.",
            
            "글로벌 암호화폐 시장에서 {coin}이 다시 한번 화제의 중심에 섰습니다. {event}에 대한 소식이 전해지면서 투자자들의 관심이 급증하고 있으며, 관련 커뮤니티에서는 활발한 토론이 이어지고 있습니다.\n\n{coin}의 창립자는 최근 인터뷰에서 \"우리는 블록체인 기술의 대중화를 위해 노력하고 있으며, 이번 {feature}는 그 일환\"이라고 밝혔습니다. 또한 \"향후 더 많은 혁신적인 기능들이 추가될 예정\"이라고 덧붙였습니다.\n\n시장 데이터에 따르면, {coin}의 온체인 활동이 크게 증가하고 있으며, 이는 실제 사용자 증가를 시사합니다. 애널리스트들은 이러한 지표들이 {coin}의 장기적 성장 가능성을 뒷받침한다고 분석했습니다."
        ]
        
        coins = ['Bitcoin', 'Ethereum', 'Cardano', 'Solana', 'Polkadot', 'Chainlink']
        directions = ['상승', '하락', '급등', '급락', '반등']
        events = ['업그레이드', '하드포크', '파트너십', '거래소 상장']
        features = ['기능', '프로토콜', '업데이트', '로드맵']
        percentages = [5, 10, 15, 20, 25, 30]
        
        template = random.choice(sample_templates)
        coin = random.choice(coins)
        direction = random.choice(directions)
        event = random.choice(events)
        feature = random.choice(features)
        
        title = template.format(
            coin=coin,
            direction=direction,
            event=event,
            feature=feature,
            percent=random.choice(percentages)
        )
        
        # 본문 생성
        body_template = random.choice(body_templates)
        body = body_template.format(coin=coin, event=event, feature=feature)
        
        sentiments = ['positive', 'negative', 'neutral']
        sources = ['coindesk', 'cryptopanic', 'cointelegraph', 'newsdata']
        
        return {
            'id': f"news_{int(time.time())}_{random.randint(1000, 9999)}",
            'source': random.choice(sources),
            'title': title,
            'description': f"{coin} 관련 최신 소식입니다. 시장 동향을 주시하고 계십시오.",
            'body': body,  # 본문 추가
            'url': f"https://example.com/news/{random.randint(1, 1000)}",
            'published_at': datetime.now().isoformat(),
            'coins': self.extract_coins(title),
            'sentiment': random.choice(sentiments),
            'timestamp': datetime.now().isoformat()
        }
    
    def send_to_elasticsearch(self, news_data):
        """뉴스를 Elasticsearch에 저장"""
        try:
            if self.es_enabled and self.es:
                # Elasticsearch에 문서 인덱싱
                response = self.es.index(
                    index='crypto-news',
                    id=news_data['id'],  # 문서 ID로 사용 (중복 방지)
                    document=news_data
                )
                
                if response.get('result') in ['created', 'updated']:
                    return True
                else:
                    print(f"⚠️ Elasticsearch 저장 이상: {response}")
                    return False
            return False
                
        except Exception as e:
            print(f"❌ Elasticsearch 저장 실패: {e}")
            return False
    
    def send_to_kafka(self, news_data):
        """뉴스를 Kafka와 Elasticsearch로 전송"""
        kafka_success = False
        es_success = False
        
        # Kafka 전송
        try:
            if self.kafka_enabled and self.producer:
                future = self.producer.send(
                    'crypto-news-normalized',
                    key=news_data['id'],
                    value=news_data
                )
                future.get(timeout=10)
                kafka_success = True
                coins_str = ', '.join(news_data['coins'])
                print(f"📡 KAFKA: [{news_data['source']}] {news_data['title'][:50]}... (코인: {coins_str})")
        except Exception as e:
            print(f"❌ Kafka 전송 실패: {e}")
        
        # Elasticsearch 저장
        es_success = self.send_to_elasticsearch(news_data)
        if es_success:
            coins_str = ', '.join(news_data['coins'])
            print(f"💾 ES: [{news_data['source']}] {news_data['title'][:50]}... (코인: {coins_str})")
        
        # 둘 다 실패하면 파일로 저장
        if not kafka_success and not es_success:
            return self.send_to_file(news_data)
        
        return kafka_success or es_success
    
    def send_to_file(self, news_data):
        """뉴스를 파일로 저장 (Kafka 백업)"""
        try:
            with open('c:/Users/dlwls/Downloads/criptonews/realtime_news_stream.jsonl', 'a', encoding='utf-8') as f:
                f.write(json.dumps(news_data, ensure_ascii=False) + '\n')
                
            coins_str = ', '.join(news_data['coins'])
            print(f"📁 FILE: [{news_data['source']}] {news_data['title'][:50]}... (코인: {coins_str})")
            return True
            
        except Exception as e:
            print(f"❌ 파일 저장 실패: {e}")
            return False
    
    def run_production(self):
        """실시간 뉴스 생산 실행"""
        print("🔄 실시간 뉴스 생산 시작")
        print("📁 출력 파일: realtime_news_stream.jsonl")
        print("Ctrl+C로 중단")
        print("=" * 50)
        
        # 이전 파일 초기화
        open('c:/Users/dlwls/Downloads/criptonews/realtime_news_stream.jsonl', 'w').close()
        
        # CoinDesk와 CryptoPanic API 초기화
        try:
            import sys
            import os
            # 현재 디렉토리를 sys.path에 추가
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            from coindesk import CoinDeskAPI
            from cryptopanic import CryptoPanicAPI
            
            coindesk_api = CoinDeskAPI("2c6101236127849e0eafee8acea90ccf9281c5bd7eeb02550bbf5f0bc013ae51")
            cryptopanic_api = CryptoPanicAPI("6fa5942ac8e6e044d02fc8a8b168607a8fc818dd")
            print("✅ 뉴스 API 클라이언트 초기화 완료")
            apis_enabled = True
        except Exception as e:
            print(f"⚠️ API 클라이언트 초기화 실패: {e}")
            print("💡 샘플 뉴스만 생성합니다")
            apis_enabled = False
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                print(f"\n📡 뉴스 생산 #{iteration}")
                
                news_sent = 0
                
                # 1. CoinDesk 뉴스 수집
                if apis_enabled:
                    try:
                        coindesk_news = coindesk_api.fetch_news(limit=5)
                        for article in coindesk_news:
                            title = article.get('TITLE', '')
                            body = article.get('BODY', '')
                            coins_list = []
                            
                            # CATEGORY_DATA에서 코인 추출
                            category_data = article.get('CATEGORY_DATA', [])
                            if isinstance(category_data, list):
                                for cat in category_data:
                                    if isinstance(cat, dict) and cat.get('CATEGORY'):
                                        coins_list.append(cat.get('CATEGORY').lower())
                            
                            if not coins_list:
                                coins_list = self.extract_coins(f"{title} {body}")
                            
                            news_data = {
                                'id': f"coindesk_{article.get('GUID', int(time.time()))}",
                                'source': 'coindesk',
                                'title': title,
                                'description': article.get('BODY', '')[:200] if article.get('BODY') else '',
                                'body': body,
                                'url': article.get('URL', ''),
                                'published_at': datetime.fromtimestamp(article.get('PUBLISHED_ON', time.time())).isoformat() if article.get('PUBLISHED_ON') else datetime.now().isoformat(),
                                'coins': coins_list,
                                'sentiment': article.get('SENTIMENT', 'neutral'),
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            if self.send_to_kafka(news_data):
                                news_sent += 1
                        
                        if coindesk_news:
                            print(f"✅ CoinDesk: {len(coindesk_news)}개 뉴스 수집")
                    except Exception as e:
                        print(f"⚠️ CoinDesk API 오류: {e}")
                    
                    # 2. CryptoPanic 뉴스 수집
                    try:
                        cryptopanic_news = cryptopanic_api.fetch_news(limit=5)
                        for article in cryptopanic_news:
                            title = article.get('title', '')
                            
                            # 코인 추출
                            coins_list = []
                            currencies = article.get('currencies', [])
                            if isinstance(currencies, list):
                                for currency in currencies:
                                    if isinstance(currency, dict) and currency.get('code'):
                                        coins_list.append(currency.get('code').lower())
                            
                            if not coins_list:
                                coins_list = self.extract_coins(title)
                            
                            # Sentiment 결정
                            sentiment = 'neutral'
                            votes = article.get('votes', {})
                            if isinstance(votes, dict):
                                positive = votes.get('positive', 0)
                                negative = votes.get('negative', 0)
                                if positive > negative:
                                    sentiment = 'positive'
                                elif negative > positive:
                                    sentiment = 'negative'
                            
                            news_data = {
                                'id': f"cryptopanic_{article.get('id', int(time.time()))}",
                                'source': 'cryptopanic',
                                'title': title,
                                'description': '',
                                'body': article.get('title', ''),  # CryptoPanic은 본문이 없어 제목 사용
                                'url': article.get('url', ''),
                                'published_at': article.get('created_at', datetime.now().isoformat()),
                                'coins': coins_list,
                                'sentiment': sentiment,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            if self.send_to_kafka(news_data):
                                news_sent += 1
                        
                        if cryptopanic_news:
                            print(f"✅ CryptoPanic: {len(cryptopanic_news)}개 뉴스 수집")
                    except Exception as e:
                        print(f"⚠️ CryptoPanic API 오류: {e}")
                
                # 3. 샘플 뉴스 생성 (API 실패 시 또는 보충용)
                sample_count = random.randint(2, 4) if not apis_enabled else random.randint(1, 2)
                for _ in range(sample_count):
                    sample_news = self.generate_sample_news()
                    if self.send_to_kafka(sample_news):
                        news_sent += 1
                
                print(f"📊 총 {news_sent}개 뉴스 생성")
                
                # 대기
                wait_time = random.randint(15, 30)
                print(f"⏳ {wait_time}초 후 다음 라운드...")
                time.sleep(wait_time)
                
        except KeyboardInterrupt:
            print("\n⏸️ 뉴스 생산 중단")

def main():
    """메인 실행"""
    print("📡 실시간 뉴스 Producer")
    print("=" * 30)
    
    producer = RealTimeNewsProducer()
    producer.run_production()

if __name__ == "__main__":
    main()