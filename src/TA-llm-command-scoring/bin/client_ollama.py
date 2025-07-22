#!/usr/bin/env python

import requests
import time
import json
import re
from urllib.parse import urlparse, urlunparse
from typing import Optional, Tuple
from helper_preprompt import * 

class OllamaLocalLLMClient:

    OLLAMA_URL = 'http://localhost'

    def __init__(
        self,
        model: Optional[str] = None,
        api_url: Optional[str] = None,
        port: Optional[int] = None,
    ):
        self.model = model
        self.url = api_url or self.OLLAMA_URL
        self.port = port or 11434
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
            "api_url": self.url_gen() or "n/a",
            "api_port": self.port
        }
        
    @staticmethod
    def _remove_think_blocks(self, text):
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    
    def url_gen(self):
        parsed = urlparse(self.url)

        # If there's already a port, we trust it's correct
        if parsed.port:
            return f"{self.url}/api/chat"
        # No port in the original, append self.port if available
        if self.port:
            # Rebuild the netloc with the port
            netloc = f"{parsed.hostname}:{self.port}"
            if parsed.username and parsed.password:
                netloc = f"{parsed.username}:{parsed.password}@{netloc}"
            elif parsed.username:
                netloc = f"{parsed.username}@{netloc}"

            new_parsed = parsed._replace(netloc=netloc)
            return f"{urlunparse(new_parsed)}/api/chat"

        # No port and no port to add
        return f"{self.url}/api/chat"
    
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

        url = self.url_gen()
        
        prompt_full = f'{pre_prompt}{prompt}\n```'
        
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": prompt_full
            }]
        }

        try:

            response = requests.post(url, headers=headers, json=payload, stream=True)
            response_text = ""
            
            with requests.post(url, json=payload, stream=True, timeout=(3.05, 27)) as response:
                
                if response.status_code > 299:
                    return (
                        False,
                        f"POST {self.url} returned an ERROR: status_code={response.status_code}, err_details={response.text}"
                    )
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line.decode('utf-8'))
                        content = chunk.get("message", {}).get("content", "")
                        response_text += content
                
            response_text_clean = self._remove_think_blocks(self, response_text)
            return True, response_text_clean

        except requests.RequestException as e:
            end_time = time.perf_counter()
            self._last_elapsed = end_time - start_time
            return False, f"POST {self.url} returned an ERROR: {str(e)}"
