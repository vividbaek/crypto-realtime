# 🚀 CriptoNews - CoinDesk API 5개 엔드포인트 완전 활용 시스템

> CoinDesk API 5개 엔드포인트를 모두 활용한 실시간 크립토 뉴스 수집·분석·스트리밍 시스템입니다.

**🎯 주요 특징:**
- ✅ CoinDesk API 5개 엔드포인트 완전 지원
- ✅ Apache Kafka 실시간 뉴스 스트리밍
- ✅ 자동 뉴스 정규화 및 분류
- ✅ 종합 테스트 도구 내장
- ✅ 프로덕션 환경 대응

---

## 🏗️ 시스템 아키텍처

```
📊 CoinDesk API (5개 엔드포인트)
    ↓
⚙️ 통합 뉴스 수집기 (Python)
    ↓
🔄 Apache Kafka (실시간 스트리밍)
    ↓
📱 다양한 소비자 (분석, 저장, 알림)
```

---

## 📋 프로젝트 구조

### 🔧 **핵심 구성 요소**

```
criptonews/
├── news_apis/                    # 뉴스 API 모듈
│   ├── coindesk.py              # 🌟 CoinDesk 5개 API 통합 클래스
│   ├── cryptopanic.py           # CryptoPanic API 클래스
│   ├── normalize.py             # 뉴스 데이터 정규화
│   └── base.py                  # API 베이스 클래스
│
├── kafka_producer.py            # 📡 Kafka 메시지 전송
├── kafka_consumer.py            # 📥 Kafka 메시지 수신
├── news_to_kafka.py             # 🎯 메인 뉴스 수집기
│
├── 🧪 테스트 도구
│   ├── test_comprehensive_coindesk_api.py  # 완전 API 테스트
│   └── test_fetch_news.py                  # 기본 테스트
│
└── 📚 문서
    ├── COINDESK_API_COMPLETE_DOCUMENTATION.md
    ├── COMPLETE_IMPLEMENTATION_GUIDE.md
    └── README.md (이 파일)
```

---

### 🎯 **CoinDesk API 5개 엔드포인트**

| API | 엔드포인트 | 기능 | 구현 상태 |
|-----|------------|------|----------|
| 1️⃣ | `/news/v1/article/list` | 최신 뉴스 목록 | ✅ 완료 |
| 2️⃣ | `/news/v1/source/list` | 뉴스 소스 관리 | ✅ 완료 |
| 3️⃣ | `/news/v1/category/list` | 카테고리 목록 | ✅ 완료 |
| 4️⃣ | `/news/v1/article/get` | 단일 기사 상세 | ✅ 완료 |
| 5️⃣ | `/news/v1/search` | 뉴스 검색 | ✅ 완료 |

### 🚀 **Kafka 통합 기능**

- **실시간 뉴스 스트리밍**: 다중 토픽 자동 분류
- **메타데이터 관리**: 소스, 카테고리 정보 동기화
- **검색 기반 필터링**: 키워드별 뉴스 자동 수집
- **감정 분석**: 뉴스 감정 상태 분류
- **개인화 필터**: 사용자 맞춤 뉴스 큐레이션

---

## 🔑 API 키 설정

### CoinDesk API 키
```python
# news_to_kafka.py에서 설정
COINDESK_KEY = "YOUR_COINDESK_API_KEY"  # 실제 키로 교체
```

**CoinDesk 개발자 계정 생성:**
1. [CoinDesk Developer Portal](https://docs.coindesk.com/) 방문
2. 개발자 계정 생성
3. API 키 발급
4. `news_to_kafka.py`에 키 입력

### CryptoPanic API 키
```python
CRYPTOPANIC_KEY = "6fa5942ac8e6e044d02fc8a8b168607a8fc818dd"  # 기본 제공
```

---

## 🚀 빠른 시작

### 1. **환경 설정**
```bash
# 1. 의존성 설치
pip install requests kafka-python

# 2. Kafka 서버 실행 (Docker)
docker run -d --name kafka-news -p 9092:9092 apache/kafka:latest

# 3. API 키 설정
# news_to_kafka.py에서 COINDESK_KEY 실제 값으로 교체
```

### 2. **실시간 뉴스 수집 시작**
```bash
# 5개 API 모두 활용하는 종합 뉴스 수집
python news_to_kafka.py
```

### 3. **Kafka 메시지 실시간 확인**
```bash
# 별도 터미널에서 실행
python kafka_consumer.py
```

### 4. **완전 테스트 실행**
```bash
# 모든 API 엔드포인트 테스트
python test_comprehensive_coindesk_api.py
```

---

## 📊 실시간 데이터 수집 현황

### **Kafka 토픽별 뉴스 분류**

| 토픽 이름 | 내용 | 업데이트 주기 |
|-----------|------|--------------|
| `coindesk-summary` | 종합 뉴스 요약 | 실시간 |
| `coindesk-latest` | 최신 뉴스 | 실시간 |
| `coindesk-bitcoin` | 비트코인 특화 | 실시간 |
| `coindesk-ethereum` | 이더리움 특화 | 실시간 |
| `coindesk-sources` | 소스 메타데이터 | 주기적 |
| `coindesk-search-defi` | DeFi 검색 결과 | 실시간 |
| `cryptopanic` | CryptoPanic 뉴스 | 실시간 |

### **데이터 정규화 구조**
```json
{
  "published_at": "2026-02-04T10:30:00Z",
  "title": "Bitcoin Reaches New All-Time High",
  "url": "https://coindesk.com/article/...",
  "source": "CoinDesk",
  "source_key": "coindesk",
  "lang": "EN",
  "guid": "unique-article-id",
  "sentiment": "positive",
  "categories": ["bitcoin", "price"],
  "search_keyword": "bitcoin"  // 검색 기반 수집시
}
```

---

---

## 🎯 고급 활용 시나리오

### 1. **트레이딩 신호 시스템**
```python
# 가격 영향 뉴스 실시간 감지
high_impact_keywords = ["regulation", "adoption", "partnership", "hack"]
for keyword in high_impact_keywords:
    results = api.search_across_all_sources(keyword, 5)
    # 긴급 알림 토픽으로 전송
    kafka_producer.send_news(results, f'urgent-{keyword}-signals')
```

### 2. **시장 심리 분석**
```python
# 전체 뉴스 감정 분석
summary = api.get_comprehensive_news_summary()
sentiment_data = {
    "positive_count": count_sentiment(summary, 'positive'),
    "negative_count": count_sentiment(summary, 'negative'),
    "market_mood": calculate_overall_sentiment(summary)
}
kafka_producer.send_news([sentiment_data], 'market-sentiment')
```

### 3. **개인화 뉴스 서비스**
```python
# 사용자 맞춤 뉴스 필터링
user_prefs = {"coins": ["bitcoin"], "categories": ["technology"]}
personalized = api.get_categorized_news(category_filter=user_prefs)
kafka_producer.send_news(personalized, f'user-{user_id}-feed')
```

---

## 🔧 기술 스택

- **언어**: Python 3.8+
- **메시징**: Apache Kafka 4.0.0
- **API 클라이언트**: requests
- **데이터 직렬화**: JSON
- **컨테이너**: Docker (Kafka)
- **테스트**: 내장 테스트 도구

---

## 📈 성능 지표

- **API 커버리지**: 100% (5개 엔드포인트 모두 지원)
- **실시간 처리**: Kafka 기반 비동기 스트리밍
- **에러 복구**: 완전한 fallback 시스템
- **확장성**: 다중 토픽, 소비자 그룹 지원
- **모니터링**: 상세 로깅 및 상태 추적

---

## 🛡️ 보안 및 모범 사례

- **API 키 보호**: 환경변수 사용 권장
- **Rate Limiting**: 자동 요청 간격 조절
- **에러 핸들링**: HTTP 상태 코드별 대응
- **데이터 검증**: 응답 구조 자동 검증
- **HTTPS**: 모든 API 통신 암호화

---

## 📚 관련 문서

- 📖 **[완전한 API 가이드](COINDESK_API_COMPLETE_DOCUMENTATION.md)** - 5개 API 상세 분석
- 🚀 **[구현 가이드](COMPLETE_IMPLEMENTATION_GUIDE.md)** - 실제 활용 시나리오
- 🧪 **[테스트 가이드](test_comprehensive_coindesk_api.py)** - 완전 테스트 도구
- 📡 **[Kafka 설정 가이드](KAFKA_SETUP.md)** - Kafka 연동 상세 설명

---

## 🤝 기여하기

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 라이선스

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🎉 결론

**CriptoNews는 CoinDesk API의 모든 기능을 완전히 활용하여 실시간 크립토 뉴스 분석 시스템을 구축할 수 있는 완전한 솔루션입니다.**

### ✨ **주요 성과**
- ✅ **5개 API 완전 지원**: 모든 엔드포인트 구현
- ✅ **실시간 스트리밍**: Kafka 기반 고성능 처리
- ✅ **프로덕션 준비**: 실제 서비스 적용 가능
- ✅ **확장 가능**: 모듈식 아키텍처
- ✅ **완전 테스트**: 신뢰성 보장

🚀 **지금 바로 시작해서 차세대 크립토 뉴스 시스템을 구축하세요!**
