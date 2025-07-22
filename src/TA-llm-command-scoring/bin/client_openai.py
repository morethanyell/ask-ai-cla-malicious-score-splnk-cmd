#!/usr/bin/env python

import requests
import time
from typing import Optional, Tuple
from helper_preprompt import *

class OpenAIGPTClient:

    OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions'

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        url: Optional[str] = None,
        temperature: Optional[float] = 0.0
    ):
        self.api_key = api_key
        self.model = model or "gpt-4o"
        self.url = url or self.OPENAI_API_URL
        self.temperature = temperature or 0.0
        self._last_elapsed = None

    @staticmethod
    def _mask_api_for_debug(self, input_string):
        if len(input_string) < 3:
            # Handle cases where the string is shorter than 3 characters
            return input_string + "*******"
        else:
            return input_string[:3] + "*******"
    
    def get_last_elapsed_time(self):
        return self._last_elapsed
    
    def get_full_query_params(self):
        return {
            "api_key": self._mask_api_for_debug(self, self.api_key) or "n/a",
            "api_url": self.url or "n/a",
            "model": self.model or "n/a",
        }

    def ask(self, prompt: str) -> Tuple[bool, str]:
        
        start_time = time.perf_counter()
        pph = PrePromptHandler()
        pre_prompt = pph.get_pre_prompt()
        
        if pre_prompt is None:
            msg = (
                "Splunk TA Error: Pre-prompt file integrity check failed. "
                f"Possible prompt injection attempt blocked. "
                f"Check $SPLUNK_HOME/etc/apps/TA-llm-command-scoring/bin/{self.PP_FNAME}"
            )
            return False, msg

        prompt_full = f'{pre_prompt}{prompt}\n```'

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt_full}],
            "temperature": self.temperature
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=30)
            end_time = time.perf_counter()
            self._last_elapsed = end_time - start_time
            
            if response.status_code == 200:
                
                data = response.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                if content:
                    return True, content
                else:
                    return False, "Sorry, the API call was fine but OpenAI ChatGPT's response was either broken or empty."
            else:
                return (
                    False,
                    f"POST {self.url} returned an ERROR: status_code={response.status_code}, err_details={response.text}"
                )
        except requests.RequestException as e:
            end_time = time.perf_counter()
            self._last_elapsed = end_time - start_time
            return False, f"POST {self.url} returned an ERROR: {str(e)}"
