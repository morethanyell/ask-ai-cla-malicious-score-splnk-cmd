#!/usr/bin/env python

import requests
import time
from helper_preprompt import * 

class OllamaLocalLLMClient:

    OLLAMA_URL = 'http://localhost'

    def __init__(self, model=None, url=None, port=11434):
        self.model = model
        self.url = url or self.OLLAMA_URL
        self.port = port
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
            "model": self.model or "n/a",
            "api_url": self.url or "n/a",
            "api_port": self.port,
        }
    
    def url_gen(self):
        return f"{self.url}:{self.port}/api/chat"
    
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

        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "stream": False,
            "message": {
                "role": "user",
                "content": prompt_full
            }
        }

        try:
            url = self.url_gen()
            response = requests.post(url, headers=headers, json=payload)
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
                    return False, f"Sorry, the API call was fine but Ollama::{self.model}'s response was either broken or empty."
                
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
