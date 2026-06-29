import requests
import json

BASE_URL = "http://localhost:8081"

AAS_ID = "dXJuOnVyMzpkaWdpdGFsdHdpbjox"

# -----------------------------
# READ PROPERTY
# -----------------------------
def read_property(submodel_id, property_id):

    encoded_submodel = submodel_id

    url = (
        f"{BASE_URL}/submodels/"
        f"{encoded_submodel}/submodel-elements/"
        f"{property_id}/$value"
    )

    response = requests.get(url)

    return response.json()


# -----------------------------
# WRITE PROPERTY
# -----------------------------
def write_property(submodel_id, property_id, value):
    url = (
        f"{BASE_URL}/submodels/"
        f"{submodel_id}/submodel-elements/"
        f"{property_id}/$value"
    )
    headers = {
        "Content-Type": "application/json"
    }
    # Always send as a JSON string
    if isinstance(value, (list, dict)):
        payload = json.dumps(json.dumps(value))
    else:
        payload = json.dumps(str(value))
    
    response = requests.patch(
        url,
        data=payload,
        headers=headers
    )
    
    return response.status_code
