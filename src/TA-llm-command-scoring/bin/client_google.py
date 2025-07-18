#!/usr/bin/env python

import requests
import os
import hashlib
import json

class GoogleGeminiClient:
    
    PP_INTEGRITY = 'afbfd42ca1e939498c481d7f38fa572d609e1131ddaaca5939b4151cc2b50974'
    PP_FNAME = 'PP000001_20250714.txt'
    GOOGLE_GEM_URL = 'https://generativelanguage.googleapis.com'

    def __init__(self, api_key, model, url=None, api_ver="v1beta"):
        self.api_key = api_key
        self.url = url or self.GOOGLE_GEM_URL
        self.model = model or "gemini-2.5-flash"
        self.api_ver = api_ver
        
    def calc_pre_prompt_sha256(self):
        sha = hashlib.sha256()
        with open(self.PP_FNAME, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha.update(chunk)
        return sha.hexdigest()
    
    def get_pre_prompt(self):
        file_path = os.path.join(os.path.dirname(__file__), self.PP_FNAME)
               
        if not os.path.exists(file_path):
            return None

        actual_hash = self.calc_pre_prompt_sha256()
        if actual_hash != self.PP_INTEGRITY:
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        return content

    @staticmethod
    def url_gen(self):
        return f"{self.url}/{self.api_ver}/models/{self.model}:generateContent"

    def ask(self, prompt):

        retval = None
        
        pre_prompt = self.get_pre_prompt()
        
        if pre_prompt is None:
            return False, f"Splunk TA Error: Pre-prompt file integrity check failed. Possible prompt injection attempt blocked. Check $SPLUNK_HOME/etc/apps/TA-llm-command-scoring/bin/{self.PP_FNAME}"
        
        prompt = f'{pre_prompt}{prompt}\n```'
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }

        try:

            url = self.url_gen(self)
            ok_http_but_no_resp = "TA-llm-command-scoring: Sorry, the API call was fine but Gemini did not respond correctly."
            
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            
            if response.status_code == 200:
                
                response_data = response.json()

                if "candidates" in response_data and response_data["candidates"]:

                    first_candidate = response_data["candidates"][0]
                    
                    if "content" in first_candidate and "parts" in first_candidate["content"]:
                        generated_text = ""
                        for part in first_candidate["content"]["parts"]:
                            if "text" in part:
                                generated_text += part["text"]
                        retval = True, generated_text
                    else:
                        retval = False, ok_http_but_no_resp
                else:
                    retval = False, ok_http_but_no_resp

            else:
                retval = False, f"POST {self.url} returned an ERROR: status_code={response.status_code}, err_details={response.text}"
            
        except requests.RequestException as e:
            retval = False, f"POST {self.url} returned an ERROR: {e}"
    
        return retval
        