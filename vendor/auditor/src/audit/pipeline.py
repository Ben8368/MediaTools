"""
pipeline.py — 审计后处理流水线，main.py 共用
"""
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List

logger = logging.getLogger(__name__)

AUDIT_TIME_FMT = "%Y-%m-%d %H:%M"

RESULT_LABEL_MAP = {
    "CONFIRMED": "双审确认问题",
    "DISPUTED": "一审发现问题",
    "SECOND_FIND": "二审发现问题",
}

VERDICT_MAP = {
    "CONFIRMED": "双审确认",
    "DISPUTED": "一审发现",
    "SECOND_FIND": "二审发现",
}


class AuditPipeline:
    """审计后处理：批量审计 → 按文件聚合 → 写结果

    注意：AuditEngine.audit_batch() 内部已包含完整的双盲请求 + 裁定逻辑，
    此类只负责结果聚合和写入。
    """

    def __init__(self, engine, designer_lookup, backend, supervisor_id=""):
        self.engine = engine
        self.designer_lookup = designer_lookup
        self.backend = backend
        self.supervisor_id = supervisor_id

    async def process(self, file_paths: List[str], include_audit_time: bool = False) -> List[Dict]:
        """执行完整审计流程，返回有问题的文件结果列表。

        Args:
            file_paths: 待审计文件路径列表
            include_audit_time: 是否在结果中包含审计时间字段
        """
        rules = self.backend.load_rules()
        strictness = next(
            (r.get("strictness_level", "STANDARD") for r in rules
             if str(r.get("enabled", "TRUE")).upper() == "TRUE"),
            "STANDARD",
        )
        rule_name_map = {r["rule_id"]: r["rule_name"] for r in rules}

        # audit_batch 返回的已经是裁定后的结果，每条记录包含 result_type
        raw_results = await self.engine.audit_batch(file_paths, strictness=strictness)

        # 按文件名分组
        by_file = defaultdict(list)
        for r in raw_results:
            by_file[r["file_name"]].append(r)

        to_write = []
        cleared_count = 0

        for file_name, rule_results in by_file.items():
            issues = [r for r in rule_results if r["result_type"] != "CLEARED"]
            cleared = [r for r in rule_results if r["result_type"] == "CLEARED"]
            cleared_count += len(cleared)

            if not issues:
                continue

            base = rule_results[0]
            match = self.designer_lookup.match(file_name, self.supervisor_id)
            notify = self.designer_lookup.resolve_notify_target(
                match, issues[0]["result_type"], self.supervisor_id
            )
            overall = self._decide_overall(issues)
            issues_summary = self._format_issues(issues, rule_name_map)
            max_conf = max((r.get("confidence", 0) for r in issues), default=0)

            row = {
                "file_name": file_name,
                "file_path": base.get("file_path", ""),
                "region": base.get("region", ""),
                "designer_name": match["designer_name"],
                "designer_pid": match["designer_pid"],
                "overall_result": overall,
                "issue_count": len(issues),
                "issues_summary": issues_summary,
                "confidence": round(max_conf, 3),
                "mention_target": notify or "",
                "strictness": strictness,
            }
            if include_audit_time:
                row["audit_time"] = datetime.now(timezone.utc).strftime(AUDIT_TIME_FMT)
            to_write.append(row)

        if to_write:
            self.backend.write_results(to_write)

        logger.info("Done: %d files with issues, %d cleared", len(to_write), cleared_count)
        return to_write

    @staticmethod
    def _decide_overall(issues: List[Dict]) -> str:
        """决定总体结论等级：CONFIRMED > DISPUTED > SECOND_FIND"""
        if any(r["result_type"] == "CONFIRMED" for r in issues):
            return "CONFIRMED"
        if any(r["result_type"] == "DISPUTED" for r in issues):
            return "DISPUTED"
        return "SECOND_FIND"

    @staticmethod
    def _format_issues(issues: List[Dict], rule_name_map: Dict[str, str]) -> str:
        """格式化问题规则列表为多行文本"""
        lines = []
        for r in issues:
            rname = rule_name_map.get(r["rule_id"], r["rule_id"])
            verdict_cn = VERDICT_MAP.get(r["result_type"], r["result_type"])
            reason = r.get("auditor1_reason") or r.get("auditor2_reason") or ""
            evidence = r.get("auditor1_evidence") or r.get("auditor2_evidence") or ""
            parts = [f"[{r['rule_id']}] {rname}｜{verdict_cn}"]
            if reason:
                parts.append(f"  结论：{reason}")
            if evidence:
                parts.append(f"  原文：{evidence}")
            lines.append("\n".join(parts))
        return "\n\n".join(lines)
