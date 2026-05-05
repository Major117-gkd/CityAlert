# CityAlert (Smart City Command Center)

CityAlert est une plateforme professionnelle de supervision urbaine multiservices. Initialement conçue pour le monitoring de l'eau, la solution a évolué pour devenir un véritable **Command Center** capable de gérer divers incidents urbains en temps réel.

- **Supervision Multi-Incidents** : Fuites d'eau, accidents de la route, pannes électriques et anomalies urbaines.
- **Bot Telegram Intelligent** : Signalement citoyen fluide avec analyse de photos par IA.
- **Tableau de Bord Premium** : Design "Command Center" futuriste (Dark Mode, Cyan Néon) pour une supervision haute performance.
- **IA de Vision Avancée** : Intégration de Groq AI pour l'expertise automatique des signalements.
- **Haute Disponibilité IA** : Utilisation des modèles Llama 3 et Llama 3.2 Vision de Groq pour garantir une réponse ultra-rapide.
- **Cerveau Local (Infaillibilité)** : Base de connaissances locale intégrée permettant à l'assistant de répondre instantanément aux questions de base sans solliciter l'IA.
- **Commandes Vocales** : Assistant intelligent acceptant la voix et le texte pour une interaction mains-libres.

## 🚀 Fonctionnalités Professionnelles

### 📊 Supervision Urbaine & BI (Django)

- **Smart Dashboard** : Visualisation temps réel des indicateurs clés (KPIs) via `dashboard/index.html` avec un design premium.
- **Analyses Stratégiques** : Graphiques dynamiques Chart.js pour le suivi des tendances d'incidents.
- **Gestion des Équipes** : Module complet de gestion des techniciens par spécialité (Eau, Voirie, Électricité).
- **Exportation de Données** : Rapports CSV natifs pour l'archivage et l'audit.

### 🧠 Intelligence Artificielle & Robustesse

- **Google Gemini 2.0 Flash (Primaire)** : Analyse visuelle et textuelle de pointe pour une précision maximale.
- **Haute Disponibilité (Failover)** : Basculement transparent vers Gemini 1.5 Flash si l'API 2.0 est saturée.
- **Cerveau Local Intégré** : Réponse instantanée aux questions de fonctionnement (aide, signalement, profil) via une base de données locale sécurisée.
- **Assistant Premium mémoriel** : Chatbot du dashboard doté d'une mémoire de conversation et d'un design Glassmorphism ultra-moderne.
- **Interface Vocale (STT)** : Transcription audio intégrée pour piloter l'assistant par la voix.
- **Expérience Citoyenne** : Bot Telegram complet avec gestion de profil et notifications d'état.

### 🗺️ Intelligence Géographique & Mapping

- **Cartographie Interactive** : Intégration Leaflet.js pour la localisation précise des incidents.
- **Heatmap Urbaine** : Visualisation des zones de forte intensité d'incidents pour optimiser les interventions.
- **Géocodage Inverse** : Traduction automatique des coordonnées GPS en adresses postales lisibles.

### 🔌 API REST

- **Accès aux données** : endpoints FastAPI dans `src/api/` pour récupérer les signalements.

## 📂 Structure du Projet

```text
WaterAlert/
├── data/                    # Base de données SQLite
├── src/
│   ├── api/                 # API REST (FastAPI)
│   ├── bot/                 # Intelligence du Bot Telegram
│   ├── database/            # Logique DB (Historique & Tracking)
│   └── utils/               # Utilitaires (IA, Geocoding, PDF)
├── dashboard/               # Application Django (UI, vues, templates)
├── water_alert_admin/       # Projet Django (settings, urls, wsgi/asgi)
├── manage.py                # Entrée principale Django
├── verify_setup.py          # Script de diagnostic technique
├── .env                     # Configuration (Tokens Telegram & Gemini)
└── requirements.txt         # Dépendances (Django, FastAPI, bot, IA)
```

> Le tableau de bord Streamlit a été supprimé : toute la partie analytique et cartographique est maintenant servie exclusivement par Django.

## 🛠️ Installation & Configuration

1. **Préparation (Environnement recommandé)** :

   ```powershell
   # Création d'un nouvel environnement si nécessaire
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

   *Note : Si vous rencontrez des problèmes avec `venv`, vous pouvez installer les dépendances globalement ou via l'espace utilisateur.*

2. **Variables d'environnement (.env)** :

   Créez un fichier `.env` à la racine :

   ```env
   TELEGRAM_BOT_TOKEN=votre_token_botfather
   GEMINI_API_KEY=votre_cle_google_ai_studio
   ```

3. **Vérification du système** :

   Lancez le script de diagnostic pour valider votre installation :

   ```powershell
   python verify_setup.py
   ```

## 🖥️ Utilisation

### Lancer le Bot (Signalement)

```bash
python src/bot/telegram_bot.py
```

### Lancer le Dashboard Django (Analyse 100% dynamique)

```bash
python manage.py migrate
python manage.py runserver
```

Puis ouvrez `http://127.0.0.1:8000/` dans votre navigateur pour accéder au tableau de bord CityAlert (Django).

### Lancer l'API FastAPI (optionnelle)

```bash
python src/api/main.py
```

## 🛡️ Sécurité

- Protection des données sensibles via `.gitignore`.
- Mode "Simulation" automatique si la clé IA est absente.
