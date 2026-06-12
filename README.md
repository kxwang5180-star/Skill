# Codex Skills

This repository stores reusable Codex skills created for Feishu/PMO workflows.

## Skills

- `skills/feishu-demand-inspection` - Generate PMO inspection reports for 信息科技部需求 work items.
- `skills/feishu-online-docs` - Publish Markdown/report content to Feishu online documents.
- `skills/feishu-online-sheets` - Publish CSV/XLSX data to fixed Feishu Sheets or Base/Bitable tables.

## Notes

- Secrets such as `FEISHU_APP_SECRET` must stay local and must not be committed.
- The Feishu publishing skills load credentials from `.env.local`, `.env`, `feishu.env`, or `feishu.env.md` in the active workspace.
- `feishu-demand-inspection` can call `feishu-online-docs` when a generated PMO report needs to be published as a Feishu document.
