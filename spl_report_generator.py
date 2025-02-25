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
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=30,
        alignment=1,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    cell_style = ParagraphStyle(
        'CustomCell',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=10,
        fontName='Helvetica',
        leading=14
    )
    
    context_style = ParagraphStyle(
        'CustomContext',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=12,
        leading=16,
        alignment=4,
        fontName='Helvetica'
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.black,
        alignment=0
    )
    
    return styles, title_style, cell_style, context_style, header_style

def create_basic_table(data, cell_style):
    """Create and style the basic information table"""
    table = Table(data, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
    ]))
    return table

def create_pdf(token_data, output_dir):
    """Generate PDF for a single token"""
    # Handle missing or invalid name/symbol
    token_name = token_data.get('name', 'Unknown')
    if token_name in ['N/A', None, '']:
        token_name = 'Unknown'
    
    token_symbol = token_data.get('symbol', 'UNKNOWN')
    if token_symbol in ['N/A', None, '']:
        token_symbol = 'UNKNOWN'
    
    filename = f"{token_name} ({token_symbol}) Security Memo.pdf"
    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '(', ')', '.'))
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
    
    # Add confidentiality notice
    confidentiality_style = ParagraphStyle(
        'Confidentiality',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=0,
        fontName='Helvetica-Oblique'
    )
    elements.append(Paragraph(
        "Confidential treatment requested under NY Banking Law § 36.10 and NY Pub. Off. Law § 87.2(d).",
        confidentiality_style
    ))
    elements.append(Spacer(1, 20))
    
    # Title
    title = Paragraph(
        f"Solana Token Security Assessment:<br/>{token_name} ({token_symbol})", 
        title_style
    )
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Add conflicts certification
    conflicts_style = ParagraphStyle(
        'Conflicts',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=12,
        leading=14,
        alignment=4,
        fontName='Helvetica'
    )
    conflicts_text = """<b>Conflicts Certification:</b> To the best of your knowledge, please confirm that you and your immediate family: (1) have not invested more than $10,000 in the asset or its issuer, (2) do not own more than 1% of the asset outstanding, and (3) do not have a personal relationship with the issuer's management, governing body, or owners. For wrapped assets, the underlying asset must be considered for the purpose of this conflict certification, unless: 1) the asset is a stablecoin; or 2) has a market cap of over $100 billion dollars. For multi-chain assets every version of the multi-chain asset must be counted together for the purpose of this conflict certification."""
    elements.append(Paragraph(conflicts_text, conflicts_style))
    elements.append(Spacer(1, 10))
    
    # Add reviewer confirmation
    reviewer_name = token_data.get('reviewer_name', 'Noama Samreen')
    confirmation_status = token_data.get('confirmation_status', 'Confirmed')
    
    reviewer_confirmation = [
        [Paragraph("Reviewer:", cell_style), Paragraph(reviewer_name, cell_style)],
        [Paragraph("Status:", cell_style), Paragraph(confirmation_status, cell_style)]
    ]
    elements.append(create_basic_table(reviewer_confirmation, cell_style))
    elements.append(Spacer(1, 30))
    
    # Build the document
    doc.build(elements)
    return filepath

# Export the function
__all__ = ['create_pdf']

if __name__ == '__main__':
    pdf_path = create_pdf(token_data, output_dir)
