"""UR3 Asset Administration Shell builder.

Assembles the complete AAS for the UR3:
- One Asset (the UR3 instance)
- One AssetAdministrationShell pointing to that Asset
- Four Submodels: Digital Nameplate, Technical Data, Operational Data,
  Simulation Models
- One DictObjectStore containing all of the above

The AAS, asset, and submodels are written to a JSON file in the storage
directory. This is the file the AAS HTTP server will then load and serve.
"""
from __future__ import annotations

from pathlib import Path

from basyx.aas import model
from basyx.aas.adapter.json import write_aas_json_file

from aas_models.constants import AAS_ID, ASSET_ID
from aas_models.submodels.digital_nameplate import build_digital_nameplate
from aas_models.submodels.operational_data import build_operational_data
from aas_models.submodels.simulation_models import build_simulation_models
from aas_models.submodels.technical_data import build_technical_data


def build_ur3_aas() -> tuple[
    model.AssetAdministrationShell,
    list[model.Submodel],
    model.DictObjectStore[model.Identifiable],
]:
    """Build the complete UR3 AAS, all submodels, and an object store
    holding everything.

    Returns:
        (aas, submodels, object_store)
    """
    # 1. Build all submodels
    nameplate    = build_digital_nameplate()
    technical    = build_technical_data()
    operational  = build_operational_data()
    simulation   = build_simulation_models()
    submodels: list[model.Submodel] = [nameplate, technical, operational, simulation]

    # 2. Build the asset information
    asset_info = model.AssetInformation(
        asset_kind=model.AssetKind.INSTANCE,
        global_asset_id=ASSET_ID,
    )

    # 3. Build the AAS itself, with references to each submodel
    aas = model.AssetAdministrationShell(
        id_=AAS_ID,
        id_short="UR3_AAS",
        asset_information=asset_info,
    )
    for sm in submodels:
        aas.submodel.add(model.ModelReference.from_referable(sm))

    # 4. Pack everything into a single object store (the format the
    #    BaSyx server loads at startup).
    store: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
    store.add(aas)
    for sm in submodels:
        store.add(sm)

    return aas, submodels, store


def persist_aas(store: model.DictObjectStore, output_path: Path) -> None:
    """Serialize the object store to a JSON file the BaSyx server can load."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_aas_json_file(str(output_path), store)
