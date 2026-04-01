#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de simulation pour tester l'intégration Telegram
"""

import requests
import json
import time
from datetime import datetime

# Configuration
WEBHOOK_URL = "http://localhost:8000/telegram/webhook/"
BOT_TOKEN = "8284846425:AAEHiSMcTq29RohwDJWNcmWJV0KdBnqrBXg"  # Token Telegram fourni

def send_telegram_message(chat_id, text):
    """Simule l'envoi d'un message Telegram vers le webhook."""
    payload = {
        "message": {
            "message_id": 12345,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Jean",
                "username": "jean_test",
                "language_code": "fr",
                "phone_number": "+33612345678"  # Numéro de téléphone simulé
            },
            "chat": {
                "id": chat_id,
                "first_name": "Jean",
                "username": "jean_test",
                "type": "private"
            },
            "date": int(time.time()),
            "text": text
        }
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"[OK] Message envoye avec succes: {text}")
            return True
        else:
            print(f"[ERREUR] Erreur envoi message: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[ERREUR] Erreur connexion webhook: {e}")
        return False

def send_telegram_location(chat_id, latitude, longitude):
    """Simule l'envoi d'une localisation Telegram."""
    payload = {
        "message": {
            "message_id": 12346,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Jean",
                "username": "jean_test",
                "language_code": "fr"
            },
            "chat": {
                "id": chat_id,
                "first_name": "Jean",
                "username": "jean_test",
                "type": "private"
            },
            "date": int(time.time()),
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "horizontal_accuracy": 50
            }
        }
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"[OK] Localisation envoyee: {latitude}, {longitude}")
            return True
        else:
            print(f"[ERREUR] Erreur envoi localisation: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERREUR] Erreur connexion webhook: {e}")
        return False

def simulate_telegram_flow():
    """Simule un flux complet d'utilisation du bot Telegram."""
    print("DEBUT DE LA SIMULATION TELEGRAM")
    print("=" * 50)
    
    chat_id = 123456789
    
    # 1. Commande /start
    print("\n1. Envoi de la commande /start...")
    send_telegram_message(chat_id, "/start")
    time.sleep(2)
    
    # 2. Signalement d'incident simple
    print("\n2. Signalement d'une fuite d'eau...")
    incident_message = "Fuite d'eau importante au coin de la rue principale. L'eau coule depuis environ 30 minutes. Merci d'intervenir rapidement."
    send_telegram_message(chat_id, incident_message)
    time.sleep(2)
    
    # 3. Signalement avec localisation
    print("\n3. Signalement d'accident avec localisation...")
    accident_message = "Accident de voiture avec deux vehicules impliques. Pas de blesses graves mais circulation bloquee."
    send_telegram_message(chat_id, accident_message)
    time.sleep(1)
    send_telegram_location(chat_id, 48.8566, 2.3522)  # Paris
    time.sleep(2)
    
    # 4. Signalement d'electricite
    print("\n4. Signalement d'un probleme electrique...")
    electric_message = "Panne de courant dans tout l'immeuble. Plus d'electricite depuis 2 heures. Plusieurs familles concernees."
    send_telegram_message(chat_id, electric_message)
    time.sleep(2)
    
    # 5. Commande /mesincidents
    print("\n5. Consultation des signalements...")
    send_telegram_message(chat_id, "/mesincidents")
    time.sleep(2)
    
    # 6. Commande /statut
    print("\n6. Consultation des statistiques...")
    send_telegram_message(chat_id, "/statut")
    time.sleep(2)
    
    # 7. Commande /help
    print("\n7. Demande d'aide...")
    send_telegram_message(chat_id, "/help")
    time.sleep(2)
    
    print("\n" + "=" * 50)
    print("SIMULATION TERMINEE")
    print("\nResume des actions simulees :")
    print("   • /start - Initialisation du bot")
    print("   • Signalement fuite d'eau")
    print("   • Signalement accident avec GPS")
    print("   • Signalement panne electrique")
    print("   • /mesincidents - Consultation")
    print("   • /statut - Statistiques")
    print("   • /help - Aide")
    
    print("\nVerifiez :")
    print("   • Les logs du serveur Django")
    print("   • La base de donnees (incidents crees)")
    print("   • Les emails envoyes a l'administrateur")
    print("   • Les reponses du bot (si configure)")

def simulate_admin_notification():
    """Simule la reception d'une notification admin."""
    print("\n" + "=" * 50)
    print("SIMULATION NOTIFICATION ADMIN")
    print("=" * 50)
    
    print("\nEmail qui devrait etre recu par l'admin :")
    print("   Destinataire: setiennetol2004@gmail.com")
    print("   Sujet: NOUVEAU SIGNALEMENT TELEGRAM - #XXX")
    print("   Contenu: Details complets du signalement")
    print("   Informations: Utilisateur, Telegram @, Email, Telephone")
    print("   Message original complet")
    
    print("\nPoints a verifier :")
    print("   • Boite de reception admin email")
    print("   • Logs d'envoi d'emails Django")
    print("   • Format HTML de l'email")
    print("   • Donnees utilisateur dans la base")

if __name__ == "__main__":
    print("LANCEMENT DE LA SIMULATION CITY ALERT TELEGRAM")
    print(f"Webhook cible: {WEBHOOK_URL}")
    print(f"Heure de debut: {datetime.now().strftime('%H:%M:%S')}")
    
    # Test de connexion au webhook
    try:
        response = requests.get("http://localhost:8000", timeout=5)
        if response.status_code == 200:
            print("Serveur Django accessible")
        else:
            print("Serveur Django non accessible")
    except:
        print("Impossible de joindre le serveur Django")
        print("\nAssurez-vous que le serveur Django est demarre sur localhost:8000")
    
    print("\nDebut automatique de la simulation...")
    
    # Lancer la simulation
    simulate_telegram_flow()
    simulate_admin_notification()
    
    print(f"\nHeure de fin: {datetime.now().strftime('%H:%M:%S')}")
