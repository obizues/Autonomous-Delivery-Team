import streamlit as st
import json
import os

REQUESTS_FILE = "requests.json"

# Load or initialize requests
if os.path.exists(REQUESTS_FILE):
    with open(REQUESTS_FILE, "r") as f:
        requests = json.load(f)
else:
    requests = []

st.title("Autonomous Delivery Feature Request Demo")

st.header("Submit a Feature Request")
with st.form("feature_form"):
    feature = st.text_area("Describe your feature request:")
    submitted = st.form_submit_button("Submit Request")
    if submitted and feature.strip():
        requests.append({"feature": feature, "before": "(before placeholder)", "after": "(after placeholder)"})
        with open(REQUESTS_FILE, "w") as f:
            json.dump(requests, f)
        st.success("Feature request submitted!")

st.header("Feature Requests")
if requests:
    for i, req in enumerate(requests[::-1]):
        st.subheader(f"Request #{len(requests)-i}")
        st.write(req["feature"])
        st.markdown("**Before:**")
        st.code(req["before"])
        st.markdown("**After:**")
        st.code(req["after"])
else:
    st.info("No feature requests yet.")
