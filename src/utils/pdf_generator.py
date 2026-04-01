from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
import os
import io

def generate_leak_pdf(leak_info):
    """
    Generates a PDF report for a specific leak.
    leak_info: tuple or dict containing (ID, User ID, Citizen, Photo Path, Lat, Lon, Address, Severity, Status, Timestamp)
    """
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(1 * inch, height - 1 * inch, "Rapport d'Intervention - WaterAlert")
    p.setStrokeColor(colors.blue)
    p.line(1 * inch, height - 1.1 * inch, width - 1 * inch, height - 1.1 * inch)

    # Content
    p.setFont("Helvetica", 12)
    y_position = height - 1.5 * inch
    
    fields = [
        ("Identifiant :", f"#{leak_info[0]}"),
        ("Citizen :", leak_info[2]),
        ("Date :", leak_info[9]),
        ("Adresse :", leak_info[6]),
        ("Coordonnées :", f"{leak_info[4]}, {leak_info[5]}"),
        ("Sévérité :", leak_info[7]),
        ("Statut Actuel :", leak_info[8]),
    ]

    for label, value in fields:
        p.setFont("Helvetica-Bold", 12)
        p.drawString(1 * inch, y_position, label)
        p.setFont("Helvetica", 12)
        p.drawString(2.5 * inch, y_position, str(value))
        y_position -= 0.3 * inch

    # Add Photo if exists
    photo_path = leak_info[3]
    if photo_path and os.path.exists(photo_path):
        try:
            p.drawString(1 * inch, y_position - 0.2 * inch, "Photo du Signalement :")
            # Resize image to fit
            p.drawImage(photo_path, 1 * inch, y_position - 3.5 * inch, width=4 * inch, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            p.drawString(1 * inch, y_position - 0.5 * inch, f"[Erreur chargement photo: {e}]")

    # Footer
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(1 * inch, 1 * inch, "Document généré automatiquement par le système WaterAlert.")

    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer
