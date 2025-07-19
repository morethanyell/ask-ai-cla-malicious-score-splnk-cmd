#!/usr/bin/env python

import os
import hashlib
import requests


class GoogleGeminiClient:
    # Constants
    PP_INTEGRITY = (
        'afbfd42ca1e939498c481d7f38fa572d609e1131ddaaca5939b4151cc2b50974'
    )
    PP_FNAME = 'PP000001_20250714.txt'
    GOOGLE_GEM_URL = 'https://generativelanguage.googleapis.com'

    def __init__(self, api_key, model=None, url=None, api_ver="v1beta"):
        self.api_key = api_key
        self.url = url or self.GOOGLE_GEM_URL
        self.model = model or "gemini-2.5-flash"
        self.api_ver = api_ver

    def _get_pre_prompt_path(self):
        """Compute and return the absolute path to the pre-prompt file."""
        dirname = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirname, self.PP_FNAME)

    def _calc_pre_prompt_sha256(self, file_path):
        """Calculate SHA256 for the provided file."""
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def get_pre_prompt(self):
        """Returns the pre-prompt content if present AND sha256 matches."""
        file_path = self._get_pre_prompt_path()

        if not os.path.exists(file_path):
            return None

        actual_hash = self._calc_pre_prompt_sha256(file_path)
        if actual_hash != self.PP_INTEGRITY:
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def url_gen(self):
        return f"{self.url}/{self.api_ver}/models/{self.model}:generateContent"

    def ask(self, prompt):
        """Ask Gemini a prompt. Returns (True, response_text) or (False, error_msg)."""
        pre_prompt = self.get_pre_prompt()

        if pre_prompt is None:
            msg = (
                "Splunk TA Error: Pre-prompt file integrity check failed. "
                f"Possible prompt injection attempt blocked. "
                f"Check $SPLUNK_HOME/etc/apps/TA-llm-command-scoring/bin/{self.PP_FNAME}"
            )
            return False, msg

        prompt_full = f'{pre_prompt}{prompt}\n```'

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
            url = self.url_gen()
            response = requests.post(url, headers=headers, json=payload, timeout=25)
            if response.status_code == 200:
                response_data = response.json()

                candidates = response_data.get("candidates")
                if not candidates:
                    return False, "Sorry, the API call was fine but Gemini did not respond correctly."

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
            return False, f"POST {self.url} returned an ERROR: {str(e)}"
