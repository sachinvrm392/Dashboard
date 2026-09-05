import requests
import logging
from django.core.cache import cache
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)

class ElevenLabsService:
    BASE_URL = "https://api.elevenlabs.io/v1"
    
    @staticmethod
    def get_subscription_info(api_key):
        cache_key = f'elevenlabs_sub_{hashlib.md5(api_key.encode()).hexdigest()}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
            
        headers = {"xi-api-key": api_key}
        try:
            response = requests.get(f"{ElevenLabsService.BASE_URL}/user/subscription", headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            cache.set(cache_key, data, timeout=300)
            return data
        except requests.exceptions.RequestException as e:
            err_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    err_json = e.response.json()
                    detail = err_json.get('detail')
                    if isinstance(detail, dict) and 'message' in detail:
                        err_msg = detail['message']
                    elif isinstance(detail, str):
                        err_msg = detail
                except Exception:
                    pass
            logger.error(f"Error fetching subscription info: {err_msg}")
            return {'error': True, 'message': err_msg}

    @staticmethod
    def get_usage_history(api_key, start_date=None, end_date=None):
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
            
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
            
        cache_key = f'elevenlabs_usage_{hashlib.md5(api_key.encode()).hexdigest()}_{start_date_str}_{end_date_str}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
            
        headers = {"xi-api-key": api_key}
        start_unix_millis = int(start_date.timestamp() * 1000)
        end_unix_millis = int(end_date.timestamp() * 1000)
        payload = {
            "start_unix_millis": start_unix_millis,
            "end_unix_millis": end_unix_millis,
            "interval_seconds": 86400
        }
        
        try:
            url = f"{ElevenLabsService.BASE_URL}/workspace/analytics/query/usage-by-product-over-time"
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            cache.set(cache_key, data, timeout=300)
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching usage history: {e}")
            return []

    @staticmethod
    def get_voices(api_key):
        cache_key = f'elevenlabs_voices_{hashlib.md5(api_key.encode()).hexdigest()}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
            
        headers = {"xi-api-key": api_key}
        try:
            response = requests.get(f"{ElevenLabsService.BASE_URL}/voices", headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json().get('voices', [])
            cache.set(cache_key, data, timeout=300)
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching voices: {e}")
            return []
