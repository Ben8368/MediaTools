"""LLM 本地化翻译 —— 独立于 Agent 层，供 photoshop_copy_translate 等服务调用."""

from __future__ import annotations

from openai import OpenAI


_LOCALIZATION_SYSTEM_PROMPT = (
    "你是专业 UI/营销/包装类文案的本地化译者。用户输入为 JSON：字段 items 为数组，每项含 "
    "i（整数任务序号）、text（待译原文）、locale（BCP 47 区域标签，如 ja-JP、en-US、de-DE、zh-CN）。\n\n"
    "【1】目标语言：必须将 text 译成 locale 所指地区的**标准书面语**（该语种+该区域），"
    "不得以其他语种为主、也不得长期混用未约定语言。\n\n"
    "【2】本地化适配：在「1」的前提下做**区域化表达**——符合当地语感、标点、数字/日期习惯、"
    "敬语/语体层级（如日韩、欧洲正式文案）、禁忌与营销语气；避免生硬直译；"
    "品牌/法律敏感处保持克制。保留原文中的数字、产品型号、URL、"
    "以及 {{name}}、{0}、%s 等占位符与变量形态，勿擅自删除或改写结构。\n\n"
    "【3】行数与换行：若 text 含换行符 \\n，则译文 t 中 **\\n 的数量必须与 text 完全一致**，"
    "且**每一行与原文分行一一对应**；禁止把多行合并为一行，禁止无故增加行；"
    "仅可在行尾保留因语种所需的必要空格（行内不得用空格替代换行）。\n\n"
    "【4】长度与体量：各**对应行**的译文在视觉与版式上要「贴原文字数体量」——"
    "优先控制为与该行原文**相近的字符量/词长**（同语种内宜 ±20% 量级；"
    "跨语系时允许适度放宽，但仍须避免单句明显过长或过短导致排版失控）。"
    "需要更正式或更短译法时，在不牺牲「3」的前提下用简洁措辞而非堆长句。\n\n"
    "只输出合法 JSON，格式严格为：{\"items\":[{\"i\":<int>,\"t\":\"译文字符串\"}]}。"
    "须为每个输入的 i 各输出**恰好一条**，顺序不限；禁止 Markdown、注释、多余字段或说明文字。"
)


def localization_batch_translate(
    batch: list[dict],
    *,
    api_key: str,
    base_url: str = "",
    model: str = "",
) -> str:
    """调用 LLM 翻译 batch（每项含 i, text, locale），返回模型原始响应文本."""
    if not api_key:
        raise ValueError("缺少模型 API Key")

    client = OpenAI(api_key=api_key, base_url=base_url or None)

    import json as _json
    user_payload = _json.dumps({"items": batch}, ensure_ascii=False)

    token_param = (
        "max_completion_tokens"
        if (model or "").lower().startswith(("gpt-5", "o1", "o3", "o4"))
        else "max_tokens"
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _LOCALIZATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        ],
        **{token_param: 8000},
    )

    content = getattr(response.choices[0].message, "content", "") or ""
    return content
