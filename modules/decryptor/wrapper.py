"""
Unlock Music CLI 封装器

通过 subprocess 调用 bin/um-cli.exe 执行音乐解密。
"""
import platform
import subprocess
from pathlib import Path

_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0


def _get_umcli_bin() -> Path:
    """返回 um-cli 二进制路径"""
    bin_dir = Path(__file__).parent.parent.parent / "bin"
    suffix = ".exe" if platform.system() == "Windows" else ""
    return bin_dir / f"um-cli{suffix}"


class DecryptorWrapper:
    """Unlock Music CLI 封装器"""

    def __init__(self, umcli_bin: Path = None):
        if umcli_bin is None:
            umcli_bin = _get_umcli_bin()
        self.umcli_bin = Path(umcli_bin)

    def is_available(self) -> bool:
        """检查 um-cli 二进制是否存在"""
        return self.umcli_bin.exists()

    def decrypt(self, input_path: str, output_dir: str = None, remove_source: bool = False) -> dict:
        """
        解密单个文件。

        参数:
            input_path: 加密文件路径
            output_dir: 输出目录（默认与输入文件同目录）
            remove_source: 是否删除源文件

        返回:
            {"success": bool, "output": str, "error": str}
        """
        if not self.is_available():
            return {
                "success": False,
                "output": "",
                "error": f"um-cli 未找到，请编译 vendor/unlock-music/ 并放置于: {self.umcli_bin}"
            }

        cmd = [str(self.umcli_bin), "-i", input_path]
        if output_dir:
            cmd += ["-o", output_dir]
        if remove_source:
            cmd.append("--remove-source")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
                creationflags=_SUBPROCESS_FLAGS,
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else "",
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": "解密超时（5分钟）"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    def decrypt_batch(self, input_dir: str, output_dir: str = None, remove_source: bool = False) -> dict:
        """
        批量解密目录下所有加密文件。

        参数:
            input_dir: 输入目录
            output_dir: 输出目录（默认与输入目录相同）
            remove_source: 是否删除源文件

        返回:
            {"success": bool, "output": str, "error": str}
        """
        if not self.is_available():
            return {
                "success": False,
                "output": "",
                "error": f"um-cli 未找到，请编译 vendor/unlock-music/ 并放置于: {self.umcli_bin}"
            }

        cmd = [str(self.umcli_bin), "-i", input_dir]
        if output_dir:
            cmd += ["-o", output_dir]
        if remove_source:
            cmd.append("--remove-source")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
                creationflags=_SUBPROCESS_FLAGS,
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else "",
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": "批量解密超时（30分钟）"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    def get_version(self) -> str:
        """获取 um-cli 版本信息"""
        if not self.is_available():
            return "未安装"
        try:
            result = subprocess.run(
                [str(self.umcli_bin), "--version"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
                creationflags=_SUBPROCESS_FLAGS,
            )
            return result.stdout.strip() if result.returncode == 0 else "未知"
        except Exception:
            return "未知"
