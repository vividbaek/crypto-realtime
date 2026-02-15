from typing import Dict, Any, List

def normalize_coindesk(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    CoinDesk API 응답을 정규화 (2026년 공식 API 구조 기반)
    """
    # CATEGORY_DATA에서 코인 정보 추출
    coins = []
    category_data = item.get("CATEGORY_DATA", [])
    if isinstance(category_data, list):
        # 실제 암호화폐 심볼만 필터링하기 위한 화이트리스트
        crypto_symbols = {
            'BTC', 'ETH', 'ADA', 'XRP', 'DOT', 'MATIC', 'SOL', 'AVAX', 'ATOM', 
            'LINK', 'UNI', 'AAVE', 'MKR', 'COMP', 'YFI', 'SUSHI', 'CRV', 'BAL', 
            'SNX', '1INCH', 'DOGE', 'SHIB', 'LTC', 'BCH', 'XLM', 'ALGO', 'VET', 
            'FIL', 'THETA', 'ICP', 'TRX', 'ETC', 'XMR', 'ZEC', 'DASH', 'NEO', 
            'ONT', 'QTUM', 'ZIL', 'EOS', 'BSV', 'CAKE', 'BNB', 'BUSD', 'USDC', 
            'USDT', 'DAI', 'TUSD', 'PAX', 'GUSD', 'NEAR', 'LUNA', 'MANA', 'SAND'
        }
        
        for category in category_data:
            if isinstance(category, dict) and category.get("CATEGORY"):
                cat_name = category.get("CATEGORY")
                # 화이트리스트에 있는 코인만 추가
                if cat_name and cat_name in crypto_symbols:
                    coins.append(cat_name)
    
    return {
        "published_at": item.get("PUBLISHED_ON") or item.get("published_at"),
        "title": item.get("TITLE") or item.get("title"),
        "url": item.get("URL") or item.get("url"),
        "source": item.get("SOURCE_DATA", {}).get("NAME") or item.get("source"),
        "source_key": item.get("SOURCE_DATA", {}).get("SOURCE_KEY"),
        "lang": item.get("LANG") or item.get("lang"),
        "guid": item.get("GUID"),
        "body": item.get("BODY"),
        "image_url": item.get("IMAGE_URL"),
        "authors": item.get("AUTHORS"),
        "keywords": item.get("KEYWORDS"),
        "sentiment": item.get("SENTIMENT"),
        "score": item.get("SCORE"),
        "upvotes": item.get("UPVOTES", 0),
        "downvotes": item.get("DOWNVOTES", 0),
        "categories": category_data,
        "coins": coins if coins else None,  # 코인이 없으면 None
    }


def normalize_cryptopanic(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    CryptoPanic API 응답을 정규화 (개선된 데이터 추출)
    """
    # None 값 필터링을 위한 헬퍼 함수
    def get_valid_value(value, default=None):
        return value if value is not None and value != "" else default
    
    # 제목 추출 (여러 필드에서 시도)
    title = get_valid_value(item.get("title")) or get_valid_value(item.get("headline")) or get_valid_value(item.get("text", "").strip()[:100])
    
    # URL 추출 (여러 필드에서 시도)
    url = get_valid_value(item.get("url")) or get_valid_value(item.get("link")) or get_valid_value(item.get("source_url"))
    
    # 소스 추출 (여러 방법으로 시도)
    source = None
    if item.get("source"):
        if isinstance(item.get("source"), dict):
            source = get_valid_value(item["source"].get("title")) or get_valid_value(item["source"].get("name")) or get_valid_value(item["source"].get("domain"))
        else:
            source = get_valid_value(item.get("source"))
    
    # 발행일 추출
    published_at = get_valid_value(item.get("created_at")) or get_valid_value(item.get("published_at"))
    
    # 코인/통화 추출 (CryptoPanic API 구조에 맞춤)
    coins = []
    currencies = item.get("currencies") or item.get("coins") or item.get("symbols")
    if isinstance(currencies, list):
        for currency in currencies:
            if isinstance(currency, dict) and currency.get("code"):
                coins.append(currency.get("code"))
            elif isinstance(currency, str):
                coins.append(currency)
    elif isinstance(currencies, str):
        coins.append(currencies)
    
    # 코인 정보가 없거나 비어있으면 제목에서 추출 시도
    if not coins and title:
        # 제목에서 일반적인 코인 심볼들을 찾기
        import re
        crypto_patterns = r'\b(BTC|ETH|ADA|XRP|DOT|MATIC|SOL|AVAX|ATOM|LINK|UNI|AAVE|MKR|COMP|YFI|SUSHI|CRV|BAL|SNX|1INCH|DOGE|SHIB|LTC|BCH|XLM|ALGO|VET|FIL|THETA|ICP|TRX|ETC|XMR|ZEC|DASH|NEO|ONT|QTUM|ZIL|EOS|BSV|CAKE|BNB|BUSD|USDC|USDT|DAI|TUSD|PAX|GUSD)\b'
        found_coins = re.findall(crypto_patterns, title.upper())
        if found_coins:
            coins.extend(found_coins)
    
    # 중복 제거
    coins = list(set(coins)) if coins else None
    
    # 감정 분석 추출 (CryptoPanic의 votes 정보 활용)
    sentiment = None
    
    # CryptoPanic의 votes 데이터에서 감정 추출 (복수형 우선)
    votes_data = item.get("votes") or item.get("vote")
    if votes_data and isinstance(votes_data, dict):
        positive = votes_data.get("positive", 0)
        negative = votes_data.get("negative", 0)
        important = votes_data.get("important", 0)
        
        # 가장 큰 값으로 sentiment 결정
        max_vote = max(positive, negative, important)
        if max_vote > 0:
            if positive == max_vote:
                sentiment = "POSITIVE"
            elif negative == max_vote:
                sentiment = "NEGATIVE"
            elif important == max_vote:
                sentiment = "IMPORTANT"
        else:
            sentiment = "NEUTRAL"
                
    # votes가 없으면 다른 sentiment 필드 확인
    if not sentiment:
        sentiment = get_valid_value(item.get("sentiment"))
    
    # kind 정보에서 감정 추출 시도
    if not sentiment and item.get("kind"):
        kind = item.get("kind", "").lower()
        if "positive" in kind or "bullish" in kind:
            sentiment = "POSITIVE"
        elif "negative" in kind or "bearish" in kind:
            sentiment = "NEGATIVE"
    
    # 여전히 sentiment가 없으면 제목에서 키워드로 추출
    if not sentiment and title:
        title_lower = title.lower()
        positive_words = ['bullish', 'surge', 'rally', 'moon', 'pump', 'gains', 'soar', 'breakout', 'bull run', 'rising']
        negative_words = ['bearish', 'crash', 'dump', 'drop', 'fall', 'decline', 'bear market', 'selloff', 'plunge', 'collapse']
        
        if any(word in title_lower for word in positive_words):
            sentiment = "POSITIVE"
        elif any(word in title_lower for word in negative_words):
            sentiment = "NEGATIVE"
        else:
            sentiment = "NEUTRAL"
    
    # None이거나 빈 값인 항목 제거
    result = {
        "published_at": published_at,
        "title": title,
        "url": url,
        "source": source,
        "lang": get_valid_value(item.get("lang")) or "en",  # 기본값 설정
        "coins": coins,
        "sentiment": sentiment,
    }
    
    # None 값이 있는 필드들을 확인하고, 유효한 데이터가 충분하지 않으면 None 반환
    essential_fields = ["title"]  # 최소 필수 필드
    if not any(result.get(field) for field in essential_fields):
        return None  # 필수 데이터가 없으면 전체 항목 버림
    
    return result
