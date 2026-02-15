from abc import ABC, abstractmethod
from typing import List, Dict, Any

class NewsAPIBase(ABC):
    @abstractmethod
    def fetch_news(self, **kwargs) -> List[Dict[str, Any]]:
        pass
