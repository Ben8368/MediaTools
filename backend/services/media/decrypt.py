"""Encrypted music helpers and external tool status text."""

import shutil
from pathlib import Path

from adapters import FFmpegAdapter, UmcliAdapter, YtdlpAdapter
from backend.services.workspace import get_current_workspace


def _normalize_input_type(input_type: str) -> str:
    aliases = {
        "文件夹": "文件夹批量",
        "folder": "文件夹批量",
        "directory": "文件夹批量",
        "file": "单文件",
    }
    return aliases.get((input_type or "").strip(), (input_type or "").strip())

def _effective_decrypt_output_dir(input_type: str, input_path: str, output_dir: str | None) -> Path:
    if output_dir:
        return Path(output_dir)
    input_obj = Path(input_path)
    if input_type == "文件夹批量":
        return input_obj.resolve()
    return input_obj.resolve().parent

def _snapshot_files(directory: Path) -> set[str]:
    if not directory.exists():
        return set()
    return {str(path.resolve()) for path in directory.rglob("*") if path.is_file()}

def _copy_to_assets(created_files: list[Path], assets_dir: Path) -> int:
    assets_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for file_path in created_files:
        if not file_path.exists() or not file_path.is_file():
            continue
        target = assets_dir / file_path.name
        if target.resolve() == file_path.resolve():
            continue
        shutil.copy2(file_path, target)
        copied += 1
    return copied

def run_decrypt_job(input_type: str, input_path: str, output_dir: str | None, remove_source: bool, add_to_assets: bool = False, cancel_check=None) -> dict:
    wrapper = UmcliAdapter()

    if not input_path.strip():
        return {
            "summary_rows": [["状态", "未开始"]],
            "result_text": "请输入文件或文件夹路径",
        }

    if not wrapper.is_available():
        return {
            "summary_rows": [["状态", "um-cli 未安装"]],
            "result_text": f"um-cli 未找到: {wrapper.binary}\n请先点击 '编译 um-cli' 或手动编译",
        }

    input_path = input_path.strip()
    input_type = _normalize_input_type(input_type)
    output_dir = output_dir.strip() if output_dir and output_dir.strip() else None
    effective_output_dir = _effective_decrypt_output_dir(input_type, input_path, output_dir)
    before_files = _snapshot_files(effective_output_dir)

    try:
        if input_type == "文件夹批量":
            result = wrapper.decrypt_batch(input_path, str(effective_output_dir), remove_source, cancel_check=cancel_check)
        else:
            result = wrapper.decrypt(input_path, str(effective_output_dir), remove_source, cancel_check=cancel_check)

        if result["success"]:
            output = result.get("output", "")
            after_files = _snapshot_files(effective_output_dir)
            created_files = [Path(path) for path in sorted(after_files - before_files)]
            if add_to_assets:
                assets_dir = Path(get_current_workspace()["assets_dir"])
                if effective_output_dir.resolve() != assets_dir.resolve():
                    _copy_to_assets(created_files, assets_dir)
            return {
                "summary_rows": [
                    ["状态", "成功"],
                    ["模式", input_type],
                    ["输入", input_path],
                    ["输出目录", str(effective_output_dir)],
                ],
                "result_text": f"解密成功!\n{output[:500]}",
            }

        return {
            "summary_rows": [["状态", "失败"], ["错误", result["error"][:200]]],
            "result_text": f"解密失败: {result['error'][:200]}",
        }
    except Exception as exc:
        return {
            "summary_rows": [["状态", "异常"], ["错误", str(exc)[:200]]],
            "result_text": f"解密异常: {str(exc)[:200]}",
        }

def get_ytdlp_status_text() -> str:
    status = YtdlpAdapter().get_status()
    return f"状态: {'已安装' if status['installed'] else '未安装'}\n版本: {status['version']}\n路径: {status['path']}"

def get_ffmpeg_status_text() -> str:
    info = FFmpegAdapter().get_info()
    if info.get("installed"):
        return f"状态: 已安装\n版本: {info['version']}\nffmpeg: {info['ffmpeg_path']}\nffprobe: {info['ffprobe_path']}"
    return f"状态: 未安装\n请将 ffmpeg/ffprobe 放置于: {info['bin_dir']}"

def get_um_status_text() -> str:
    wrapper = UmcliAdapter()
    return f"状态: {'已安装' if wrapper.is_available() else '未安装'}\n版本: {wrapper.get_version()}\n路径: {wrapper.binary}"

def build_umcli() -> str:
    import platform
    import subprocess

    repo_root = Path(__file__).resolve().parents[3]
    vendor_dir = repo_root / "vendor" / "um-cli" / "source"
    bin_dir = repo_root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    suffix = ".exe" if platform.system() == "Windows" else ""
    output_bin = bin_dir / f"um-cli{suffix}"

    if not (vendor_dir / "go.mod").exists():
        return "编译失败: vendor/um-cli/source/go.mod 不存在，请确认源码已就位（上游 https://git.um-react.app/um/cli）"

    try:
        cmd = ["go", "build", "-o", str(output_bin), "./cmd/um"]
        result = subprocess.run(cmd, cwd=str(vendor_dir), capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode == 0:
            return f"编译成功: {output_bin}"
        return f"编译失败: {result.stderr[:200]}"
    except Exception as exc:
        return f"编译异常: {str(exc)[:200]}"
