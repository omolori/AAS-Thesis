"""Phase 3 milestone: query the running AAS HTTP server.

Run this in a SECOND terminal (the first one is running the AAS server):
    python scripts/test_aas_server.py

It will:
    1. List all AASs on the server
    2. List all submodels
    3. Fetch the Digital Nameplate submodel and print its properties
    4. Fetch the Operational Data submodel and print its properties

If you see a clean printout with the UR3's manufacturer / serial number /
zeroed operational data -- Phase 3 is done.
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import requests  # noqa: E402

from aas_models.constants import (  # noqa: E402
    SUBMODEL_NAMEPLATE_ID,
    SUBMODEL_OPERATIONAL_ID,
)
from config_loader import config  # noqa: E402


def b64url(identifier: str) -> str:
    """URL-safe Base64 encoding of an identifier, no padding -- the form
    the AAS API expects in URL paths."""
    return base64.urlsafe_b64encode(identifier.encode("utf-8")).decode("ascii").rstrip("=")


def print_dict(obj, indent: int = 0) -> None:
    """Pretty-print nested AAS API JSON in a readable way."""
    pad = "  " * indent
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                print(f"{pad}{k}:")
                print_dict(v, indent + 1)
            else:
                print(f"{pad}{k}: {v}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            print(f"{pad}- [{i}]")
            print_dict(item, indent + 1)
    else:
        print(f"{pad}{obj}")


def main() -> int:
    host = config["aas_server"]["host"]
    if host == "0.0.0.0":
        host = "localhost"
    port = int(config["aas_server"]["port"])
    base = f"http://{host}:{port}/api/v3.0"

    print(f"Hitting AAS server at {base}\n")

    # 1. List all shells
    print("--- GET /shells ---")
    try:
        r = requests.get(f"{base}/shells", timeout=5)
    except requests.exceptions.ConnectionError:
        print("ERROR: server is not running.")
        print("Start it first in another terminal: python scripts/start_aas_server.py")
        return 1
    r.raise_for_status()
    shells = r.json()
    # Most AAS servers return {"result": [...], "paging_metadata": {...}}
    shell_list = shells.get("result", shells) if isinstance(shells, dict) else shells
    print(f"Found {len(shell_list)} AAS(s):")
    for shell in shell_list:
        print(f"  - {shell.get('id', shell)}  ({shell.get('idShort', '')})")

    # 2. List all submodels
    print("\n--- GET /submodels ---")
    r = requests.get(f"{base}/submodels", timeout=5)
    r.raise_for_status()
    sms = r.json()
    sm_list = sms.get("result", sms) if isinstance(sms, dict) else sms
    print(f"Found {len(sm_list)} submodel(s):")
    for sm in sm_list:
        print(f"  - {sm.get('idShort', '')}  ({sm.get('id', sm)})")

    # 3. Fetch the Digital Nameplate
    print("\n--- GET /submodels/{Nameplate} ---")
    url = f"{base}/submodels/{b64url(SUBMODEL_NAMEPLATE_ID)}"
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    print(json.dumps(r.json(), indent=2)[:1500])  # first ~1500 chars
    print("  (truncated)")

    # 4. Fetch the Operational Data
    print("\n--- GET /submodels/{OperationalData} ---")
    url = f"{base}/submodels/{b64url(SUBMODEL_OPERATIONAL_ID)}"
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    print(json.dumps(r.json(), indent=2)[:1500])
    print("  (truncated)")

    print("\nPhase 3 milestone reached: AAS server is reachable and serving "
          "submodels via the standard AAS REST API.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
