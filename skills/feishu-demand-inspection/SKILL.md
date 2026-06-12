---
name: feishu-demand-inspection
description: Generate stable PMO inspection reports for Feishu Project demand work items, especially 信息科技部 space / 需求(story) work items. Use when the user asks for 信息科技部需求周报/月报/巡查/项目巡检/PMO报告, wants recurring weekly or monthly Feishu MCP reporting, wants the report published to Feishu online documents, or asks to analyze demand flow, stage bottlenecks, P0/P1 governance, node risks, schedule/resource load, delivery quality, and PMO intervention items from Feishu project data.
---

# Feishu Demand Inspection

## Purpose

Generate PMO-oriented inspection reports from Feishu Project data using a fixed scope, fixed metrics, fixed thresholds, and fixed output structure. Prefer exception management over activity listing: highlight delivery risk, stage bottlenecks, resource mismatch, and items requiring PMO coordination.

Default domain:

- Space: `信息科技部`
- Project key: `62a43e1881329ed76a597141`
- Simple name: `hdltech`
- Work item type: `story` / `需求`
- Timezone: `Asia/Shanghai`

## Resources

Read `references/inspection-template.md` when preparing a full report, updating the template, or the user asks for the template content. Keep `SKILL.md` as the workflow guide and the reference file as the reusable report structure.

Use `$feishu-online-docs` when the user asks to create/publish/save the inspection report as a 飞书云文档/在线文档, or when Feishu Docs publication is part of the requested output.

## Workflow

1. Confirm or infer report period.
   - Weekly: use natural week Monday-Sunday unless the user specifies dates.
   - Monthly: use calendar month unless the user specifies dates.
   - If the current date is inside the period, mark the report as "截至 YYYY-MM-DD HH:mm".
2. Query Feishu work item data.
   - Use `search_by_mql` for demand work item metrics and lists.
   - Use explicit fields; never use `SELECT *`.
   - Use paging when the user asks for full lists or when exact distributions require more than the first page.
3. Query node risk and plan integrity.
   - Use `risk_label()` to retrieve node schedule/risk labels.
   - Treat `risk_label() is not null` as a broad "node label / schedule prompt" scope.
   - For strict PMO risk, keep labels containing `延期`, `今日到期`, or `排期信息不全`; exclude `正常`.
   - When a risk label points to a node, attribute the risk to the delayed/due/incomplete node owner, not the demand-level current owner.
   - Use `get_node_detail` for sampled/high-priority risks to resolve node owners, role owners, assignee schedules, and sub-task owners. If a node has multiple owners, show the role or sub-task owner when it identifies the specific delayed work; otherwise list all node owners and mark the primary owner only when the data supports it.
   - Use the demand-level `current_status_operator` only as a fallback when node owner details are unavailable, and label it explicitly as "需求当前负责人".
4. Query schedule/resource load when requested.
   - Use `list_schedule` for specific users or known complete user lists.
   - Do not extrapolate all-person workload from an incomplete team/user list.
   - If the visible Feishu page has more people than available via MCP queries, state the personnel-scope limitation and ask for/export the complete user list.
5. Classify exceptions.
   - Prioritize P0/P1, overdue nodes, today-due nodes, incomplete schedules, no owner, high-priority without schedule, stage aging, and overloaded people.
   - Turn raw findings into PMO actions: decision needed, owner, deadline, impact.
6. Fill the report.
   - Use the structure in `references/inspection-template.md`.
   - Keep tables concise. Show top risks and PMO intervention items instead of dumping every work item.
   - Include exact dates and the data-as-of time.
   - Default output is a document artifact, not only inline chat. Save a Markdown source copy under `/Users/kk/Documents` unless the user specifies another path.
   - Prefer Markdown (`.md`) for editable source and Word (`.docx`) when the user asks for an office document.
   - For Feishu online output, first generate the final Markdown report locally, then invoke `$feishu-online-docs` to create the Feishu document from that file and return its link. The online-docs skill converts Markdown tables into native Feishu tables, splits larger tables to stay within Feishu limits, normalizes very wide tables into clean bullet rows, and preserves supported inline styling. If publication fails, keep the local report path and summarize the Feishu API error without exposing secrets.
7. Compare with history when available.
   - If prior reports exist, compute week-over-week or month-over-month change.
   - If no prior baseline exists, mark comparison columns as "暂无基线".

## Core Metrics

Always try to produce these metrics:

- Updated demand count in period
- New demand count in period
- Completed/closed demand count in period
- Net demand growth: new minus completed
- Active backlog / unclosed demand count when feasible
- P0/P1 demand count
- P0/P1 without schedule count
- Overdue demand count
- Today-due demand count
- Due-this-period demand count
- Incomplete-schedule demand count
- No-owner demand count
- Long-stagnant demand count
- Resource overload count when a complete people scope is available

## Recommended MQL Patterns

Use these as patterns, adapting dates and fields as needed.

Updated demands:

```sql
SELECT `work_item_id`, `name`, `work_item_status`, `current_status_operator`, `priority`, `start_time`, `updated_at`
FROM `信息科技部`.`需求`
WHERE `updated_at` between 'YYYY-MM-DD' and 'YYYY-MM-DD'
ORDER BY `updated_at` DESC
```

New demands:

```sql
SELECT `work_item_id`, `name`, `work_item_status`, `current_status_operator`, `priority`, `start_time`
FROM `信息科技部`.`需求`
WHERE `start_time` between 'YYYY-MM-DD' and 'YYYY-MM-DD'
ORDER BY `start_time` DESC
```

Completed demands:

```sql
SELECT `work_item_id`, `name`, `work_item_status`, `current_status_operator`, `priority`, `updated_at`
FROM `信息科技部`.`需求`
WHERE `updated_at` between 'YYYY-MM-DD' and 'YYYY-MM-DD'
AND `work_item_status` in ('已结束', '已终止')
ORDER BY `updated_at` DESC
```

High-priority demands:

```sql
SELECT `work_item_id`, `name`, `work_item_status`, `current_status_operator`, `priority`, `updated_at`
FROM `信息科技部`.`需求`
WHERE `updated_at` between 'YYYY-MM-DD' and 'YYYY-MM-DD'
AND `priority` in ('P0', 'P1')
ORDER BY `updated_at` DESC
```

Node labels and strict risk candidates:

```sql
SELECT `work_item_id`, `name`, risk_label(), `current_status_operator`, `work_item_status`, `updated_at`
FROM `信息科技部`.`需求`
WHERE `updated_at` between 'YYYY-MM-DD' and 'YYYY-MM-DD'
AND risk_label() is not null
ORDER BY `updated_at` DESC
```

After retrieving rows, classify strict risks by labels containing `延期`, `今日到期`, or `排期信息不全`.

## PMO Thresholds

Default thresholds:

- 待确认需求: more than 3 days
- 待需求评审: more than 3 days
- 待产品评审: more than 5 days
- 待技术评审: more than 5 days
- 待排期 / 待排期确认: more than 5 days
- 测试中: more than 7 days or beyond planned end
- 待上线: more than 3 days
- 待验收: more than 5 days
- Severe overdue: P0/P1 overdue, or any demand overdue more than 7 days
- Long overdue: more than 20 days
- Weekly workload overload: more than 5 person-days is full, more than 6 person-days is overloaded
- Monthly workload overload: more than 100% capacity is overloaded, more than 120% is severe

## Output Guidance

Write in Chinese by default. Use a PMO management tone: concise, factual, and action-oriented.

Include:

- Data scope and exact period
- Executive summary
- Core metric table
- Demand flow and throughput
- Stage distribution and bottlenecks
- P0/P1 governance
- Node risks and plan integrity
- Resource and schedule risk, only when personnel scope is complete enough
- Quality risk, if related fields/data are available
- PMO intervention list
- Next-period actions
- Output document path or Feishu online document link

## Feishu Online Document Output

When publishing a巡查报告 to Feishu Docs:

1. Complete all data queries and report writing first.
2. Save the final report as Markdown.
3. Use `$feishu-online-docs` with the report title and Markdown file; rely on its Feishu-native table conversion and inline formatting cleanup.
4. Return both the local Markdown path and the Feishu online document link.
5. If credentials or folder settings are missing, ask only for the missing non-secret inputs and direct the user to store `FEISHU_APP_SECRET` locally, not in chat.

Avoid:

- Treating every `risk_label()` row as strict risk without parsing labels
- Reporting incomplete workforce coverage as full coverage
- Listing all work items when the PMO report only needs exceptions
- Hiding assumptions about period, scope, or missing data
- Mixing demand-level current owners with node-risk owners without labeling the difference

## Stable Prompts

Weekly:

```text
请使用 feishu-demand-inspection skill，按固定模板生成信息科技部需求工作项周度巡查报告。
周期：YYYY-MM-DD 至 YYYY-MM-DD
口径：自然周，统计截至当前时间
重点输出：核心指标、阶段分布、P0/P1治理、节点风险、人员排期、需PMO介入事项、下周动作。
```

Monthly:

```text
请使用 feishu-demand-inspection skill，按固定模板生成信息科技部需求工作项月度巡查报告。
周期：YYYY-MM-01 至 YYYY-MM-DD
口径：自然月
重点输出：月度趋势、需求吞吐、阶段瓶颈、P0/P1治理、资源负载、质量风险、需PMO介入事项、下月治理建议。
```

## Archiving

When the user asks to save the output, save reports under `/Users/kk/Documents` unless another path is specified.

Suggested filenames:

- Weekly: `YYYY-WW 信息科技部需求工作项项目巡查周报.md`
- Monthly: `YYYY-MM 信息科技部需求工作项项目巡查月报.md`
