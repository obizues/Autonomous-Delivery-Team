"""
Test import conventions for UI and package modules.
Ensures no ModuleNotFoundError for documented launch/import styles.
"""
import importlib
import sys
import os

# UI local import test
os.chdir(os.path.dirname(__file__))
try:
    import config
    print("UI local import: SUCCESS")
except ModuleNotFoundError as e:
    print(f"UI local import: FAIL - {e}")

# Package absolute import test
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
    import ai_software_factory.orchestration.repo_ingestion
    print("Package absolute import: SUCCESS")
except ModuleNotFoundError as e:
    print(f"Package absolute import: FAIL - {e}")

# Streamlit import test (optional)
try:
    import streamlit
    print("Streamlit import: SUCCESS")
except ModuleNotFoundError as e:
    print(f"Streamlit import: FAIL - {e}")
