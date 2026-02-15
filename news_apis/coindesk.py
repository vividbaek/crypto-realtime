import requests
from base import NewsAPIBase
from typing import List, Dict, Any, Optional
from datetime import datetime

class CoinDeskAPI(NewsAPIBase):
    """
    CoinDesk 공식 API v1 클라이언트
    공식 문서: https://docs.coindesk.com/
    실제 API 도메인: data-api.coindesk.com
    """
    
    # 공식 문서에서 확인된 실제 도메인과 엔드포인트
    BASE_DOMAIN = "https://data-api.coindesk.com"
    
    # News API 엔드포인트들
    ARTICLE_LIST_URL = f"{BASE_DOMAIN}/news/v1/article/list"
    ARTICLE_GET_URL = f"{BASE_DOMAIN}/news/v1/article/get"
    SOURCE_LIST_URL = f"{BASE_DOMAIN}/news/v1/source/list" 
    CATEGORY_LIST_URL = f"{BASE_DOMAIN}/news/v1/category/list"
    NEWS_SEARCH_URL = f"{BASE_DOMAIN}/news/v1/search"

    def __init__(self, api_key: str):
        """
        CoinDesk API 클라이언트 초기화
        
        Args:
            api_key: CoinDesk API 키 (개발자 계정에서 발급)
        """
        self.api_key = api_key
        # 공식 문서 확인: API 키는 query parameter로 전달
        self.default_params = {"api_key": api_key}

    def fetch_news(self, lang="EN", source_ids=None, categories=None, exclude_categories=None, 
                   limit=50, to_ts=None) -> List[Dict[str, Any]]:
        """
        최신 뉴스 기사 목록 조회 (Latest Articles API)
        
        Args:
            lang: 언어 코드 (EN, ES, TR, FR, JP, PT)
            source_ids: 특정 소스 키 배열 (예: ["coindesk", "cryptocompare"])
            categories: 포함할 카테고리 배열 (최대 200개)
            exclude_categories: 제외할 카테고리 배열 (최대 200개)
            limit: 결과 개수 제한 (1-100, 기본값 50)
            to_ts: 지정된 타임스탬프 이전 기사만 조회
        
        Returns:
            뉴스 기사 목록
        """
        params = self.default_params.copy()
        params.update({
            "lang": lang,
            "limit": min(max(1, limit), 100)  # 1-100 범위 강제
        })
        
        if source_ids:
            params["source_ids"] = source_ids if isinstance(source_ids, list) else [source_ids]
            
        if categories:
            params["categories"] = categories if isinstance(categories, list) else [categories]
            
        if exclude_categories:
            params["exclude_categories"] = exclude_categories if isinstance(exclude_categories, list) else [exclude_categories]
            
        if to_ts:
            params["to_ts"] = to_ts
        
        try:
            resp = requests.get(self.ARTICLE_LIST_URL, params=params, timeout=20)
            data = self._handle_api_response(resp)
            return data.get("Data", [])
        except Exception as e:
            print(f"CoinDesk API 기사 목록 조회 오류: {e}")
            return []
    
    def get_single_article(self, source_key: str, guid: str) -> Dict[str, Any]:
        """
        단일 기사 상세 조회 (Article Get)
        
        Args:
            source_key: 뉴스 소스의 고유 키 (예: 'coindesk', 'cryptocompare')
            guid: 기사의 Global Unique Identifier
        
        Returns:
            기사 상세 정보
        """
        params = self.default_params.copy()
        params.update({
            "source_key": source_key,
            "guid": guid
        })
        
        try:
            resp = requests.get(self.ARTICLE_GET_URL, params=params, timeout=20)
            data = self._handle_api_response(resp)
            return data.get("Data", {})
        except Exception as e:
            print(f"CoinDesk API 단일 기사 조회 오류: {e}")
            return {}
    
    def get_news_sources(self, lang="EN", source_type="RSS", status=["ACTIVE"], 
                        search_string=None) -> List[Dict[str, Any]]:
        """
        뉴스 소스 목록 조회 (Sources API)
        
        Args:
            lang: 언어 코드 (EN, ES, TR, FR, JP, PT)
            source_type: 소스 유형 (RSS, API, TWITTER)
            status: 상태 목록 (ACTIVE, INACTIVE) - 최대 10개
            search_string: 소스 검색 문자열 (ID, 이름, 키로 검색, 최대 100자)
        
        Returns:
            뉴스 소스 목록 (ID, SOURCE_KEY, NAME, IMAGE_URL, URL, LANG, SOURCE_TYPE, STATUS)
        """
        params = self.default_params.copy()
        params.update({
            "lang": lang,
            "source_type": source_type
        })
        
        # status는 배열로 전달
        if isinstance(status, list):
            params["status"] = status
        else:
            params["status"] = [status]
        
        if search_string:
            # 길이 제한 적용 (최대 100자)
            params["search_string"] = search_string[:100]
        
        try:
            resp = requests.get(self.SOURCE_LIST_URL, params=params, timeout=20)
            data = self._handle_api_response(resp)
            return data.get("Data", [])
        except Exception as e:
            print(f"CoinDesk API 뉴스 소스 목록 조회 오류: {e}")
            return []
    
    def get_news_categories(self, status="ACTIVE", search_string=None) -> List[Dict[str, Any]]:
        """
        뉴스 카테고리 목록 조회 (Categories API)
        
        Args:
            status: 카테고리 상태 (ACTIVE, INACTIVE)
            search_string: 카테고리 검색 문자열 (ID, 이름으로 검색, 최대 100자)
        
        Returns:
            카테고리 목록 (ID, NAME, STATUS 등)
        """
        params = self.default_params.copy()
        params.update({
            "status": status
        })
        
        if search_string:
            # 길이 제한 적용 (최대 100자)
            params["search_string"] = search_string[:100]
        
        try:
            resp = requests.get(self.CATEGORY_LIST_URL, params=params, timeout=20)
            data = self._handle_api_response(resp)
            return data.get("Data", [])
        except Exception as e:
            print(f"CoinDesk API 카테고리 목록 조회 오류: {e}")
            return []
    
    def search_news(self, search_string: str, source_key: str, lang="EN", 
                   limit=10, to_ts=None) -> List[Dict[str, Any]]:
        """
        뉴스 검색 (News Search API)
        
        Args:
            search_string: 검색 키워드 (필수, 1-1000자)
            source_key: 검색할 뉴스 소스 키 (필수, 예: 'coindesk', 'cryptocompare')
            lang: 언어 코드 (EN, ES, TR, FR, JP, PT)
            limit: 결과 개수 제한 (1-100, 기본값 10)
            to_ts: 지정된 타임스탬프 이전 기사만 검색
        
        Returns:
            검색 결과 목록
        """
        # 필수 파라미터 검증
        if not search_string or len(search_string.strip()) == 0:
            raise ValueError("search_string은 필수 파라미터입니다")
        if not source_key or len(source_key.strip()) == 0:
            raise ValueError("source_key는 필수 파라미터입니다")
            
        params = self.default_params.copy()
        params.update({
            "search_string": search_string[:1000],  # 최대 1000자 제한
            "source_key": source_key[:50],  # 최대 50자 제한
            "lang": lang,
            "limit": min(max(1, limit), 100)  # 1-100 범위 강제
        })
        
        if to_ts:
            params["to_ts"] = to_ts
        
        try:
            resp = requests.get(self.NEWS_SEARCH_URL, params=params, timeout=20)
            data = self._handle_api_response(resp)
            return data.get("Data", [])
        except Exception as e:
            print(f"CoinDesk API 뉴스 검색 오류: {e}")
            return []
    
    def get_latest_bitcoin_news(self, limit=5) -> List[Dict[str, Any]]:
        """
        최신 비트코인 뉴스 조회 (Search API 활용)
        """
        try:
            # CoinDesk 소스에서 비트코인 검색
            return self.search_news("bitcoin", "coindesk", limit=limit)
        except Exception as e:
            print(f"비트코인 뉴스 조회 실패: {e}")
            return []
    
    def get_latest_ethereum_news(self, limit=5) -> List[Dict[str, Any]]:
        """
        최신 이더리움 뉴스 조회 (Search API 활용)
        """
        try:
            return self.search_news("ethereum", "coindesk", limit=limit)
        except Exception as e:
            print(f"이더리움 뉴스 조회 실패: {e}")
            return []
    
    def get_all_active_sources(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        모든 활성 소스를 타입별로 분류하여 조회
        
        Returns:
            소스 타입별 분류된 딕셔너리 {'RSS': [...], 'API': [...], 'TWITTER': [...]}
        """
        result = {}
        source_types = ['RSS', 'API', 'TWITTER']
        
        for source_type in source_types:
            try:
                sources = self.get_news_sources(
                    source_type=source_type, 
                    status=["ACTIVE"]
                )
                result[source_type] = sources
            except Exception as e:
                print(f"{source_type} 소스 조회 실패: {e}")
                result[source_type] = []
                
        return result
    
    def search_across_all_sources(self, keyword: str, limit_per_source=5) -> Dict[str, List[Dict[str, Any]]]:
        """
        모든 활성 소스에서 키워드 검색
        
        Args:
            keyword: 검색할 키워드
            limit_per_source: 소스당 최대 결과 수
            
        Returns:
            소스별 검색 결과
        """
        results = {}
        
        try:
            # 1. 활성 소스 목록 가져오기
            all_sources = self.get_all_active_sources()
            
            # 2. 각 소스에서 검색 실행
            for source_type, sources in all_sources.items():
                for source in sources:
                    source_key = source.get('SOURCE_KEY')
                    if source_key:
                        try:
                            search_results = self.search_news(
                                keyword, 
                                source_key, 
                                limit=limit_per_source
                            )
                            if search_results:
                                results[source_key] = search_results
                        except Exception as e:
                            print(f"소스 {source_key} 검색 실패: {e}")
                            
        except Exception as e:
            print(f"전체 소스 검색 실패: {e}")
            
        return results
    
    def get_categorized_news(self, category_filter=None, limit=20) -> Dict[str, Any]:
        """
        카테고리별로 분류된 최신 뉴스 조회
        
        Args:
            category_filter: 특정 카테고리만 조회 (None이면 모든 활성 카테고리)
            limit: 총 뉴스 개수 제한
            
        Returns:
            카테고리별 뉴스 및 메타데이터
        """
        result = {
            "categories": [],
            "news_by_category": {},
            "total_articles": 0
        }
        
        try:
            # 1. 카테고리 목록 조회
            categories = self.get_news_categories(status="ACTIVE")
            result["categories"] = categories
            
            # 2. 카테고리별 뉴스 조회
            if category_filter:
                # 특정 카테고리만
                target_categories = [category_filter]
            else:
                # 모든 활성 카테고리
                target_categories = [cat.get('NAME') or cat.get('ID') for cat in categories[:5]]  # 상위 5개만
            
            for category in target_categories:
                if category:
                    try:
                        news = self.fetch_news(
                            categories=[category],
                            limit=limit//len(target_categories) if len(target_categories) > 0 else limit
                        )
                        result["news_by_category"][category] = news
                        result["total_articles"] += len(news)
                    except Exception as e:
                        print(f"카테고리 {category} 뉴스 조회 실패: {e}")
                        
        except Exception as e:
            print(f"카테고리별 뉴스 조회 실패: {e}")
            
        return result
    
    def get_comprehensive_news_summary(self) -> Dict[str, Any]:
        """
        5개 API를 모두 활용한 종합 뉴스 요약
        
        Returns:
            모든 API 정보를 포함한 종합 요약
        """
        summary = {
            "timestamp": datetime.now().isoformat(),
            "sources": {"total": 0, "by_type": {}},
            "categories": {"total": 0, "active": []},
            "latest_news": [],
            "bitcoin_news": [],
            "ethereum_news": [],
            "api_status": "unknown"
        }
        
        try:
            # API 키 유효성 검증
            if self.validate_api_key():
                summary["api_status"] = "valid"
                
                # 1. Sources 정보
                all_sources = self.get_all_active_sources()
                summary["sources"]["by_type"] = {k: len(v) for k, v in all_sources.items()}
                summary["sources"]["total"] = sum(summary["sources"]["by_type"].values())
                
                # 2. Categories 정보
                categories = self.get_news_categories()
                summary["categories"]["total"] = len(categories)
                summary["categories"]["active"] = [cat.get('NAME', 'Unknown') for cat in categories[:10]]
                
                # 3. 최신 일반 뉴스
                summary["latest_news"] = self.fetch_news(limit=10)
                
                # 4. 비트코인 특화 뉴스
                summary["bitcoin_news"] = self.get_latest_bitcoin_news(limit=5)
                
                # 5. 이더리움 특화 뉴스
                summary["ethereum_news"] = self.get_latest_ethereum_news(limit=5)
                
            else:
                summary["api_status"] = "invalid_key"
                
        except Exception as e:
            summary["api_status"] = f"error: {str(e)}"
            print(f"종합 뉴스 요약 생성 실패: {e}")
            
        return summary
    
    def get_active_sources_by_type(self, source_type="RSS") -> List[Dict[str, Any]]:
        """
        특정 유형의 활성 소스 조회
        
        Args:
            source_type: 소스 유형 (RSS, API, TWITTER)
        
        Returns:
            필터링된 활성 소스 목록
        """
        return self.get_news_sources(source_type=source_type, status=["ACTIVE"])
    
    def _handle_api_response(self, response) -> Dict[str, Any]:
        """
        API 응답 처리 및 에러 핸들링
        
        Args:
            response: requests.Response 객체
        
        Returns:
            파싱된 JSON 데이터
        
        Raises:
            Exception: API 에러 발생시
        """
        try:
            response.raise_for_status()
            data = response.json()
            
            # CoinDesk API 에러 구조 체크
            if "Err" in data and data["Err"]:
                error_info = data["Err"]
                raise Exception(f"CoinDesk API Error: {error_info}")
            
            return data
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise Exception("인증 실패: API 키를 확인하세요")
            elif response.status_code == 403:
                raise Exception("접근 거부: API 키 권한을 확인하세요")
            elif response.status_code == 429:
                raise Exception("요청 한도 초과: API 사용량을 확인하세요")
            else:
                raise Exception(f"HTTP 에러 {response.status_code}: {e}")
        except requests.exceptions.ConnectionError:
            raise Exception("CoinDesk API 서버에 연결할 수 없습니다")
        except requests.exceptions.Timeout:
            raise Exception("API 요청 시간이 초과되었습니다")
        except ValueError as e:
            raise Exception(f"응답 데이터 파싱 실패: {e}")
    
    def validate_api_key(self) -> bool:
        """
        API 키 유효성 검증 (Sources API 활용)
        
        Returns:
            API 키 유효 여부
        """
        try:
            # 간단한 소스 목록 조회로 API 키 테스트
            params = self.default_params.copy()
            params["lang"] = "EN"
            params["source_type"] = "RSS"
            params["status"] = ["ACTIVE"]
            
            print(f"🔍 API 키 검증 중... URL: {self.SOURCE_LIST_URL}")
            print(f"🔑 사용 중인 API 키: {self.api_key[:20]}...")
            
            resp = requests.get(self.SOURCE_LIST_URL, params=params, timeout=10)
            print(f"📡 응답 코드: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"📊 응답 데이터 키들: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                if isinstance(data, dict) and "Data" in data:
                    print(f"✅ 검증 성공! 데이터 수: {len(data.get('Data', []))}")
                    return True
            
            print(f"❌ 검증 실패 - 응답: {resp.text[:200]}")
            return False
            
        except Exception as e:
            print(f"API 키 검증 실패: {e}")
            return False
    
    def get_api_usage_info(self) -> Dict[str, Any]:
        """
        API 사용량 정보 조회 (가능한 경우)
        
        Returns:
            API 사용량 정보
        """
        # 실제 사용량 엔드포인트가 있다면 구현
        # 현재는 기본 정보만 반환
        return {
            "api_key": self.api_key[:10] + "...",  # API 키의 일부만 표시
            "base_domain": self.BASE_DOMAIN,
            "endpoints": {
                "article_list": self.ARTICLE_LIST_URL,
                "article_get": self.ARTICLE_GET_URL,
                "source_list": self.SOURCE_LIST_URL,
                "category_list": self.CATEGORY_LIST_URL,
                "search": self.NEWS_SEARCH_URL
            }
        }

