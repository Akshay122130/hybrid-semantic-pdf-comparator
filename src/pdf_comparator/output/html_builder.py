"""HTML report builder for standalone visual document comparison reports."""

import html
from pathlib import Path
from typing import Dict, List, Union
from pdf_comparator.core.models import ComparisonResult, MatchResult, MatchStatus, SeverityLevel
from pdf_comparator.output.json_builder import JSONReportBuilder


class HTMLReportBuilder:
    """Builds a standalone, responsive XSS-safe HTML comparison report."""

    def __init__(self):
        self.json_builder = JSONReportBuilder()

    def _render_summary_card(self, label: str, count: int, card_class: str) -> str:
        return f"""
        <div class="stat-card {card_class}">
            <div class="stat-count">{count}</div>
            <div class="stat-label">{html.escape(label)}</div>
        </div>
        """

    def _render_structural_changes(self, struct_dict: dict) -> str:
        if not struct_dict or not struct_dict.get("has_structural_changes"):
            return ""

        changes: List[dict] = struct_dict.get("changes", [])
        if not changes:
            return ""

        rows_html = []
        for c in changes:
            c_type = html.escape(str(c.get("change_type", "")).upper().replace("_", " "))
            old_val = html.escape(str(c.get("old_value", "N/A"))) if c.get("old_value") is not None else "<span class='none-val'>None</span>"
            new_val = html.escape(str(c.get("new_value", "N/A"))) if c.get("new_value") is not None else "<span class='none-val'>None</span>"
            expl = html.escape(str(c.get("explanation", "")))

            rows_html.append(f"""
            <tr>
                <td><span class="badge type-badge">{c_type}</span></td>
                <td class="diff-val old-val">{old_val}</td>
                <td class="arrow">&rarr;</td>
                <td class="diff-val new-val">{new_val}</td>
                <td class="expl-col">{expl}</td>
            </tr>
            """)

        return f"""
        <div class="structural-box">
            <div class="sub-heading">Structural & Entity Modifications</div>
            <table class="struct-table">
                <thead>
                    <tr>
                        <th>Change Type</th>
                        <th>Old Value</th>
                        <th></th>
                        <th>New Value</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows_html)}
                </tbody>
            </table>
        </div>
        """

    def _render_match_card(self, idx: int, match: MatchResult) -> str:
        status_val = match.status.value.lower()
        severity_val = match.severity.value.lower()

        src_text = html.escape(match.source_chunk.original_text) if match.source_chunk else "<span class='empty-chunk'>[None - Added Content]</span>"
        tgt_text = html.escape(match.target_chunk.original_text) if match.target_chunk else "<span class='empty-chunk'>[None - Removed Content]</span>"

        src_meta = f"Page {match.source_chunk.page_num}" if match.source_chunk else "N/A"
        if match.source_chunk and match.source_chunk.section:
            src_meta += f" &bull; Section: {html.escape(match.source_chunk.section)}"

        tgt_meta = f"Page {match.target_chunk.page_num}" if match.target_chunk else "N/A"
        if match.target_chunk and match.target_chunk.section:
            tgt_meta += f" &bull; Section: {html.escape(match.target_chunk.section)}"

        explanation = html.escape(match.explanation)
        struct_html = self._render_structural_changes(match.structural_changes)

        sim_pct = f"{match.similarity_score * 100:.1f}%"
        conf_pct = f"{match.confidence * 100:.1f}%"

        card_id = f"match-card-{idx}"

        return f"""
        <div class="result-card status-{status_val} severity-{severity_val}" data-status="{status_val}" data-severity="{severity_val}" id="{card_id}">
            <div class="card-header" onclick="toggleCard('{card_id}')">
                <div class="header-left">
                    <span class="badge status-badge status-{status_val}">{status_val.upper()}</span>
                    <span class="badge severity-badge severity-{severity_val}">SEVERITY: {severity_val.upper()}</span>
                </div>
                <div class="header-right">
                    <span class="pill">Similarity: {sim_pct}</span>
                    <span class="pill">Confidence: {conf_pct}</span>
                    <span class="toggle-icon">&#9660;</span>
                </div>
            </div>
            <div class="card-body">
                <div class="explanation-box">
                    <strong>Rationale:</strong> {explanation}
                </div>
                {struct_html}
                <div class="side-by-side">
                    <div class="chunk-pane pane-source">
                        <div class="pane-title">Source Document A ({src_meta})</div>
                        <div class="chunk-content">{src_text}</div>
                    </div>
                    <div class="chunk-pane pane-target">
                        <div class="pane-title">Target Document B ({tgt_meta})</div>
                        <div class="chunk-content">{tgt_text}</div>
                    </div>
                </div>
            </div>
        </div>
        """

    def build(self, result: ComparisonResult) -> str:
        """Generate a complete standalone HTML document string from ComparisonResult."""
        summary = self.json_builder.calculate_summary(result)
        src_doc = html.escape(result.source_document)
        tgt_doc = html.escape(result.target_document)

        cards_html = []
        if not result.results:
            cards_html.append("<div class='no-diff-banner'>No differences or comparison results found.</div>")
        else:
            for idx, match in enumerate(result.results, 1):
                cards_html.append(self._render_match_card(idx, match))

        cards_body = "\n".join(cards_html)

        proc_sec = f"{result.stats.processing_time_ms / 1000.0:.2f}s"
        timestamp = html.escape(result.timestamp) if result.timestamp else "N/A"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Comparison Report - {src_doc} vs {tgt_doc}</title>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;

            --unchanged-color: #10b981;
            --modified-color: #3b82f6;
            --added-color: #06b6d4;
            --removed-color: #ef4444;

            --severity-high: #ef4444;
            --severity-medium: #f59e0b;
            --severity-low: #3b82f6;
            --severity-none: #64748b;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            padding: 24px;
            line-height: 1.5;
        }}

        .container {{ max-width: 1280px; margin: 0 auto; }}

        /* Header */
        .report-header {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }}
        .report-title {{ font-size: 24px; font-weight: 700; margin-bottom: 12px; color: #38bdf8; }}
        .header-meta {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; color: var(--text-muted); font-size: 14px; }}
        .meta-item strong {{ color: var(--text-main); }}

        /* Summary Stats Grid */
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 12px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }}
        .stat-count {{ font-size: 24px; font-weight: 700; }}
        .stat-label {{ font-size: 12px; color: var(--text-muted); text-transform: uppercase; margin-top: 4px; }}

        .card-unchanged .stat-count {{ color: var(--unchanged-color); }}
        .card-modified .stat-count {{ color: var(--modified-color); }}
        .card-added .stat-count {{ color: var(--added-color); }}
        .card-removed .stat-count {{ color: var(--removed-color); }}
        .card-high .stat-count {{ color: var(--severity-high); }}
        .card-medium .stat-count {{ color: var(--severity-medium); }}
        .card-low .stat-count {{ color: var(--severity-low); }}

        /* Controls */
        .control-bar {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            justify-content: space-between;
            align-items: center;
            background: var(--card-bg);
            padding: 16px;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            margin-bottom: 24px;
        }}
        .filter-buttons {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .filter-btn {{
            background: #334155;
            border: none;
            color: var(--text-main);
            padding: 6px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s;
        }}
        .filter-btn:hover, .filter-btn.active {{ background: #38bdf8; color: #0f172a; font-weight: 600; }}
        .search-input {{
            background: #0f172a;
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 8px 14px;
            border-radius: 6px;
            width: 260px;
            font-size: 14px;
        }}

        /* Result Cards */
        .results-container {{ display: flex; flex-direction: column; gap: 16px; }}
        .result-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            overflow: hidden;
            transition: border-color 0.2s;
        }}
        .result-card:hover {{ border-color: #64748b; }}

        .card-header {{
            padding: 14px 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(255, 255, 255, 0.02);
            cursor: pointer;
            user-select: none;
        }}
        .header-left, .header-right {{ display: flex; align-items: center; gap: 10px; }}

        .badge {{
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}
        .status-unchanged {{ background: rgba(16, 185, 129, 0.15); color: var(--unchanged-color); border: 1px solid var(--unchanged-color); }}
        .status-modified {{ background: rgba(59, 130, 246, 0.15); color: var(--modified-color); border: 1px solid var(--modified-color); }}
        .status-added {{ background: rgba(6, 182, 212, 0.15); color: var(--added-color); border: 1px solid var(--added-color); }}
        .status-removed {{ background: rgba(239, 68, 68, 0.15); color: var(--removed-color); border: 1px solid var(--removed-color); }}

        .severity-high {{ background: rgba(239, 68, 68, 0.2); color: var(--severity-high); }}
        .severity-medium {{ background: rgba(245, 158, 11, 0.2); color: var(--severity-medium); }}
        .severity-low {{ background: rgba(59, 130, 246, 0.2); color: var(--severity-low); }}
        .severity-none {{ background: rgba(100, 116, 139, 0.2); color: var(--severity-none); }}

        .pill {{
            background: #0f172a;
            border: 1px solid var(--border-color);
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 12px;
            color: var(--text-muted);
        }}

        .card-body {{ padding: 18px; border-top: 1px solid var(--border-color); display: block; }}
        .result-card.collapsed .card-body {{ display: none; }}

        .explanation-box {{
            background: #0f172a;
            border-left: 3px solid #38bdf8;
            padding: 10px 14px;
            border-radius: 4px;
            font-size: 13px;
            margin-bottom: 16px;
        }}

        /* Structural Changes Table */
        .structural-box {{ margin-bottom: 16px; }}
        .sub-heading {{ font-size: 13px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px; }}
        .struct-table {{ width: 100%; border-collapse: collapse; font-size: 13px; background: #0f172a; border-radius: 6px; overflow: hidden; }}
        .struct-table th, .struct-table td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border-color); }}
        .struct-table th {{ background: #1e293b; color: var(--text-muted); font-size: 11px; text-transform: uppercase; }}
        .diff-val {{ font-family: monospace; font-size: 13px; }}
        .old-val {{ color: #f87171; }}
        .new-val {{ color: #34d399; }}
        .arrow {{ color: var(--text-muted); width: 20px; }}
        .none-val {{ color: var(--text-muted); font-style: italic; }}

        /* Side by Side Diff */
        .side-by-side {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
        .chunk-pane {{
            background: #0f172a;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 12px;
        }}
        .pane-title {{ font-size: 12px; font-weight: 600; color: var(--text-muted); margin-bottom: 8px; border-bottom: 1px solid var(--border-color); padding-bottom: 6px; }}
        .chunk-content {{ font-size: 14px; white-space: pre-wrap; word-break: break-word; }}
        .empty-chunk {{ color: var(--text-muted); font-style: italic; }}

        .no-diff-banner {{
            background: var(--card-bg);
            border: 1px solid var(--unchanged-color);
            color: var(--unchanged-color);
            padding: 24px;
            text-align: center;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
        }}

        @media print {{
            body {{ background: #fff; color: #000; padding: 0; }}
            .control-bar {{ display: none; }}
            .result-card {{ page-break-inside: avoid; border: 1px solid #ccc; background: #fff; color: #000; margin-bottom: 12px; }}
            .chunk-pane, .explanation-box, .struct-table {{ background: #f8fafc; color: #000; border: 1px solid #ccc; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="report-header">
            <h1 class="report-title">Hybrid Semantic PDF Comparison Report</h1>
            <div class="header-meta">
                <div class="meta-item">Source Doc (A): <strong>{src_doc}</strong></div>
                <div class="meta-item">Target Doc (B): <strong>{tgt_doc}</strong></div>
                <div class="meta-item">Pages Processed: <strong>{result.stats.pages_processed}</strong></div>
                <div class="meta-item">Chunks Extracted: <strong>{result.stats.chunks_extracted}</strong></div>
                <div class="meta-item">Processing Time: <strong>{proc_sec}</strong></div>
                <div class="meta-item">Timestamp: <strong>{timestamp}</strong></div>
            </div>
        </header>

        <!-- Summary Grid -->
        <section class="summary-grid">
            {self._render_summary_card("Unchanged", summary["unchanged"], "card-unchanged")}
            {self._render_summary_card("Modified", summary["modified"], "card-modified")}
            {self._render_summary_card("Added", summary["added"], "card-added")}
            {self._render_summary_card("Removed", summary["removed"], "card-removed")}
            {self._render_summary_card("High Severity", summary["high"], "card-high")}
            {self._render_summary_card("Medium Severity", summary["medium"], "card-medium")}
            {self._render_summary_card("Low Severity", summary["low"], "card-low")}
        </section>

        <!-- Filter Controls -->
        <section class="control-bar">
            <div class="filter-buttons">
                <button class="filter-btn active" onclick="filterResults('all')">All ({len(result.results)})</button>
                <button class="filter-btn" onclick="filterResults('modified')">Modified ({summary['modified']})</button>
                <button class="filter-btn" onclick="filterResults('added')">Added ({summary['added']})</button>
                <button class="filter-btn" onclick="filterResults('removed')">Removed ({summary['removed']})</button>
                <button class="filter-btn" onclick="filterResults('unchanged')">Unchanged ({summary['unchanged']})</button>
                <button class="filter-btn" onclick="filterResults('high')">High Sev ({summary['high']})</button>
                <button class="filter-btn" onclick="filterResults('medium')">Med Sev ({summary['medium']})</button>
                <button class="filter-btn" onclick="filterResults('low')">Low Sev ({summary['low']})</button>
            </div>
            <input type="text" id="searchInput" class="search-input" placeholder="Search comparison text..." onkeyup="searchCards()">
        </section>

        <!-- Results List -->
        <main class="results-container" id="resultsContainer">
            {cards_body}
        </main>
    </div>

    <script>
        function toggleCard(cardId) {{
            const card = document.getElementById(cardId);
            if (card) {{
                card.classList.toggle('collapsed');
            }}
        }}

        function filterResults(filter) {{
            const cards = document.querySelectorAll('.result-card');
            const buttons = document.querySelectorAll('.filter-btn');

            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            cards.forEach(card => {{
                const status = card.getAttribute('data-status');
                const severity = card.getAttribute('data-severity');

                if (filter === 'all') {{
                    card.style.display = 'block';
                }} else if (filter === status || filter === severity) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}

        function searchCards() {{
            const query = document.getElementById('searchInput').value.toLowerCase();
            const cards = document.querySelectorAll('.result-card');

            cards.forEach(card => {{
                const text = card.innerText.toLowerCase();
                if (text.includes(query)) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>
"""

    def write(self, result: ComparisonResult, output_path: Union[str, Path]) -> Path:
        """Write HTML report to disk."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self.build(result)
        path.write_text(content, encoding="utf-8")
        return path
