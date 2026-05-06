"""
MediaTools 全局配置

路径解析规则：
- BASE_DIR: 项目根目录（本文件所在位置）
- BIN_DIR:  外部二进制目录（ffmpeg, ffprobe, yt-dlp, um-cli）
- VENDOR_DIR: git submodule 存放目录
"""
import os
from pathlib import Path

try:
    from dotenv import dotenv_values, load_dotenv
except ImportError:
    def dotenv_values(path: str) -> dict[str, str]:
        env_path = Path(path)
        if not env_path.exists():
            return {}

        values: dict[str, str] = {}
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
        return values

    def load_dotenv(dotenv_path: str | None = None, override: bool = False) -> bool:
        if not dotenv_path:
            return False
        values = dotenv_values(dotenv_path)
        for key, value in values.items():
            if override or key not in os.environ:
                os.environ[key] = value
        return bool(values)

BASE_DIR = Path(__file__).parent
BIN_DIR = BASE_DIR / "bin"
VENDOR_DIR = BASE_DIR / "vendor"
DOWNLOADS_DIR = BASE_DIR / "projects" / "default" / "downloads"

ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=str(ENV_PATH))

# ── LLM API（用于字幕分析）────────────────────────────────────────────
API_KEY = os.getenv("TEC_CHI_API_KEY", "")
API_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://ai-gateway.tec-do.cn/claw-agents/text/v1")
ANALYSIS_MODEL = os.getenv("ANALYSIS_MODEL", "qwen3.6-plus")

# ── 媒体获取默认配置 ──────────────────────────────────────────────────
DEFAULT_OUTPUT_DIR = Path(os.getenv("MEDIA_OUTPUT_DIR", str(DOWNLOADS_DIR)))
DEFAULT_NAMING_TEMPLATE = os.getenv("MEDIA_NAMING_TEMPLATE", "{index}_{title}_{upload_date}")

# ── 任务中心配置 ──────────────────────────────────────────────────────
TASK_HISTORY_DAYS = int(os.getenv("TASK_HISTORY_DAYS", "7"))  # 任务历史保留天数
TASK_DB_PATH = os.getenv("TASK_DB_PATH", str(BASE_DIR / "data" / "tasks.db"))  # 任务数据库路径
MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "5"))  # 最大并发任务数
TASK_TIMEOUT_SECONDS = int(os.getenv("TASK_TIMEOUT_SECONDS", "3600"))  # 任务超时时间（秒）

CAPCUT_MATE_BASE_URL = os.getenv("CAPCUT_MATE_BASE_URL", "http://localhost:30000")

FILEBROWSER_ENABLED = os.getenv("FILEBROWSER_ENABLED", "false").lower() == "true"
FILEBROWSER_HOST = os.getenv("FILEBROWSER_HOST", "127.0.0.1")
FILEBROWSER_PORT = int(os.getenv("FILEBROWSER_PORT", "30010"))
FILEBROWSER_BASE_URL = os.getenv("FILEBROWSER_BASE_URL", "http://127.0.0.1:30010")
FILEBROWSER_BINARY_RAW = os.getenv("FILEBROWSER_BINARY", str(BIN_DIR / "filebrowser.exe"))
FILEBROWSER_DB_PATH_RAW = os.getenv("FILEBROWSER_DB_PATH", str(BASE_DIR / "runtime" / "filebrowser.db"))

# ── GUI 服务配置 ───────────────────────────────────────────────────────
GUI_SERVER_NAME = os.getenv("GUI_SERVER_NAME", "127.0.0.1")
GUI_SERVER_PORT = int(os.getenv("GUI_SERVER_PORT", "7860"))
GUI_SHARE = os.getenv("GUI_SHARE", "false").lower() == "true"
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")  # 留空则不启用认证
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://127.0.0.1:7860,http://localhost:7860,http://127.0.0.1:5173,http://localhost:5173",
    ).split(",")
    if origin.strip()
]
PREVIEW_MAX_BYTES = int(os.getenv("PREVIEW_MAX_BYTES", str(25 * 1024 * 1024)))
ASSET_SCAN_MAX_FILES = int(os.getenv("ASSET_SCAN_MAX_FILES", "5000"))


def _config_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else BASE_DIR / path


FILEBROWSER_BINARY = _config_path(FILEBROWSER_BINARY_RAW)
FILEBROWSER_DB_PATH = _config_path(FILEBROWSER_DB_PATH_RAW)


WORKSPACE_ALLOWED_ROOTS = [
    _config_path(root.strip())
    for root in os.getenv("WORKSPACE_ALLOWED_ROOTS", str(BASE_DIR / "projects")).split(os.pathsep)
    if root.strip()
]

# ── CSV 字段定义（媒体获取记录）──────────────────────────────────────
CSV_FIELDS = [
    "video_id", "url", "title", "uploader", "duration", "upload_date",
    "view_count", "like_count", "language", "resolution", "fps",
    "file_size_mb", "categories", "tags",
    "original_subs", "chinese_subs", "highlights_count",
    "download_time", "local_path", "subtitle_path",
    "video_status", "video_error",
]

# ── LLM 字幕分析 Prompt ───────────────────────────────────────────────
ANALYSIS_PROMPT = """你是一位专业的短视频内容分析师。请分析以下视频字幕文本，提取所有亮点和卖点片段。

分类标准：
- 产品卖点：核心功能、优势、价格优惠等
- 情感共鸣：触动人心的故事、观点、金句
- 数据亮点：关键数据、统计、对比
- 故事转折：悬念、反转、高潮
- 知识干货：实用技巧、方法论、干货知识

返回JSON格式，严格遵守：
[
  {
    "start_time": "00:01:23",
    "end_time": "00:02:15",
    "quote": "原文关键句",
    "reason": "为什么这是一个亮点/卖点的详细分析",
    "category": "产品卖点|情感共鸣|数据亮点|故事转折|知识干货"
  }
]

要求：
1. 只返回有效JSON，不要包含任何其他文字
2. 每个片段必须有明确的时间段
3. 至少提取3-5个亮点（如果内容允许）
4. quote必须是字幕中的原文，不要改写"""


def get_api_config() -> dict:
    """从 .env 文件实时读取 API 配置（不使用模块级缓存）"""
    values = dotenv_values(str(ENV_PATH)) if ENV_PATH.exists() else {}
    return {
        "api_key": values.get("TEC_CHI_API_KEY", ""),
        "api_base_url": values.get("OPENAI_BASE_URL", "https://ai-gateway.tec-do.cn/claw-agents/text/v1"),
        "analysis_model": values.get("ANALYSIS_MODEL", "qwen3.6-plus"),
    }
