# Generic font weight mapper - find closest weight by numeric CSS value.

WEIGHT_VALUES = {
    "Thin": 100, "ExtraLight": 200, "SemiLight": 250,
    "Light": 300, "Regular": 400, "Medium": 500,
    "SemiBold": 600, "Bold": 700, "ExtraBold": 800,
    "ExtraBlack": 850, "Black": 900,
}

WEIGHT_ALIASES = {
    "Book": "Regular", "Normal": "Regular", "Roman": "Regular",
    "Demi": "SemiBold", "Demibold": "SemiBold",
    "Heavy": "Black", "Ultra": "ExtraBold",
}


def normalize_weight(weight_name: str) -> str:
    name = weight_name.replace("Italic", "").replace("Oblique", "").strip()
    return name or "Regular"


def get_weight_value(weight_name: str) -> int:
    cleaned = normalize_weight(weight_name)
    if cleaned in WEIGHT_VALUES:
        return WEIGHT_VALUES[cleaned]
    if cleaned in WEIGHT_ALIASES:
        return WEIGHT_VALUES[WEIGHT_ALIASES[cleaned]]
    return 400


MIN_WEIGHT_VALUE = 400  # 不允许映射到比 Regular 更细的字重（防止字体过细难以辨认）


def find_closest_weight(original_font: str, target_family: str, available_weights: list, min_weight: int = MIN_WEIGHT_VALUE, separator: str = "-") -> str:
    """
    找到最接近原字体字重的目标字体。
    
    Args:
        original_font: 原字体 PostScript 名（如 ByteSans-Bold）
        target_family: 目标字体家族名（如 Noto Sans JP）
        available_weights: list of (weight_name, postscript_name) tuples
        min_weight: 最小字重值（默认 400 = Regular）
        separator: 已废弃，保留兼容性
    
    Returns:
        目标字体的 PostScript 名（如 NotoSansJP-Bold）
    """
    orig_weight = original_font.split("-")[-1] if "-" in original_font else "Regular"
    orig_value = get_weight_value(orig_weight)

    if not available_weights:
        return target_family + "-" + orig_weight

    # 解析 available_weights 格式（兼容旧格式 list[str] 和新格式 list[tuple]）
    if available_weights and isinstance(available_weights[0], tuple):
        # 新格式：list of (weight_name, postscript_name)
        weight_tuples = available_weights
    else:
        # 旧格式：list of weight_name，回退到拼接
        weight_tuples = [(w, target_family + "-" + w) for w in available_weights]

    # 先过滤掉低于最低字重的选项
    eligible = [(w, ps) for w, ps in weight_tuples if get_weight_value(w) >= min_weight]
    # 如果过滤后为空，回退到最粗的可用字重
    if not eligible:
        eligible = sorted(weight_tuples, key=lambda x: get_weight_value(x[0]), reverse=True)[:1]

    def weight_dist(w):
        return abs(get_weight_value(w) - orig_value)

    w_dists = [(w, ps, weight_dist(w)) for w, ps in eligible]
    min_d = min(d for _, _, d in w_dists)
    closest = [(w, ps) for w, ps, d in w_dists if d == min_d]
    
    if len(closest) == 1:
        chosen_weight, chosen_ps = closest[0]
    else:
        # 同等距离选较粗的
        chosen_weight, chosen_ps = max(closest, key=lambda x: get_weight_value(x[0]))
    
    return chosen_ps
