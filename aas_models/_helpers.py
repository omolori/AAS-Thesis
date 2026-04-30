"""Small helpers to reduce boilerplate when building AAS submodels.

The basyx-python-sdk is faithful to the AAS metamodel, which means a lot
of typing for simple things like "make a Property with a string value."
These helpers wrap the common patterns.
"""
from __future__ import annotations

from typing import Any

from basyx.aas import model


def make_property(
    id_short: str,
    value: Any,
    value_type: type,
    semantic_id: str | None = None,
    description: str | None = None,
) -> model.Property:
    """Create an AAS Property with optional semantic id and description."""
    sem_ref: model.ExternalReference | None = None
    if semantic_id is not None:
        sem_ref = model.ExternalReference((
            model.Key(type_=model.KeyTypes.GLOBAL_REFERENCE, value=semantic_id),
        ))

    description_obj: model.MultiLanguageTextType | None = None
    if description is not None:
        description_obj = model.MultiLanguageTextType({"en": description})

    return model.Property(
        id_short=id_short,
        value_type=value_type,
        value=value,
        semantic_id=sem_ref,
        description=description_obj,
    )


def make_collection(
    id_short: str,
    elements: list[model.SubmodelElement],
    description: str | None = None,
) -> model.SubmodelElementCollection:
    """Create a SubmodelElementCollection with the given child elements."""
    description_obj: model.MultiLanguageTextType | None = None
    if description is not None:
        description_obj = model.MultiLanguageTextType({"en": description})

    coll = model.SubmodelElementCollection(
        id_short=id_short,
        description=description_obj,
    )
    for el in elements:
        coll.value.add(el)
    return coll
