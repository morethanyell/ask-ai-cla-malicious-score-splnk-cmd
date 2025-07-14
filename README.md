# 🧠 TA-llm-command-scoring

TA-llm-command-scoring is a Splunk Technology Add-on that houses a custom Splunk command. It queries OpenAI's GPT to assess whether a process' command-line argument (CLA) appears malicious. 

This Splunk custom command accepts a field that contains a valid Command Line Argument, e.g.: `powershell.exe -nop -w hidden -enc aAB0AHQAcAA6AC8ALwAxADAAMAAuADEAMAAwAC4AMQAwADAALwBtAGEAbAB3AGEAcgBlAC4AZQB4AGUA`

The command will ask ChatGPT to scrutinize the command and will respond with a Likert-type score:

- [5] Definitely Malicious 
- [4] Possibly Malicious
- [3] Unclear 
- [2] Likely Benign 
- [1] Definitely Benign 
- [0] Invalid Process Command 

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
| claaiscore textfield=process api_name=my-openai-key output_field=ai_score
```

### Other optional params
- api_url — OpenAI's current working API URL
- temperature — A number ranging from 0.0 to 1.9. Temperature controls the randomness or creativity of the model's responses.

### Example search
```spl
| tstats max(_time) as _time from datamodel=Endpoint.Processes where Processes.process_name="cmd.exe" by Process.user Process.process
| rename Process.* as *
| claaiscore textfield=process api_name=my-api-key-with-valid-credit-0001
| table _time, user, process, ai_mal_score__process
```
