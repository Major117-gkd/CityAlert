import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

candidates = [
    "llama-3.2-11b-vision-preview",
    "llama-3.2-11b-vision",
    "llama-3.2-11b-vision-instruct",
    "llama-3.2-90b-vision-preview",
    "llama-3.2-90b-vision",
    "llama-3-8b-8192",
    "llama3-8b-8192"
]

url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

for model in candidates:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 5
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        print(f"Model: {model} -> Status: {response.status_code}")
        if response.status_code == 200:
            print(f"SUCCESS: {model}")
            break
    except:
        pass
