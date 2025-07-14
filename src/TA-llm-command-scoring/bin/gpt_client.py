#!/usr/bin/env python

import requests
import os
import hashlib

class GPTClient:
    
    PP_INTEGRITY = 'afbfd42ca1e939498c481d7f38fa572d609e1131ddaaca5939b4151cc2b50974'
    PP_FNAME = 'PP000001_20250714'
    
    def __init__(self, api_key, url, temperature=0, model="gpt-4o"):
        self.api_key = api_key
        self.url = url
        self.temperature = temperature
        self.model = model
    
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

    def ask(self, prompt):
        
        retval = None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        pre_prompt = self.get_pre_prompt()
        
        if pre_prompt is None:
            return False, f"Splunk TA Error: Pre-prompt file integrity check failed. Possible prompt injection attempt blocked. Check $SPLUNK_HOME/etc/apps/TA-llm-command-scoring/bin/{self.PP_FNAME}"
        
        prompt = f'{pre_prompt}{prompt}\n```'
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature
        }
        
        try:
            
            response = requests.post(self.url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                retval = True, result["choices"][0]["message"]["content"]
            else:
                retval = False, f"POST {self.url} returned an ERROR: status_code={response.status_code}, err_details={response.text}"
            
        except requests.RequestException as e:
            return False, f"POST {self.url} returned an ERROR: {e}"       
        
        return retval
