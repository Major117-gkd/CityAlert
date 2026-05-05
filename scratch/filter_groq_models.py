import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

url = "https://api.groq.com/openai/v1/models"
headers = {
    "Authorization": f"Bearer {api_key}"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        models = response.json().get('data', [])
        for model in models:
            m_id = model['id']
            if "vision" in m_id.lower() or "llama" in m_id.lower():
                print(f"- {m_id}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Error: {e}")
