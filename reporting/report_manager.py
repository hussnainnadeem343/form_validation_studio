"""Report manager for generating HTML, JSON, and terminal test summaries."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from form_engine.models import TestResult, TestStatus
from reporting.logger import logger


class ReportManager:
    """Generates execution summaries in JSON, HTML, and formatted console tables."""

    @staticmethod
    def print_console_summary(results: List[TestResult]) -> None:
        """Prints a structured summary table to the console."""
        total = len(results)
        passed = sum(1 for r in results if r.status == TestStatus.PASS)
        failed = sum(1 for r in results if r.status == TestStatus.FAIL)
        observed = sum(1 for r in results if r.status == TestStatus.OBSERVATION)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)

        logger.info("=" * 80)
        logger.info(f"{'EXECUTION SUMMARY':^80}")
        logger.info("=" * 80)
        logger.info(f"Total Tests : {total}")
        logger.info(f"Passed      : {passed}")
        logger.info(f"Failed      : {failed}")
        logger.info(f"Observation : {observed}")
        logger.info(f"Skipped     : {skipped}")
        logger.info("-" * 80)

        for r in results:
            tc = r.test_case
            status_symbol = {
                TestStatus.PASS: "[PASS]",
                TestStatus.FAIL: "[FAIL]",
                TestStatus.OBSERVATION: "[OBSV]",
                TestStatus.SKIPPED: "[SKIP]",
            }.get(r.status, "[????]")
            logger.info(f"{status_symbol:<8} | Field: {tc.field_name:<16} | Rule: {tc.rule_name:<26} | Status: {r.status.value}")
        logger.info("=" * 80)

    @staticmethod
    def save_json_summary(results: List[TestResult], output_dir: str | Path) -> Path:
        """Saves machine-readable JSON summary of results."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        file_path = out_path / "summary.json"

        data = {
            "timestamp": datetime.now().isoformat(),
            "totals": {
                "total": len(results),
                "passed": sum(1 for r in results if r.status == TestStatus.PASS),
                "failed": sum(1 for r in results if r.status == TestStatus.FAIL),
                "observation": sum(1 for r in results if r.status == TestStatus.OBSERVATION),
                "skipped": sum(1 for r in results if r.status == TestStatus.SKIPPED),
            },
            "results": [
                {
                    "field_name": r.test_case.field_name,
                    "step_number": r.step_number,
                    "semantic_type": r.test_case.semantic_type.value,
                    "rule_name": r.test_case.rule_name,
                    "input_value": str(r.test_case.input_value),
                    "expected_behavior": r.test_case.expected_behavior.value,
                    "status": r.status.value,
                    "actual_behavior": r.actual_behavior,
                    "validation_message": r.validation_message,
                    "screenshot_path": r.screenshot_path,
                    "duration_ms": r.duration_ms,
                }
                for r in results
            ],
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"JSON summary generated at: {file_path}")
        return file_path

    @staticmethod
    def save_html_summary(results: List[TestResult], output_dir: str | Path, project_name: str = "Generic Form Automation") -> Path:
        """Generates a responsive, standalone HTML summary report."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        file_path = out_path / "summary.html"

        total = len(results)
        passed = sum(1 for r in results if r.status == TestStatus.PASS)
        failed = sum(1 for r in results if r.status == TestStatus.FAIL)
        observed = sum(1 for r in results if r.status == TestStatus.OBSERVATION)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)

        rows_html = []
        for idx, r in enumerate(results, start=1):
            tc = r.test_case
            status_class = {
                TestStatus.PASS: "badge-pass",
                TestStatus.FAIL: "badge-fail",
                TestStatus.OBSERVATION: "badge-obs",
                TestStatus.SKIPPED: "badge-skip",
            }.get(r.status, "")

            screenshot_link = ""
            if r.screenshot_path:
                rel_path = f"../screenshots/{Path(r.screenshot_path).name}"
                screenshot_link = f"<a href='{rel_path}' target='_blank' class='screenshot-btn'>View Screenshot</a>"

            step_badge = f"<span class='badge' style='background:#e0e7ff; color:#3730a3; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;'>Step {r.step_number}</span>" if r.step_number else ""
            rows_html.append(f"""
            <tr>
                <td>{idx}</td>
                <td><strong>{tc.field_name}</strong> {step_badge}<br><span class="text-muted">{tc.semantic_type.value}</span></td>
                <td><code>{tc.rule_name}</code></td>
                <td><code>{html_escape(str(tc.input_value))}</code></td>
                <td><span class="badge {status_class}">{r.status.value}</span></td>
                <td>{html_escape(r.actual_behavior)}</td>
                <td>{screenshot_link}</td>
            </tr>
            """)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} - Validation Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 24px; background: #f8fafc; color: #1e293b; }}
        .header {{ margin-bottom: 24px; }}
        h1 {{ margin: 0 0 8px 0; font-size: 26px; }}
        .timestamp {{ color: #64748b; font-size: 14px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .card {{ background: #fff; padding: 16px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 4px solid #94a3b8; }}
        .card.total {{ border-color: #3b82f6; }}
        .card.pass {{ border-color: #10b981; }}
        .card.fail {{ border-color: #ef4444; }}
        .card.obs {{ border-color: #f59e0b; }}
        .card.skip {{ border-color: #6b7280; }}
        .card-val {{ font-size: 28px; font-weight: bold; margin-top: 4px; }}
        .card-lbl {{ font-size: 13px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }}
        .table-wrap {{ background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }}
        th, td {{ padding: 12px 16px; border-bottom: 1px solid #e2e8f0; }}
        th {{ background: #f1f5f9; font-weight: 600; color: #475569; }}
        tr:hover {{ background: #f8fafc; }}
        .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .badge-pass {{ background: #d1fae5; color: #065f46; }}
        .badge-fail {{ background: #fee2e2; color: #991b1b; }}
        .badge-obs {{ background: #fef3c7; color: #92400e; }}
        .badge-skip {{ background: #f3f4f6; color: #374151; }}
        .screenshot-btn {{ font-size: 12px; color: #2563eb; text-decoration: none; padding: 3px 8px; border: 1px solid #bfdbfe; border-radius: 4px; background: #eff6ff; }}
        .screenshot-btn:hover {{ background: #dbeafe; }}
        .text-muted {{ color: #94a3b8; font-size: 12px; }}
        code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 13px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{project_name}</h1>
        <div class="timestamp">Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
    </div>
    <div class="metrics-grid">
        <div class="card total"><div class="card-lbl">Total Tests</div><div class="card-val">{total}</div></div>
        <div class="card pass"><div class="card-lbl">Passed</div><div class="card-val">{passed}</div></div>
        <div class="card fail"><div class="card-lbl">Failed</div><div class="card-val">{failed}</div></div>
        <div class="card obs"><div class="card-lbl">Observations</div><div class="card-val">{observed}</div></div>
        <div class="card skip"><div class="card-lbl">Skipped</div><div class="card-val">{skipped}</div></div>
    </div>
    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Field</th>
                    <th>Rule</th>
                    <th>Test Input</th>
                    <th>Status</th>
                    <th>Actual Outcome</th>
                    <th>Screenshot</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"HTML summary generated at: {file_path}")
        return file_path


def html_escape(text: str) -> str:
    """Escapes HTML special characters for report rendering."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
