---
name: credit_dossier_9b7dad31
description: "Подготовка клиентского мини-досье"
version: 1.0.0
type: script
runtime: python3
timeout_sec: 30
permissions: []
scripts:
  - name: dossier.py
    description: Build a deterministic evidence-backed synthetic credit dossier
---
# Generated Credit Dossier Micro-Skill

Reads one JSON case from standard input and writes one JSON dossier to standard output.
It performs no network, filesystem, subprocess, or external-system operations.
