#!/usr/bin/env python

import sys
import re
import json
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from client_openai import OpenAIGPTClient
from client_google import GoogleGeminiClient

@Configuration()
class CLAAiScore(StreamingCommand):

    textfield = Option(
        doc='''
        **Syntax:** **textfield=***<input_field_name>*
        **Description:** The field containing the command line argument, e.g.: process.''',
        require=True, validate=validators.Fieldname())

    api_name = Option(
        doc='''
        **Syntax:** **api_name=***<string>*
        **Description:** The exact name of the API Name as created in the Configuration page.''',
        require=True)

    api_url = Option(
        doc='''
        **Syntax:** **api_url=***<string>*
        **Description:** The URL where the LLM's API reside. Defaults to OpenAI Chat Completions.''',
        require=False)
    
    model = Option(
        doc='''
        **Syntax:** **model=***<string>*
        **Description:** Select the OpenAI LLModel, e.g.: gpt-4o. Defaults to gpt-4o''',
        require=False, default='gpt-4o')
    
    temperature = Option(
        doc='''
        **Syntax:** **output_field=***<range from 0-2.0>*
        **Description:** Temperature controls the randomness or creativity of the model's responses. Defaults to 0''',
        require=False, default=0)
    
    output_field = Option(
        doc='''
        **Syntax:** **output_field=***<string>*
        **Description:** The field name for the AI's response. Defaults to CMD_AI_MAL_SCORE''',
        require=False, default='ai_mal_score')
    
    def safe_float(self, val):
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    
    def llm_provider(self, llm_provider, llm_api_key, llm_api_url, llm_model, llm_temp=0.7):
        
        llm = None
        
        if llm_provider == 'openai':

            llm = OpenAIGPTClient(
                            api_key=llm_api_key,
                            url=llm_api_url,
                            temperature=llm_temp,
                            model=llm_model
                        )
        elif llm_provider == 'google':
            
            llm = GoogleGeminiClient(
                            api_key=llm_api_key,
                            url=llm_api_url,
                            model=llm_model
                        )
            
        return llm

    def stream(self, records):
        
        no_result = f"Did not find any API Key that matches: {self.api_name}"
        err_m = 'err_msg'
        api_name = re.sub(r'\s+', '-', self.api_name.strip())
        secrets = self.service.storage_passwords
        fs_clearpwd = None
        
        for r in records:
            
            if self.textfield not in r:
                r[err_m] = f"No field such as '{self.textfield}' exists in this event."
                yield r
                continue
            
            found_secrets = secrets.list(search=api_name)
            
            if len(found_secrets) < 0:
                r[err_m] = no_result
                yield r
                continue
            
            for fs in found_secrets:
                fs_username = fs.content['username']
                if api_name != fs_username:
                    continue
                else:
                    fs_clearpwd = fs.content['clear_password']
                    break
            
            if fs_clearpwd is None or fs_clearpwd == '':
                r[err_m] = no_result
                yield r
                continue
            
            llm_temp = self.safe_float(self.temperature)
            if llm_temp is None or not (0 <= llm_temp <= 1.9):
                r[err_m] = "Invalid temperature parameter. Must be a number from 0 to 1.9"
                yield r
                continue
            
            fs_param = json.loads(fs_clearpwd)
            fs_param_llm_provider = fs_param.get('credLlmProv')
            fs_param_llm_api_key = fs_param.get('credApiKey')
            fs_param_llm_api_model = fs_param.get('credModel', self.model)
            cla_payload = r[self.textfield]
            
            llm = self.llm_provider(llm_provider=fs_param_llm_provider, llm_api_key=fs_param_llm_api_key, llm_api_url=self.api_url, llm_model=fs_param_llm_api_model, llm_temp=llm_temp)
            
            if llm is None:
                r[err_m] = "The custom command `claaiscore` failed to generate an LLM Provider instance. Please contact the author of the app."
                yield r
                continue
            
            no_err, response = llm.ask(prompt=cla_payload)
            outf = f'{self.output_field}__{fs_param_llm_provider}__{self.textfield}' if no_err else err_m
            r[outf] = response
            
            yield r
            
        
dispatch(CLAAiScore, sys.argv, sys.stdin, sys.stdout, __name__)
