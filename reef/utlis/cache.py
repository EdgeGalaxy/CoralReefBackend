import time
from typing import Dict, Tuple



class URLCache:
    def __init__(self):
        self._cache: Dict[Tuple[str, int], Tuple[float, str]] = {}
    
    def get(self, key: str, expires: int) -> str | None:
        cache_key = (key, expires)
        if cache_key in self._cache:
            timestamp, value = self._cache[cache_key]
            if time.time() < timestamp:
                return value
            del self._cache[cache_key]
        return None
    
    def set(self, key: str, expires: int, value: str):
        cache_key = (key, expires)
        self._cache[cache_key] = (time.time() + expires, value)


url_cache = URLCache()