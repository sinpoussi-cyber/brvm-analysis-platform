#!/usr/bin/env python3
# ==============================================================================
# SCRIPT DE TEST DES NOUVEAUX ENDPOINTS
# ==============================================================================

import requests
import json
from pprint import pprint

# Configuration
BASE_URL = "https://brvm-api.onrender.com"  # ou "http://localhost:8000"
API_VERSION = "/api/v1"

# ==============================================================================
# 1. AUTHENTIFICATION
# ==============================================================================

def get_access_token():
    """Se connecter et récupérer le token"""
    print("\n" + "="*60)
    print("1️⃣  AUTHENTIFICATION")
    print("="*60)
    
    # Inscription (si nécessaire)
    register_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "User",
        "user_type": "retail"
    }
    
    # Tenter l'inscription (ignorera si l'utilisateur existe)
    try:
        response = requests.post(
            f"{BASE_URL}{API_VERSION}/auth/register",
            json=register_data
        )
        if response.status_code == 201:
            print("✅ Inscription réussie")
        elif response.status_code == 400:
            print("ℹ️  Utilisateur déjà existant, connexion...")
    except Exception as e:
        print(f"⚠️  Erreur inscription: {e}")
    
    # Connexion
    login_data = {
        "username": "test@example.com",  # OAuth2 utilise 'username'
        "password": "testpassword123"
    }
    
    response = requests.post(
        f"{BASE_URL}{API_VERSION}/auth/login",
        data=login_data  # form-data pour OAuth2
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✅ Token obtenu: {token[:30]}...")
        return token
    else:
        print(f"❌ Erreur connexion: {response.status_code}")
        print(response.text)
        return None

# ==============================================================================
# 2. TEST PERFORMANCE PAR SECTEUR
# ==============================================================================

def test_sectors_performance(token):
    """Tester l'endpoint de performance par secteur"""
    print("\n" + "="*60)
    print("2️⃣  PERFORMANCE PAR SECTEUR")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test avec différentes périodes
    periods = [7, 30, 90]
    
    for period in periods:
        print(f"\n📊 Performance sur {period} jours:")
        
        response = requests.get(
            f"{BASE_URL}{API_VERSION}/market/sectors/performance",
            headers=headers,
            params={"period": period}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {len(data['sectors'])} secteurs analysés")
            
            # Afficher top 3
            for i, sector in enumerate(data['sectors'][:3], 1):
                print(f"   {i}. {sector['sector']}: {sector['avg_change_percent']:.2f}%")
                print(f"      ({sector['company_count']} sociétés)")
        else:
            print(f"❌ Erreur {response.status_code}: {response.text}")

# ==============================================================================
# 3. TEST SOCIÉTÉS COMPARABLES
# ==============================================================================

def test_comparable_companies(token):
    """Tester l'endpoint des sociétés comparables"""
    print("\n" + "="*60)
    print("3️⃣  SOCIÉTÉS COMPARABLES")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Tester avec quelques symboles
    symbols = ["BICC", "SGBC", "NTLC", "PALC"]
    
    for symbol in symbols:
        print(f"\n🔍 Sociétés comparables à {symbol}:")
        
        response = requests.get(
            f"{BASE_URL}{API_VERSION}/companies/{symbol}/comparable",
            headers=headers,
            params={"limit": 5}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Secteur: {data['sector']}")
            print(f"✅ {len(data['comparable_companies'])} sociétés comparables:")
            
            for comp in data['comparable_companies']:
                print(f"   • {comp['symbol']} ({comp['name']})")
                print(f"     Similarité: {comp['similarity_score']:.1f}%")
                print(f"     Prix: {comp['current_price']:.2f} F CFA")
                print(f"     Variation: {comp['change_percent']:.2f}%")
        else:
            print(f"❌ Erreur {response.status_code}: {response.text}")

# ==============================================================================
# 4. TEST PRÉFÉRENCES UTILISATEUR
# ==============================================================================

def test_user_preferences(token):
    """Tester les endpoints de préférences"""
    print("\n" + "="*60)
    print("4️⃣  PRÉFÉRENCES UTILISATEUR")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Récupérer les préférences actuelles
    print("\n📖 Récupération des préférences:")
    response = requests.get(
        f"{BASE_URL}{API_VERSION}/users/preferences",
        headers=headers
    )
    
    if response.status_code == 200:
        prefs = response.json()
        print("✅ Préférences actuelles:")
        pprint(prefs)
    else:
        print(f"❌ Erreur {response.status_code}: {response.text}")
        return
    
    # Mettre à jour les préférences
    print("\n✏️  Mise à jour des préférences:")
    update_data = {
        "theme": "dark",
        "language": "en",
        "favorite_sectors": ["Banque", "Télécommunications"],
        "chart_type": "line"
    }
    
    response = requests.put(
        f"{BASE_URL}{API_VERSION}/users/preferences",
        headers=headers,
        json=update_data
    )
    
    if response.status_code == 200:
        updated = response.json()
        print("✅ Préférences mises à jour:")
        print(f"   Theme: {updated['theme']}")
        print(f"   Language: {updated['language']}")
        print(f"   Favorite sectors: {updated['favorite_sectors']}")
        print(f"   Chart type: {updated['chart_type']}")
    else:
        print(f"❌ Erreur {response.status_code}: {response.text}")
    
    # Réinitialiser les préférences
    print("\n🔄 Réinitialisation des préférences:")
    response = requests.post(
        f"{BASE_URL}{API_VERSION}/users/preferences/reset",
        headers=headers
    )
    
    if response.status_code == 200:
        reset = response.json()
        print("✅ Préférences réinitialisées:")
        print(f"   Theme: {reset['theme']}")
        print(f"   Language: {reset['language']}")
    else:
        print(f"❌ Erreur {response.status_code}: {response.text}")

# ==============================================================================
# EXÉCUTION DES TESTS
# ==============================================================================

def main():
    """Exécuter tous les tests"""
    print("\n" + "="*60)
    print("🧪 TEST DES NOUVEAUX ENDPOINTS - BRVM API")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    
    # 1. Authentification
    token = get_access_token()
    if not token:
        print("\n❌ Impossible de continuer sans token")
        return
    
    # 2. Performance par secteur
    test_sectors_performance(token)
    
    # 3. Sociétés comparables
    test_comparable_companies(token)
    
    # 4. Préférences utilisateur
    test_user_preferences(token)
    
    print("\n" + "="*60)
    print("✅ TOUS LES TESTS TERMINÉS")
    print("="*60)

if __name__ == "__main__":
    main()
