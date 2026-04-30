"""Digital Nameplate submodel.

Maps to the 'Physical model' DT-class in the thesis Table 2.1 (it identifies
*which* asset we are talking about, including manufacturer markings).

In a fully IDTA-conformant deployment this would follow the Nameplate
submodel template (https://admin-shell.io/zvei/nameplate/2/0/Nameplate)
exactly. For a thesis project we use the same id_shorts as that template
where they apply, and add UR3-specific properties where they don't.
"""
from __future__ import annotations

from basyx.aas import model

from aas_models.constants import (
    SEM_NAMEPLATE_TEMPLATE,
    SUBMODEL_NAMEPLATE_ID,
    UR3_MANUFACTURER,
    UR3_MODEL,
    UR3_SERIAL_NUMBER,
    UR3_YEAR_OF_CONSTRUCTION,
)
from aas_models._helpers import make_property


def build_digital_nameplate() -> model.Submodel:
    """Build a Digital Nameplate submodel populated with UR3 details."""
    submodel = model.Submodel(
        id_=SUBMODEL_NAMEPLATE_ID,
        id_short="DigitalNameplate",
        semantic_id=model.ExternalReference((
            model.Key(
                type_=model.KeyTypes.GLOBAL_REFERENCE,
                value=SEM_NAMEPLATE_TEMPLATE,
            ),
        )),
    )

    submodel.submodel_element.add(make_property(
        id_short="ManufacturerName",
        value=UR3_MANUFACTURER,
        value_type=model.datatypes.String,
        description="Legal name of the manufacturer.",
    ))
    submodel.submodel_element.add(make_property(
        id_short="ManufacturerProductDesignation",
        value=UR3_MODEL,
        value_type=model.datatypes.String,
        description="Product designation as used by the manufacturer.",
    ))
    submodel.submodel_element.add(make_property(
        id_short="SerialNumber",
        value=UR3_SERIAL_NUMBER,
        value_type=model.datatypes.String,
        description="Unique serial number of the asset instance.",
    ))
    submodel.submodel_element.add(make_property(
        id_short="YearOfConstruction",
        value=UR3_YEAR_OF_CONSTRUCTION,
        value_type=model.datatypes.String,
        description="Year the asset was manufactured.",
    ))
    submodel.submodel_element.add(make_property(
        id_short="CountryOfOrigin",
        value="DK",
        value_type=model.datatypes.String,
        description="ISO 3166-1 alpha-2 country code where the asset was made.",
    ))

    return submodel
