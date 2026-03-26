import streamlit as st
from autonomous_delivery.changes import get_before_after

st.title("Autonomous Delivery Feature Request UI")

st.header("Submit a Feature Request")
feature = st.text_area("Describe your feature request:")

if st.button("Submit Request"):
    # Placeholder: integrate with autonomous workflow
    st.success("Feature request submitted!")

st.header("View Before/After Changes")
before, after = get_before_after()
st.subheader("Before:")
st.code(before, language="python")
st.subheader("After:")
st.code(after, language="python")
