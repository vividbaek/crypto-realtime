import requests
from base import NewsAPIBase
from typing import List, Dict, Any

class CryptoPanicAPI(NewsAPIBase):
    BASE_URL = "https://cryptopanic.com/api/developer/v2/posts/"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch_news(self, limit=20) -> List[Dict[str, Any]]:
        params = {
            "auth_token": self.api_key,
            "public": "true"
        }
        resp = requests.get(self.BASE_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        
        # 디버깅: 첫 번째 항목의 구조 출력
        if results:
            print(f"🔍 CryptoPanic API 첫 번째 항목 구조:")
            first_item = results[0]
            print(f"   📋 사용 가능한 키들: {list(first_item.keys())}")
            print(f"   📰 제목: {first_item.get('title', 'N/A')}")
            print(f"   🔗 URL: {first_item.get('url', 'N/A')}")
            print(f"   📊 소스 구조: {first_item.get('source', 'N/A')}")
        
        return results[:limit] if limit else results
