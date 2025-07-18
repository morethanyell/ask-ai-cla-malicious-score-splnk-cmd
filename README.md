# 🧠 TA-llm-command-scoring

TA-llm-command-scoring is a Splunk Technology Add-on that provides a custom streaming command designed specifically for evaluating command-line arguments (CLAs) from process events. It leverages large language models to assess the likelihood that a given CLA is malicious, assigning a simple, interpretable score.

This add-on isn’t a general-purpose AI chatbot or prompt interface. It doesn’t aim to replace Splunk’s `| ai prompt=<prompt>` command from MLTK v5.6. Instead, it's a purpose-built, lightweight assistant focused solely on scrutinizing CLAs—a specialized tool to help SOC analysts cut through noise and surface risky executions fast.

The custom command accepts a field that contains a valid Command Line Argument, e.g.: `powershell.exe -nop -w hidden -enc aAB0AHQAcAA6AC8ALwAxADAAMAAuADEAMAAwAC4AMQAwADAALwBtAGEAbAB3AGEAcgBlAC4AZQB4AGUA`

It will ask the chosen AI model to scrutinize the command and will respond with a Likert-type score:
```
[5] Definitely Malicious 
[4] Possibly Malicious
[3] Unclear 
[2] Likely Benign 
[1] Definitely Benign 
[0] Invalid Process Command 
```
and a short explanation of why it chose that score. It integrates directly into Splunk searches via a custom streaming command and leverages LLMs' ability to read between the lines — at scale, without fatigue.

---

## ⚙️ Features

- 🧠 Supports both OpenAI GPT and Google Gemini (for now) to evaluate command-line arguments in real-time
- 🔐 Secure API key handling via Splunk's native credential storage
- ⚡ Fast, streaming-compatible custom search command
- 🔎 Customizable model, temperature, and output fields
- 🧩 Modular GPT client with pre-prompt integrity check to block tampering

---

## 📦 Installation

1. Get the latest release from the `releases` directory of this repo
2. Copy the TAR file into your Splunk search head
3. As a Splunk admin (or similar role), install the app by using the command `$SPLUNK_HOME/bin/splunk install app <release_file_name>`, e.g.: `$SPLUNK_HOME/bin/splunk install app /tmp/TA-llm-command-scoring_2_0_0.tar.gz`
4. Restart Splunk

---

## 🔐 API Key Setup

#### Button [ Add New LLM Provider ] (actually add new API credential)
- On first launch, a Splunk user with Admin role will be redirected to the setup page.
    - ⚠️ Note: Users without the Admin role cannot set up an API key or view the Configuration page.

    Form Fields
- Name : Provide a short, unique identifier for your API credential.
    - Special characters are not allowed
    - Whitespace will be replaced with hyphens
    - This name acts as the primary key used in the `api_name` command parameter
    - e.g., "My First ChatGPT" becomes: my-first-chatgpt
- Description : Add a brief summary—such as project purpose or key expiration date.
- LLM Provider : Pick the provider from the dropdown. Straightforward.
- Model : Optionally override the default model.
    - Examples: gemini-2.5-flash-lite-preview-06-17, gpt-4.1-2025-04-14
    - Invalid model names will throw an error.
- API Key : Paste your secret key here. Handle with care.

#### Button [ Add New LLM Provider ] (modify existing)
- If the name you enter already exists, the credential will be updated—not duplicated.
    - For example, if a credential with Name = "bard" already exists, re-submitting with "bard" will overwrite its description, provider, model, and secret key.

#### Button [ Delete Selected ]
- Click to delete the selected credential(s). (You know what this does. No surprises.)
---

## 🧪 Usage

This app comes with an authorize.conf that defines a role called "can_run_claaiscore". Only users with Admin and this role can view the app and run the command. However the custom command may be ran everywhere as it is exported globally. 

```spl
| your_search_here 
| claaiscore textfield=process api_name=my-openai-key
```

### Other optional params
- api_url — OpenAI's current working API URL (defaults to OpenAI or Google Gemini's working API URL as of 2025-July)
- temperature — A number ranging from 0.0 to 1.9. Temperature controls the randomness or creativity of the model's responses. (Defaults to 0.0)
- output_field — Give a field name to the AI's reponse (Defaults to `ai_mal_score__by<llm provider, i.e.: openai | google>__<name of the input textfied>`)

### Example search
```spl
| tstats max(_time) as _time from datamodel=Endpoint.Processes where Processes.process_name="lsass.exe" by Process.user Process.process
| rename Process.* as *
| claaiscore textfield=process api_name=chatgpt-expires-aug2025 output_field=decision
| fields _time user process decision__byopenai__process
| where match(decision__byopenai__process, "\[[45]\].+Malicious")
```

### TO-DO
- Add feature to support more LLM providers

### Beers
If you think this helps your organization and you're feeling a bit generous today, I'm happy to accept funds for my IPA beer, paypal: daniel.l.astillero@gmail.com
