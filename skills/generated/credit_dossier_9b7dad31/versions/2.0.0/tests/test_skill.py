from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_generated_dossier_matches_contract():
    root = Path(__file__).resolve().parents[1]
    fixture = (root / "fixtures" / "case.json").read_text(encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(root / "scripts" / "dossier.py")],
        input=fixture,
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(completed.stdout)
    assert result["ok"] is True
    assert result["external_writes"] == []
    assert result["final_credit_decision"] == "remains with authorized employee"
