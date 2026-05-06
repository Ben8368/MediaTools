"""朋友圈图片生成器

从wechat_moments模块迁移而来，统一到素材生成模块。
"""
from pathlib import Path
from typing import Any

from adapters import WechatMomentsRuntimeAdapter
from core.logger import get_logger

logger = get_logger(__name__)

WORKSPACE_LAYOUT = {
    "inputs_dir": "inputs",
    "downloads_dir": "downloads",
    "decrypted_dir": "decrypted",
    "transcoded_dir": "transcoded",
    "clips_dir": "clips",
    "subtitles_dir": "subtitles",
    "analysis_dir": "analysis",
    "assets_dir": "assets",
    "imports_dir": "imports",
    "exports_dir": "exports",
    "cache_dir": "cache",
    "logs_dir": "logs",
    "manifests_dir": "manifests",
}
DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[2] / "projects" / "default"


DEFAULT_DRAFT = {
    "author": "A",
    "text": "很实用的教程 [微笑]\n需要收集五个赞，谢谢大家啦。",
    "location": "",
    "app": "",
    "like_count": 18,
    "comment_name": "朋友",
    "comment_text": "收藏了，晚点试一下。",
    "theme": "dark",
    "avatar_seed": "mediatools",
}


class WechatMomentsGenerator:
    """朋友圈图片生成器"""

    def __init__(self):
        self._adapter = WechatMomentsRuntimeAdapter()

    def _resolve_workspace_dir(self, kind: str, workspace: dict | None = None) -> Path:
        ws = workspace or {}
        key = kind if kind.endswith("_dir") else f"{kind}_dir"
        raw_value = ws.get(key)
        if raw_value:
            target = Path(raw_value)
            target.mkdir(parents=True, exist_ok=True)
            return target

        if key == "project_root":
            root = DEFAULT_PROJECT_ROOT
            root.mkdir(parents=True, exist_ok=True)
            return root

        folder = WORKSPACE_LAYOUT.get(key)
        if not folder:
            raise KeyError(f"Unknown workspace dir kind: {kind}")

        fallback_root = DEFAULT_PROJECT_ROOT
        fallback_root.mkdir(parents=True, exist_ok=True)
        target = fallback_root / folder
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _wechat_root(self, kind: str, workspace: dict | None = None) -> Path:
        """获取朋友圈相关目录"""
        target = self._resolve_workspace_dir(kind, workspace) / "wechat_moments"
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _draft_path(self, workspace: dict | None = None) -> Path:
        """获取草稿文件路径"""
        return self._wechat_root("manifests", workspace) / "draft.json"

    def _exports_index_path(self, workspace: dict | None = None) -> Path:
        """获取导出索引路径"""
        return self._wechat_root("manifests", workspace) / "exports.json"

    def get_status(self, workspace: dict | None = None) -> dict[str, Any]:
        """
        获取朋友圈生成器状态。

        返回:
            状态信息字典
        """
        status = self._adapter.get_status()
        manifests_dir = self._wechat_root("manifests", workspace)
        status.update({
            "module_id": "wechat_moments",
            "manifests_dir": str(manifests_dir),
            "draft_path": str(self._draft_path(workspace)),
        })
        return status

    def get_draft(self, workspace: dict | None = None) -> dict[str, Any]:
        """
        获取当前草稿。

        返回:
            草稿内容字典
        """
        draft_path = self._draft_path(workspace)
        if not draft_path.exists():
            return DEFAULT_DRAFT.copy()

        try:
            import json
            return json.loads(draft_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"读取草稿失败: {e}")
            return DEFAULT_DRAFT.copy()

    def save_draft(self, draft: dict, workspace: dict | None = None) -> dict:
        """
        保存草稿。

        参数:
            draft: 草稿内容
            workspace: 工作区配置

        返回:
            操作结果
        """
        try:
            import json
            draft_path = self._draft_path(workspace)
            draft_path.write_text(
                json.dumps(draft, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            logger.info(f"草稿已保存: {draft_path}")
            return {"success": True, "path": str(draft_path)}
        except Exception as e:
            logger.error(f"保存草稿失败: {e}")
            return {"success": False, "error": str(e)}

    def export_image(
        self,
        draft: dict | None = None,
        output_path: str | None = None,
        workspace: dict | None = None,
    ) -> dict:
        """
        导出朋友圈图片。

        参数:
            draft: 草稿内容（可选，默认使用当前草稿）
            output_path: 输出路径（可选）
            workspace: 工作区配置

        返回:
            导出结果
        """
        if draft is None:
            draft = self.get_draft(workspace)

        if output_path is None:
            import time
            timestamp = int(time.time())
            exports_dir = self._wechat_root("exports", workspace)
            output_path = str(exports_dir / f"moments_{timestamp}.png")

        try:
            # 调用适配器导出图片
            result = self._adapter.export_image(draft, output_path)

            if result.get("success"):
                logger.info(f"朋友圈图片已导出: {output_path}")

                # 更新导出索引
                self._update_exports_index(output_path, draft, workspace)

            return result
        except Exception as e:
            logger.error(f"导出图片失败: {e}")
            return {"success": False, "error": str(e)}

    def _update_exports_index(
        self,
        output_path: str,
        draft: dict,
        workspace: dict | None = None,
    ) -> None:
        """更新导出索引"""
        try:
            import json
            import time

            index_path = self._exports_index_path(workspace)

            # 读取现有索引
            if index_path.exists():
                exports = json.loads(index_path.read_text(encoding="utf-8"))
            else:
                exports = []

            # 添加新记录
            exports.append({
                "path": output_path,
                "timestamp": int(time.time()),
                "draft": draft,
            })

            # 保存索引
            index_path.write_text(
                json.dumps(exports, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"更新导出索引失败: {e}")
