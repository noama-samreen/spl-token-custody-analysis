import os
import json
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def create_styles():
    styles = getSampleStyleSheet()
    
    # Title style with better spacing and alignment
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    # Cell style with better formatting
    cell_style = ParagraphStyle(
        'CustomCell',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=10,
        fontName='Helvetica',
        leading=14  # Line spacing
    )
    
    # Context style with better readability
    context_style = ParagraphStyle(
        'CustomContext',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=12,
        leading=16,  # Increased line spacing
        alignment=4,  # Justified text
        fontName='Helvetica'
    )
    
    # Header style for table headers
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.black,
        alignment=0  # Left alignment
    )
    
    return styles, title_style, cell_style, context_style, header_style

def create_basic_table(data, cell_style):
    table = Table(data, colWidths=[2.5*inch, 3.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  # Bold headers in first column
        ('FONTNAME', (1, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    return table

def create_additional_table(data, cell_style):
    """Create and style the additional fields table"""
    table = Table(data, colWidths=[2.5*inch, 3.5*inch])
    table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),  # Bold header row
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f0f0f0')),  # Light gray header
        ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
        ('PADDING', (0,0), (-1,-1), 12),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9f9f9')])  # Alternating rows
    ]))
    return table

def create_pdf(token_data, output_dir):
    """Generate PDF for a single token"""
    filename = f"{token_data['name']} ({token_data['symbol']}) Security Memo.pdf"
    filepath = os.path.join(output_dir, filename)
    
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        leftMargin=72,
        rightMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    styles, title_style, cell_style, context_style, header_style = create_styles()
    elements = []
    
    # Title with better spacing
    title = Paragraph(
        f"Solana Token Security Assessment:<br/>{token_data['name']} ({token_data['symbol']})", 
        title_style
    )
    elements.append(title)
    elements.append(Spacer(1, 30))
    
    # Basic information table
    current_date = datetime.now().strftime("%Y-%m-%d")
    data = [
        [Paragraph("Reviewer", header_style), Paragraph("noamasamreen", cell_style)],
        [Paragraph("Profile", header_style), Paragraph(token_data['owner_program'], cell_style)],
        [Paragraph("Review Date", header_style), Paragraph(current_date, cell_style)],
        [Paragraph("Network", header_style), Paragraph("Solana", cell_style)],
        [Paragraph("Address", header_style), Paragraph(token_data['address'], cell_style)]
    ]
    
    elements.append(create_basic_table(data, cell_style))
    elements.append(Spacer(1, 30))
    
    # Context text with better formatting
    context_text = """<b>Solana SPL Token Review Context:</b> Solana tokens do not possess customizable code per 
asset. Rather, a single "program" generates boiler template tokens with distinct states for each 
newly created token. Therefore, examining the base program configurations is adequate for 
reviewing all other tokens associated with it. The 'Token Program' adheres to standard 
practices, undergoing thorough review and auditing procedures. Therefore, within this review 
process, the focus remains on validating token configurations specific to tokens managed by the 
trusted Token Program"""
    
    elements.append(Paragraph(context_text, context_style))
    elements.append(Spacer(1, 25))
    
    # Recommendation with emphasis
    recommendation = (
        f"<b>{token_data['name']} ({token_data['symbol']}) "
        f"{'is' if token_data['security_review'] == 'PASSED' else 'is not'} recommended for listing.</b>"
    )
    elements.append(Paragraph(recommendation, ParagraphStyle(
        'CustomRecommendation',
        parent=context_style,
        fontSize=12,
        textColor=colors.HexColor('#006400') if token_data['security_review'] == 'PASSED' else colors.red
    )))
    elements.append(Spacer(1, 25))
    
    # Additional details table
    additional_data = [["Field", "Value"]]
    skip_fields = {'name', 'symbol', 'address', 'owner_program'}
    for key, value in token_data.items():
        if key not in skip_fields:
            if isinstance(value, dict):
                value = json.dumps(value, indent=2)
            additional_data.append([
                Paragraph(str(key).replace('_', ' ').title(), cell_style),
                Paragraph(str(value), cell_style)
            ])
    
    elements.append(create_additional_table(additional_data, cell_style))
    
    # Build PDF
    doc.build(elements)
    return filepath
