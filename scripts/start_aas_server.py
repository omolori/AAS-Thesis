"""Start the AAS HTTP server.

Serves the UR3 AAS over HTTP. The server uses Flask for the HTTP layer,
but the response *bodies* are produced by basyx-python-sdk's official
JSON serializer -- so the data on the wire is spec-compliant AAS JSON,
identical to what Eclipse BaSyx's own server would emit.

The endpoint shape follows the AAS Part 2 API specification:
    GET /api/v3.0/shells                    -- list AASs
    GET /api/v3.0/shells/{base64UrlId}      -- get one AAS
    GET /api/v3.0/submodels                 -- list submodels
    GET /api/v3.0/submodels/{base64UrlId}   -- get one submodel

Identifiers in URLs are URL-safe Base64-encoded (without padding), as the
AAS spec requires. Clients use scripts/test_aas_server.py to talk to this.

Run in a terminal and leave running:
    python scripts/start_aas_server.py
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, abort, jsonify                               # noqa: E402
from waitress import serve                                            # noqa: E402

from basyx.aas import model                                           # noqa: E402
from basyx.aas.adapter.json import json_serialization                 # noqa: E402

from aas_models.ur3_aas_builder import build_ur3_aas, persist_aas     # noqa: E402
from config_loader import config                                      # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def b64url_decode(token: str) -> str:
    """Decode a URL-safe Base64 identifier (with or without padding)."""
    pad = "=" * (-len(token) % 4)
    return base64.urlsafe_b64decode((token + pad).encode("ascii")).decode("utf-8")


def serialize_obj(obj: model.Identifiable) -> dict:
    """Serialize a single AAS object using BaSyx's official JSON encoder."""
    # AASToJsonEncoder is the spec-compliant encoder. Round-trip via json
    # so we return a plain dict and Flask handles the response encoding.
    return json.loads(json.dumps(obj, cls=json_serialization.AASToJsonEncoder))


def paged_response(items: list[dict]) -> dict:
    """Wrap a collection response in the AAS API's standard envelope."""
    return {"result": items, "paging_metadata": {}}


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def make_app(store: model.DictObjectStore) -> Flask:
    app = Flask(__name__)
    api_base = "/api/v3.0"

    # Build lookup tables once, keyed by identifier string.
    aas_by_id: dict[str, model.AssetAdministrationShell] = {}
    sm_by_id: dict[str, model.Submodel] = {}
    for obj in store:
        if isinstance(obj, model.AssetAdministrationShell):
            aas_by_id[obj.id] = obj
        elif isinstance(obj, model.Submodel):
            sm_by_id[obj.id] = obj

    # ---- Root / health -----------------------------------------------------
    @app.get("/")
    def root():
        return jsonify({
            "service": "AAS-UR3 HTTP server",
            "api_base": api_base,
            "endpoints": [
                f"GET {api_base}/shells",
                f"GET {api_base}/shells/{{base64UrlId}}",
                f"GET {api_base}/submodels",
                f"GET {api_base}/submodels/{{base64UrlId}}",
            ],
            "shells_loaded": len(aas_by_id),
            "submodels_loaded": len(sm_by_id),
        })

    # ---- AAS Repository ----------------------------------------------------
    @app.get(f"{api_base}/shells")
    def list_shells():
        return jsonify(paged_response([serialize_obj(a) for a in aas_by_id.values()]))

    @app.get(f"{api_base}/shells/<token>")
    def get_shell(token: str):
        try:
            aas_id = b64url_decode(token)
        except Exception:
            abort(400, description="Invalid Base64URL identifier.")
        aas = aas_by_id.get(aas_id)
        if aas is None:
            abort(404, description=f"AAS not found: {aas_id}")
        return jsonify(serialize_obj(aas))

    # ---- Submodel Repository -----------------------------------------------
    @app.get(f"{api_base}/submodels")
    def list_submodels():
        return jsonify(paged_response([serialize_obj(s) for s in sm_by_id.values()]))

    @app.get(f"{api_base}/submodels/<token>")
    def get_submodel(token: str):
        try:
            sm_id = b64url_decode(token)
        except Exception:
            abort(400, description="Invalid Base64URL identifier.")
        sm = sm_by_id.get(sm_id)
        if sm is None:
            abort(404, description=f"Submodel not found: {sm_id}")
        return jsonify(serialize_obj(sm))

    return app


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    storage_dir = PROJECT_ROOT / config["aas_server"]["storage_dir"]
    aas_json_path = storage_dir / "ur3_aas.json"
    host = config["aas_server"]["host"]
    port = int(config["aas_server"]["port"])

    print("=" * 70)
    print("Building UR3 AAS...")
    aas, submodels, store = build_ur3_aas()
    print(f"  AAS:        {aas.id}")
    for sm in submodels:
        print(f"  Submodel:   {sm.id}")

    print(f"\nPersisting to {aas_json_path}...")
    persist_aas(store, aas_json_path)
    print("  done.")

    print("\nStarting AAS HTTP server...")
    app = make_app(store)
    bind_host = "localhost" if host == "0.0.0.0" else host
    print(f"  Listening on http://{bind_host}:{port}/api/v3.0")
    print(f"  Try: curl http://{bind_host}:{port}/api/v3.0/shells")
    print("  Press Ctrl+C to stop.")
    print("=" * 70)
    serve(app, host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
