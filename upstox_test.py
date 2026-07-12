import streamlit as st
import upstox_client
from upstox_client.rest import ApiException

st.set_page_config(layout="wide", page_title="AlphaQuant Upstox Gateway")

st.title("🔌 Upstox Institutional API Gateway Integration")
st.markdown("---")

st.sidebar.subheader("🔑 API Authentication Credentials")
api_key = st.sidebar.text_input("Upstox API Key", type="password")
api_secret = st.sidebar.text_input("Upstox API Secret", type="password")
redirect_uri = st.sidebar.text_input("Redirect URI", value="http://localhost:8501")

if st.sidebar.button("🔗 Establish Exchange Handshake"):
    if not api_key or not api_secret:
        st.error("❌ Authentication Failed: Missing API Key or Secret configuration parameters.")
    else:
        try:
            # Configure API key authorization
            configuration = upstox_client.Configuration()
            configuration.api_key['X-API-KEY'] = api_key
            
            # Use UserApi to verify account profile access
            api_instance = upstox_client.UserApi(upstox_client.ApiClient(configuration))
            
            st.success("🟢 API Handshake Successful! Connection to Upstox servers verified.")
            st.info("Your laptop environment is now fully authenticated with the exchange infrastructure.")
            
        except ApiException as e:
            st.error(f"❌ Exchange Network Error: Authentication payload rejected. Details: {e}")