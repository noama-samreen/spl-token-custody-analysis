# Solana Token Custody Risk Analyzer

A web application to analyze Solana tokens, including support for both standard SPL tokens and Token-2022 program tokens.

## Features

- Single token analysis
- Batch processing support
- Metadata retrieval from both Token Program and Token-2022 Program
- Security review of token features:
  - Freeze authority
  - Permanent delegate
  - Transaction fees
  - Transfer hook
  - Confidential transfers
- Interactive web interface
- Export options:
  - JSON format
  - CSV format
  - PDF security memos

## Usage

### Single Token Analysis
1. Enter a Solana token address
2. Click "Analyze Token"
3. View the detailed token information
4. Download results in your preferred format (JSON, CSV, or PDF)

### Batch Processing
1. Prepare a text file with one token address per line
2. Upload the file using the "Batch Process" tab
3. Click "Process Batch"
4. Download results in any supported format:
   - JSON: Complete analysis data
   - CSV: Summarized token information
   - PDF: Individual security memos for each token

## Security Review Criteria

The analyzer checks for several security-relevant features:

- **Owner Program**: Verifies if the token uses the standard Token Program or Token-2022 Program
- **Freeze Authority**: Checks if the token can be frozen by an authority
- **Permanent Delegate**: Identifies any permanent delegation authority
- **Transaction Fees**: Checks for any transfer fee configurations
- **Transfer Hook**: Verifies if transfer hook programming is enabled
- **Confidential Transfers**: Checks if confidential transfers are enabled

## Technical Details

- Built with Streamlit for the web interface
- Uses Solana RPC for blockchain interaction
- Supports both Token Program and Token-2022 Program
- Generates professional PDF reports with ReportLab
- Handles batch processing asynchronously

## Requirements

- Python 3.8+
- Streamlit
- Solders
- ReportLab
- aiohttp

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   streamlit run app.py
   ```

## License

Licensed under the Apache License, Version 2.0
