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

# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'batch_results' not in st.session_state:
    st.session_state.batch_results = None
if 'mitigation_text' not in st.session_state:
    st.session_state.mitigation_text = ""
if 'mitigation_approved' not in st.session_state:
    st.session_state.mitigation_approved = False

# Set page config
st.set_page_config(
    page_title="SPL Token Custody Risk Analyzer",
    page_icon="🔍",
    layout="wide"
)

# Add custom CSS
st.markdown("""
<style>
    .risk-box {
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
        display: inline-block;
    }
    .risk-high { background-color: #ffebee; }
    .risk-low { background-color: #e8f5e9; }
    .outcome-header {
        margin: 0;
        font-size: 1em;
    }
    .mitigation-container {
        margin: 10px 0;
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 5px;
    }
    .error-box {
        padding: 1rem;
        background-color: #fff3f3;
        border: 1px solid #ffcdd2;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .error-title {
        color: #d32f2f;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Title and description
st.title("🔍 SPL Token Custody Risk Analyzer")
st.markdown("""
Analyze details of SPL tokens and Token-2022 assets on the Solana blockchain, including tokens from pump.fun.
""")

# Create tabs
tab1, tab2 = st.tabs(["Single Token", "Batch Process"])

with tab1:
    # Reviewer information first
    reviewer_col1, reviewer_col2 = st.columns(2)
    with reviewer_col1:
        reviewer_name = st.text_input("Reviewer Name", value="Noama Samreen")
    with reviewer_col2:
        confirmation_status = st.radio(
            "Conflicts Certification Status",
            options=["Confirmed", "Denied"],
            horizontal=True
        )

    # Token address input
    token_address = st.text_input("Enter token address", placeholder="Enter Solana token address...")

    if token_address:
        async def get_token():
            async with aiohttp.ClientSession() as session:
                details, error = await get_token_details_async(token_address, session)
                if error:
                    return {'status': 'error', 'error': error}
                if details.owner_program == "System Program" or "Not a token program" in details.owner_program:
                    return {
                        'status': 'error',
                        'error': 'The provided address is not a valid SPL token. Please check the address and try again.'
                    }
                return {'status': 'success', 'data': details.to_dict()}
            
        if st.button("Analyze Token", use_container_width=True):
            with st.spinner("Analyzing token..."):
                try:
                    result = asyncio.run(get_token())
                    if result['status'] == 'success':
                        st.session_state.analysis_results = result['data']
                        st.session_state.mitigation_approved = False
                    else:
                        st.markdown(f"""
                        <div class="error-box">
                            <div class="error-title">❌ Analysis Failed</div>
                            <p>{result['error']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(f"""
                    <div class="error-box">
                        <div class="error-title">❌ Unexpected Error</div>
                        <p>An error occurred while analyzing the token: {str(e)}</p>
                    </div>
                    """, unsafe_allow_html=True)

    # Display results if they exist
    if st.session_state.analysis_results:
        result_dict = st.session_state.analysis_results
        # Add reviewer information to the result dictionary
        result_dict['reviewer_name'] = reviewer_name
        result_dict['confirmation_status'] = confirmation_status
        
        # Display key metrics in columns
        col1, col2 = st.columns(2)
        with col1:
            security_review = result_dict.get('security_review', 'N/A')
            st.metric("Security Review", security_review)
            
            # Show mitigation section if security review failed
            if security_review == "FAILED":
                st.markdown("""
                <div class="risk-box risk-high">
                    <h3 class="outcome-header">⚠️ Security Review Failed</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Display risk factors
                st.subheader("Risk Factors")
                if result_dict.get('freeze_authority'):
                    st.markdown("❌ **Freeze Authority is present**")
                if result_dict.get('permanent_delegate'):
                    st.markdown("❌ **Permanent Delegate is present**")
                if result_dict.get('transfer_hook'):
                    st.markdown("❌ **Transfer Hook is present**")
                if result_dict.get('confidential_transfers'):
                    st.markdown("❌ **Confidential Transfers Authority is present**")
                if result_dict.get('transaction_fees') not in [None, 'None', '0', 0]:
                    st.markdown("❌ **Non-zero Transfer Fees**")

                # Global mitigation section
                st.subheader("Risk Mitigation")
                mitigation_text = st.text_area(
                    "Mitigation Documentation",
                    value=st.session_state.mitigation_text,
                    help="Document why these risks are acceptable and how they are mitigated",
                    key="mitigation_text"
                )

                if st.button("Apply Mitigation"):
                    if not mitigation_text.strip():
                        st.error("Please provide mitigation documentation")
                    else:
                        st.session_state.mitigation_text = mitigation_text
                        result_dict['mitigation_text'] = mitigation_text
                        result_dict['mitigation_approved'] = True
                        result_dict['security_review'] = "PASSED"
                        st.session_state.analysis_results = result_dict
                        st.session_state.mitigation_approved = True
                        st.success("✅ Mitigation applied - Security Review updated to PASSED")
                        st.rerun()
            
            elif security_review == "PASSED":
                st.markdown("""
                <div class="risk-box risk-low">
                    <h3 class="outcome-header">✅ Security Review Passed</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Show mitigation if it exists
                if result_dict.get('mitigation_text') and result_dict.get('mitigation_approved'):
                    with st.expander("View Applied Mitigation"):
                        st.write(result_dict['mitigation_text'])
        
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
    # Reviewer information first
    reviewer_col1, reviewer_col2 = st.columns(2)
    with reviewer_col1:
        reviewer_name = st.text_input("Reviewer Name", value="Noama Samreen", key="batch_reviewer_name")
    with reviewer_col2:
        confirmation_status = st.radio(
            "Conflicts Certification Status",
            options=["Confirmed", "Denied"],
            horizontal=True,
            key="batch_confirmation_status"
        )

    # File upload section
    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "Upload a text file with one token address per line",
            type="txt",
            help="File should contain one Solana token address per line"
        )
    
    if uploaded_file:
        addresses = [line.decode().strip() for line in uploaded_file if line.decode().strip()]
        st.info(f"Found {len(addresses)} addresses in file")
        
        if st.button("Process Batch", key="batch_process", use_container_width=True):
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
                # Add reviewer information to each result
                for result in results:
                    if result['status'] == 'success':
                        result['reviewer_name'] = reviewer_name
                        result['confirmation_status'] = confirmation_status
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

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    Noama Samreen | 
    <a href='https://github.com/noama-samreen/spl-token-custody-analysis' target='_blank'>GitHub</a>
</div>
""", unsafe_allow_html=True) 
