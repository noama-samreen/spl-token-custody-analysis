def create_pdf(token_data, output_dir):
    """Generate PDF for a single token"""
    # Create filename
    filename = f"{token_data['name']} ({token_data['symbol']}) Security Memo.pdf"
    filepath = os.path.join(output_dir, filename)
    
    # Create PDF document
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        leftMargin=72,
        rightMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    styles, title_style, cell_style, context_style = create_styles()
    elements = []
    
    # Title
    title = Paragraph(
        f"Solana Token Security Assessment: {token_data['name']} ({token_data['symbol']})", 
        title_style
    )
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Basic information table
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    data = [
        [Paragraph("Reviewer", cell_style), Paragraph("noamasamreen", cell_style)],
        [Paragraph("Profile", cell_style), Paragraph(token_data['owner_program'], cell_style)],
        [Paragraph("Review Date", cell_style), Paragraph(current_date, cell_style)],
        [Paragraph("Network", cell_style), Paragraph("Solana", cell_style)],
        [Paragraph("Address", cell_style), Paragraph(token_data['address'], cell_style)]
    ]
    
    elements.append(create_basic_table(data, cell_style))
    elements.append(Spacer(1, 30))
    
    # Add security review result
    recommendation = (
        f"<b>{token_data['name']} ({token_data['symbol']}) "
        f"{'is' if token_data['security_review'] == 'PASSED' else 'is not'} recommended for listing.</b>"
    )
    elements.append(Paragraph(recommendation, context_style))
    elements.append(Spacer(1, 20))
    
    # Build PDF
    doc.build(elements)
    return filepath 
