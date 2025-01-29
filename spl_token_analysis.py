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
CONCURRENT_LIMIT = 1
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
                        wait_time = RETRY_DELAY * (2 ** retry)
                        logging.warning(f"Rate limit hit in metadata fetch, waiting {wait_time} seconds...")
                        await sleep(wait_time)
                        continue
                    return None
                    
                if response.status != 200:
                    return None
                    
                data = await response.json()
                
            account_data = data["result"]["value"]["data"][0]
            decoded_data = base64.b64decode(account_data)
            
            if len(decoded_data) < 8:
                return None
                
            try:
                offset = 1 + 32 + 32
                
                name_length = int.from_bytes(decoded_data[offset:offset + 4], byteorder='little')
                offset += 4
                name = decoded_data[offset:offset + name_length].decode('utf-8').rstrip('\x00')
                offset += name_length
                
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

    def to_dict(self) -> Dict:
        result = {
            'name': self.name,
            'symbol': self.symbol,
            'address': self.address,
            'owner_program': self.owner_program,
            'freeze_authority': self.freeze_authority,
            'security_review': self.security_review
        }
        
        if self.extensions:
            result.update({
                'permanent_delegate': self.extensions.permanent_delegate,
                'transaction_fees': self.extensions.transfer_fee,
                'transfer_hook': self.extensions.transfer_hook_authority,
                'confidential_transfers': self.extensions.confidential_transfers_authority,
            })
        return result

@lru_cache(maxsize=100)
def get_owner_program_label(owner_address: str) -> str:
    """Cached helper function to get the label for owner program"""
    return OWNER_LABELS.get(owner_address, "Unknown Owner")

async def get_token_details_async(token_address: str, session: aiohttp.ClientSession) -> Tuple[TokenDetails, Optional[str]]:
    """Async version of get_token_details with more conservative retry logic"""
    for retry in range(MAX_RETRIES):
        try:
            if retry > 0:
                wait_time = RETRY_DELAY * (2 ** retry)
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

                if (owner_program == TOKEN_PROGRAM and 
                    (token_details.name == 'N/A' or token_details.symbol == 'N/A')):
                    metadata = await get_metadata(session, token_address)
                    if metadata:
                        token_details.name = metadata["name"]
                        token_details.symbol = metadata["symbol"]

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
    parsed_data = account_data.get("data", {}).get("parsed", {})
    owner_program = account_data.get('owner', 'N/A')
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

    if owner_program == TOKEN_PROGRAM:
        base_details.security_review = "PASSED" if freeze_authority is None else "FAILED"
    elif owner_program == TOKEN_2022_PROGRAM:
        base_details = process_token_2022_extensions(base_details, info)
    else:
        base_details.security_review = "FAILED"

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
