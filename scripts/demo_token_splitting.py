#!/usr/bin/env python3
"""
Terminal Interactive Token Splitting Visualizer
================================================
Demonstrates and visualizes boundary-aware recursive token splitting in the terminal.

Usage:
  # Split default resume or synthetic sample:
  python scripts/demo_token_splitting.py

  # Split specific resume file (PDF, DOCX, TXT):
  python scripts/demo_token_splitting.py data/sessions/SES-2026-0001/cleaned_text/CAND-0001.txt

  # Custom parameters:
  python scripts/demo_token_splitting.py --safe-limit 1200 --overlap 120

  # Synthetic high-token resume demo:
  python scripts/demo_token_splitting.py --demo --tokens 8000
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.llm.splitter import parse_and_split_cli

if __name__ == "__main__":
    parse_and_split_cli()
