import streamlit as st
import asyncio
import aiohttp
import json
from spl_token_analysis import get_token_details_async, process_tokens_concurrently

# Page config
st.set_page_config(
    page_title="Solana Token Analyzer",
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
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<div class='header-container'>", unsafe_allow_html=True)
st.title("🔍 Solana Token Analyzer")
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
                        # Display results in a nice format
                        st.markdown("<div class='output-container'>", unsafe_allow_html=True)
                        st.json(result)
                        
                        # Add download button for single result
                        st.download_button(
                            "Download Result (JSON)",
                            data=json.dumps(result, indent=2),
                            file_name=f"token_analysis_{token_address}.json",
                            mime="application/json",
                            key="single_download"
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
        # Read and display preview of addresses
        addresses = [line.decode().strip() for line in uploaded_file if line.decode().strip()]
        st.info(f"Found {len(addresses)} addresses in file")
        
        if len(addresses) > 0:
            with st.expander("Preview addresses"):
                st.write(addresses[:5])
                if len(addresses) > 5:
                    st.write("...")
        
        if st.button("Process Batch", key="batch_process"):
            # Initialize progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.empty()
            
            async def process_batch():
                async with aiohttp.ClientSession() as session:
                    results = await process_tokens_concurrently(addresses, session)
                    return results
            
            try:
                with st.spinner("Processing batch..."):
                    results = asyncio.run(process_batch())
                    
                    # Display summary
                    success_count = sum(1 for r in results if r.get('status') == 'success')
                    st.success(f"Batch processing complete! Successfully processed {success_count}/{len(addresses)} tokens")
                    
                    # Display results in expandable section
                    with st.expander("View Results", expanded=True):
                        st.json(results)
                    
                    # Add download buttons for different formats
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            "Download Results (JSON)",
                            data=json.dumps(results, indent=2),
                            file_name="token_analysis_results.json",
                            mime="application/json",
                            key="batch_download_json"
                        )
                    with col2:
                        # Create CSV format
                        csv_data = "address,name,symbol,owner_program,security_review\n"
                        for r in results:
                            if r['status'] == 'success':
                                csv_data += f"{r['address']},{r.get('name', 'N/A')},{r.get('symbol', 'N/A')},"
                                csv_data += f"{r.get('owner_program', 'N/A')},{r.get('security_review', 'N/A')}\n"
                        
                        st.download_button(
                            "Download Results (CSV)",
                            data=csv_data,
                            file_name="token_analysis_results.csv",
                            mime="text/csv",
                            key="batch_download_csv"
                        )
            except Exception as e:
                st.error(f"Error during batch processing: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    Author: noamasamreen | 
    <a href='https://github.com/noama-samreen/solana-token-analyzer' target='_blank'>GitHub</a>
</div>
""", unsafe_allow_html=True) 
