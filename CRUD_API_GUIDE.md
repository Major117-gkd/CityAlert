# CRUD API pour la gestion des équipes et utilisateurs

## 📋 Vue d'ensemble

Les vues suivantes ont été converties en API CRUD complètes avec support AJAX/JSON :

### 🔧 **Gestion des Techniciens**

#### 1. **technician_list** - READ
- **URL** : `/technicians/`
- **Permissions** : Admin uniquement
- **Fonctionnalités** :
  - Retourne HTML (navigation normale)
  - Retourne JSON (AJAX requests)
  - Liste tous les techniciens avec informations complètes

#### 2. **add_technician** - CREATE
- **URL** : `/technicians/add/`
- **Permissions** : Admin uniquement
- **Fonctionnalités** :
  - Accepte JSON et formulaires
  - Validation des champs obligatoires
  - Retourne les données du technicien créé
  - Messages d'erreur détaillés

#### 3. **edit_technician** - UPDATE
- **URL** : `/technicians/edit/<pk>/`
- **Permissions** : Admin uniquement
- **Fonctionnalités** :
  - Mise à jour partielle ou complète
  - Gestion des erreurs de coordonnées
  - Retourne les données mises à jour

#### 4. **delete_technician** - DELETE
- **URL** : `/technicians/delete/<pk>/`
- **Permissions** : Admin uniquement
- **Fonctionnalités** :
  - Support POST et DELETE
  - Confirmation de suppression
  - Message de succès

### 👥 **Gestion des Utilisateurs**

#### 1. **user_management** - READ
- **URL** : `/users/`
- **Permissions** : Admin uniquement
- **Fonctionnalités** :
  - Liste tous les utilisateurs
  - Inclut les informations du profil
  - Support HTML/JSON

#### 2. **add_user** - CREATE
- **URL** : `/users/add/`
- **Permissions** : Admin uniquement
- **Fonctionnalités** :
  - Création d'utilisateurs complets
  - Vérification des doublons
  - Support staff/utilisateur normal

## 🔐 **Sécurité**

- **Vérification des permissions** : `is_staff` requis
- **Protection CSRF** : Maintenue pour les formulaires
- **Validation des données** : Contrôle complet des entrées
- **Gestion des erreurs** : Messages clairs et codes HTTP appropriés

## 📡 **Format des réponses JSON**

### Succès
```json
{
  "status": "success",
  "message": "Action réussie",
  "data": { ... }
}
```

### Erreur
```json
{
  "status": "error", 
  "message": "Description de l'erreur"
}
```

## 🔄 **Utilisation AJAX**

Les endpoints supportent les requêtes AJAX avec :
- **Header** : `X-Requested-With: XMLHttpRequest`
- **Content-Type** : `application/json` ou `form-data`
- **Méthodes** : GET, POST, PUT, DELETE

## 📝 **Exemples d'utilisation**

### Ajouter un technicien (JavaScript)
```javascript
fetch('/technicians/add/', {
  method: 'POST',
  headers: {
    'X-Requested-With': 'XMLHttpRequest',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'Jean Dupont',
    email: 'jean@example.com',
    phone: '0123456789',
    category: 'Eau',
    latitude: 48.8566,
    longitude: 2.3522
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

### Lister les utilisateurs (JavaScript)
```javascript
fetch('/users/', {
  headers: {
    'X-Requested-With': 'XMLHttpRequest'
  }
})
.then(response => response.json())
.then(data => {
  console.log(data.users);
});
```

## ✅ **Avantages**

1. **Double interface** : HTML + JSON
2. **Compatible SPA** : Applications modernes
3. **Réactivité** : Mises à jour sans rechargement
4. **Sécurité** : Validation et permissions
5. **Flexibilité** : Support multiples formats de données

Le système est maintenant prêt pour une interface d'administration moderne et réactive !
