"""
requirements_input.py

Streamlit interface for business stakeholders to submit requirements, and for Product Owners/BA/Dev roles to refine and process them.
Integrates with workflow engine for autonomous requirements-to-code pipeline.
"""

import streamlit as st
from services.requirement_service import process_requirement

st.title("Submit Business Requirements")

requirement = st.text_area("Enter a new business requirement:")


if st.button("Submit Requirement"):
    status = process_requirement(requirement)
    st.success(status or f"Requirement submitted: {requirement}")

st.markdown("---")
st.header("Requirements Processing Pipeline")
st.markdown("""
1. Business Stakeholder submits requirement
2. Product Owner refines requirement
3. Business Analyst translates to technical tasks
4. Development cycle is triggered
5. Automated code generation, testing, review, deployment
6. Verification of new functionality
""")

# ...existing integration and workflow logic...
