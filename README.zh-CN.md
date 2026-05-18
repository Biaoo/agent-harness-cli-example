# Agent Harness CLI Research Workflow Example

[English](README.md) | [简体中文](README.zh-CN.md)

本仓库是 [Biaoo/agent-harness-cli](https://github.com/Biaoo/agent-harness-cli) 的可运行示例，演示 workflow controller 模式如何驱动一个 research 任务，通过显式状态、checks、路由决策和 Codex Stop hook continuation 完成长流程控制。

这个仓库现在只保留 research workflow 示例。

## Workflow 目标

workflow 将一个粗略的 research idea 推进成按主题隔离的完整研究交付包：

```text
Research Context
Idea Intake
World Knowledge Map
Insight Direction Discovery
Research Design
Data Acquisition
Analysis
Insight Verification
Results Architecture
Figures + Manuscript
Reader / Evidence Audit
Submission Package
Final Quality Review
Research Complete
```

核心路由规则是：

```text
要么产生主文级 insight，要么回炉修复。
不走 SI-only 消化、不做降级发表、不把弱结果包装成 fallback paper。
```

## Harness Engineering Flow

1. Codex 先创建 `research/context.json`，记录本次研究主题元数据。
2. Codex 修改 `research/<topic_slug>/` 下当前 active 节点要求的研究 artifact。
3. 项目级 Stop hook 运行 `agent-harness step`。
4. workflow controller 验收当前 active node 的 artifact 结构和 `Status:` 值。
5. 节点未通过时，hook block，并告诉 Codex 需要修复什么。
6. 节点通过且只有一个 transition 匹配时，workflow state 自动推进，并用 block 提示下一阶段。
7. 多个 transition 同时匹配时，state 进入 `choosing`；Codex 需要查看 `agent-harness options` 并运行 `agent-harness choose`。
8. 只有进入 terminal workflow node 后，Stop hook 才不再 block。

## 试运行

在本目录启动 Codex session，并输入：

```text
Research this idea with the research workflow:

<你的研究想法>
```

`AGENTS.md` 已经包含项目级 workflow 操作规则，所以用户不需要在提示词里重复粘贴 workflow 协议。

第一步 Codex 会创建：

```json
{
  "topic_title": "可读的研究主题",
  "topic_slug": "lower-kebab-topic-slug",
  "research_dir": "research/lower-kebab-topic-slug"
}
```

workflow 中后续 artifact path 使用 `research/{topic_slug}/...`；check 脚本会从
`research/context.json` 展开这个占位符。

当 Codex 准备停止时，`.codex/hooks.json` 会运行：

```bash
bash "$(git rev-parse --show-toplevel)/.codex/hooks/run-agent-harness-check.sh"
```

该脚本调用：

```bash
agent-harness step --task workflows/research.json --report-id research-latest --hook-json
```

hook 会优先使用已安装的 `agent-harness`，否则回退到：

```bash
uvx --from agent-harness-cli==0.1.2 agent-harness
```

## 常用命令

验证 workflow：

```bash
agent-harness validate-workflow --task workflows/research.json
```

执行一次 workflow step：

```bash
agent-harness step --task workflows/research.json --hook-json
```

查看 state：

```bash
agent-harness status --state .agent-harness/research-state.json
```

查看并选择 model-choice transition：

```bash
agent-harness options --state .agent-harness/research-state.json
agent-harness choose <transition-id> --state .agent-harness/research-state.json --reason "why this route is appropriate"
```

查看最新 workflow report：

```bash
agent-harness view research-latest --report-dir reports/research --failed-only
```

## 验收面

workflow 使用四层 gate：

| 层级 | 目的 | 实现 |
| --- | --- | --- |
| Structure | 确认 active artifact 存在、必需标题齐全，并达到最低内容量。 | `check_markdown_sections.py` |
| Stage semantics | 判断阶段是否真的完成，`Status:` 是否有证据支撑。 | `check_research_checklist.py` + `checklists/research/stage/*.md` |
| Deep research quality | 检查研究对象建模、真实信息增量、方法-claim 匹配、数据来源可复现性、证据边界、反解释、图表质量、出版式主文和主文承载力。 | `check_research_checklist.py` + `checklists/research/deep/*.md` |
| Evidence controls | 强制 source evidence pack、data fitness matrix、claim-evidence trace、真实生成的图表资产、读者可解析的引用/References、claim 强度校准、引用链完整性、overclaim review 和最终质量报告。 | `check_research_csv_contract.py`, `check_research_trace_links.py`, `check_research_figure_assets.py`, `check_research_manuscript_publication_style.py`, 专用 checklists |

workflow 使用这些 check 脚本：

| Check | 作用 | 要求来源 |
| --- | --- | --- |
| `check_research_context.py` | 检查 `research/context.json` 和对应主题目录。 | `research/context.json` |
| `check_markdown_sections.py` | 检查当前 Markdown artifact 是否存在、是否包含必需标题、内容是否达到最低信息量。 | `workflows/research.json` |
| `check_research_status.py` | 读取 artifact 中的 `Status: <value>`，并把它作为 `metadata.status` 提供给 transition 条件。 | `workflows/research.json` |
| `check_research_csv_contract.py` | 检查 CSV 证据控制 artifact 的字段、行数、非空单元和枚举值。 | `workflows/research.json` |
| `check_research_trace_links.py` | 检查 claim trace 是否引用真实存在的 source IDs 和 data-fitness claim IDs。 | `source_evidence_pack.csv`, `claim_evidence_trace.csv`, `data_fitness_matrix.csv` |
| `check_research_figure_assets.py` | 检查生成的图表资产是否存在于主题 figures 目录，并被 manuscript 引用。 | `figure_manifest.csv`, `manuscript.md` |
| `check_research_manuscript_form.py` | 检查 manuscript 是否是论文式展开，而不是 memo bullets 或 Figure Plan。 | `manuscript.md` |
| `check_research_manuscript_publication_style.py` | 检查主文是否泄露 harness 内部信息，并要求出版式引用、References 和命名结果小节。 | `manuscript.md` |
| `check_research_checklist.py` | 调用本地 `codex exec` 填写 Markdown checklist，再把 checked/unchecked items 解析成 harness JSON。 | `checklists/research/` |

workflow graph 负责路由。结构和状态检查是确定性的。Checklist checks 是语义质量 gate；只有做 deterministic-only 调试时才设置 `AGENT_HARNESS_ENABLE_LLM=0`。

`research/context.json` 是运行时路径解析器。同一个 checkout 可以按不同
`topic_slug` 运行多个主题，产物隔离在 `research/<topic_slug>/` 下。

## 项目结构

```text
AGENTS.md                            Codex 项目级操作说明。
.agents/
  skills/research-workflow-runner/   项目级 research workflow skill。
.codex/
  hooks.json                         项目级 Stop hook 配置。
  hooks/run-agent-harness-check.sh   workflow Stop hook 入口。
checks/
  check_research_context.py          运行时主题 context 检查。
  check_markdown_sections.py         Markdown artifact 结构检查。
  check_research_status.py           workflow 路由状态检查。
  check_research_csv_contract.py     CSV 证据控制合同检查。
  check_research_trace_links.py      claim/source/data 链接完整性检查。
  check_research_figure_assets.py    生成图表资产检查。
  check_research_manuscript_form.py  论文式正文形态检查。
  check_research_manuscript_publication_style.py
                                      读者可见主文风格检查。
  check_research_checklist.py        Markdown checklist 语义/深层质量 gate。
  local_codex_judge.py               本地 Codex checklist judge helper。
  research_paths.py                  共享主题路径解析器。
checklists/
  research/stage/                    阶段完成度 checklist 模板。
  research/deep/                     深层研究质量 checklist 模板。
workflows/
  research.json                      研究 workflow graph。
research/
  README.md                          artifact 契约和允许状态。
  context.json                       Codex 运行时生成的主题 context。
  <topic_slug>/                      按主题隔离的研究产物。
pyproject.toml                       示例包元数据。
```

运行时生成文件会被忽略：

```text
.agent-harness/
reports/
research/context.json
research/<topic_slug>/
```

## 设计说明

- 示例把领域逻辑留在 workspace：workflow spec、artifact contract、checklists 和 check scripts。
- CLI 负责状态控制、验收、报告、transition 应用和 hook JSON。
- Stop hook 在 workflow 到达 `research_complete` 之前始终返回 `decision: "block"`。
- check 脚本只使用 Python 标准库。语义/深层质量 gate 需要本地 Codex CLI，因为会调用 `codex exec`。
