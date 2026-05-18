# Agent Harness CLI Research Workflow Example

[English](README.md) | [简体中文](README.zh-CN.md)

本仓库是 [Biaoo/agent-harness-cli](https://github.com/Biaoo/agent-harness-cli) 的可运行示例，演示 workflow controller 模式如何驱动一个 AI-IE 研究任务，通过显式状态、checks、路由决策和 Codex Stop hook continuation 完成长流程控制。

这个仓库现在只保留 research workflow 示例。

## Workflow 目标

workflow 将一个粗略的 AI-IE research idea 推进成完整研究交付包：

```text
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
Research Complete
```

核心路由规则是：

```text
要么产生主文级 insight，要么回炉修复。
不走 SI-only 消化、不做降级发表、不把弱结果包装成 fallback paper。
```

## Harness Engineering Flow

1. Codex 修改 `research/ai-ie/` 下当前 active 节点要求的研究 artifact。
2. 项目级 Stop hook 运行 `agent-harness step`。
3. workflow controller 验收当前 active node 的 artifact 结构和 `Status:` 值。
4. 节点未通过时，hook block，并告诉 Codex 需要修复什么。
5. 节点通过且只有一个 transition 匹配时，workflow state 自动推进，并用 block 提示下一阶段。
6. 多个 transition 同时匹配时，state 进入 `choosing`；Codex 需要查看 `agent-harness options` 并运行 `agent-harness choose`。
7. 只有进入 terminal workflow node 后，Stop hook 才不再 block。

## 试运行

在本目录启动 Codex session，并输入：

```text
Research this idea with the AI-IE research workflow:

<你的研究想法>
```

`AGENTS.md` 已经包含项目级 workflow 操作规则，所以用户不需要在提示词里重复粘贴 workflow 协议。

当 Codex 准备停止时，`.codex/hooks.json` 会运行：

```bash
bash "$(git rev-parse --show-toplevel)/.codex/hooks/run-agent-harness-check.sh"
```

该脚本调用：

```bash
agent-harness step --task workflows/ai-ie-research.json --report-id research-latest --hook-json
```

hook 会优先使用已安装的 `agent-harness`，否则回退到：

```bash
uvx --from agent-harness-cli==0.1.2 agent-harness
```

## 常用命令

验证 workflow：

```bash
agent-harness validate-workflow --task workflows/ai-ie-research.json
```

执行一次 workflow step：

```bash
agent-harness step --task workflows/ai-ie-research.json --hook-json
```

查看 state：

```bash
agent-harness status --state .agent-harness/ai-ie-research-state.json
```

查看并选择 model-choice transition：

```bash
agent-harness options --state .agent-harness/ai-ie-research-state.json
agent-harness choose <transition-id> --state .agent-harness/ai-ie-research-state.json --reason "why this route is appropriate"
```

查看最新 workflow report：

```bash
agent-harness view research-latest --report-dir reports/research-workflow --failed-only
```

## 验收面

workflow 使用三层 gate：

| 层级 | 目的 | 实现 |
| --- | --- | --- |
| Structure | 确认 active artifact 存在、必需标题齐全，并达到最低内容量。 | `check_markdown_sections.py` |
| Stage semantics | 判断阶段是否真的完成，`Status:` 是否有证据支撑。 | `check_research_checklist.py` + `checklists/research/stage/*.md` |
| Deep research quality | 检查研究对象建模、真实信息增量、方法-claim 匹配、数据来源可复现性、证据边界、反解释和主文承载力。 | `check_research_checklist.py` + `checklists/research/deep/*.md` |

workflow 使用这些 check 脚本：

| Check | 作用 | 要求来源 |
| --- | --- | --- |
| `check_markdown_sections.py` | 检查当前 Markdown artifact 是否存在、是否包含必需标题、内容是否达到最低信息量。 | `workflows/ai-ie-research.json` |
| `check_research_status.py` | 读取 artifact 中的 `Status: <value>`，并把它作为 `metadata.status` 提供给 transition 条件。 | `workflows/ai-ie-research.json` |
| `check_research_checklist.py` | 调用本地 `codex exec` 填写 Markdown checklist，再把 checked/unchecked items 解析成 harness JSON。 | `checklists/research/` |

workflow graph 负责路由。结构和状态检查是确定性的。Checklist checks 是语义质量 gate；只有做 deterministic-only 调试时才设置 `AGENT_HARNESS_ENABLE_LLM=0`。

## 项目结构

```text
AGENTS.md                            Codex 项目级操作说明。
.agents/
  skills/harness-workflow-runner/    项目级 workflow runner skill。
.codex/
  hooks.json                         项目级 Stop hook 配置。
  hooks/run-agent-harness-check.sh   workflow Stop hook 入口。
checks/
  check_markdown_sections.py         Markdown artifact 结构检查。
  check_research_status.py           workflow 路由状态检查。
  check_research_checklist.py        Markdown checklist 语义/深层质量 gate。
  local_codex_judge.py               本地 Codex checklist judge helper。
checklists/
  research/stage/                    阶段完成度 checklist 模板。
  research/deep/                     深层研究质量 checklist 模板。
workflows/
  ai-ie-research.json                研究 workflow graph。
research/
  ai-ie/README.md                    artifact 契约和允许状态。
pyproject.toml                       示例包元数据。
```

运行时生成文件会被忽略：

```text
.agent-harness/
reports/
```

## 设计说明

- 示例把领域逻辑留在 workspace：workflow spec、artifact contract、checklists 和 check scripts。
- CLI 负责状态控制、验收、报告、transition 应用和 hook JSON。
- Stop hook 在 workflow 到达 `research_complete` 之前始终返回 `decision: "block"`。
- check 脚本只使用 Python 标准库。语义/深层质量 gate 需要本地 Codex CLI，因为会调用 `codex exec`。
