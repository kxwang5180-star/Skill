# Feishu Docs OpenAPI Reference

## Endpoints

- Tenant access token: `POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`
- Create document: `POST https://open.feishu.cn/open-apis/docx/v1/documents`
- Append children blocks: `POST https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/children`

The created document's `document_id` is also the root block ID for appending children.

## Minimum Configuration

Create a local `feishu.env` or `feishu.env.md` in the active workspace. Use `.env` only when dot-prefixed filenames are allowed:

```dotenv
FEISHU_APP_ID=cli_aa8855dd366a9cd1
FEISHU_APP_SECRET=replace_locally
FEISHU_FOLDER_TOKEN=KYSyfIyARlkOoId4oUqcSlqTnCe
FEISHU_BASE_URL=https://open.feishu.cn
FEISHU_DOC_HOST=https://haidilao.feishu.cn
```

Do not commit local env files or place secrets in skill files.

## Folder Token

From a Feishu folder URL:

```text
https://tenant.feishu.cn/drive/folder/KYSyfIyARlkOoId4oUqcSlqTnCe
```

Use:

```text
KYSyfIyARlkOoId4oUqcSlqTnCe
```

## Permissions Checklist

- The app has document creation/editing permissions for新版文档.
- The app is installed/enabled for the tenant.
- The target folder allows the app or application identity to create documents.
- The app credentials are for the same tenant as the folder URL.

## Common Errors

- Missing `tenant_access_token`: check `FEISHU_APP_ID` and `FEISHU_APP_SECRET`.
- Permission error when creating document: check app scopes and folder authorization.
- Document created but no full link: set `FEISHU_DOC_HOST`.
- Network/DNS error in Codex: rerun the command with network escalation.
