---
name: feishu-online-docs
description: Create Feishu/Lark online cloud documents from conversation content or generated local reports using Feishu OpenAPI. Use when the user asks Codex to create a 飞书云文档/在线文档/Docs document, save output into a Feishu folder, return a Feishu document link, or publish another skill's generated report to Feishu Docs.
---

# Feishu Online Docs

## Purpose

Create Feishu online documents from a title and body content, then return the document ID and link. Prefer using the bundled script for deterministic API calls.

## Safety

- Never store or repeat `app_secret` in chat output.
- Prefer credentials in a local `feishu.env` or `feishu.env.md` file in the active workspace. Use `.env` only when the environment allows dot-prefixed files.
- If the user pasted a secret in chat, complete the requested setup but recommend rotating the secret after testing.
- Do not create a document until the title, target folder, and content are clear enough.

## Required Inputs

Use existing environment variables when available; otherwise ask for the missing non-secret information.

- `FEISHU_APP_ID`: Feishu app ID, for example `cli_xxx`
- `FEISHU_APP_SECRET`: Feishu app secret, stored locally
- `FEISHU_FOLDER_TOKEN`: target folder token from `/drive/folder/<token>`
- `FEISHU_DOC_HOST`: tenant host such as `https://haidilao.feishu.cn`
- `FEISHU_BASE_URL`: optional, defaults to `https://open.feishu.cn`

## Workflow

1. Resolve the target folder.
   - If the user gives a folder URL, extract the token after `/drive/folder/`.
   - Extract the tenant host from the same URL for `FEISHU_DOC_HOST`.
2. Prepare content.
   - Preserve Chinese PMO/report wording unless the user asks for rewriting.
   - Prefer writing generated long content to a temporary Markdown file and passing `--content-file`.
   - The script supports simple Markdown-like blocks: headings, bullets, numbered lists, quotes, dividers, code fences, and paragraphs.
   - Markdown tables are automatically converted into native Feishu table blocks when possible; larger tables are split into multiple native tables to stay within Feishu's per-table creation limit. Very wide tables fall back to clean bullet rows.
   - Keep individual generated tables at 9 rows / 50 cells or below; the script repeats headers when splitting a source table.
   - Common inline Markdown markers such as bold and inline code are converted into Feishu text styling where supported.
   - Short lines ending in `：` are treated as subsection headings to keep report text more structured.
3. Create the document.
   - Run `scripts/create_feishu_doc.py` from this skill.
   - The script appends blocks with `document_revision_id=-1`, which is required for reliable native table creation.
   - If network access is blocked by sandboxing, request escalation for the command.
4. Return the result.
   - Include the Feishu document link when available.
   - If only `document_id` is returned, provide it and explain that `FEISHU_DOC_HOST` is needed for a full link.

## Script Usage

From a workspace containing `feishu.env`, `feishu.env.md`, or `.env`:

```sh
python3 /Users/kk/.codex/skills/feishu-online-docs/scripts/create_feishu_doc.py --title "项目纪要" --content-file report.md
```

Inline content:

```sh
python3 /Users/kk/.codex/skills/feishu-online-docs/scripts/create_feishu_doc.py --title "周报" --content "# 本周进展

- 完成事项 A
- 风险事项 B"
```

The script loads `.env`, `.env.local`, `feishu.env`, and `feishu.env.md` from the current workspace first, then from the skill directory if present.

## References

Read `references/feishu-docs-openapi.md` when checking endpoints, permissions, configuration, or troubleshooting API errors.
