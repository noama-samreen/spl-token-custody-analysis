import streamlit as st
import asyncio
import aiohttp
import json
from spl_token_analysis import get_token_details_async, process_tokens_concurrently
from spl_report_generator import create_pdf
import tempfile
import os
import zipfile
from datetime import datetime
import time

# Initialize session state if not already done
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'batch_results' not in st.session_state:
    st.session_state.batch_results = None
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'start_time' not in st.session_state:
    st.session_state.start_time = None

# Page config
st.set_page_config(
    page_title="Solana Token Custody Risk Analyzer",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS - Smaller fonts and better alignment
st.markdown("""
<style>
/* Base styles */
.main {
    padding: 1rem;
    max-width: 1200px;
    margin: 0 auto;
}

/* Title and description */
h1 {
    font-size: 16px !important;
    font-weight: 500;
    margin-bottom: 0.5rem;
}

.stMarkdown p {
    font-size: 14px !important;
    margin-bottom: 1.5rem;
}

/* Input section */
[data-testid="stTextInput"] label {
    font-size: 14px !important;
    color: #424242;
    margin-bottom: 0.25rem;
}

[data-testid="stTextInput"] input {
    border-radius: 6px;
    border: 1px solid #ddd;
    padding: 0.5rem;
    font-size: 13px;
}

/* Button styling */
.stButton>button {
    background-color: #7047EB;
    color: white;
    border-radius: 6px;
    padding: 0.5rem 1rem;
    border: none;
    transition: all 0.3s ease;
    font-size: 14px;
}

/* Results section */
[data-testid="stMarkdownContainer"] h3 {
    font-size: 12px !important;
    color: #666;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.25rem;
}

[data-testid="stMarkdownContainer"] p {
    font-size: 14px !important;
    color: #1f1f1f;
    font-weight: 500;
    margin-bottom: 1rem;
}

/* Tab styling */
.stTabs [data-baseweb="tab"] {
    height: 40px;
    border-radius: 6px;
    padding: 0 16px;
    font-size: 14px;
    background-color: #f8f9fa;
}

/* View Raw Data expander */
.streamlit-expanderHeader {
    font-size: 14px;
    padding: 0.75rem;
}

/* Download buttons */
.stDownloadButton button {
    font-size: 13px;
    padding: 0.5rem 1rem;
}

/* Footer text */
footer {
    margin-top: 2rem;
    padding: 0.75rem;
    text-align: center;
    font-size: 13px;
}

/* Grid layout for results */
.results-container {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
    margin: 1rem 0;
}

/* Log display */
[data-testid="stCode"] {
    font-size: 13px;
    line-height: 1.4;
    padding: 0.75rem;
}

/* Container padding and spacing */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
}

/* Progress bar */
.stProgress > div > div > div {
    background-color: #7047EB;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    padding: 0.5rem;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background-color: #7047EB;
    color: white;
}

/* Footer styling */
footer a {
    color: #7047EB;
    text-decoration: none;
    font-weight: 600;
}

footer a:hover {
    color: #5835c4;
}

/* Scrollbar styling */
[data-testid="stCode"]::-webkit-scrollbar {
    width: 8px;
}

[data-testid="stCode"]::-webkit-scrollbar-track {
    background: #f1f1f1;
}

[data-testid="stCode"]::-webkit-scrollbar-thumb {
    background: #7047EB;
    border-radius: 4px;
}

[data-testid="stCode"]::-webkit-scrollbar-thumb:hover {
    background: #5835c4;
}
</style>
""", unsafe_allow_html=True)

# Update the header section
st.markdown("<div class='header'>", unsafe_allow_html=True)
st.title("🔍 Solana Token Custody Risk Analyzer")
st.markdown("Analyze token details from the Solana blockchain, including Token-2022 program support")
st.markdown("</div>", unsafe_allow_html=True)

# Create tabs
tab1, tab2 = st.tabs(["Single Token", "Batch Process"])

with tab1:
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        token_address = st.text_input("Enter token address", placeholder="Enter Solana token address...")
    with col2:
        analyze_button = st.button("Analyze Token", key="single_analyze")
    with col3:
        if st.button("Start New Analysis", key="reset_single"):
            st.session_state.analysis_results = None
            token_address = ""
            st.experimental_rerun()
    
    if analyze_button and token_address:
        with st.spinner("Analyzing token..."):
            async def get_token():
                start_timer()
                add_log(f"Starting analysis for token: {token_address[:8]}...")
                add_log("Fetching token data from blockchain...")
                async with aiohttp.ClientSession() as session:
                    details, _ = await get_token_details_async(token_address, session)
                    add_log("Analyzing security parameters...")
                    # More processing
                    add_log("✅ Analysis complete!")
                    display_logs()
                    return details
            
            try:
                result = asyncio.run(get_token())
                if isinstance(result, str):  # Error message
                    st.error(result)
                else:
                    st.session_state.analysis_results = result.to_dict()
            except Exception as e:
                st.error(f"Error analyzing token: {str(e)}")
    
    # Display results if they exist
    if st.session_state.analysis_results:
        result_dict = st.session_state.analysis_results
        
        # Display key metrics in columns
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Security Review", result_dict.get('security_review', 'N/A'))
        with col2:
            st.metric("Token Program", "Token-2022" if "Token 2022" in result_dict.get('owner_program', '') else "SPL Token")
        
        # Display authorities in columns
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Update Authority", result_dict.get('update_authority', 'None'))
        with col2:
            st.metric("Freeze Authority", result_dict.get('freeze_authority', 'None'))
        
        # Display pump.fun specific metrics if applicable
        if "Pump.Fun Mint Authority" in str(result_dict.get('update_authority', '')):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Genuine Pump Fun Token", "Yes" if result_dict.get('is_genuine_pump_fun_token', False) else "No")
            with col2:
                st.metric("Graduated to Raydium", "Yes" if result_dict.get('token_graduated_to_raydium', False) else "No")
            
            if result_dict.get('interacted_with'):
                st.metric("Interaction Type", result_dict.get('interacted_with', 'None'))
                
                if result_dict.get('interacting_account'):
                    with st.expander("Interaction Details"):
                        st.text("Interacting Account")
                        st.code(result_dict.get('interacting_account'))
                        if result_dict.get('interaction_signature'):
                            st.text("Transaction Signature")
                            st.code(result_dict.get('interaction_signature'))
        
        # If token is Token-2022, display extension features
        if "Token 2022" in result_dict.get('owner_program', ''):
            st.subheader("Token-2022 Features")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Permanent Delegate", result_dict.get('permanent_delegate', 'None'))
                st.metric("Transfer Hook", result_dict.get('transfer_hook', 'None'))
            with col2:
                st.metric("Transaction Fees", result_dict.get('transaction_fees', 'None'))
                st.metric("Confidential Transfers", result_dict.get('confidential_transfers', 'None'))
        
        # Display full results
        with st.expander("View Raw Data"):
            st.json(result_dict)
        
        # Download buttons
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download JSON",
                data=json.dumps(result_dict, indent=2),
                file_name=f"token_analysis_{token_address}.json",
                mime="application/json"
            )
        
        with col2:
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf_path = create_pdf(result_dict, temp_dir)
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        "Download PDF",
                        data=pdf_file.read(),
                        file_name=f"token_analysis_{token_address}.pdf",
                        mime="application/pdf"
                    )

with tab2:
    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "Upload a text file with one token address per line",
            type="txt",
            help="File should contain one Solana token address per line"
        )
    with col2:
        if st.button("Start New Batch", key="reset_batch"):
            st.session_state.batch_results = None
            uploaded_file = None
            st.experimental_rerun()
    
    if uploaded_file:
        addresses = [line.decode().strip() for line in uploaded_file if line.decode().strip()]
        st.info(f"Found {len(addresses)} addresses in file")
        
        if st.button("Process Batch", key="batch_process"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            async def process_batch():
                start_timer()
                add_log("Starting batch processing...")
                async with aiohttp.ClientSession() as session:
                    results = await process_tokens_concurrently(addresses, session)
                    for i, _ in enumerate(results, 1):
                        progress = i / len(addresses)
                        progress_bar.progress(progress)
                        status_text.text(f"Processed {i}/{len(addresses)} tokens")
                    add_log("Batch processing completed!")
                    display_logs()
                    return results
            
            try:
                results = asyncio.run(process_batch())
                st.session_state.batch_results = results
                st.success(f"Successfully processed {len(results)} tokens")
            except Exception as e:
                st.error(f"Error during batch processing: {str(e)}")

    # Display batch results if they exist
    if st.session_state.batch_results:
        results = st.session_state.batch_results
        st.json(results)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                "Download JSON",
                data=json.dumps(results, indent=2),
                file_name="token_analysis_results.json",
                mime="application/json"
            )
        
        with col2:
            # Create CSV with update authority
            csv_data = "address,name,symbol,owner_program,update_authority,freeze_authority,security_review\n"
            for r in results:
                if r['status'] == 'success':
                    csv_data += f"{r['address']},{r.get('name', 'N/A')},{r.get('symbol', 'N/A')},"
                    csv_data += f"{r.get('owner_program', 'N/A')},{r.get('update_authority', 'None')},"
                    csv_data += f"{r.get('freeze_authority', 'None')},{r.get('security_review', 'N/A')}\n"
            
            st.download_button(
                "Download CSV",
                data=csv_data,
                file_name="token_analysis_results.csv",
                mime="text/csv"
            )
        
        with col3:
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, "token_analysis_pdfs.zip")
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for result in results:
                        if result['status'] == 'success':
                            pdf_path = create_pdf(result, temp_dir)
                            zipf.write(pdf_path, os.path.basename(pdf_path))
                
                with open(zip_path, "rb") as zip_file:
                    st.download_button(
                        "Download PDFs",
                        data=zip_file.read(),
                        file_name="token_analysis_pdfs.zip",
                        mime="application/zip"
                    )

# Update the footer section
st.markdown("""
<footer>
    <div style='color: #666;'>
        Noama Samreen | 
        <a href='https://github.com/noama-samreen/spl-token-custody-analysis' target='_blank' style='color: #7047EB; text-decoration: none;'>GitHub</a>
    </div>
</footer>
""", unsafe_allow_html=True)

def start_timer():
    """Start the execution timer"""
    st.session_state.start_time = time.time()
    st.session_state.logs = []  # Clear previous logs
    add_log("Starting execution...")

def get_elapsed_time():
    """Get elapsed time since start"""
    if st.session_state.start_time:
        elapsed = time.time() - st.session_state.start_time
        return f"{elapsed:.2f} seconds"
    return "Not started"

def add_log(message):
    """Add a log message with timestamp and elapsed time"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    elapsed = get_elapsed_time()
    st.session_state.logs.append(f"[{timestamp}] ({elapsed}) {message}")

def display_logs():
    """Display all logs and total time in the placeholder"""
    log_text = "\n".join(st.session_state.logs)
    if st.session_state.start_time:
        log_text += f"\n\n{'='*50}\nTotal execution time: {get_elapsed_time()}"
    st.empty().code(log_text, language=None) 
