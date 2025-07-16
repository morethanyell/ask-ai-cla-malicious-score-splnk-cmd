# 🧠 TA-llm-command-scoring

TA-llm-command-scoring is a Splunk Technology Add-on that provides a custom streaming command designed specifically for evaluating command-line arguments (CLAs) from process events. It leverages large language models to assess the likelihood that a given CLA is malicious, assigning a simple, interpretable score.

This add-on isn’t a general-purpose AI chatbot or prompt interface. It doesn’t aim to replace Splunk’s | ai prompt=<prompt> command from MLTK v5.6. Instead, it's a purpose-built, lightweight assistant focused solely on scrutinizing CLAs—a specialized tool to help SOC analysts cut through noise and surface risky executions fast.

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

- 🧠 Uses OpenAI (only, and for now) to evaluate command-line arguments in real-time
- 🔐 Secure API key handling via Splunk's native credential storage
- ⚡ Fast, streaming-compatible custom search command
- 🔎 Customizable model, temperature, and output fields
- 🧩 Modular GPT client with pre-prompt integrity check to block tampering

---

## 📦 Installation

1. Clone or download this repo into `$SPLUNK_HOME/etc/apps/`
2. Restart Splunk

---

## 🔐 API Key Setup

- During the first launch of the app, a Splunk user with Admin role would be redirected to setup page
- Add your OpenAI Developer Platform API Key and give it a unique name
---

## 🧪 Usage

This app comes with an authorize.conf that defines a role called "can_run_claaiscore". Only users with Admin and this role can view the app and run the command. However the custom command may be ran everywhere as it is exported globally.

```spl
| your_search_here 
| claaiscore textfield=process api_name=my-openai-key
```

### Other optional params
- api_url — OpenAI's current working API URL (Defaults to https://api.openai.com/v1/chat/completions)
- temperature — A number ranging from 0.0 to 1.9. Temperature controls the randomness or creativity of the model's responses. (Defaults to 0.0)
- output_field — Give a field name to the AI's reponse (Defaults to `ai_mal_score__<name of the input textfied>`)

### Example search
```spl
| tstats max(_time) as _time from datamodel=Endpoint.Processes where Processes.process_name="cmd.exe" by Process.user Process.process
| rename Process.* as *
| claaiscore textfield=process api_name=my-api-key-with-valid-credit-0001
| fields _time user process ai_mal_score__process
| where match(ai_mal_score__process, "\[[45]\].+Malicious")
```

### TO-DO
- Make the custom command multi-model

### Beers
If you think this helps your organization and you're feeling a bit generous today, I'm happy to accept funds for my IPA beer, paypal: daniel.l.astillero@gmail.com
