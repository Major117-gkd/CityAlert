import sys
import os
import sqlite3

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))
from database.db_manager import DBManager

def test_database():
    print("--- 1. Verification de la Base de Données ---")
    db = DBManager("data/test_water_leaks.db")
    
    # Test insertion
    leak_id = db.add_leak(
        user_id=123,
        user_name="Test Citizen",
        photo_path="uploads/test.jpg",
        latitude=1.23,
        longitude=4.56
    )
    print(f"[OK] Insertion reussie (ID: {leak_id})")
    
    # Test retrieval
    leaks = db.get_all_leaks()
    if len(leaks) > 0:
        print(f"[OK] Recuperation reussie ({len(leaks)} signalements trouves)")
    else:
        print("[ERREUR] Aucun signalement trouve")
        return False

    # Test status update
    db.update_leak_status(leak_id, "En cours")
    updated_leak = db.get_leak_by_id(leak_id)
    # Status is the 11th column (index 10) according to the schema in db_manager.py
    if updated_leak[10] == "En cours":
        print("[OK] Mise a jour de statut reussie")
    else:
        print(f"[ERREUR] Echec de la mise a jour (Statut actuel: {updated_leak[10]})")
        return False
    
    # Cleanup test db
    import time
    time.sleep(0.5) # Wait for file lock release
    try:
        os.remove("data/test_water_leaks.db")
    except PermissionError:
        print("[NOTE] Impossible de supprimer le fichier de test temporaire (verrouille par Windows), mais les tests logiques ont reussi.")
    return True

def test_files():
    print("\n--- 2. Verification de la Structure des Fichiers ---")
    required_files = [
        "src/database/db_manager.py",
        "src/bot/telegram_bot.py",
        "src/dashboard/app.py",
        ".env",
        "requirements.txt"
    ]
    for f in required_files:
        if os.path.exists(f):
            print(f"[OK] {f} present")
        else:
            print(f"[ERREUR] {f} manquant")

if __name__ == "__main__":
    test_files()
    if test_database():
        print("\n[OK] TOUT FONCTIONNE ! Le systeme est pret.")
    else:
        print("\n[ERREUR] DES ERREURS ONT ETE DETECTEES.")
