import requests
import json

class GoogleGeminiClient:

    def __init__(self, api_key, url, model="gemini-2.5-flash", api_ver="v1beta"):
        self.api_key = api_key
        self.url = url
        self.model = model
        self.api_ver = api_ver

    @staticmethod
    def url_gen(self):
        return f"{self.url}/{self.api_ver}/models/{self.model}:generateContent"

    def ask(self, prompt):

        retval = None
        
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

            base_url = self.url_gen(self)
            ok_http_but_no_resp = "TA-llm-command-scoring: Sorry, the API call was fine but Gemini did not respond correctly."
            
            response = requests.post(base_url, headers=headers, data=json.dumps(payload))
            
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
        