#!/usr/bin/env python3
"""Create Feishu cloud documents from a title and plain/Markdown-like text."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def env(name: str, required: bool = True, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise SystemExit(f"Missing required setting: {name}")
    return value or ""


def debug(message: str) -> None:
    if os.environ.get("FEISHU_DOC_DEBUG"):
        print(message, file=sys.stderr)


def request_json(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Feishu API HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Network error calling Feishu API: {exc}") from exc

    result = json.loads(body)
    code = result.get("code", 0)
    if code not in (0, None):
        raise SystemExit(f"Feishu API error {code}: {result.get('msg') or body}")
    return result


def tenant_access_token(base_url: str, app_id: str, app_secret: str) -> str:
    result = request_json(
        "POST",
        f"{base_url}/open-apis/auth/v3/tenant_access_token/internal",
        payload={"app_id": app_id, "app_secret": app_secret},
    )
    token = result.get("tenant_access_token")
    if not token:
        raise SystemExit(f"Feishu did not return tenant_access_token: {result}")
    return token


def create_document(base_url: str, token: str, folder_token: str, title: str) -> dict[str, Any]:
    result = request_json(
        "POST",
        f"{base_url}/open-apis/docx/v1/documents",
        token=token,
        payload={"folder_token": folder_token, "title": title},
    )
    document = result.get("data", {}).get("document", {})
    document_id = document.get("document_id")
    if not document_id:
        raise SystemExit(f"Feishu did not return document_id: {result}")
    return document


MAX_NATIVE_TABLE_CELLS = 50
MAX_NATIVE_TABLE_COLUMNS = 9
MAX_NATIVE_TABLE_ROWS = 9


def plain_text_from_markdown(text: str) -> str:
    """Remove Markdown markers when a plain string is needed."""
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1（\2）", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"<br\s*/?>", "；", text, flags=re.IGNORECASE)
    return text.strip()


def text_run(content: str, *, bold: bool = False, inline_code: bool = False) -> dict[str, Any]:
    run: dict[str, Any] = {"content": content}
    style = {}
    if bold:
        style["bold"] = True
    if inline_code:
        style["inline_code"] = True
    run["text_element_style"] = style
    return {"text_run": run}


def text_elements_from_markdown(text: str, *, force_bold: bool = False) -> list[dict[str, Any]]:
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1（\2）", text)
    text = re.sub(r"<br\s*/?>", "；", text, flags=re.IGNORECASE)
    elements: list[dict[str, Any]] = []
    pattern = re.compile(r"(\*\*.+?\*\*|__.+?__|`[^`]+`)")
    position = 0
    for match in pattern.finditer(text):
        if match.start() > position:
            elements.append(text_run(text[position : match.start()], bold=force_bold))
        token = match.group(0)
        if token.startswith("`"):
            elements.append(text_run(token[1:-1], bold=force_bold, inline_code=True))
        else:
            elements.append(text_run(token[2:-2], bold=True))
        position = match.end()
    if position < len(text):
        elements.append(text_run(text[position:], bold=force_bold))
    if not elements:
        elements.append(text_run(" ", bold=force_bold))
    return elements


def text_block(
    block_type: int,
    key: str,
    content: str,
    *,
    bold: bool = False,
    parse_markdown: bool = True,
) -> dict[str, Any]:
    return {
        "block_type": block_type,
        key: {
            "elements": (
                text_elements_from_markdown(content, force_bold=bold)
                if parse_markdown
                else [text_run(content, bold=bold)]
            ),
            "style": {"align": 1, "folded": False},
        },
    }


def normalize_inline_markdown(text: str) -> str:
    """Remove common Markdown markers that look noisy in Feishu docs."""
    return plain_text_from_markdown(text)


def looks_like_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def split_table_row(line: str) -> list[str]:
    return [plain_text_from_markdown(cell) for cell in line.strip().strip("|").split("|")]


def is_table_separator(row: list[str]) -> bool:
    if not row:
        return False
    return all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in row)


def table_row_text(headers: list[str], row: list[str]) -> str:
    cells = row + [""] * max(0, len(headers) - len(row))
    pairs = [
        (header.strip() or f"列{index + 1}", cell.strip())
        for index, (header, cell) in enumerate(zip(headers, cells))
        if cell.strip()
    ]
    if len(pairs) == 2 and pairs[0][0] in {"项目", "指标", "事项", "维度", "字段"}:
        return f"{pairs[0][1]}：{pairs[1][1]}"
    return "；".join(f"{header}：{cell}" for header, cell in pairs)


def blocks_from_table_lines(table_lines: list[str]) -> list[dict[str, Any]]:
    table_item = table_item_from_lines(table_lines)
    if table_item:
        if table_item.get("kind") == "table_group":
            blocks = []
            for table in table_item["tables"]:
                blocks.extend(fallback_blocks_from_table_rows(table["rows"]))
            return blocks
        return fallback_blocks_from_table_rows(table_item["rows"])
    return []


def fallback_blocks_from_table_rows(rows: list[list[str]]) -> list[dict[str, Any]]:
    if len(rows) < 2:
        return []
    headers = rows[0]
    data_rows = rows[1:]
    blocks = []
    for row in data_rows:
        content = table_row_text(headers, row)
        if content:
            blocks.append(text_block(12, "bullet", content))
    return blocks


def table_item_from_lines(table_lines: list[str]) -> dict[str, Any] | None:
    rows = [split_table_row(line) for line in table_lines]
    if len(rows) < 2 or not is_table_separator(rows[1]):
        return None

    headers = rows[0]
    data_rows = [row for row in rows[2:] if not is_table_separator(row)]
    if not headers or not data_rows:
        return None

    max_cols = max(len(row) for row in [headers, *data_rows])
    normalized_rows = [
        row + [""] * max(0, max_cols - len(row))
        for row in [headers, *data_rows]
    ]
    if max_cols > MAX_NATIVE_TABLE_COLUMNS:
        return {"kind": "fallback_table", "rows": normalized_rows}
    if len(normalized_rows) > MAX_NATIVE_TABLE_ROWS or len(normalized_rows) * max_cols > MAX_NATIVE_TABLE_CELLS:
        max_rows_per_table = min(MAX_NATIVE_TABLE_ROWS, max(2, MAX_NATIVE_TABLE_CELLS // max_cols))
        data_rows_per_table = max_rows_per_table - 1
        tables = []
        for start in range(0, len(data_rows), data_rows_per_table):
            chunk = data_rows[start : start + data_rows_per_table]
            chunk_rows = [
                row + [""] * max(0, max_cols - len(row))
                for row in [headers, *chunk]
            ]
            tables.append({"kind": "table", "rows": chunk_rows})
        return {"kind": "table_group", "tables": tables}
    return {"kind": "table", "rows": normalized_rows}


def estimate_column_widths(rows: list[list[str]]) -> list[int]:
    widths = []
    column_count = max(len(row) for row in rows)
    for column in range(column_count):
        max_len = max(len(row[column]) if column < len(row) else 0 for row in rows)
        widths.append(max(90, min(360, max_len * 10 + 32)))
    return widths


def looks_like_subheading(stripped: str) -> bool:
    return (
        stripped.endswith(("：", ":"))
        and len(stripped) <= 32
        and not stripped.startswith(("http://", "https://"))
    )


def document_items_from_markdownish(content: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    in_code = False
    code_lines: list[str] = []
    lines = content.splitlines()
    index = 0

    while index < len(lines):
        raw_line = lines[index]
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                items.append(text_block(14, "code", "\n".join(code_lines), parse_markdown=False))
                code_lines = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue

        if in_code:
            code_lines.append(line)
            index += 1
            continue

        if looks_like_table_line(line):
            end = index
            table_lines = []
            while end < len(lines) and looks_like_table_line(lines[end]):
                table_lines.append(lines[end])
                end += 1
            table_item = table_item_from_lines(table_lines)
            if table_item:
                if table_item.get("kind") == "table_group":
                    items.extend(table_item["tables"])
                else:
                    items.append(table_item)
                index = end
                continue

        if not stripped:
            index += 1
            continue
        if stripped in {"---", "***", "___"}:
            items.append({"block_type": 22, "divider": {}})
            index += 1
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            level = len(heading.group(1))
            block_type = 2 + level
            items.append(text_block(block_type, f"heading{level}", plain_text_from_markdown(heading.group(2))))
            index += 1
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            items.append(text_block(12, "bullet", stripped[2:].strip()))
            index += 1
            continue

        ordered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if ordered:
            items.append(text_block(13, "ordered", ordered.group(1)))
            index += 1
            continue

        if stripped.startswith("> "):
            items.append(text_block(15, "quote", stripped[2:].strip()))
            index += 1
            continue

        if looks_like_subheading(stripped):
            items.append(text_block(5, "heading3", plain_text_from_markdown(stripped.rstrip("：:"))))
            index += 1
            continue

        items.append(text_block(2, "text", line))
        index += 1

    if in_code and code_lines:
        items.append(text_block(14, "code", "\n".join(code_lines), parse_markdown=False))

    return items


def blocks_from_markdownish(content: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for item in document_items_from_markdownish(content):
        if item.get("kind") in {"table", "fallback_table"}:
            blocks.extend(fallback_blocks_from_table_rows(item["rows"]))
        else:
            blocks.append(item)
    return blocks


def append_blocks_to_parent(
    base_url: str,
    token: str,
    document_id: str,
    parent_id: str,
    blocks: list[dict[str, Any]],
    index: int = -1,
) -> dict[str, Any] | None:
    if not blocks:
        return None
    endpoint = (
        f"{base_url}/open-apis/docx/v1/documents/{document_id}/blocks/{parent_id}/children"
        "?document_revision_id=-1"
    )
    result = None
    for start in range(0, len(blocks), 50):
        result = request_json(
            "POST",
            endpoint,
            token=token,
            payload={"index": index, "children": blocks[start : start + 50]},
        )
        time.sleep(0.35)
    return result


def append_blocks(base_url: str, token: str, document_id: str, blocks: list[dict[str, Any]]) -> None:
    append_blocks_to_parent(base_url, token, document_id, document_id, blocks)


def append_table(base_url: str, token: str, document_id: str, rows: list[list[str]]) -> None:
    row_size = len(rows)
    column_size = max(len(row) for row in rows)
    debug(f"create table {row_size}x{column_size}")
    table_block = {
        "block_type": 31,
        "table": {
            "property": {
                "row_size": row_size,
                "column_size": column_size,
            }
        },
    }
    result = append_blocks_to_parent(base_url, token, document_id, document_id, [table_block])
    children = (result or {}).get("data", {}).get("children", [])
    cells = children[0].get("table", {}).get("cells", []) if children else []
    if len(cells) < row_size * column_size:
        raise SystemExit(f"Feishu did not return enough table cells: {result}")

    for row_index, row in enumerate(rows):
        for column_index in range(column_size):
            content = row[column_index] if column_index < len(row) else ""
            if not content:
                continue
            debug(f"write cell r{row_index}c{column_index} len={len(content)}")
            cell_id = cells[row_index * column_size + column_index]
            append_blocks_to_parent(
                base_url,
                token,
                document_id,
                cell_id,
                [text_block(2, "text", content, bold=(row_index == 0))],
                index=0,
            )


def append_items(base_url: str, token: str, document_id: str, items: list[dict[str, Any]]) -> None:
    pending_blocks: list[dict[str, Any]] = []

    def flush_pending() -> None:
        nonlocal pending_blocks
        if pending_blocks:
            append_blocks(base_url, token, document_id, pending_blocks)
            pending_blocks = []

    for item in items:
        kind = item.get("kind")
        if kind == "table":
            flush_pending()
            append_table(base_url, token, document_id, item["rows"])
        elif kind == "fallback_table":
            pending_blocks.extend(fallback_blocks_from_table_rows(item["rows"]))
        else:
            pending_blocks.append(item)

    flush_pending()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a Feishu cloud document.")
    parser.add_argument("--title", required=True, help="Document title")
    parser.add_argument("--content", default="", help="Document content")
    parser.add_argument("--content-file", help="Read document content from a UTF-8 file")
    parser.add_argument("--stdin", action="store_true", help="Read document content from stdin")
    return parser.parse_args()


def main() -> None:
    for dotenv in (
        Path.cwd() / ".env",
        Path.cwd() / ".env.local",
        Path.cwd() / "feishu.env",
        Path.cwd() / "feishu.env.md",
        SKILL_DIR / ".env",
        SKILL_DIR / ".env.local",
        SKILL_DIR / "feishu.env",
        SKILL_DIR / "feishu.env.md",
    ):
        load_dotenv(dotenv)
    args = parse_args()

    content = args.content
    if args.content_file:
        content = Path(args.content_file).read_text(encoding="utf-8")
    if args.stdin:
        content = sys.stdin.read()

    base_url = env("FEISHU_BASE_URL", default="https://open.feishu.cn").rstrip("/")
    app_id = env("FEISHU_APP_ID")
    app_secret = env("FEISHU_APP_SECRET")
    folder_token = env("FEISHU_FOLDER_TOKEN")
    doc_host = env("FEISHU_DOC_HOST", required=False).rstrip("/")

    token = tenant_access_token(base_url, app_id, app_secret)
    document = create_document(base_url, token, folder_token, args.title)
    document_id = document["document_id"]
    append_items(base_url, token, document_id, document_items_from_markdownish(content))

    url = document.get("url")
    if not url and doc_host:
        url = f"{doc_host}/docx/{document_id}"

    print(json.dumps({"document_id": document_id, "url": url}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
