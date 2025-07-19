#!/usr/bin/env python

import os
import hashlib
import requests
from typing import Optional, Tuple


class OpenAIGPTClient:
    """
    Client for querying OpenAI GPT models, with pre-prompt integrity checking.
    """

    # File and integrity constants
    PP_INTEGRITY = 'afbfd42ca1e939498c481d7f38fa572d609e1131ddaaca5939b4151cc2b50974'
    PP_FNAME = 'PP000001_20250714.txt'
    OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions'

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        url: Optional[str] = None,
        temperature: float = 0.0
    ):
        self.api_key = api_key
        self.model = model or "gpt-4o"
        self.url = url or self.OPENAI_API_URL
        self.temperature = temperature

    def _pre_prompt_path(self) -> str:
        """Return absolute path to pre-prompt file."""
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), self.PP_FNAME)

    def _calc_file_sha256(self, file_path: str) -> str:
        """Compute the SHA256 of the given file."""
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def get_pre_prompt(self) -> Optional[str]:
        """
        Load and verify the pre-prompt file content.
        Returns file content if the integrity check passes, else None.
        """
        file_path = self._pre_prompt_path()
        if not os.path.exists(file_path):
            return None

        if self._calc_file_sha256(file_path) != self.PP_INTEGRITY:
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def ask(self, prompt: str) -> Tuple[bool, str]:
        """
        Queries the OpenAI model with the pre_prompt + user prompt.
        Returns (success, response_text or error_message).
        """
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
                    return False, "API call succeeded but no content returned."
            else:
                return (
                    False,
                    f"POST {self.url} returned ERROR: status_code={response.status_code}, details={response.text}"
                )
        except requests.RequestException as e:
            return False, f"POST {self.url} returned ERROR: {e}"
