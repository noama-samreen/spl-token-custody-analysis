import streamlit as st
import asyncio
import aiohttp
import json
from spl_token_analysis import get_token_details_async, process_tokens_concurrently
from spl_report_generator import create_pdf
import tempfile
import os
import zipfile

# Page config
st.set_page_config(
    page_title="Solana Token Custody Risk Analyzer",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS
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
    font-size: 0.85rem;
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

/* New styles for metrics */
[data-testid="stMetricValue"] {
    font-size: 1.9rem !important;
    font-weight: 600;
}
[data-testid="stMetricLabel"] {
    font-size: 1rem !important;
    font-weight: 500;
    color: #555;
}
[data-testid="stMetricDelta"] {
    font-size: 0.9rem !important;
}

/* Style for long addresses */
[data-testid="stMetricValue"] div {
    font-family: 'Courier New', monospace;
    font-size: 0.85rem !important;
    word-break: break-all;
    line-height: 1.2;
}

/* Adjust overall container padding */
.element-container {
    padding: 0.5rem 0;
}

/* Style JSON display */
.stJson {
    font-size: 0.85rem !important;
    line-height: 1.4;
}
</style>
""", unsafe_allow_html=True)

# Header
st.title("🔍 Solana Token Custody Risk Analyzer")
st.markdown("Analyze details of standard SPL-Token program and Token-2022 program tokens on the Solana blockchain, including tokens from pump.fun.")

# Create tabs
tab1, tab2 = st.tabs(["Single Token", "Batch Process"])

with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        token_address = st.text_input("Enter token address", placeholder="Enter Solana token address...")
    with col2:
        analyze_button = st.button("Analyze Token", key="single_analyze")
    
    if analyze_button and token_address:
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
                    
                    # If it's a pump token, show additional metrics
                    if token_address.lower().endswith('pump'):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Transaction Count", result_dict.get('transaction_count', 'N/A'))
                        with col2:
                            st.metric("Genuine Pump Token", "Yes" if result_dict.get('is_genuine_pump_fun_token', False) else "No")
                    
                    # Display full results
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
            except Exception as e:
                st.error(f"Error: {str(e)}")

with tab2:
    uploaded_file = st.file_uploader(
        "Upload a text file with one token address per line",
        type="txt",
        help="File should contain one Solana token address per line"
    )
    
    if uploaded_file:
        addresses = [line.decode().strip() for line in uploaded_file if line.decode().strip()]
        st.info(f"Found {len(addresses)} addresses in file")
        
        if st.button("Process Batch", key="batch_process"):
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
            
            try:
                results = asyncio.run(process_batch())
                st.success(f"Successfully processed {len(results)} tokens")
                
                # Display and download options
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
