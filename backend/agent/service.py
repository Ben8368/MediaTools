"""AI Agent service with executable project tools and structured outputs."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from backend.config import get_api_config
from modules.adobe.after_effects import get_ae_status, list_ae_tickets, scan_ae_project
from modules.assets.library import AssetLibrary
from modules.generator import ScreenshotGenerator
from backend.agent.routes import try_direct_route as _try_direct_route_impl
from backend.agent.helpers import (
    _extend_unique,
    _json_dumps,
    _response,
    _summarize_tool_result,
    _summary_success,
)
from backend.agent.tool_specs import build_agent_tool_specs
from backend.agent.tools import (
    tool_analyze_subtitle_impl,
    tool_execute_decrypt_to_assets_impl,
    tool_execute_fetch_analyze_slice_impl,
    tool_execute_slice_video_impl,
    tool_execute_transcode_impl,
    tool_export_wechat_moments_impl,
    tool_extract_screenshot_impl,
    tool_get_ae_status_impl,
    tool_get_auditor_status_impl,
    tool_get_video_info_impl,
    tool_inspect_subtitle_impl,
    tool_list_ae_tickets_impl,
    tool_list_psd_tickets_impl,
    tool_recommend_transcode_impl,
    tool_run_audit_scan_impl,
    tool_scan_ae_project_impl,
    tool_scan_assets_impl,
    tool_scan_psd_impl,
    tool_suggest_asset_names_impl,
)
from backend.services.auditor import get_auditor_config, run_auditor_scan_once
from backend.services.media.core import (
    fetch_video_info,
    run_decrypt_job,
    run_fetch_analyze_slice_job,
    run_slice_job,
    run_transcode_job,
)
from backend.services.photoshop import list_photoshop_tickets, scan_photoshop_document
from backend.services.wechat_moments import export_wechat_moments_image, get_wechat_moments_draft, save_wechat_moments_draft
from backend.services.workspace import get_current_workspace

DEFAULT_AGENT_SYSTEM_PROMPT = (
    "你是 MediaTools 的执行型媒体助手。"
    "优先调用工具获取真实信息而不是猜测；"
    "当用户要求执行动作时，优先执行安全、可逆、范围明确的动作；"
    "当用户想要分析、推荐或规划时，先调用工具拿到输入，再给出结论；"
    "输出尽量结构化，明确说明调用了哪些工具、得到什么结果和下一步建议；"
    "对重命名、批量覆盖等潜在破坏性动作，当前版本只提供建议，不直接执行。"
)


def _tool_execute_decrypt_to_assets(input_path: str) -> dict:
    return tool_execute_decrypt_to_assets_impl(
        get_current_workspace_fn=get_current_workspace,
        run_decrypt_job_fn=run_decrypt_job,
        summary_success_fn=_summary_success,
        input_path=input_path,
    )


def _tool_get_video_info(url: str) -> dict:
    return tool_get_video_info_impl(fetch_video_info_fn=fetch_video_info, get_current_workspace_fn=get_current_workspace, url=url)


def _tool_inspect_subtitle(subtitle_path: str) -> dict:
    return tool_inspect_subtitle_impl(subtitle_path)


def _tool_analyze_subtitle(subtitle_path: str, api_key: str, base_url: str, model: str) -> dict:
    return tool_analyze_subtitle_impl(subtitle_path, api_key, base_url, model)


def _tool_recommend_transcode(input_path: str, goal: str) -> dict:
    return tool_recommend_transcode_impl(input_path, goal)


def _tool_execute_transcode(input_path: str, codec: str, output_path: str = "", crf: int = 23, preset: str = "medium") -> dict:
    return tool_execute_transcode_impl(
        run_transcode_job_fn=run_transcode_job,
        input_path=input_path,
        codec=codec,
        output_path=output_path,
        crf=crf,
        preset=preset,
    )


def _tool_execute_slice_video(input_path: str, start_time: str, end_time: str, output_path: str = "", accurate: bool = True) -> dict:
    return tool_execute_slice_video_impl(
        run_slice_job_fn=run_slice_job,
        input_path=input_path,
        start_time=start_time,
        end_time=end_time,
        output_path=output_path,
        accurate=accurate,
    )


def _tool_execute_fetch_analyze_slice(
    url: str,
    api_key: str,
    base_url: str,
    model: str,
    clip_count: int = 3,
    video_codec_preference: str = "h264",
) -> dict:
    return tool_execute_fetch_analyze_slice_impl(
        run_fetch_analyze_slice_job_fn=run_fetch_analyze_slice_job,
        url=url,
        api_key=api_key,
        base_url=base_url,
        model=model,
        clip_count=clip_count,
        video_codec_preference=video_codec_preference,
    )


def _tool_scan_assets(directory: str, keyword: str = "", asset_type: str = "") -> dict:
    return tool_scan_assets_impl(asset_library_cls=AssetLibrary, directory=directory, keyword=keyword, asset_type=asset_type)


def _tool_suggest_asset_names(paths: list[str], style: str = "kebab-case") -> dict:
    return tool_suggest_asset_names_impl(paths, style)


def _tool_extract_screenshot(video_path: str, timestamp: str, output_path: str = "") -> dict:
    return tool_extract_screenshot_impl(
        screenshot_generator_cls=ScreenshotGenerator,
        video_path=video_path,
        timestamp=timestamp,
        output_path=output_path,
    )


def _tool_export_wechat_moments(text: str, author: str = "A", theme: str = "dark") -> dict:
    return tool_export_wechat_moments_impl(
        get_current_workspace_fn=get_current_workspace,
        get_draft_fn=get_wechat_moments_draft,
        save_draft_fn=save_wechat_moments_draft,
        export_image_fn=export_wechat_moments_image,
        text=text,
        author=author,
        theme=theme,
    )


def _tool_list_psd_tickets() -> dict:
    return tool_list_psd_tickets_impl(get_current_workspace_fn=get_current_workspace, list_tickets_fn=list_photoshop_tickets)


def _tool_scan_psd(psd_path: str, languages: list[str] | None = None) -> dict:
    return tool_scan_psd_impl(get_current_workspace_fn=get_current_workspace, scan_psd_fn=scan_photoshop_document, psd_path=psd_path, languages=languages)


def _tool_get_auditor_status() -> dict:
    return tool_get_auditor_status_impl(get_current_workspace_fn=get_current_workspace, get_auditor_config_fn=get_auditor_config)


def _tool_run_audit_scan() -> dict:
    return tool_run_audit_scan_impl(get_current_workspace_fn=get_current_workspace, run_auditor_scan_once_fn=run_auditor_scan_once)


def _tool_get_ae_status() -> dict:
    return tool_get_ae_status_impl(get_current_workspace_fn=get_current_workspace, get_ae_status_fn=get_ae_status)


def _tool_list_ae_tickets() -> dict:
    return tool_list_ae_tickets_impl(get_current_workspace_fn=get_current_workspace, list_ae_tickets_fn=list_ae_tickets)


def _tool_scan_ae_project(project_path: str) -> dict:
    return tool_scan_ae_project_impl(get_current_workspace_fn=get_current_workspace, scan_ae_project_fn=scan_ae_project, project_path=project_path)


class MediaAgentService:
    def __init__(self, api_key: str, base_url: str, model: str):
        cfg = get_api_config()
        self.api_key = api_key or cfg["api_key"]
        self.base_url = base_url or cfg["api_base_url"]
        self.model = model or cfg["analysis_model"]
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if not self.api_key:
            raise ValueError("Agent model API key is not configured")
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def _tools(self) -> list[dict]:
        return build_agent_tool_specs()

    def _run_tool(self, name: str, arguments: dict) -> dict:
        mapping = {
            "get_video_info": lambda: _tool_get_video_info(arguments["url"]),
            "inspect_subtitle": lambda: _tool_inspect_subtitle(arguments["subtitle_path"]),
            "analyze_subtitle": lambda: _tool_analyze_subtitle(arguments["subtitle_path"], self.api_key, self.base_url, self.model),
            "recommend_transcode": lambda: _tool_recommend_transcode(arguments["input_path"], arguments["goal"]),
            "execute_transcode": lambda: _tool_execute_transcode(arguments["input_path"], arguments["codec"], arguments.get("output_path", ""), int(arguments.get("crf", 23)), arguments.get("preset", "medium")),
            "execute_slice_video": lambda: _tool_execute_slice_video(arguments["input_path"], arguments["start_time"], arguments["end_time"], arguments.get("output_path", ""), bool(arguments.get("accurate", True))),
            "execute_fetch_analyze_slice": lambda: _tool_execute_fetch_analyze_slice(arguments["url"], self.api_key, self.base_url, self.model, int(arguments.get("clip_count", 3)), arguments.get("video_codec_preference", "h264")),
            "scan_assets": lambda: _tool_scan_assets(arguments["directory"], arguments.get("keyword", ""), arguments.get("asset_type", "")),
            "suggest_asset_names": lambda: _tool_suggest_asset_names(arguments["paths"], arguments.get("style", "kebab-case")),
            "extract_screenshot": lambda: _tool_extract_screenshot(arguments["video_path"], arguments["timestamp"], arguments.get("output_path", "")),
            "export_wechat_moments": lambda: _tool_export_wechat_moments(arguments["text"], arguments.get("author", "A"), arguments.get("theme", "dark")),
            "list_psd_tickets": _tool_list_psd_tickets,
            "scan_psd": lambda: _tool_scan_psd(arguments["psd_path"], arguments.get("languages")),
            "get_auditor_status": _tool_get_auditor_status,
            "run_audit_scan": _tool_run_audit_scan,
            "get_ae_status": _tool_get_ae_status,
            "list_ae_tickets": _tool_list_ae_tickets,
            "scan_ae_project": lambda: _tool_scan_ae_project(arguments["project_path"]),
        }
        runner = mapping.get(name)
        if runner is None:
            return {"ok": False, "error": f"不支持的工具: {name}"}
        return runner()

    def _chat_completion(self, max_completion_tokens: int, **kwargs):
        request_kwargs = dict(kwargs)
        token_param = "max_completion_tokens" if self.model.lower().startswith(("gpt-5", "o1", "o3", "o4")) else "max_tokens"
        last_error: Exception | None = None
        for _ in range(3):
            try:
                return self.client.chat.completions.create(**request_kwargs, **{token_param: max_completion_tokens})
            except Exception as exc:
                message = str(exc)
                if "max_tokens" in message and "max_completion_tokens" in message and token_param == "max_tokens":
                    token_param = "max_completion_tokens"
                    last_error = exc
                    continue
                if "max_completion_tokens" in message and "max_tokens" in message and token_param == "max_completion_tokens":
                    token_param = "max_tokens"
                    last_error = exc
                    continue
                if "temperature" in message and "unsupported" in message.lower() and "temperature" in request_kwargs:
                    request_kwargs.pop("temperature", None)
                    last_error = exc
                    continue
                raise
        if last_error is not None:
            raise last_error
        raise RuntimeError("chat completion request failed")

    def test_connection(self) -> dict:
        try:
            response = self._chat_completion(
                model=self.model,
                messages=[{"role": "user", "content": "reply ok"}],
                temperature=0,
                max_completion_tokens=8,
            )
            return {"ok": True, "message": response.choices[0].message.content or "ok"}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def execute(self, task: str, extra_context: str = "") -> dict:
        user_prompt = task.strip()
        if extra_context.strip():
            user_prompt += f"\n\n补充上下文:\n{extra_context.strip()}"

        direct_route = self._try_direct_route(task, extra_context)
        if direct_route is not None:
            return direct_route

        if not self.api_key:
            return _response(
                False,
                "Agent model API key is not configured. Direct local routes can still run, but model planning needs an API key.",
                [{"route": "model_agent", "result": "missing_api_key"}],
                [],
                [],
            )

        messages = [{"role": "system", "content": DEFAULT_AGENT_SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}]
        tool_traces: list[dict] = []
        actions: list[dict] = []
        artifacts: list[dict] = []

        for _ in range(6):
            response = self._chat_completion(
                model=self.model,
                messages=messages,
                tools=self._tools(),
                tool_choice="auto",
                temperature=0.2,
                max_completion_tokens=3000,
            )
            message = response.choices[0].message
            assistant_payload = {"role": "assistant", "content": message.content or ""}
            if getattr(message, "tool_calls", None):
                assistant_payload["tool_calls"] = [tool_call.model_dump() for tool_call in message.tool_calls]
            messages.append(assistant_payload)

            if not getattr(message, "tool_calls", None):
                return _response(True, message.content or "", tool_traces, actions, artifacts)

            for tool_call in message.tool_calls:
                arguments = json.loads(tool_call.function.arguments or "{}")
                result = self._run_tool(tool_call.function.name, arguments)
                tool_traces.append({"tool": tool_call.function.name, "arguments": arguments, "result": result})
                new_actions, new_artifacts = _summarize_tool_result(tool_call.function.name, arguments, result)
                _extend_unique(actions, new_actions)
                _extend_unique(artifacts, new_artifacts)
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": _json_dumps(result)})

        return _response(False, "Agent reached the step limit before producing a final answer.", tool_traces, actions, artifacts)

    def localization_batch_translate_json(self, batch: list[dict[str, Any]]) -> str:
        """将工单文案按 BCP 47 区域本地化翻译；batch 每项含 i、text、locale，返回文本应为 JSON。"""
        if not self.api_key:
            raise ValueError("缺少模型 API Key")
        system = (
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
        user_payload = json.dumps({"items": batch}, ensure_ascii=False)
        response = self._chat_completion(
            8000,
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_payload},
            ],
            temperature=0.2,
        )
        return (response.choices[0].message.content or "").strip()

    def _try_direct_route(self, task: str, extra_context: str) -> dict | None:
        return _try_direct_route_impl(
            task,
            extra_context,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            get_current_workspace_fn=get_current_workspace,
            run_fetch_analyze_slice_job_fn=run_fetch_analyze_slice_job,
            tool_scan_assets_fn=_tool_scan_assets,
            tool_execute_decrypt_to_assets_fn=_tool_execute_decrypt_to_assets,
        )
