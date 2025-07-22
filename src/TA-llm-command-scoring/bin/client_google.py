#!/usr/bin/env python

import requests
import time
from helper_preprompt import * 

class GoogleGeminiClient:

    GOOGLE_GEM_URL = 'https://generativelanguage.googleapis.com'

    def __init__(self, api_key, model=None, url=None, api_ver="v1beta"):
        self.api_key = api_key
        self.url = url or self.GOOGLE_GEM_URL
        self.model = model or "gemini-2.5-flash"
        self.api_ver = api_ver
        self._last_elapsed = None
    
    @staticmethod
    def _mask_api_for_debug(self, input_string):
        if len(input_string) < 3:
            # Handle cases where the string is shorter than 3 characters
            return input_string + "*******"
        else:
            return input_string[:3] + "*******"
    
    def get_full_query_params(self):
        return {
            "api_key": self._mask_api_for_debug(self, self.api_key) or "n/a",
            "api_url": self.url or "n/a",
            "api_ver": self.api_ver or "n/a",
            "model": self.model or "n/a",
        }
    
    def url_gen(self):
        return f"{self.url}/{self.api_ver}/models/{self.model}:generateContent"
    
    def get_last_elapsed_time(self):
        return self._last_elapsed

    def ask(self, prompt):
        
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
        
        url = self.url_gen()

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt_full}]
                }
            ]
        }

        try:
            
            response = requests.post(url, headers=headers, json=payload, timeout=25)
            end_time = time.perf_counter()
            self._last_elapsed = end_time - start_time
            
            if response.status_code == 200:
                
                response_data = response.json()

                candidates = response_data.get("candidates")
                if not candidates:
                    return False, "Sorry, the API call was fine but Gemini's response was either broken or empty."

                first_candidate = candidates[0]
                content = first_candidate.get("content", {})
                parts = content.get("parts", [])
                generated_text = "".join(
                    part.get("text", "") for part in parts if "text" in part
                )
                return True, generated_text if generated_text else "No response text generated."
            else:
                error_msg = (
                    f"POST {self.url} returned an ERROR: "
                    f"status_code={response.status_code}, err_details={response.text}"
                )
                return False, error_msg

        except requests.RequestException as e:
            end_time = time.perf_counter()
            self._last_elapsed = end_time - start_time
            return False, f"POST {self.url} returned an ERROR: {str(e)}"
        
        
