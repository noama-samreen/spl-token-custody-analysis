# Copyright 2025 noamasamreen

from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any, List
import base64
from functools import lru_cache
import asyncio
import aiohttp
import logging
import json
from solders.pubkey import Pubkey as PublicKey
import time
from asyncio import sleep

# Constants
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
METADATA_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
MAX_RETRIES = 3
BASE_DELAY = 2.0  # 2 second between requests
RETRY_DELAY = 2.0  # Additional delay when rate limited

# Original constants
CONCURRENT_LIMIT = 1  # Back to original value
SESSION_TIMEOUT = aiohttp.ClientTimeout(total=30)

OWNER_LABELS = {
    TOKEN_PROGRAM: "Token Program",
    TOKEN_2022_PROGRAM: "Token 2022 Program"
}

# Add constant at the top
PUMP_FUN_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

async def get_metadata_account(mint_address: str) -> Tuple[PublicKey, int]:
    """Derive the metadata account address for a mint"""
    try:
        metadata_program_id = PublicKey.from_string(METADATA_PROGRAM_ID)
        mint_pubkey = PublicKey.from_string(mint_address)
        
        seeds = [
            b"metadata",
            bytes(metadata_program_id),
            bytes(mint_pubkey)
        ]
        
        return PublicKey.find_program_address(
            seeds,
            metadata_program_id
        )
    except Exception as e:
        logging.error(f"Error deriving metadata account: {e}")
        return None, None

async def get_metadata(session: aiohttp.ClientSession, mint_address: str) -> Optional[Dict]:
    """Fetch metadata for a token with more conservative retry logic"""
    for retry in range(MAX_RETRIES):
        try:
            # Add base delay before every request
            await sleep(BASE_DELAY)
            
            metadata_address, _ = await get_metadata_account(mint_address)
            if not metadata_address:
                return None

            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    str(metadata_address),
                    {"encoding": "base64"}
                ]
            }
            
            async with session.post(SOLANA_RPC_URL, json=payload) as response:
                if response.status == 429:  # Rate limit hit
                    if retry < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY * (2 ** retry)  # Exponential backoff
                        logging.warning(f"Rate limit hit in metadata fetch, waiting {wait_time} seconds...")
                        await sleep(wait_time)
                        continue
                    return None
                    
                if response.status != 200:
                    return None
                    
                data = await response.json()
                
            # Parse the metadata account data
            account_data = data["result"]["value"]["data"][0]
            decoded_data = base64.b64decode(account_data)
            
            if len(decoded_data) < 8:  # Ensure we have enough data
                return None
                
            try:
                # Skip the first 1 + 32 + 32 bytes (discriminator + update auth + mint)
                offset = 1 + 32 + 32
                
                # Read name length and name
                name_length = int.from_bytes(decoded_data[offset:offset + 4], byteorder='little')
                offset += 4
                name = decoded_data[offset:offset + name_length].decode('utf-8').rstrip('\x00')
                offset += name_length
                
                # Read symbol length and symbol
                symbol_length = int.from_bytes(decoded_data[offset:offset + 4], byteorder='little')
                offset += 4
                symbol = decoded_data[offset:offset + symbol_length].decode('utf-8').rstrip('\x00')
                
                return {
                    "name": name,
                    "symbol": symbol
                }
            except UnicodeDecodeError:
                logging.error("Error decoding metadata strings")
                return None
            
            return None
        except Exception as e:
            if retry < MAX_RETRIES - 1:
                await sleep(RETRY_DELAY * (retry + 1))
                continue
            logging.error(f"Error fetching metadata: {str(e)}")
            return None
        

@dataclass
class Token2022Extensions:
    permanent_delegate: Optional[str] = None
    transfer_fee: Optional[int] = None
    transfer_hook_authority: Optional[str] = None
    confidential_transfers_authority: Optional[str] = None

@dataclass
class TokenDetails:
    name: str
    symbol: str
    address: str
    owner_program: str
    freeze_authority: Optional[str]
    extensions: Optional[Token2022Extensions] = None
    security_review: str = "FAILED"  # Default to FAILED
    is_pump_fun: bool = False  # Add new field

    def to_dict(self) -> Dict:
        # Create dict with existing fields
        result = {
            'name': self.name,
            'symbol': self.symbol,
            'address': self.address,
            'owner_program': self.owner_program,
            'freeze_authority': self.freeze_authority,
            'genuine_pump_fun_token': 'YES' if self.is_pump_fun else 'NO'  # Add new field to output
        }
        
        # Add extensions if they exist
        if self.extensions:
            result.update({
                'permanent_delegate': self.extensions.permanent_delegate,
                'transaction_fees': self.extensions.transfer_fee,
                'transfer_hook': self.extensions.transfer_hook_authority,
                'confidential_transfers': self.extensions.confidential_transfers_authority,
            })
        
        # Add security_review last
        result['security_review'] = self.security_review
        
        return result

@lru_cache(maxsize=100)
def get_owner_program_label(owner_address: str) -> str:
    """Cached helper function to get the label for owner program"""
    return OWNER_LABELS.get(owner_address, "Unknown Owner")

async def get_token_creator(session: aiohttp.ClientSession, token_address: str) -> Optional[str]:
    """Get the program that created this token"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [
                token_address,
                {"limit": 1}  # Get oldest transaction
            ]
        }
        
        async with session.post(SOLANA_RPC_URL, json=payload) as response:
            if response.status != 200:
                return None
                
            data = await response.json()
            if "result" not in data or not data["result"]:
                return None
                
            # Get the oldest transaction signature
            oldest_tx = data["result"][-1]["signature"]
            
            # Get transaction details
            tx_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [
                    oldest_tx,
                    {"encoding": "json", "maxSupportedTransactionVersion": 0}
                ]
            }
            
            async with session.post(SOLANA_RPC_URL, json=tx_payload) as tx_response:
                if tx_response.status != 200:
                    return None
                    
                tx_data = await tx_response.json()
                if "result" not in tx_data or not tx_data["result"]:
                    return None
                
                # Check if Pump.fun program was involved in the transaction
                for account in tx_data["result"]["transaction"]["message"]["accountKeys"]:
                    if account["pubkey"] == PUMP_FUN_PROGRAM:
                        return PUMP_FUN_PROGRAM
                
                return None
                
    except Exception as e:
        logging.error(f"Error getting token creator: {str(e)}")
        return None

async def get_token_details_async(token_address: str, session: aiohttp.ClientSession) -> Tuple[TokenDetails, Optional[str]]:
    """Async version of get_token_details with more conservative retry logic"""
    for retry in range(MAX_RETRIES):
        try:
            # Add delay before each request, even the first one
            if retry > 0:
                wait_time = RETRY_DELAY * (2 ** retry)  # Exponential backoff
                logging.warning(f"Waiting {wait_time} seconds before retry {retry+1}...")
                await sleep(wait_time)
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    token_address,
                    {"encoding": "jsonParsed", "commitment": "confirmed"}
                ]
            }
            
            async with session.post(SOLANA_RPC_URL, json=payload) as response:
                if response.status == 429:
                    if retry < MAX_RETRIES - 1:
                        continue
                    return f"Error: Rate limit exceeded after {MAX_RETRIES} retries", None
                
                if response.status != 200:
                    return f"Error: RPC returned status code {response.status}", None
                    
                data = await response.json()
                
                if "error" in data:
                    return f"Error: {data['error']['message']}", None

                result = data.get("result", {})
                if not result or not result.get("value"):
                    return "Token not found or invalid address", None

                token_details, owner_program = process_token_data(result["value"], token_address)

                # If it's a standard SPL token and name/symbol are N/A, try to get metadata
                if (owner_program == TOKEN_PROGRAM and 
                    (token_details.name == 'N/A' or token_details.symbol == 'N/A')):
                    metadata = await get_metadata(session, token_address)
                    if metadata:
                        token_details.name = metadata["name"]
                        token_details.symbol = metadata["symbol"]

                # If it's a valid token, check if it was created by Pump.fun
                if owner_program == TOKEN_PROGRAM:
                    creator = await get_token_creator(session, token_address)
                    if creator == PUMP_FUN_PROGRAM:
                        token_details.is_pump_fun = True  # Just set the flag, don't modify security review

                return token_details, owner_program

        except aiohttp.ClientError as e:
            if retry < MAX_RETRIES - 1:
                await sleep(RETRY_DELAY * (retry + 1))
                continue
            logging.error(f"Network error: {str(e)}")
            return f"Network error: {str(e)}", None
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            return f"Unexpected error: {str(e)}", None

def process_token_data(account_data: Dict, token_address: str) -> Tuple[TokenDetails, str]:
    """Process the token data and return structured information"""
    # Check if this is a system account
    owner_program = account_data.get('owner', 'N/A')
    if owner_program == "11111111111111111111111111111111":
        return TokenDetails(
            name="N/A",
            symbol="N/A",
            address=token_address,
            owner_program="System Program",
            freeze_authority=None,
            security_review="NOT_A_TOKEN"
        ), owner_program

    # Check if it's a valid token program
    if owner_program not in [TOKEN_PROGRAM, TOKEN_2022_PROGRAM]:
        return TokenDetails(
            name="N/A",
            symbol="N/A",
            address=token_address,
            owner_program=f"{owner_program} (Not a token program)",
            freeze_authority=None,
            security_review="NOT_A_TOKEN"
        ), owner_program

    parsed_data = account_data.get("data", {}).get("parsed", {})
    owner_label = get_owner_program_label(owner_program)
    
    info = parsed_data.get("info", {})
    freeze_authority = info.get('freezeAuthority')
    
    base_details = TokenDetails(
        name=info.get('name', 'N/A'),
        symbol=info.get('symbol', 'N/A'),
        address=token_address,
        owner_program=f"{owner_program} ({owner_label})",
        freeze_authority=freeze_authority,
        extensions=None
    )
    # Set security review based on token program type
    if owner_program == TOKEN_PROGRAM:
        # For standard SPL tokens, PASSED if no freeze authority
        base_details.security_review = "PASSED" if freeze_authority is None else "FAILED"
    elif owner_program == TOKEN_2022_PROGRAM:
        base_details = process_token_2022_extensions(base_details, info)
        # Security review will be set in process_token_2022_extensions
    else:
        base_details.security_review = "FAILED"  # Unknown token program

    return base_details, owner_program

def process_token_2022_extensions(token_details: TokenDetails, info: Dict) -> TokenDetails:
    """Process Token 2022 specific extensions"""
    extensions_info = info.get("extensions", [])
    extensions = Token2022Extensions()

    for extension in extensions_info:
        ext_type = extension.get("extension")
        state = extension.get("state", {})

        if ext_type == "tokenMetadata":
            token_details.name = state.get('name', token_details.name)
            token_details.symbol = state.get('symbol', token_details.symbol)
        elif ext_type == "permanentDelegate":
            extensions.permanent_delegate = state.get("delegate")
        elif ext_type == "transferFeeConfig":
            extensions.transfer_fee = state.get("newerTransferFee", {}).get("transferFeeBasisPoints")
        elif ext_type == "transferHook":
            extensions.transfer_hook_authority = state.get("authority")
        elif ext_type == "confidentialTransferMint":
            extensions.confidential_transfers_authority = state.get("authority")

    token_details.extensions = extensions

    # Set security review for Token 2022
    has_security_features = any([
        token_details.freeze_authority is not None,
        extensions.permanent_delegate is not None,
        extensions.confidential_transfers_authority is not None,
        extensions.transfer_hook_authority is not None,
        extensions.transfer_fee not in [None, 0]
    ])
    
    token_details.security_review = "FAILED" if has_security_features else "PASSED"
    return token_details

async def process_tokens_concurrently(token_addresses: List[str], session: aiohttp.ClientSession) -> List[Dict]:
    """Process multiple tokens concurrently with rate limiting"""
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    total_tokens = len(token_addresses)
    
    async def process_single_token(token_address: str, index: int) -> Dict:
        async with semaphore:
            logging.info(f"Processing token {index + 1}/{total_tokens} - {token_address}")
            details, owner_program = await get_token_details_async(token_address, session)
            if isinstance(details, TokenDetails):
                return {
                    'address': token_address,
                    'status': 'success',
                    **details.to_dict()
                }
            return {
                'address': token_address,
                'status': 'error',
                'error': str(details)
            }
    
    return await asyncio.gather(
        *(process_single_token(addr, idx) for idx, addr in enumerate(token_addresses))
    )

async def main():
    try:
        import sys
        if len(sys.argv) > 1:
            input_file = sys.argv[1]
            output_prefix = sys.argv[2] if len(sys.argv) > 2 else "spl_token_details"
            with open(input_file, 'r') as f:
                token_addresses = [line.strip() for line in f if line.strip()]
        else:
            token_address = input("Enter Solana token address: ").strip()
            token_addresses = [token_address]
            output_prefix = "single_token"
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        json_output = f"{output_prefix}_{timestamp}.json"
        log_output = f"{output_prefix}_{timestamp}.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_output),
                logging.StreamHandler()
            ]
        )
        
        async with aiohttp.ClientSession(timeout=SESSION_TIMEOUT) as session:
            results = await process_tokens_concurrently(token_addresses, session)
            
            # Write outputs
            with open(json_output, 'w') as f:
                json.dump(results, f, indent=2)
            
            logging.info(f"Analysis complete. Check {json_output} for results.")
            
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
