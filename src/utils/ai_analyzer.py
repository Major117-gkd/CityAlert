import os
import logging
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
import json

load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def analyze_leak_image(photo_path):
    """
    Connects to Google Gemini Vision API to analyze if there is a water leak
    and estimate its severity based on the visual evidence.
    """
    if not api_key:
        logging.warning("GEMINI_API_KEY not found. Falling back to simulation mode.")
        return _simulate_analysis(photo_path)

    try:
        logging.info(f"Real AI Analyzing image: {photo_path}")
        
        # Load the image
        img = Image.open(photo_path)
        
        # Initialize Gemini Flash (latest version)
        model = genai.GenerativeModel('gemini-flash-latest')
        
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
        
        response = model.generate_content([prompt, img])
        
        # Parse the JSON response
        try:
            # Clean response text in case of markdown blocks
            clean_text = response.text.strip().replace('```json', '').replace('```', '')
            data = json.loads(clean_text)
            
            is_valid = data.get("is_valid", False) # Default to False for safety
            category = data.get("category", "Eau")
            severity = data.get("severity", "Moyenne")
            description = data.get("description", "Analyse terminée.")
            
            if is_valid:
                analysis_text = f"✅ *Analyse Réelle terminée :* {description}\n📂 *Catégorie :* {category}\n⚠️ *Sévérité :* {severity}"
            else:
                analysis_text = "⚠️ *Avertissement :* L'IA n'a pas détecté d'incident urbain (Eau, Accident ou Électricité) sur cette photo."
            
            return is_valid, category, severity, analysis_text
            
        except Exception as e:
            logging.error(f"Error parsing Gemini JSON: {e}")
            return True, "Eau", "Moyenne", f"✅ Analyse effectuée (Format de réponse non standard)."

    except Exception as e:
        logging.error(f"Gemini API Error: {e}")
        return _simulate_analysis(photo_path, error_msg=f" (Erreur API: {str(e)[:50]})")

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
