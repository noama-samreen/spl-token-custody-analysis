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
    """Create and style the basic information table"""
    # Reduced table width (adjusted from 6 inches to 5 inches total)
    table = Table(data, colWidths=[1.2*inch, 3.8*inch])
    table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
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
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f9f9f9')]),  # Alternating rows
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f8f8f8')),  # Slight emphasis on last row
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
    
    # Title first
    title = Paragraph(
        f"Solana Token Security Assessment:<br/>{token_name} ({token_symbol})", 
        title_style
    )
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Basic information table (reviewer, profile, date, etc.)
    current_date = datetime.now().strftime("%Y-%m-%d")
    profile = "SPL Token 2022 Standard" if "Token 2022" in token_data['owner_program'] else "SPL Token Standard"
    
    metadata_data = [
        [Paragraph("Reviewer", cell_style), Paragraph(token_data.get('reviewer_name', 'Noama Samreen'), cell_style)],
        [Paragraph("Profile", cell_style), Paragraph(profile, cell_style)],
        [Paragraph("Review Date", cell_style), Paragraph(current_date, cell_style)],
        [Paragraph("Network", cell_style), Paragraph("Solana", cell_style)],
        [Paragraph("Address", cell_style), Paragraph(token_data['address'], cell_style)]
    ]
    
    elements.append(create_basic_table(metadata_data, cell_style))
    elements.append(Spacer(1, 20))
    
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
    
    # Add reviewer confirmation (single row table)
    reviewer_confirmation = [[
        Paragraph("Reviewer:", cell_style), 
        Paragraph(token_data.get('reviewer_name', 'Noama Samreen'), cell_style),
        Paragraph("Status:", cell_style),
        Paragraph(token_data.get('confirmation_status', 'Confirmed'), cell_style)
    ]]
    
    # Create table with 4 columns for single-row layout
    reviewer_table = Table(reviewer_confirmation, colWidths=[1*inch, 2*inch, 1*inch, 2*inch])
    reviewer_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (0,0), colors.lightgrey),
        ('BACKGROUND', (2,0), (2,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(reviewer_table)
    elements.append(Spacer(1, 30))
    
    # Context text
    context_text = """<b>Solana SPL Token Review Context:</b> Solana tokens do not possess customizable code per 
asset. Rather, a single "program" generates boiler template tokens with distinct states for each 
newly created token. Therefore, examining the base program configurations is adequate for 
reviewing all other tokens associated with it. The 'Token Program' adheres to standard 
practices, undergoing thorough review and auditing procedures. Therefore, within this review 
process, the focus remains on validating token configurations specific to tokens managed by the 
trusted Token Program"""
    
    elements.append(Paragraph(context_text, context_style))
    elements.append(Spacer(1, 25))
    
    # Recommendation with error handling and risk scores
    security_review = token_data.get('security_review', 'UNKNOWN')
    if security_review in ['N/A', None, '']:
        security_review = 'UNKNOWN'
    
    # Determine risk scores based on security review
    risk_score = 1 if security_review == 'PASSED' else 5
    
    recommendation = (
        f"<b>{token_name} ({token_symbol}) "
        f"{'is' if security_review == 'PASSED' else 'is not'} recommended for listing.</b>"
    )
    elements.append(Paragraph(recommendation, ParagraphStyle(
        'CustomRecommendation',
        parent=context_style,
        fontSize=12,
        textColor=colors.HexColor('#006400') if security_review == 'PASSED' else colors.red
    )))
    elements.append(Spacer(1, 15))
    
    # Add risk scores
    risk_style = ParagraphStyle(
        'RiskScore',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        leading=14,
        fontName='Helvetica'
    )
    
    elements.append(Paragraph(
        f"<b>Residual Security Risk Score:</b> {risk_score}",
        risk_style
    ))
    elements.append(Paragraph(
        f"<b>Inherent Security Risk Score:</b> {risk_score}",
        risk_style
    ))
    elements.append(Spacer(1, 25))
    
    # Additional details table
    additional_data = [["Field", "Value"]]
    
    # Base fields for all tokens
    field_order = [
        'owner_program',
        'freeze_authority',
        'update_authority'
    ]
    
    # Add Token 2022 specific fields if applicable
    if "Token 2022" in token_data.get('owner_program', ''):
        field_order.extend([
            'permanent_delegate',
            'transaction_fees',
            'transfer_hook',
            'confidential_transfers'
        ])
    
    # Add pump.fun specific fields if applicable
    if "Pump.Fun Mint Authority" in str(token_data.get('update_authority', '')):
        field_order.extend([
            'is_genuine_pump_fun_token',
            'interacted_with',
            'token_graduated_to_raydium'
        ])
        if token_data.get('interacting_account') or token_data.get('interaction_signature'):
            field_order.extend([
                'interacting_account',
                'interaction_signature'
            ])
    
    # Add fields in specified order
    for field in field_order:
        value = token_data.get(field, 'None')
        if value in ['N/A', None, '']:
            value = 'None'
        if isinstance(value, bool):
            value = str(value)
        display_name = str(field).replace('_', ' ').title()
        additional_data.append([
            Paragraph(display_name, cell_style),
            Paragraph(str(value), cell_style)
        ])
    
    # Add security review as the last row
    security_style = ParagraphStyle(
        'SecurityCell',
        parent=cell_style,
        textColor=colors.HexColor('#006400') if security_review == 'PASSED' 
                 else colors.red if security_review == 'FAILED'
                 else colors.black,
        fontName='Helvetica-Bold'
    )
    
    additional_data.append([
        Paragraph("Security Review", cell_style),
        Paragraph(security_review, security_style)
    ])
    
    elements.append(create_additional_table(additional_data, cell_style))
    
    # Build PDF
    doc.build(elements)
    return filepath

# Export the function
__all__ = ['create_pdf']

if __name__ == '__main__':
    pdf_path = create_pdf(token_data, output_dir)
