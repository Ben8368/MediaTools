"""OpenAI tool schema definitions for MediaAgentService."""

def build_agent_tool_specs() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_video_info",
                "description": "获取视频元信息，并判断是否存在人工字幕或自动字幕。",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "inspect_subtitle",
                "description": "检查本地字幕文件，输出段数、时长和前几段内容。支持 .srt 和 .vtt。",
                "parameters": {
                    "type": "object",
                    "properties": {"subtitle_path": {"type": "string"}},
                    "required": ["subtitle_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_subtitle",
                "description": "调用当前配置的 LLM 分析字幕亮点，并生成可切片片段建议。",
                "parameters": {
                    "type": "object",
                    "properties": {"subtitle_path": {"type": "string"}},
                    "required": ["subtitle_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "recommend_transcode",
                "description": "根据输入文件和用途，推荐转码策略。goal 例如：通用发布、长期存档、只要音频、低体积分发。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input_path": {"type": "string"},
                        "goal": {"type": "string"},
                    },
                    "required": ["input_path", "goal"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "execute_transcode",
                "description": "执行实际转码任务。codec 只支持 H.264 (AVC)、H.265 (HEVC)、提取音频。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input_path": {"type": "string"},
                        "codec": {"type": "string"},
                        "output_path": {"type": "string"},
                        "crf": {"type": "integer"},
                        "preset": {"type": "string"},
                    },
                    "required": ["input_path", "codec"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "execute_slice_video",
                "description": "执行视频切片。默认优先使用精确切片 accurate=true，作为 capcut-mate 不可用时的备选方案。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input_path": {"type": "string"},
                        "start_time": {"type": "string"},
                        "end_time": {"type": "string"},
                        "output_path": {"type": "string"},
                        "accurate": {"type": "boolean"},
                    },
                    "required": ["input_path", "start_time", "end_time"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "execute_fetch_analyze_slice",
                "description": "执行完整自动化链路：下载视频与字幕、分析字幕亮点、并批量切出片段。默认输出到当前项目工作区。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "clip_count": {"type": "integer"},
                        "video_codec_preference": {"type": "string"},
                    },
                    "required": ["url"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "scan_assets",
                "description": "扫描素材目录，并按关键词或类型筛选素材。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string"},
                        "keyword": {"type": "string"},
                        "asset_type": {"type": "string"},
                    },
                    "required": ["directory"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "suggest_asset_names",
                "description": "根据路径列表生成命名建议，当前只输出建议，不会真正重命名。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "paths": {"type": "array", "items": {"type": "string"}},
                        "style": {"type": "string"},
                    },
                    "required": ["paths"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "extract_screenshot",
                "description": "从视频中提取指定时间点的截图。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "video_path": {"type": "string"},
                        "timestamp": {"type": "string"},
                        "output_path": {"type": "string"},
                    },
                    "required": ["video_path", "timestamp"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "export_wechat_moments",
                "description": "生成微信朋友圈图片，输出到当前工作区。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "author": {"type": "string"},
                        "theme": {"type": "string"},
                    },
                    "required": ["text"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_psd_tickets",
                "description": "列出当前工作区的 Photoshop 工单。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "scan_psd",
                "description": "扫描 PSD 文件的文本层，并生成工单。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "psd_path": {"type": "string"},
                        "languages": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["psd_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_auditor_status",
                "description": "获取审核流水线的配置状态。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_audit_scan",
                "description": "执行一次审核扫描任务。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_ae_status",
                "description": "获取 After Effects 自动化模块的状态。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_ae_tickets",
                "description": "列出当前工作区的 After Effects 工单。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "scan_ae_project",
                "description": "扫描 After Effects 工程，提取可修改的合成和图层，生成工单。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "description": "AE 工程文件路径（.aep）"},
                    },
                    "required": ["project_path"],
                },
            },
        },
    ]
