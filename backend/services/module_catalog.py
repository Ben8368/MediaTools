"""Module catalog data — shared by api/modules and services/system_monitor."""

from __future__ import annotations


def _status(dep_ok: bool, *, experimental: bool = False) -> str:
    if not dep_ok:
        return "dep_missing"
    return "staged" if experimental else "ready"


def build_module_catalog(
    *,
    auditor_ok: bool,
    ffmpeg_ok: bool,
    filebrowser_ok: bool = False,
    photoshop_ok: bool,
    umcli_ok: bool,
    wechat_ok: bool,
    ytdlp_ok: bool,
) -> dict:
    modules = [
        {
            "id": "fetcher",
            "name": "媒体获取",
            "desc": "下载视频和字幕，并通过任务中心回传进度。",
            "icon": "download",
            "status": _status(ytdlp_ok),
            "dep": "yt-dlp",
            "dep_ok": ytdlp_ok,
            "experimental": False,
        },
        {
            "id": "encoder",
            "name": "编码转码",
            "desc": "执行 H.264 / H.265 转码、音频提取和精确切片。",
            "icon": "film",
            "status": _status(ffmpeg_ok),
            "dep": "ffmpeg",
            "dep_ok": ffmpeg_ok,
            "experimental": False,
        },
        {
            "id": "decryptor",
            "name": "音乐解密",
            "desc": "解密常见音乐平台加密文件，并可归档到素材库。",
            "icon": "key",
            "status": _status(umcli_ok),
            "dep": "um-cli",
            "dep_ok": umcli_ok,
            "experimental": False,
        },
        {
            "id": "assets",
            "name": "素材库",
            "desc": "扫描、索引并检索当前工作区素材。",
            "icon": "folder",
            "status": "ready",
            "dep": None,
            "dep_ok": True,
            "experimental": False,
        },
        {
            "id": "workbench",
            "name": "剪辑工作台",
            "desc": "基于字幕分析生成片段建议，并批量导出片段。",
            "icon": "scissors",
            "status": _status(ffmpeg_ok),
            "dep": "ffmpeg",
            "dep_ok": ffmpeg_ok,
            "experimental": False,
        },
        {
            "id": "editor",
            "name": "剪映联动",
            "desc": "通过 capcut-mate HTTP API 进行实验性草稿创建和编辑。",
            "icon": "clapperboard",
            "status": "staged",
            "dep": "capcut-mate",
            "dep_ok": False,
            "experimental": True,
        },
        {
            "id": "photoshop",
            "name": "Photoshop 自动化",
            "desc": "扫描 PSD 文本层、管理工单，并导出当前工作区副本。",
            "icon": "badge-ps",
            "status": _status(photoshop_ok),
            "dep": "Photoshop + pywin32",
            "dep_ok": photoshop_ok,
            "experimental": False,
        },
        {
            "id": "wechat_moments",
            "name": "朋友圈生成",
            "desc": "生成微信朋友圈样式的静态分享图。",
            "icon": "message-circle",
            "status": _status(wechat_ok, experimental=True),
            "dep": "vendored source",
            "dep_ok": wechat_ok,
            "experimental": True,
        },
        {
            "id": "filebrowser",
            "name": "文件管理器增强",
            "desc": "基于 filebrowser 的增强文件管理后端能力。",
            "icon": "folder-tree",
            "status": _status(filebrowser_ok, experimental=True),
            "dep": "filebrowser",
            "dep_ok": filebrowser_ok,
            "experimental": True,
        },
        {
            "id": "auditor",
            "name": "审核流水线",
            "desc": "扫描监控目录并把审核结果写入工作区产物。",
            "icon": "clipboard-check",
            "status": _status(auditor_ok, experimental=True),
            "dep": "vendored source",
            "dep_ok": auditor_ok,
            "experimental": True,
        },
    ]
    return {"modules": modules}
