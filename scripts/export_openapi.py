#!/usr/bin/env python3
"""Export the OpenAPI schema and a Postman collection from the FastAPI app.

Run from the backend venv:

    cd backend && . .venv/bin/activate
    PYTHONPATH=. python ../scripts/export_openapi.py

Outputs:
    docs/api/openapi.json
    docs/api/mandate.postman_collection.json
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import app  # noqa: E402

OUT = ROOT / "docs" / "api"
OUT.mkdir(parents=True, exist_ok=True)

schema = app.openapi()
(OUT / "openapi.json").write_text(json.dumps(schema, indent=2))


def to_postman(openapi: dict) -> dict:
    items = []
    for path, methods in openapi.get("paths", {}).items():
        for method, op in methods.items():
            items.append(
                {
                    "name": op.get("summary") or f"{method.upper()} {path}",
                    "request": {
                        "method": method.upper(),
                        "header": [{"key": "Content-Type", "value": "application/json"}],
                        "url": {
                            "raw": "{{baseUrl}}" + path,
                            "host": ["{{baseUrl}}"],
                            "path": [p for p in path.split("/") if p],
                        },
                        "description": op.get("description", ""),
                    },
                }
            )
    return {
        "info": {
            "name": "Mandate API",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [{"key": "baseUrl", "value": "http://localhost:8000"}],
        "item": items,
    }


(OUT / "mandate.postman_collection.json").write_text(json.dumps(to_postman(schema), indent=2))
print(f"Wrote {OUT/'openapi.json'} and {OUT/'mandate.postman_collection.json'}")
