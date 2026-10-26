# learn-flow 使用说明

> 版本：**1.0.0** · 更新：2026-10-26
> 包含技能：`learn-start`（建体系）、`learn-task`（日常纪律）
> 血缘：改造自 [dev-flow](https://github.com/lansi-ai/dev-flow) 1.4.0

---

## 0. 30 秒版

| 你要做的事 | 用哪个技能 | 一句话启动 |
|---|---|---|
| 开始一个新领域的学习 / 项目里还没有 `docs/LEARN-RULES.md` | `learn-start` | 「按 learn-start 流程，先做目标澄清」 |
| 已有体系，要学 / 练 / 产出 / 复习 / 复盘 | `learn-task` | 「按看板下一步开始」 |

三条最容易被违反的硬规则：

1. **无目标不学。** 开工前说得出「这次学完能独立做什么」，说不出就不许开始。
2. **无产出不算完成。** 「看完了 / 收藏了 / 做了笔记」不是完成，产出物或闭卷复述才是。
3. **状态即时上板。** `todo → doing → done`，不许跳步；每次变更重跑看板脚本。

---

## 1. 和 dev-flow 的对应关系

| dev-flow | learn-flow | 处理 |
|---|---|---|
| `start-project` 建项目规则 | `learn-start` 建学习体系 | 结构照搬 |
| `task-flow` 开发纪律 | `learn-task` 学习纪律 | 结构照搬 |
| Sign-off 门禁（确认才动手） | 目标共识门禁（确认才落盘） | **原样搬** |
| `tasks.yaml` 单源 + 派生 HTML | `board.yaml` 单源 + 派生 HTML | **原样搬** |
| A/B/C 任务分级 | A/B/C 学习分级 | **原样搬**（换内容） |
| 质量门禁：测试通过 / 契约符合 | 能力证据门禁：闭卷 + 产出 + 数据 | **换锚** |
| 提交规范 / 分支 / 端口 | — | 丢弃（无对应物） |

### 为什么"验收"必须换锚

开发的完成有机器判：`npm test` 绿了就绿了，没人能自欺。
学习没有测试套件，于是默认退化成"我读完了"——**这是所有学习工具的死因**。

所以 learn-flow 把验收锚点从"完成度"换成三样可查的东西：

1. **闭卷检索**：不看材料复述一遍。说过得糙可以，照着念不行。
2. **产出物**：必须有一个能给外人看的东西。
3. **外部数据**：能拿到反馈的任务（发布、交付、测试），必须回填。

---

## 2. dev-flow 没有、必须新增的四样

| 机制 | 解决的问题 | 落点 |
|---|---|---|
| **双轴状态**（`status` × `mastery`） | "做完了但没学会"看不见 | `board.yaml` 字段 + 看板橙色标记 |
| **闭卷检索门禁** | 输入当掌握 | `learn-task` 门禁 3 |
| **复习调度**（1/3/7/15/30 天） | 学完就忘，且不自知 | `review_due` + 概览页到期列表 |
| **类型占比诊断**（学/练/产/复） | 输入囤积症 | 看板概览，`学 > 50%` 报警 |

**双轴是这套体系的核心。** 允许 `status=done` 且 `mastery=1` 不是 bug——它逼你看见"我做完了但没学会"。看板上显示为橙色左框，一眼扎眼。

---

## 3. 产物结构

### 技能包（维护源）

```
learn-flow/
├── VERSION
├── README.md
├── examples/board.example.yaml     ← 可直接抄的看板样例
└── skills/
    ├── learn-start/
    │   ├── SKILL.md
    │   ├── references/
    │   │   ├── goal-breakdown-guide.md    目标澄清 5 维 + 终点行为写法
    │   │   ├── capability-map-guide.md    能力地图 / 掌握度 / 单元粒度
    │   │   ├── board-guide.md             看板字段 + 生成器契约 + 四视图
    │   │   └── practice-guide.md          练习四段式 + 三种反馈来源
    │   └── assets/build-board.py          看板生成器（仅依赖 PyYAML）
    └── learn-task/
        ├── SKILL.md
        └── references/
            └── media-ops.md               自媒体运营领域包
```

### 项目实例（跑完 learn-start 后）

```
<项目>/
├── AGENTS.md                  ← ≤15 行纯导航
├── docs/
│   ├── learning-plan.md       ← 能力地图（能力终点 + 能力域 + 单元）
│   ├── LEARN-RULES.md         ← 规则单源（五条门禁 + 掌握度 + 分级）
│   ├── board.yaml             ← 看板唯一源
│   ├── board-html/index.html  ← 派生物，禁止手改
│   ├── practice/<域>/         ← 练习与产出物
│   ├── reviews/               ← 复盘 + pitfalls.md
│   └── archive/               ← 完成史归档
└── scripts/build-board.py     ← 从技能 assets 复制
```

---

## 4. 看板怎么用

```bash
python scripts/build-board.py           # 生成 docs/board-html/index.html
python scripts/build-board.py --check   # 只校验，不出 HTML
```

四个视图：

| 视图 | 回答什么 |
|---|---|
| 概览 | 我在真学还是假学？（输入占比、完成但未掌握数、复习到期） |
| 看板 | 今天做什么？（按 todo/doing/blocked/done 四列） |
| 能力树 | 哪块是空的？（域 → 单元 → 任务） |
| 矩阵 | 我偏科吗？（域 × 掌握度分布） |

概览页会主动报警的两件事：

- **输入占比 > 50%**：你在囤积输入，不是在练能力
- **完成但未掌握 > 0**：有任务 done 了但掌握度 ≤1

---

## 5. 掌握度五级

| 级别 | 名称 | 判定证据 |
|---|---|---|
| 0 | 未接触 | 无 |
| 1 | 能认 | 看得懂，但自己做不出来 |
| 2 | 能复述 | 不看材料能说清要点 |
| 3 | 能独立做 | 无模板独立产出合格品 |
| 4 | 能教别人 | 能讲清为什么，能给别人纠错 |

纪律：**没证据最高记 1；跟着教程做过只算 2；复习答不出降 1 级。降级是机制不是失败。**

---

## 6. 怎么触发

### 自动触发

description 已写明场景，正常提需求即命中：

- 「我想系统学一下 XX」「帮我做个学习计划」「搭个学习看板」→ `learn-start`
- 「今天练什么」「按看板继续」「发一条」「复盘一下」→ `learn-task`

### 显式触发

`learn-start` 加载后会先输出一行确认，用于验证技能真的生效：

> ✅ 已加载 `learn-start` 技能；将按流程执行：阶段 1 目标澄清 → Sign-off → 阶段 2 体系落盘 → 步骤 6 审阅闸门 → 阶段 3 收官。

**改完技能必须新开会话**——技能清单在会话启动时固定，旧会话不热更新。

---

## 7. 常见误用（照着查）

| 现象 | 原因 | 处理 |
|---|---|---|
| AI 没问几句就开始排计划 | 违反 Sign-off 门禁 | 提醒「先给共识小结，等我确认」 |
| 看板上一堆 done，但心里没底 | 掌握度自评放水 | 逐个问「不看材料能做一遍吗」，答不出降级 |
| 学了两周没进展 | 全是 `学` 类任务，没有 `练 / 产` | 看概览的输入占比，超 50% 就砍输入加练习 |
| 看板 HTML 不改 | 改了 YAML 没重跑脚本 | `python scripts/build-board.py` |
| 不知道该复习什么 | 没排 `review_due` | 单元 mastery ≥2 时必须排复习 |
| 计划越做越大 | 没有「不做清单」 | 回 `learning-plan.md` 补上，新方向一律进清单 |

---

## 8. 维护：改完技能怎么生效

本机路径：

| 位置 | 角色 |
|---|---|
| `G:\Projects\learn-flow\` | **维护源**（改这里，对应 GitHub 仓库） |
| `C:\Users\Administrator\.workbuddy\skills\learn-start\` | 生效位 |
| `C:\Users\Administrator\.workbuddy\skills\learn-task\` | 生效位 |

同步命令：

```bash
cp -r "G:/Projects/learn-flow/skills/learn-start" "C:/Users/Administrator/.workbuddy/skills/"
cp -r "G:/Projects/learn-flow/skills/learn-task"  "C:/Users/Administrator/.workbuddy/skills/"
```

**只改维护源不同步 = 改了不生效。** 同步后必须新开会话验证。

---

## 9. 版本记录

| 版本 | 日期 | 说明 |
|---|---|---|
| 1.0.0 | 2026-10-26 | 首版。从 dev-flow 1.4.0 迁移四机制，换锚质量门禁为能力证据门禁，新增双轴状态、闭卷检索、复习调度、类型占比诊断；内置自媒体运营领域包 |
