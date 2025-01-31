# Solana Token Custody Analyzer

A Python-based tool for analyzing Solana tokens, supporting both standard SPL tokens and Token-2022 program tokens, with special verification for Pump.Fun tokens.

## Features

### Token Analysis
- **Program Verification**:
  - Standard SPL Token Program
  - Token-2022 Program
- **Metadata Retrieval**:
  - Token name and symbol
  - Update authority
  - Program ownership

### Security Features Detection
- **Standard SPL Tokens**:
  - Freeze authority status
- **Token-2022 Program Extensions**:
  - Permanent delegate
  - Transaction fees
  - Transfer hook programming
  - Confidential transfers
  - Token metadata

### Pump.Fun Token Verification
- **Authority Verification**:
  - Update authority check against Pump.Fun authority
- **Program Interaction**:
  - Verification of Pump.Fun program interaction
  - Raydium AMM program interaction detection
- **Token Status**:
  - Genuine Pump.Fun token verification
  - Raydium graduation status using Raydium API https://api-v3.raydium.io/docs/
  - Transaction signature tracking
  - Interacting account details

### Processing Capabilities
- Single token analysis
- Concurrent batch processing
- Rate-limiting and retry logic
- Exponential backoff for API calls

## Technical Details

### Dependencies
- Python 3.8+
- aiohttp: For async HTTP requests
- solders: For Solana public key operations
- logging: For detailed operation logging

### Configuration
- Customizable RPC endpoint
- Adjustable rate limits
- Configurable retry parameters
- Concurrent processing limits

## Usage

### Command Line
```bash
# Single token analysis
python spl_token_analysis_v2.py

# Batch processing
python spl_token_analysis_v2.py input_file.txt [output_prefix]
```

### Output Formats
- **JSON**: Detailed analysis results

### Example Output Structure
```json
{
  "name": "Token Name",
  "symbol": "SYMBOL",
  "address": "token_address",
  "owner_program": "Token Program",
  "freeze_authority": null,
  "update_authority": "authority_address",
  "security_review": "PASSED/FAILED",
  "is_genuine_pump_fun_token": true/false,
  "token_graduated_to_raydium": true/false
}
```

## Security Review Criteria

### Standard SPL Tokens
- PASSED: No freeze authority
- FAILED: Has freeze authority

### Token-2022 Program
- PASSED: No security-sensitive features
- FAILED: Has any of:
  - Freeze authority
  - Permanent delegate
  - Transfer hook
  - Confidential transfers
  - Non-zero transfer fees

### Pump.Fun Verification
- Checks update authority
- Verifies program interactions
- Tracks Raydium graduation status

## Error Handling
- Robust retry mechanism
- Rate limit handling
- Detailed error logging
- Graceful failure recovery
