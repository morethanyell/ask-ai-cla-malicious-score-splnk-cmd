#!/usr/bin/env python

import sys
import re
import json
from typing import Generator, Dict, Any, Tuple, Optional

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

# You must ensure that these client classes exist and are themselves well-structured.
from client_openai import OpenAIGPTClient
from client_google import GoogleGeminiClient

@Configuration()
class CLAAiScore(StreamingCommand):
    """
    Splunk streaming command for classifying command line arguments using LLM APIs.
    """

    textfield = Option(
        doc='''
        **Syntax:** **textfield=***<input_field_name>*
        **Description:** The field containing the command line argument, e.g.: process.''',
        require=True, validate=validators.Fieldname()
    )

    api_name = Option(
        doc='''
        **Syntax:** **api_name=***<string>*
        **Description:** The exact name of the API Name as created in the Configuration page.''',
        require=True
    )

    api_url = Option(
        doc='''
        **Syntax:** **api_url=***<string>*
        **Description:** (Optional) The URL where the LLM's API resides.''',
        require=False
    )

    model = Option(
        doc='''
        **Syntax:** **model=***<string>*
        **Description:** Select the Model, e.g.: gpt-4o or gemini-2.5.''',
        require=False
    )

    temperature = Option(
        doc='''
        **Syntax:** **temperature=***<range from 0-2.0>*
        **Description:** Model randomness. Defaults to 0.''',
        require=False, default=0
    )

    output_field = Option(
        doc='''
        **Syntax:** **output_field=***<string>*
        **Description:** The output field name. Defaults to ai_mal_score.''',
        require=False, default='ai_mal_score'
    )

    @staticmethod
    def safe_float(val) -> Optional[float]:
        """Safely convert input to float; return None on failure."""
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def get_llm_client(
        self, provider: str, api_key: str, api_url: Optional[str], model: Optional[str], temperature: float
    ):
        """Factory for supported LLM clients."""
        provider = provider.lower()

        if provider == 'openai':
            return OpenAIGPTClient(
                api_key=api_key,
                url=api_url,
                model=model,
                temperature=temperature
            )
        if provider == 'google':
            return GoogleGeminiClient(
                api_key=api_key,
                url=api_url,
                model=model
            )
        return None

    def stream(self, records: Generator[Dict[str, Any], None, None]) -> Generator[Dict[str, Any], None, None]:
        """
        The main Splunk streaming handler.
        """
        api_name_key = re.sub(r'\s+', '-', self.api_name.strip())
        secrets = self.service.storage_passwords
        no_result = f"Did not find any API Key that matches: {self.api_name}"
        err_field = 'err_msg'

        for record in records:
            # 1. Check for text field presence
            if self.textfield not in record:
                record[err_field] = f"No field such as '{self.textfield}' exists in this event."
                yield record
                continue

            # 2. Lookup credentials
            found_secrets = secrets.list(search=api_name_key) or []
            fs_clearpwd = None

            for fs in found_secrets:
                if api_name_key == fs.content['username']:
                    fs_clearpwd = fs.content.get('clear_password', '')
                    break

            if not fs_clearpwd:
                record[err_field] = no_result
                yield record
                continue

            # 3. Parse secrets blob (prevents splatting if the JSON is corrupt)
            try:
                fs_param = json.loads(fs_clearpwd)
            except Exception:
                record[err_field] = "Could not parse credential JSON."
                yield record
                continue

            llm_provider = fs_param.get('credLlmProv')
            llm_api_key = fs_param.get('credApiKey')
            llm_model = fs_param.get('credModel') or self.model
            llm_temp = self.safe_float(self.temperature)
            if llm_temp is None or not (0 <= llm_temp <= 1.9):
                record[err_field] = "Invalid temperature parameter. Must be a number from 0 to 1.9"
                yield record
                continue

            # 4. Build prompt and LLM client
            prompt_text = record[self.textfield]
            llm_client = self.get_llm_client(
                provider=llm_provider,
                api_key=llm_api_key,
                api_url=self.api_url,
                model=llm_model,
                temperature=llm_temp
            )

            if not llm_client:
                record[err_field] = (
                    f"Custom command 'claaiscore' failed to generate "
                    f"an LLM Provider instance ({llm_provider}). Check configuration."
                )
                yield record
                continue

            # 5. Send to LLM and capture output
            try:
                ok, response = llm_client.ask(prompt=prompt_text)
            except Exception as exc:
                ok, response = False, f"Exception calling LLM: {exc}"

            result_field = (
                f"{self.output_field}__by{llm_provider}__{self.textfield}"
                if ok else err_field
            )
            record[result_field] = response

            yield record


# Command Registration
if __name__ == "__main__":
    dispatch(CLAAiScore, sys.argv, sys.stdin, sys.stdout, __name__)