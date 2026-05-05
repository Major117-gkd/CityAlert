import os
import logging
import requests
import base64
from PIL import Image
from dotenv import load_dotenv
import json

load_dotenv()

# Configure Groq
api_key = os.getenv("GROQ_API_KEY")


def analyze_leak_image(photo_path):
    """
    Connects to Groq Vision API to analyze if there is an incident
    and estimate its severity based on the visual evidence.
    """
    if not api_key:
        logging.warning("GROQ_API_KEY not found. Falling back to simulation mode.")
        return _simulate_analysis(photo_path)

    try:
        logging.info(f"Real AI Analyzing image with Groq: {photo_path}")
        
        # Read and encode image in base64
        with open(photo_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = """
        Regarde attentivement cette photo envoyée par un citoyen.
        
        S'agit-il d'un incident urbain valide nécessitant une intervention ? Nous gérons 3 catégories principales :
        - Eau (Fuite d'eau, canalisation cassée, inondation, regard débordant)
        - Accident (Accident de la route, collision, véhicule accidenté, poteau renversé par voiture)
        - Electricité (Câbles électriques tombés, poteau électrique endommagé, étincelles, feu sur installation électrique)
        
        1. Indique si c'est valide (is_valid: bool). C'est valide SEULEMENT S'IL Y A DES PREUVES VISUELLES CLAIRES d'un vrai problème (ex: eau visible, voitures accidentées, câbles électriques arrachés). Si c'est juste une photo de chat, ou un sol sec normal, renvoie false.
        2. Détermine la catégorie (category: string) parmi: "Eau", "Accident", "Electricité", ou "Autre".
        3. Si is_valid est true, évalue la gravité (severity: string) parmi : "Petite", "Moyenne", "Élevée".
        
        Réponds uniquement sous format JSON strict comme ceci :
        {"is_valid": true, "category": "Eau", "severity": "Moyenne", "description": "Brève description en 10 mots"}
        """
        
        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            data_str = response.json()['choices'][0]['message']['content']
            data = json.loads(data_str)
                
            is_valid = data.get("is_valid", False)
            category = data.get("category", "Eau")
            severity = data.get("severity", "Moyenne")
            description = data.get("description", "Analyse terminée.")
            
            if is_valid:
                analysis_text = f"✅ *Analyse Réelle terminée :* {description}\n📂 *Catégorie :* {category}\n⚠️ *Sévérité :* {severity}"
            else:
                analysis_text = "⚠️ *Avertissement :* L'IA n'a pas détecté d'incident urbain (Eau, Accident ou Électricité) sur cette photo."
            
            return is_valid, category, severity, analysis_text
        else:
            logging.error(f"Groq API Error: {response.status_code} - {response.text}")
            return _simulate_analysis(photo_path, error_msg=f" (Erreur API: {response.status_code})")

    except Exception as e:
        logging.error(f"Groq Processing Error: {e}")
        return _simulate_analysis(photo_path, error_msg=f" (Erreur: {str(e)[:50]})")

def _simulate_analysis(photo_path, error_msg=""):
    """Fallback simulation mode if API key is missing or failed."""
    import random
    import time
    time.sleep(1)
    
    # Simple simulation logic: if filename contains 'fake', it's not a leak
    is_fake = "fake" in photo_path.lower()
    
    if is_fake:
         return False, "Inconnue", "Inconnue", f"ℹ️ *Mode Simulation{error_msg} :* Aucun incident détecté."
    
    severity_levels = ["Petite", "Moyenne", "Élevée"]
    categories = ["Eau", "Accident", "Electricité"]
    severity = random.choice(severity_levels)
    category = random.choice(categories)
    return True, category, severity, f"ℹ️ *Mode Simulation{error_msg} :* Incident détecté ({category})."
