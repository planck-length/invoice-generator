from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import simpleSplit
import io
from flask import send_file
import datetime
import os

# Register Fonts
base_dir = os.path.dirname(os.path.abspath(__file__))
dejavu_sans_path = os.path.join(base_dir, 'static', 'DejaVuSans.ttf')
dejavu_sans_bold_path = os.path.join(base_dir, 'static', 'DejaVuSans-Bold.ttf')

try:
    pdfmetrics.registerFont(TTFont('DejaVuSans', dejavu_sans_path))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', dejavu_sans_bold_path))
except Exception as e:
    print(f"Error registering font: {e}")

def generate_main_invoice_pdf(data):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Margins
    left_margin = 10 * mm
    right_margin = 10 * mm
    top_margin = 10 * mm
    bottom_margin = 10 * mm

    # Header
    # Logo
    try:
        logo_path = "static/logo.png"
        c.drawImage(logo_path, left_margin, height - top_margin - 25*mm, width=25*mm, height=25*mm, mask='auto')
    except Exception:
        # Fallback if logo not found
        c.circle(left_margin + 15*mm, height - top_margin - 15*mm, 10*mm)
    
    # Company Name "UNA TEKSTIL"
    c.setFont("DejaVuSans-Bold", 24)
    c.drawString(left_margin + 35*mm, height - top_margin - 10*mm, '"UNA TEKSTIL"')
    
    # Subtitle
    c.setFont("DejaVuSans", 8)
    c.drawString(left_margin + 35*mm, height - top_margin - 15*mm, "DOO za proizvodnju i trgovinu tekstilom")
    c.drawString(left_margin + 55*mm, height - top_margin - 19*mm, "Safeta Zajke 314")
    c.drawString(left_margin + 60*mm, height - top_margin - 23*mm, "SARAJEVO")
    c.drawString(left_margin + 58*mm, height - top_margin - 27*mm, "P.J. ŽIVINICE")

    # Company Details (Top Right)
    c.setFont("DejaVuSans", 8)
    details_x = width - right_margin - 60*mm
    details_y = height - top_margin - 10*mm
    line_height = 3.5*mm
    
    c.drawString(details_x + 15*mm, details_y, "Tel/fax: 033 673 300;")
    c.drawString(details_x, details_y - line_height, "Mob: 061 135 926; 061 252 919")
    c.drawString(details_x + 2*mm, details_y - 2*line_height, "Žiro račun: 1610000001700033")
    c.drawString(details_x + 10*mm, details_y - 3*line_height, "I.D. Broj: 420002130000")
    c.drawString(details_x + 6*mm, details_y - 4*line_height, "Poreski broj: 01634522")
    c.drawString(details_x - 10*mm, details_y - 5*line_height, "UF/I-472/02 Kantonalni sud Sarajevo")

    # Line separator
    c.line(left_margin, height - top_margin - 35*mm, width - right_margin, height - top_margin - 35*mm)

    # Title
    c.setFont("DejaVuSans-Bold", 14)
    title_y = height - top_margin - 45*mm
    c.drawString(left_margin, title_y, "SPISAK KUPACA - Račun br. __________________")
    
    # Invoice Number overlay
    if data.get('invoice_number'):
        c.drawString(left_margin + 85*mm, title_y, data['invoice_number'])

    # Subtitle 2
    c.setFont("DejaVuSans", 10)
    c.drawString(left_margin, title_y - 5*mm, "(U pozivu na broj navesti broj računa)")

    # Second Line separator
    c.line(left_margin, title_y - 15*mm, width - right_margin, title_y - 15*mm)
    
    # Table Header
    table_top = title_y - 20*mm
    row_height = 8*mm
    
    # Column widths
    col_widths = [
        10*mm,  # Red broj
        115*mm, # Prezime i ime kupca
        25*mm,  # UKUPNO OTPLATA
        40*mm   # Broj Telefona
    ]
    
    x_positions = [left_margin]
    for w in col_widths:
        x_positions.append(x_positions[-1] + w)

    # Draw Grid Header
    c.setLineWidth(1)
    c.rect(left_margin, table_top - 15*mm, width - left_margin - right_margin, 15*mm)
    
    # Vertical lines for header
    for x in x_positions[1:-1]:
        c.line(x, table_top, x, table_top - 15*mm)

    # Header Text
    c.setFont("DejaVuSans-Bold", 9)
    
    # Red broj
    c.drawString(x_positions[0] + 1*mm, table_top - 6*mm, "Red")
    c.drawString(x_positions[0] + 1*mm, table_top - 10*mm, "broj")
    
    # Prezime i ime
    c.drawString(x_positions[1] + 15*mm, table_top - 8*mm, "Prezime i ime kupca")
    
    # Ukupno Otplata
    c.drawString(x_positions[2] + 2*mm, table_top - 4*mm, "UKUPNO")
    c.drawString(x_positions[2] + 2*mm, table_top - 8*mm, "OTPLATA")
    c.line(x_positions[2] + 1*mm, table_top - 10*mm, x_positions[3] - 1*mm, table_top - 10*mm)

    # Broj Telefona
    c.drawString(x_positions[3] + 2*mm, table_top - 8*mm, "Broj Telefona")

    # Table Rows
    current_y = table_top - 15*mm
    row_height = 6.5*mm # Adjusted to fit 25 rows
    
    entries = data.get('entries', [])
    
    for i in range(1, 26):
        # Draw row lines
        c.rect(left_margin, current_y - row_height, width - left_margin - right_margin, row_height)
        
        # Vertical lines
        for x in x_positions[1:-1]:
            c.line(x, current_y, x, current_y - row_height)
            
        # Row Number
        c.setFont("DejaVuSans-Bold", 9)
        c.drawCentredString(x_positions[0] + col_widths[0]/2, current_y - 4.5*mm, str(i))
        
        # Data
        if i <= len(entries):
            entry = entries[i-1]
            c.setFont("DejaVuSans", 9)
            # Name
            name_text = str(entry.get('name', ''))
            lines = simpleSplit(name_text, "DejaVuSans", 9, col_widths[1] - 4*mm)
            
            if len(lines) == 1:
                c.drawString(x_positions[1] + 2*mm, current_y - 4.5*mm, lines[0])
            elif len(lines) > 1:
                # Draw 2 lines
                c.drawString(x_positions[1] + 2*mm, current_y - 3*mm, lines[0])
                c.drawString(x_positions[1] + 2*mm, current_y - 6*mm, lines[1])
            
            # Total
            c.drawRightString(x_positions[3] - 2*mm, current_y - 4.5*mm, str(entry.get('total', '')))
            # Phone
            c.drawString(x_positions[3] + 2*mm, current_y - 4.5*mm, str(entry.get('phone', '')))
        
        current_y -= row_height

    # Total Row
    c.setFont("DejaVuSans-Bold", 10)
    c.drawString(x_positions[1] + 30*mm, current_y - 5*mm, "UKUPNO:")
    
    # Calculate totals if needed, or just leave blank/user input
    # For now, we'll just draw the grid for the total row
    c.rect(left_margin, current_y - row_height, width - left_margin - right_margin, row_height)
    for x in x_positions[1:-1]:
        c.line(x, current_y, x, current_y - row_height)
        
    # Footer
    footer_y = 21*mm
    c.setFont("DejaVuSans", 10)
    
    c.drawString(left_margin, footer_y + 10*mm, "U ________________________ dana....................201....god.")
    
    c.drawString(left_margin, footer_y, "Primitak ovog spiska kupaca i ........................................pojedinačnih računa")
    c.drawString(left_margin, footer_y - 5*mm, "kupaca potvrđuje:")
    c.drawCentredString(left_margin + 80*mm, footer_y - 5*mm, "(broj)")
    
    c.line(left_margin, footer_y - 20*mm, left_margin + 60*mm, footer_y - 20*mm)
    c.drawString(left_margin + 15*mm, footer_y - 15*mm, "Potpis primatelja")
    
    c.line(width - right_margin - 60*mm, footer_y - 20*mm, width - right_margin, footer_y - 20*mm)
    c.drawRightString(width - right_margin - 10*mm, footer_y - 15*mm, 'Za "Una tekstil"')

    c.save()
    buffer.seek(0)
    return buffer
