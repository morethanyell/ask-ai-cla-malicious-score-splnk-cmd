#!/usr/bin/env python

import sys
import re
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from client_openai import OpenAIGPTClient

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

    def stream(self, records):
        
        no_result = f"Did not find any API Key that matches: {self.api_name}"
        api_name = re.sub(r'\s+', '-', self.api_name.strip())
        secrets = self.service.storage_passwords
        fs_clearpwd = None
        
        for r in records:
            
            if self.textfield not in r:
                r['err_msg'] = f"No field such as '{self.textfield}' exists in this event."
                yield r
                continue
            
            found_secrets = secrets.list(search=api_name)
            
            if len(found_secrets) < 0:
                r['err_msg'] = no_result
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
                r['err_msg'] = no_result
                yield r
                continue
            
            llm_temp = self.safe_float(self.temperature)
            if llm_temp is None:
                r['err_msg'] = "Invalid temperature paramter. Must be a number from 0 to 1.9"
                yield r
                continue
            
            soc_assistant = OpenAIGPTClient(
                api_key=fs_clearpwd,
                url=self.api_url,
                temperature=float(llm_temp),
                model=self.model
            )
            
            del fs_clearpwd
            
            cla_payload = r[self.textfield]
            no_err, response = soc_assistant.ask(prompt=cla_payload)
            outf = f'{self.output_field}__{self.textfield}' if no_err else 'err_msg'
            r[outf] = response
            
            yield r
            
        
dispatch(CLAAiScore, sys.argv, sys.stdin, sys.stdout, __name__)
