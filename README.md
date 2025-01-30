# Solana Token Security Analyzer

A web application to analyze Solana tokens, including support for both standard SPL tokens and Token-2022 program tokens.

## Features

- Single token analysis with persistent results display
- Batch processing support
- Metadata retrieval from both Token Program and Token-2022 Program
- Pump.Fun token verification:
  - Address suffix verification
  - Update authority verification
  - Transaction history verification (when needed)
  - Genuine token status display
- Security review of token features:
  - Freeze authority
  - Permanent delegate (Token-2022)
  - Transaction fees (Token-2022)
  - Transfer hook (Token-2022)
  - Confidential transfers (Token-2022)
- Interactive web interface:
  - Real-time analysis results
  - Persistent display until reset
  - Start New Analysis option
  - Start New Batch option
- Export options:
  - JSON format (complete analysis)
  - CSV format (summarized data)
  - PDF security memos (detailed reports)
  - Batch ZIP download for PDFs

## Usage

### Single Token Analysis
1. Enter a Solana token address
2. Click "Analyze Token"
3. View the detailed token information
4. Download results in your preferred format (JSON, CSV, or PDF)
5. Use "Start New Analysis" to reset and analyze another token

### Batch Processing
1. Prepare a text file with one token address per line
2. Upload the file using the "Batch Process" tab
3. Click "Process Batch"
4. View results for all tokens
5. Download results in any supported format:
   - JSON: Complete analysis data
   - CSV: Summarized token information
   - ZIP: Collection of individual PDF security memos
6. Use "Start New Batch" to reset and process another batch

## Security Review Criteria

The analyzer checks for several security-relevant features:

### Standard SPL Tokens
- **Owner Program**: Verifies if the token uses the standard Token Program
- **Freeze Authority**: Checks if the token can be frozen by an authority

### Token-2022 Program Tokens
- All standard token checks plus:
- **Permanent Delegate**: Identifies any permanent delegation authority
- **Transaction Fees**: Checks for any transfer fee configurations
- **Transfer Hook**: Verifies if transfer hook programming is enabled
- **Confidential Transfers**: Checks if confidential transfers are enabled

### Pump.Fun Token Verification
- **Address Check**: Verifies if address ends with 'pump'
- **Authority Check**: Verifies if update authority is Pump.Fun Mint Authority
- **Transaction History**: Verifies first transaction includes interaction with the Pump.fun program in the createAccount instruction
- **Status Display**: Shows genuine status in results

## Technical Details

- Built with Streamlit for the web interface
- Uses Solana RPC for blockchain interaction
- Supports both Token Program and Token-2022 Program
- Generates professional PDF reports with ReportLab
- Handles batch processing asynchronously
- Maintains session state for better user experience

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
