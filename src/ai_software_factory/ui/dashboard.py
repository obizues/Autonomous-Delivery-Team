import streamlit as st

def get_capability_report():
    return {"capability": "stub"}

def render_overview_tab():
    report = get_capability_report()
    if report is None:
        st.error("Capability report missing.")
    else:
        st.write("Capability Report: Stubbed overview tab.")
