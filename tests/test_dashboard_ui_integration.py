import pytest
import streamlit as st


def test_dashboard_overview_render(monkeypatch):
    # Patch st.write to capture output
    output = []
    monkeypatch.setattr(st, "write", lambda x: output.append(x))
    from ai_software_factory.ui.dashboard import render_overview_tab
    render_overview_tab()
    assert any("Capability Report" in str(item) for item in output)


def test_dashboard_error_handling(monkeypatch):
    # Patch st.error to capture error output
    errors = []
    monkeypatch.setattr(st, "error", lambda x: errors.append(x))
    import ai_software_factory.ui.dashboard as dashboard
    monkeypatch.setattr(dashboard, "get_capability_report", lambda: None)
    dashboard.render_overview_tab()
    assert errors, "Dashboard should show error if report missing"

