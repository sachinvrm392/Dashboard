import math
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
        api_key = (api_key or "").strip()
        if not api_key:
            return {'error': True, 'message': 'API key is missing or empty.'}
            
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
        api_key = (api_key or "").strip()
        if not api_key:
            return []
            
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
        api_key = (api_key or "").strip()
        if not api_key:
            return []
            
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

    @staticmethod
    def sync_conversations(bp):
        """
        Fetches conversation history for the given BusinessPartner from ElevenLabs
        and updates/creates records in CallConversations.
        """
        from datetime import datetime, timezone as dt_timezone
        from django.utils import timezone
        from .models import CallConversation
        from concurrent.futures import ThreadPoolExecutor

        api_key = (bp.elevenlabs_api_key or "").strip()
        if not api_key:
            return {'error': True, 'message': 'Business Partner does not have an ElevenLabs API key.'}

        headers = {"xi-api-key": api_key}
        conversations_list = []
        cursor = None
        page = 0
        max_pages = 5  # safety limit

        try:
            while page < max_pages:
                page += 1
                params = {'page_size': 100}
                if cursor:
                    params['cursor'] = cursor

                resp = requests.get(f"{ElevenLabsService.BASE_URL}/convai/conversations", headers=headers, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                page_items = data.get('conversations', [])
                if not page_items:
                    break
                conversations_list.extend(page_items)

                if data.get('has_more') and data.get('next_cursor'):
                    cursor = data.get('next_cursor')
                else:
                    break
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching conversation list: {e}")
            return {'error': True, 'message': f"Failed to fetch conversations: {str(e)}"}

        if not conversations_list:
            return {'success': True, 'synced_count': 0, 'created_count': 0, 'updated_count': 0, 'message': 'No conversations found on ElevenLabs.'}

        def fetch_detail(conv_summary):
            cid = conv_summary.get('conversation_id')
            if not cid:
                return conv_summary, None
            try:
                d_resp = requests.get(f"{ElevenLabsService.BASE_URL}/convai/conversations/{cid}", headers=headers, timeout=30)
                if d_resp.status_code == 200:
                    return conv_summary, d_resp.json()
            except Exception as ex:
                logger.warning(f"Error fetching detail for conversation {cid}: {ex}")
            return conv_summary, None

        with ThreadPoolExecutor(max_workers=6) as executor:
            detail_results = list(executor.map(fetch_detail, conversations_list))

        created_count = 0
        updated_count = 0

        for conv_summary, detail in detail_results:
            cid = conv_summary.get('conversation_id')
            if not cid:
                continue

            meta = (detail.get('metadata') or {}) if detail else {}
            charging = meta.get('charging') or {}
            phone_call = meta.get('phone_call') or {}
            init_data = (detail.get('conversation_initiation_client_data') or {}) if detail else {}

            # 1. Timestamp
            start_unix = conv_summary.get('start_time_unix_secs') or meta.get('start_time_unix_secs') or 0
            if start_unix:
                call_timestamp = datetime.fromtimestamp(start_unix, tz=dt_timezone.utc)
            else:
                call_timestamp = timezone.now()

            # 2. Agent ID
            agent_id = conv_summary.get('agent_id') or (detail.get('agent_id') if detail else '') or bp.elevenlabs_agent_id or ''

            # 3. Evaluation
            eval_val = conv_summary.get('call_successful')
            if not eval_val and detail:
                eval_val = (detail.get('analysis') or {}).get('call_successful') or detail.get('status')
            evaluation = str(eval_val).capitalize() if eval_val else (conv_summary.get('status', '').capitalize() or 'Unknown')

            # 4. Duration (raw seconds from API)
            duration = int(conv_summary.get('call_duration_secs') or meta.get('call_duration_secs') or 0)

            # 5. Messages
            transcript = (detail.get('transcript', [])) if detail else []

            # 6. Conversation Cost (integer truncation)
            if float(bp.cost_per_minute or 0) > 0:
                cost = float(int((duration / 60.0) * float(bp.cost_per_minute)))
            else:
                cost = float(int(float(meta.get('cost', 0))))

            # 7. Credits (LLM)
            credits_llm = float(charging.get('llm_charge', 0))

            # 8. Phone call fields
            caller_number = ''
            called_number = ''
            call_sid = ''
            caller_name = ''

            if isinstance(phone_call, dict) and phone_call:
                caller_number = phone_call.get('from_number') or phone_call.get('caller_id') or phone_call.get('caller_number') or ''
                called_number = phone_call.get('to_number') or phone_call.get('called_number') or ''
                call_sid = phone_call.get('call_sid') or phone_call.get('sid') or ''
                caller_name = phone_call.get('caller_name') or phone_call.get('name') or ''

            if isinstance(init_data, dict) and init_data:
                if not caller_number:
                    caller_number = init_data.get('caller_number') or init_data.get('phone_number') or ''
                if not caller_name:
                    caller_name = init_data.get('caller_name') or init_data.get('user_name') or init_data.get('name') or ''

            obj, created = CallConversation.objects.update_or_create(
                conversation_id=cid,
                defaults={
                    'business_partner': bp,
                    'call_timestamp': call_timestamp,
                    'agent_id': agent_id,
                    'evaluation': evaluation,
                    'duration': duration,
                    'messages': transcript,
                    'conversation_cost': cost,
                    'credits_llm': credits_llm,
                    'caller_number': caller_number,
                    'called_number': called_number,
                    'call_sid': call_sid,
                    'caller_name': caller_name,
                }
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        return {
            'success': True,
            'synced_count': len(detail_results),
            'created_count': created_count,
            'updated_count': updated_count,
            'message': f"Successfully synchronized {len(detail_results)} conversations ({created_count} new, {updated_count} updated)."
        }

