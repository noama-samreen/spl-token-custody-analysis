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
MAX_RETRIES = 4
BASE_DELAY = 2.0  # 2 second between requests
RETRY_DELAY = 2.0  # Additional delay when rate limited
BATCH_SIZE = 1000  # Maximum allowed by Solana

# Original constants
CONCURRENT_LIMIT = 1  # Back to original value
SESSION_TIMEOUT = aiohttp.ClientTimeout(total=30)

OWNER_LABELS = {
    TOKEN_PROGRAM: "Token Program",
    TOKEN_2022_PROGRAM: "Token 2022 Program"
}

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
                logging.warning(f"Could not derive metadata address for {mint_address}")
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
                    logging.warning(f"Non-200 status code: {response.status}")
                    return None
                    
                data = await response.json()
                if "result" not in data or not data["result"] or not data["result"]["value"]:
                    logging.warning("No metadata data returned from RPC")
                    return None

                # Parse the metadata account data
                account_data = data["result"]["value"]["data"][0]
                decoded_data = base64.b64decode(account_data)
                
                if len(decoded_data) < 8:  # Ensure we have enough data
                    logging.warning("Metadata data too short")
                    return None
                    
                try:
                    # Skip the first byte (discriminator)
                    offset = 1
                    
                    # Read update authority (32 bytes)
                    update_authority = str(PublicKey(decoded_data[offset:offset + 32]))
                    offset += 32
                    
                    # Skip mint address (32 bytes)
                    offset += 32
                    
                    # Read name length and name
                    name_length = int.from_bytes(decoded_data[offset:offset + 4], byteorder='little')
                    offset += 4
                    if name_length > 0:
                        name = decoded_data[offset:offset + name_length].decode('utf-8').rstrip('\x00')
                    else:
                        name = "N/A"
                    offset += name_length
                    
                    # Read symbol length and symbol
                    symbol_length = int.from_bytes(decoded_data[offset:offset + 4], byteorder='little')
                    offset += 4
                    if symbol_length > 0:
                        symbol = decoded_data[offset:offset + symbol_length].decode('utf-8').rstrip('\x00')
                    else:
                        symbol = "N/A"
                    
                    logging.info(f"Successfully parsed metadata - Name: {name}, Symbol: {symbol}, Update Authority: {update_authority}")
                    return {
                        "name": name,
                        "symbol": symbol,
                        "update_authority": update_authority
                    }
                except UnicodeDecodeError as e:
                    logging.error(f"Error decoding metadata strings: {e}")
                    return None
                except Exception as e:
                    logging.error(f"Error parsing metadata: {e}")
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
    update_authority: Optional[str] = None  # Added update authority field
    extensions: Optional[Token2022Extensions] = None
    first_transaction: Optional[str] = None
    transaction_count: Optional[int] = None
    is_genuine_pump_fun_token: bool = False
    security_review: str = "FAILED"  # Default to FAILED

    def to_dict(self) -> Dict:
        # First create dict with base fields
        result = {
            'name': self.name,
            'symbol': self.symbol,
            'address': self.address,
            'owner_program': self.owner_program,
            'freeze_authority': self.freeze_authority,
            'update_authority': self.update_authority  # Added to dict output
        }
        
        # Add extensions if they exist
        if self.extensions:
            result.update({
                'permanent_delegate': self.extensions.permanent_delegate,
                'transaction_fees': self.extensions.transfer_fee,
                'transfer_hook': self.extensions.transfer_hook_authority,
                'confidential_transfers': self.extensions.confidential_transfers_authority,
            })
        
        # Add pump-specific fields only if it's a pump token
        if self.address.lower().endswith('pump'):
            if self.first_transaction is not None:
                result['first_transaction'] = self.first_transaction
            if self.transaction_count is not None:
                result['transaction_count'] = self.transaction_count
            result['is_genuine_pump_fun_token'] = self.is_genuine_pump_fun_token
        
        result['security_review'] = self.security_review
        return result

@lru_cache(maxsize=100)
def get_owner_program_label(owner_address: str) -> str:
    """Cached helper function to get the label for owner program"""
    return OWNER_LABELS.get(owner_address, "Unknown Owner")

async def get_signatures_batch(session: aiohttp.ClientSession, address: str, before: str = None) -> list:
    """Get a batch of signatures with retries"""
    #logging.info(f"Fetching signatures for {address}")
    params = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [
            address,
            {
                "before": before,
                "limit": BATCH_SIZE,
                "commitment": "confirmed"
            }
        ]
    }
    
    retry_count = 0
    while True:
        try:
            async with session.post(SOLANA_RPC_URL, json=params) as response:
                #logging.info(f"Response status: {response.status}")
                data = await response.json()
                if "error" in data:
                    if data["error"].get("code") == 429:
                        retry_count += 1
                        wait_time = min(2 * (1.5 ** retry_count), 10)  # Exponential backoff up to 10 seconds
                        logging.info(f"Rate limited. Waiting {wait_time} seconds...")
                        await sleep(wait_time)
                        continue
                    return []
                signatures = data.get('result', [])
                logging.info(f"Got {len(signatures)} signatures")
                return signatures
        except Exception as e:
            logging.error(f"Error in get_signatures_batch: {str(e)}")
            retry_count += 1
            wait_time = min(2 * (1.5 ** retry_count), 10)
            await sleep(wait_time)
            continue

async def verify_pump_token(session: aiohttp.ClientSession, token_address: str) -> Tuple[bool, Optional[str], int]:
    """Verify if token is a genuine pump.fun token by checking its first transaction"""
    PUMP_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
    PUMP_UPDATE_AUTHORITY = "TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM"
    
    logging.info(f"Starting pump token verification for {token_address}")
    
    # Check if it's a pump token by address suffix or update authority
    is_pump_address = token_address.lower().endswith('pump')
    metadata = await get_metadata(session, token_address)
    is_pump_authority = metadata and metadata.get("update_authority") == PUMP_UPDATE_AUTHORITY
    
    if not (is_pump_address or is_pump_authority):
        logging.info("Not a pump token (neither ends with 'pump' nor has pump update authority)")
        return False, None, 0

    try:
        total_signatures = []
        before = None
        found_first = False
        first_tx_sig = None
        retry_count = 0
        
        while not found_first:
            signatures = await get_signatures_batch(session, token_address, before)
            
            if not signatures:
                logging.info("No signatures found in batch")
                break
                
            total_signatures.extend(signatures)
            logging.info(f"Total signatures collected: {len(total_signatures)}")
            
            if len(signatures) < BATCH_SIZE:
                found_first = True
                first_tx_sig = signatures[-1]['signature']
                logging.info(f"Found first transaction: {first_tx_sig}")
                
                # Get transaction details
                tx_params = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTransaction",
                    "params": [
                        first_tx_sig,
                        {
                            "encoding": "jsonParsed",
                            "maxSupportedTransactionVersion": 0
                        }
                    ]
                }
                
                logging.info("Fetching transaction details")
                while True:
                    try:
                        async with session.post(SOLANA_RPC_URL, json=tx_params) as tx_response:
                            if tx_response.status == 429:
                                retry_count += 1
                                wait_time = min(2 * (1.5 ** retry_count), 10)
                                logging.info(f"Rate limited in tx fetch. Waiting {wait_time} seconds...")
                                await sleep(wait_time)
                                continue
                                
                            tx_data = await tx_response.json()
                            if "error" in tx_data:
                                logging.error(f"Transaction fetch error: {tx_data['error']}")
                                break
                                
                            if "result" in tx_data and tx_data["result"]:
                                tx_result = tx_data["result"]
                                inner_instructions = tx_result.get("meta", {}).get("innerInstructions", [])
                                
                                for inner_group in inner_instructions:
                                    for instruction in inner_group.get("instructions", []):
                                        if "parsed" in instruction:
                                            parsed_type = instruction["parsed"].get("type")
                                            if parsed_type == "createAccount":
                                                owner = instruction["parsed"].get("info", {}).get("owner")
                                                if owner == PUMP_PROGRAM:
                                                    logging.info("Verified as genuine pump.fun token!")
                                                    return True, first_tx_sig, len(total_signatures)
                            break
                    except Exception as e:
                        retry_count += 1
                        wait_time = min(2 * (1.5 ** retry_count), 10)
                        await sleep(wait_time)
                        continue
                break
            
            before = signatures[-1]['signature']
            await sleep(2)  # Base delay between signature batches
        
        logging.info("Completed verification - not a genuine pump.fun token")
        return False, first_tx_sig, len(total_signatures)
            
    except Exception as e:
        logging.error(f"Error in verify_pump_token: {str(e)}")
        return False, None, 0

async def get_token_details_async(token_address: str, session: aiohttp.ClientSession) -> Tuple[TokenDetails, Optional[str]]:
    """Async version of get_token_details with more conservative retry logic"""
    for retry in range(MAX_RETRIES):
        try:
            # First get metadata to check update authority
            metadata = await get_metadata(session, token_address)
            is_pump_address = token_address.lower().endswith('pump')
            is_pump_authority = metadata and metadata.get("update_authority") == "TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM"
            
            # Verify pump token if either condition is met
            is_genuine_pump_fun_token = False
            first_transaction = None
            transaction_count = None
            
            if is_pump_address or is_pump_authority:
                logging.info(f"Potential pump token detected - Address ends with 'pump': {is_pump_address}, Has pump authority: {is_pump_authority}")
                is_genuine_pump_fun_token, first_transaction, transaction_count = await verify_pump_token(session, token_address)
            
            # Add base delay before request
            await sleep(BASE_DELAY)
            
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
                if response.status == 429:  # Rate limit hit
                    if retry < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY * (2 ** retry)  # Exponential backoff
                        logging.warning(f"Rate limit hit, waiting {wait_time} seconds...")
                        await sleep(wait_time)
                        continue
                    return "Rate limit exceeded", None
                    
                data = await response.json()
                
                if "error" in data:
                    return f"RPC error: {data['error']}", None
                    
                if "result" not in data or not data["result"]:
                    return "No data returned", None
                    
                account_data = data["result"]["value"]
                
                # Process the token data
                token_details, owner_program = process_token_data(account_data, token_address)
                
                # Update token details with metadata if available
                if owner_program == TOKEN_PROGRAM and metadata:
                    token_details.name = metadata["name"]
                    token_details.symbol = metadata["symbol"]
                    token_details.update_authority = metadata["update_authority"]
                    logging.info(f"Updated token details with metadata: {metadata}")
                
                # Update pump verification details if either condition was met
                if is_pump_address or is_pump_authority:
                    token_details.is_genuine_pump_fun_token = is_genuine_pump_fun_token
                    token_details.first_transaction = first_transaction
                    token_details.transaction_count = transaction_count
                    logging.info(f"Updated pump verification details - Genuine: {is_genuine_pump_fun_token}, Tx count: {transaction_count}")

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
            is_genuine_pump_fun_token=False,
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
            is_genuine_pump_fun_token=False,
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
        extensions=None,
        is_genuine_pump_fun_token=False
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
