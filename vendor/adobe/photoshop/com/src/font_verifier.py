"""
Font verification and cache module.
Simplified: maps (original_font, alignment) -> target_font using numeric weight matching.
"""

import csv
import os
import time
from dataclasses import dataclass

from font_analyzer import FontProfile, _get_font_family
from ps_connector import PhotoshopConnector


@dataclass
class FontMapping:
    original_font: str
    alignment: str
    target_font: str
    verified: bool = True


def _resolve_target_font(ps: PhotoshopConnector, original_font: str, target_spec: str) -> str:
    if "-" in target_spec:
        return target_spec
    from font_weight_mapper import find_closest_weight
    available = ps.get_available_weights(target_spec)
    return find_closest_weight(original_font, target_spec, available)


def verify_font_mapping(ps: PhotoshopConnector, profiles: list, font_from_family: str, font_to_spec: str, existing_mappings: dict = None) -> list:
    if existing_mappings is None:
        existing_mappings = {}
    results = {}
    for (orig_font, alignment), target_font in existing_mappings.items():
        results[(orig_font, alignment)] = FontMapping(original_font=orig_font, alignment=alignment, target_font=target_font, verified=True)
    for profile in profiles:
        if _get_font_family(profile.font) != font_from_family:
            continue
        key = (profile.font, profile.alignment)
        if key in results:
            continue
        target_font = _resolve_target_font(ps, profile.font, font_to_spec)
        print(f"  [Match] {profile.font} | {profile.alignment} -> {target_font}")
        results[key] = FontMapping(original_font=profile.font, alignment=profile.alignment, target_font=target_font, verified=True)
    return list(results.values())


def write_cache_csv(mappings: list, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    fieldnames = ["original_font", "alignment", "target_font", "verified"]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as cf:
        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()
        for m in mappings:
            writer.writerow({"original_font": m.original_font, "alignment": m.alignment, "target_font": m.target_font, "verified": str(m.verified).lower()})
    print(f"  [OK] Font cache: {output_path} ({len(mappings)} entries)")


def load_cache(filepath: str) -> dict:
    cache = {}
    with open(filepath, "r", encoding="utf-8-sig") as cf:
        reader = csv.DictReader(cf)
        for row in reader:
            cache[(row["original_font"], row["alignment"])] = row["target_font"]
    return cache


read_cache_csv = load_cache
write_cache = write_cache_csv
