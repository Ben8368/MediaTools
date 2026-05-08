"""Request body models for the FastAPI surface."""

from typing import Any

from pydantic import BaseModel


class WorkspaceBody(BaseModel):
    project_root: str

class WechatMomentsDraftBody(BaseModel):
    draft: dict[str, Any]

class WechatMomentsExportBody(BaseModel):
    image_data_url: str
    draft: dict[str, Any]

class AuditorConfigBody(BaseModel):
    config: dict[str, Any]

class AgentChatBody(BaseModel):
    task: str
    extra_context: str = ""
    api_key: str = ""
    base_url: str = ""
    model: str = ""

class AgentTestConnectionBody(BaseModel):
    api_key: str = ""
    base_url: str = ""
    model: str = ""

class FetcherDownloadBody(BaseModel):
    url: str
    platform: str = "auto"
    quality: str = "best"
    subtitles: bool = True
    analyze: bool = False
    output_dir: str = ""

class EncoderTranscodeBody(BaseModel):
    input_path: str
    output_path: str | None = None
    codec: str = "H.264 (AVC)"
    crf: int = 23
    preset: str = "medium"
    vcodec: str = ""
    acodec: str = ""

class DecryptorDecryptBody(BaseModel):
    input_type: str = "单文件"
    input_path: str
    output_dir: str | None = None
    remove_source: bool = False
    add_to_assets: bool = False

class WorkbenchAnalyzeBody(BaseModel):
    subtitle_path: str
    clip_count: int = 5

class WorkbenchExportBody(BaseModel):
    video_path: str
    subtitle_path: str = ""
    clips_json: str
    burn_subtitles: bool = True
    accurate: bool = True
    start_padding: float = 0.8
    end_padding: float = 1.0


class DownloaderAiAnalyzeBody(BaseModel):
    task_id: str
    target_duration: float = 0.0
    extra_context: str = ""


class DownloaderAiSliceBody(BaseModel):
    task_id: str
    burn_subtitles: bool = True
    padding: float = 0.8
    target_duration: float = 0.0
    extra_context: str = ""

class PhotoshopScanBody(BaseModel):
    psd_path: str = ""
    languages: list[str] = []
    timeout_sec: int = 180

class FolderScanBody(BaseModel):
    directory: str = ""
    recursive: bool = True
    languages: list[str] = []
    timeout_sec: int = 180
    max_files: int = 30

class PhotoshopTicketBody(BaseModel):
    ticket: dict[str, Any]

class TicketImportBody(BaseModel):
    file_path: str
    ticket_id: str = ""

class PhotoshopExecuteBody(BaseModel):
    dry_run: bool = False
    selected_task_indexes: list[int] | None = None

class AdobeScanBody(BaseModel):
    """统一 Adobe 工具扫描请求体"""
    file_path: str = ""
    languages: list[str] = []
    timeout_sec: int = 180
    # 快照相关
    label: str = ""
    step_index: int = 0
    notes: str = ""
    create_branch: bool = False
    # 渲染相关
    comp_index: int = 1
    output_path: str = ""
    output_module_template: str = "Best Settings"

class AdobeTicketBody(BaseModel):
    """统一 Adobe 工具工单更新请求体"""
    ticket: dict[str, Any]

class AdobeExecuteBody(BaseModel):
    """统一 Adobe 工具执行请求体"""
    dry_run: bool = False
    selected_task_indexes: list[int] | None = None

class FilesMkdirBody(BaseModel):
    path: str

class FilesDeleteBody(BaseModel):
    path: str
    recursive: bool = False

class FilesRenameBody(BaseModel):
    old_path: str
    new_name: str

class FilesCopyBody(BaseModel):
    source_path: str
    dest_path: str

class FilesMoveBody(BaseModel):
    source_path: str
    dest_path: str

class FilesExtractIconBody(BaseModel):
    exe_path: str
    output_png: str | None = None

class FilebrowserTrashBody(BaseModel):
    id: str
    restore_path: str | None = None

class ModelConfigBody(BaseModel):
    baseUrl: str = ""
    model: str = ""
    apiKey: str = ""
