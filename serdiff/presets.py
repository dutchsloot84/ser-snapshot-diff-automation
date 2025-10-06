"""Presets for SER and Exposure Type tables."""
from __future__ import annotations

from dataclasses import dataclass

from .diff import DiffConfig


@dataclass(frozen=True)
class Preset:
    name: str
    config: DiffConfig
    description: str


def _build_presets() -> dict[str, Preset]:
    presets: dict[str, Preset] = {}

    ser_config = DiffConfig(
        record_path=".//Rate",
        fields=[
            "PublicID",
            "Partner",
            "State",
            "AgeBand",
            "EffectiveDate",
            "ExpirationDate",
            "Factor",
        ],
        key_fields=[
            ["PublicID"],
            ["Partner", "State", "AgeBand", "EffectiveDate"],
        ],
        table_name="SER",
    )
    presets["SER"] = Preset(
        name="SER",
        config=ser_config,
        description="Simple Exposure Rates table preset",
    )

    exposure_config = DiffConfig(
        record_path=".//ExposureType",
        fields=[
            "PublicID",
            "ExposureCode",
            "Partner",
            "State",
            "EffectiveDate",
            "ExpirationDate",
        ],
        key_fields=[["PublicID"]],
        table_name="EXPOSURE",
    )
    presets["EXPOSURE"] = Preset(
        name="EXPOSURE",
        config=exposure_config,
        description="Exposure Types table preset",
    )

    return presets


PRESETS: dict[str, Preset] = _build_presets()


def list_presets() -> list[Preset]:
    return list(PRESETS.values())


def get_preset(name: str) -> Preset:
    try:
        return PRESETS[name.upper()]
    except KeyError as exc:
        raise KeyError(f"Unknown preset {name!r}") from exc


__all__ = ["Preset", "PRESETS", "get_preset", "list_presets"]
