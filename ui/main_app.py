"""
Main UI for Autonomous Delivery Demo (Minimal, Story-Driven, Collaboration-Focused)
"""

import streamlit as st

st.set_page_config(
    page_title="Autonomous Delivery Demo",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
body, [class*="css"] { font-size: 16px !important; }
.main { display: flex; flex-direction: column; align-items: center; }
.product-request-box { margin: 40px auto 24px; max-width: 600px; }
.timeline { margin: 0 auto; max-width: 700px; }
</style>
""", unsafe_allow_html=True)


# Tabbed interface: Main Workflow | Audit/History
tab_main, tab_audit = st.tabs(["Workflow", "Audit / History"])

from autonomous_delivery.ui.config import STAGE_ORDER, STAGE_META

# Parallel implementation demo: 3 engineers, 3 tasks
ENGINEER_TASKS = [
    ("Engineer 1", "Implement Task A"),
    ("Engineer 2", "Implement Task B"),
    ("Engineer 3", "Implement Task C"),
]
# Peer review mapping: each reviews another's code
PEER_REVIEWS = [
    ("Engineer 1", "reviews Engineer 2's code"),
    ("Engineer 2", "reviews Engineer 3's code"),
    ("Engineer 3", "reviews Engineer 1's code"),
]
# Multi-role steps
MULTI_ROLE = {
    "ARCHITECTURE_REVIEW_GATE": ["Architect", "Engineer 1", "Engineer 2", "Engineer 3"],
    "TEST_VALIDATION_GATE": ["Engineer 1", "Engineer 2", "Engineer 3", "Test Engineer"],
}

# --- MAIN UI LOGIC ---
with tab_main:
    st.title("Autonomous Delivery: Agile Team Demo")
    st.markdown("""
    Welcome! Enter a product or feature request below. The autonomous team will process your request step by step, collaborating to deliver real code changes.
    """)

    # Product request entry (centered, not sidebar)
    show_timeline = False
    with st.form(key="product_request_form"):
        st.markdown('<div class="product-request-box">', unsafe_allow_html=True)
        product_request = st.text_area(
            "Enter your product or feature request:",
            placeholder="e.g. Add a dark mode toggle to the dashboard...",
            height=80,
        )
        submit_request = st.form_submit_button("Submit Request 🚀")
        st.markdown('</div>', unsafe_allow_html=True)

    # Store the request in session state for demo purposes
    if submit_request and product_request.strip():
        st.session_state["product_request"] = product_request.strip()
        st.success("Product request submitted! The autonomous team will begin processing.")
        show_timeline = True
    elif "product_request" in st.session_state:
        show_timeline = True

    if show_timeline:
        st.info(f"**Current request:** {st.session_state['product_request']}")
        # Render the workflow timeline
        for i, stage in enumerate(STAGE_ORDER):
            icon, label, agent = STAGE_META.get(stage, ("", stage.title(), "?"))
            score = 95 - i * 4
            loop_count = 1 if stage in ("MERGE_CONFLICT_GATE", "PEER_CODE_REVIEW_GATE") else 0
            status = "✅ Complete" if i < 3 else ("🔄 In Progress" if i == 3 else "⏳ Pending")
            with st.container():
                cols = st.columns([1, 6])
                with cols[0]:
                    st.markdown(f"{icon}", unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f"**{label}**")
                    # Implementation: show parallel tasks
                    if stage == "IMPLEMENTATION":
                        for eng, task in ENGINEER_TASKS:
                            st.markdown(f"{eng}: {task}")
                    # Peer review: show explicit review mapping
                    elif stage == "PEER_CODE_REVIEW_GATE":
                        for reviewer, reviewee in PEER_REVIEWS:
                            st.markdown(f"{reviewer} {reviewee}")
                    # Multi-role steps: show all roles
                    elif stage in MULTI_ROLE:
                        st.markdown(" ".join(MULTI_ROLE[stage]))
                        st.markdown(f"<span style='color:#2563eb'>🤝 Collaboration</span>", unsafe_allow_html=True)
                    # All other steps: show single role
                    else:
                        st.markdown(agent)
                    st.markdown(
                        f"Score: <b style='color:#059669'>{score}</b> &nbsp; | &nbsp; Loops: <b style='color:#f59e42'>{loop_count}</b> &nbsp; | &nbsp; Status: <b style='color:#2563eb'>{status}</b>",
                        unsafe_allow_html=True
                    )
                st.markdown("---")

        # Final "See Your Change!" section
        st.markdown("\n")
        st.markdown("<div style='background:#e0f7fa; border-radius:12px; padding:28px 24px; margin-top:32px; text-align:center;'><h2 style='color:#00796b;'>🎉 See Your Change!</h2><p style='font-size:1.1rem;'>The autonomous team has delivered your requested change. (Demo placeholder: code diff, screenshot, or summary will appear here.)</p></div>", unsafe_allow_html=True)
    else:
        st.markdown('<div class="timeline">[Workflow timeline will appear here after request is submitted]</div>', unsafe_allow_html=True)

# Audit/History tab
with tab_audit:
    st.title("Audit / History")
    st.markdown("""
    _Workflow logs, agent actions, and event history will appear here._
    """)
    st.info("This is a placeholder for the audit/history view. Integrate with workflow logs or event data for full traceability.")
