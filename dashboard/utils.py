import math
from .models import Technician

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculates the Haversine distance between two points in km.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float('inf')
        
    R = 6371  # Earth radius in km
    
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2)**2
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def find_closest_technician(incident):
    """
    Finds the closest available technician for the incident's category.
    """
    if incident.latitude is None or incident.longitude is None:
        return None, None
        
    # Filter technicians by category and available status
    available_techs = Technician.objects.filter(
        category=incident.category,
        status='Libre',
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    closest_tech = None
    min_distance = float('inf')
    
    for tech in available_techs:
        dist = calculate_distance(
            incident.latitude, incident.longitude,
            tech.latitude, tech.longitude
        )
        if dist < min_distance:
            min_distance = dist
            closest_tech = tech
            
    return closest_tech, min_distance
