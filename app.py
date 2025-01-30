import streamlit as st
import asyncio
import aiohttp
import json
from spl_token_analysis import get_token_details_async, process_tokens_concurrently
from spl_report_generator import create_pdf
import tempfile
import os

# Page config
st.set_page_config(
    page_title="Solana Token Custody Risk Analyzer",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #7047EB;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        margin: 1rem 0;
    }
    .stButton>button:hover {
        background-color: #5835c4;
    }
    .json-output {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        font-family: monospace;
        white-space: pre-wrap;
    }
    .output-container {
        margin: 2rem 0;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }
    .header-container {
        text-align: center;
        padding: 2rem 0;
    }
    .stProgress > div > div > div {
        background-color: #7047EB;
    }
    .metric-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<div class='header-container'>", unsafe_allow_html=True)
st.title("🔍 Solana Token Custody Risk Analyzer")
st.markdown("Analyze token details from the Solana blockchain, including Token-2022 program support")
st.markdown("</div>", unsafe_allow_html=True)

# Create tabs
tab1, tab2 = st.tabs(["Single Token", "Batch Process"])

with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        token_address = st.text_input("Enter token address", placeholder="Enter Solana token address...")
    with col2:
        analyze_button = st.button("Analyze Token", key="single_analyze")
    
    if analyze_button:
        if token_address:
            with st.spinner("Analyzing token..."):
                async def get_token():
                    async with aiohttp.ClientSession() as session:
                        details, _ = await get_token_details_async(token_address, session)
                        return details
                
                try:
                    result = asyncio.run(get_token())
                    if isinstance(result, str):  # Error message
                        st.error(result)
                    else:
                        # Convert TokenDetails to dictionary
                        result_dict = result.to_dict()
                        
                        # Display key metrics in a more visual way
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
                            st.metric("Security Review", result_dict.get('security_review', 'N/A'))
                            st.markdown("</div>", unsafe_allow_html=True)
                        with col2:
                            st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
                            st.metric("Token Program", "Token-2022" if "Token 2022" in result_dict.get('owner_program', '') else "SPL Token")
                            st.markdown("</div>", unsafe_allow_html=True)
                        
                        # If it's a pump token, show additional metrics
                        if token_address.lower().endswith('pump'):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
                                st.metric("Transaction Count", result_dict.get('transaction_count', 'N/A'))
                                st.markdown("</div>", unsafe_allow_html=True)
                            with col2:
                                st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
                                st.metric("Genuine Pump Token", "Yes" if result_dict.get('is_genuine_pump_fun_token', False) else "No")
                                st.markdown("</div>", unsafe_allow_html=True)
                        
                        # Display full results
                        st.markdown("<div class='output-container'>", unsafe_allow_html=True)
                        st.json(result_dict)
                        
                        # Create columns for download buttons
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.download_button(
                                "Download JSON",
                                data=json.dumps(result_dict, indent=2),
                                file_name=f"token_analysis_{token_address}.json",
                                mime="application/json",
                                key="single_download_json"
                            )
                        
                        with col2:
                            # Generate PDF
                            with tempfile.TemporaryDirectory() as temp_dir:
                                pdf_path = create_pdf(result_dict, temp_dir)
                                with open(pdf_path, "rb") as pdf_file:
                                    pdf_bytes = pdf_file.read()
                                    st.download_button(
                                        "Download PDF",
                                        data=pdf_bytes,
                                        file_name=f"token_analysis_{token_address}.pdf",
                                        mime="application/pdf",
                                        key="single_download_pdf"
                                    )
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Please enter a token address")

with tab2:
    st.markdown("### Batch Process Multiple Tokens")
    uploaded_file = st.file_uploader(
        "Upload a text file with one token address per line", 
        type="txt",
        help="File should contain one Solana token address per line"
    )
    
    if uploaded_file:
        addresses = [line.decode().strip() for line in uploaded_file if line.decode().strip()]
        st.info(f"Found {len(addresses)} addresses in file")
        
        if len(addresses) > 0:
            with st.expander("Preview addresses"):
                st.write(addresses[:5])
                if len(addresses) > 5:
                    st.write("...")
        
        if st.button("Process Batch", key="batch_process"):
            try:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                async def process_batch():
                    async with aiohttp.ClientSession() as session:
                        results = await process_tokens_concurrently(addresses, session)
                        for i, _ in enumerate(results, 1):
                            progress = i / len(addresses)
                            progress_bar.progress(progress)
                            status_text.text(f"Processed {i}/{len(addresses)} tokens")
                        return results
                    
                with st.spinner("Processing batch..."):
                    results = asyncio.run(process_batch())
                    
                    # Display summary
                    success_count = sum(1 for r in results if r.get('status') == 'success')
                    st.success(f"Batch processing complete! Successfully processed {success_count}/{len(addresses)} tokens")
                    
                    # Display results
                    with st.expander("View Results", expanded=True):
                        st.json(results)
                    
                    # Download buttons in columns
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.download_button(
                            "Download JSON",
                            data=json.dumps(results, indent=2),
                            file_name="token_analysis_results.json",
                            mime="application/json",
                            key="batch_download_json"
                        )
                    
                    with col2:
                        # Create CSV with conditional pump token fields
                        csv_data = "address,name,symbol,owner_program,security_review"
                        # Add pump-specific headers only if any pump tokens are present
                        has_pump_tokens = any(r['address'].lower().endswith('pump') for r in results if r['status'] == 'success')
                        if has_pump_tokens:
                            csv_data += ",transaction_count,is_genuine_pump_fun_token"
                        csv_data += "\n"
                        
                        for r in results:
                            if r['status'] == 'success':
                                csv_data += f"{r['address']},{r.get('name', 'N/A')},{r.get('symbol', 'N/A')},"
                                csv_data += f"{r.get('owner_program', 'N/A')},{r.get('security_review', 'N/A')}"
                                if has_pump_tokens:
                                    if r['address'].lower().endswith('pump'):
                                        csv_data += f",{r.get('transaction_count', 'N/A')},{r.get('is_genuine_pump_fun_token', 'N/A')}"
                                    else:
                                        csv_data += ",N/A,N/A"
                                csv_data += "\n"
                        
                        st.download_button(
                            "Download CSV",
                            data=csv_data,
                            file_name="token_analysis_results.csv",
                            mime="text/csv",
                            key="batch_download_csv"
                        )
                    
                    with col3:
                        # Generate PDFs for batch
                        with tempfile.TemporaryDirectory() as temp_dir:
                            import zipfile
                            zip_path = os.path.join(temp_dir, "token_analysis_pdfs.zip")
                            with zipfile.ZipFile(zip_path, 'w') as zipf:
                                for result in results:
                                    if result['status'] == 'success':
                                        pdf_path = create_pdf(result, temp_dir)
                                        zipf.write(pdf_path, os.path.basename(pdf_path))
                            
                            with open(zip_path, "rb") as zip_file:
                                st.download_button(
                                    "Download PDFs",
                                    data=zip_file,
                                    file_name="token_analysis_pdfs.zip",
                                    mime="application/zip",
                                    key="batch_download_pdfs"
                                )
            except Exception as e:
                st.error(f"Error during batch processing: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    Noama Samreen | 
    <a href='https://github.com/noama-samreen/spl-token-custody-analysis' target='_blank'>GitHub</a>
</div>
""", unsafe_allow_html=True) 
