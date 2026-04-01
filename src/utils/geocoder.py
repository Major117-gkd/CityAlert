from geopy.geocoders import Nominatim
from geopy.exc import GeopyError
import logging

def get_address(latitude, longitude):
    """
    Convert lat, lon to a readable address using Nominatim (OpenStreetMap).
    """
    try:
        geolocator = Nominatim(user_agent="wateralert_app")
        location = geolocator.reverse((latitude, longitude), timeout=10)
        return location.address if location else "Adresse inconnue"
    except GeopyError as e:
        logging.error(f"Geocoding error: {e}")
        return "Erreur de géocodage"
    except Exception as e:
        logging.error(f"Unexpected error during geocoding: {e}")
        return "Localisation indisponible"
