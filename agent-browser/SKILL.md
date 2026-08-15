---
name: agent-browser
description: OpenClaw 全局浏览器自动化基础设施。提供统一、安全、反检测、可恢复的网页浏览与交互能力。触发场景包括打开网页、页面观察、元素点击输入、表单填写、数据提取、截图、多标签管理、高危操作人工确认、Session 恢复等。业务 Skill 必须通过本 Skill 提供的标准 API 操作浏览器，禁止直接调用 Playwright。
---

# Agent Browser

## 1. Skill Identity

- **Name**: agent-browser
- **Version**: 1.0.0
- **Type**: Infrastructure / Browser Automation / Agent Tool
- **Role**: OpenClaw 全局浏览器基础设施
- **Primary Runtime**: Playwright + Chrome/Chromium + CDP
- **Purpose**: 为 OpenClaw 主 Agent、Sub-Agent、Cron、业务 Skill 提供统一、可靠、安全、可恢复的浏览器操作能力。

---

## 2. Core Principle

Agent Browser 不是某一个业务 Agent 专属的浏览器。

所有需要浏览器的 Agent 必须优先调用 Agent Browser，而不是自行实现 Playwright、Chrome、DOM、截图、Session 等功能。

统一架构：

```text
Business Agent
     ↓
Agent Browser API
     ↓
Agent Browser Core
     ↓
Playwright / CDP
     ↓
Chrome / Chromium / Edge
     ↓
Internet
```

禁止业务 Skill 重复实现浏览器基础能力。

---

## 3. Supported Use Cases

Agent Browser 用于：

- 网页访问
- 网页搜索
- 页面信息读取
- 表格数据提取
- 表单填写
- 网页操作
- 多页面协作
- 文件下载
- 文件上传
- 登录状态复用
- 截图
- OCR
- Vision 页面理解
- 网页任务自动化
- 多 Agent 浏览器任务
- Cron 浏览器任务
- Human-in-the-loop
- 高风险操作人工确认

---

## 4. Architecture

```text
 OpenClaw
 │
 ┌──────────────┼──────────────┐
 │              │              │
 Main Agent   Sub-Agent     Cron
 │              │              │
 └──────────────┼──────────────┘
                ↓
        Agent Browser API
                ↓
   ┌──────────────────┐
   │   Agent Browser  │
   └────────┬─────────┘
            │
   ┌────────┼────────┐
   ↓        ↓        ↓
Perception  Action   Safety
   Engine
   │        │        │
   └────────┼────────┘
            ↓
     Agent Runtime
            ↓
    Playwright / CDP
            ↓
  Chrome / Chromium / Edge
```

---

## 5. Browser Runtime

默认使用：

- Playwright
- Chrome
- Chromium
- CDP

支持：

- Headless
- Headed
- Remote Browser
- Browser Restart
- Browser Recovery

Browser 生命周期：

```text
launch → connect → create → restart → recover → close
```

如果 Browser 崩溃：

```text
detect → save task state → restart browser → restore profile → restore session → resume task
```

---

## 6. Profile Management

Profile 用于保存浏览器环境和合法登录状态。

示例：

```text
profiles/
├── default
├── trading
├── finance
├── quotation
└── research
```

Profile 可以保存：

- Cookies
- LocalStorage
- SessionStorage
- 登录状态
- 浏览器配置

原则：**优先复用人工完成登录后的 Profile，不要求 Agent 获取账号密码。**

---

## 7. Secret Security

禁止把以下内容直接提供给 LLM：

- 密码
- Cookie
- Access Token
- Session Token
- 银行卡信息
- API Secret
- 私密凭证

正确架构：

```text
LLM
 ↓
Browser Runtime
 ↓
Secret / Profile
 ↓
Website
```

LLM 只需要知道：`authenticated = true`

---

## 8. Session Management

每个 Browser Task 应拥有独立 Session。

Session 至少包含：

```text
session_id, agent_id, browser_id, profile_id,
tabs, current_url, current_page, task_id,
state, created_at, updated_at
```

支持：create / pause / resume / switch / close / recover

---

## 9. Tab Management

支持：

- new_tab
- close_tab
- switch_tab
- list_tabs
- duplicate_tab

允许一个 Agent 同时管理多个页面。

---

## 10. Page Observation

执行重要操作前，应优先执行 `browser.observe()`。

页面观察结果至少包含：

```text
URL, Title, Page Text, DOM, Accessibility Tree,
Interactive Elements, Forms, Tables, Dialogs,
Iframes, Screenshot, Page State
```

**不得仅依赖截图进行普通网页操作。**

---

## 11. Perception Layer

页面感知采用多通道：

```text
Accessibility Tree → DOM → Page Text → Vision → OCR → Coordinate
```

- **Accessibility**：role / label / button / input / link / checkbox / textbox
- **DOM**：元素结构 / 属性 / 文本 / CSS / XPath
- **Vision**：Canvas / SVG / 图表 / 图片按钮 / 页面布局
- **OCR**：图片文字 / Canvas / 截图 / 扫描文档

---

## 12. Element Locator

元素定位必须采用多策略，优先级：

```text
ARIA → Role → Label → Text → DOM → CSS → XPath → Vision → Coordinate
```

例如 `browser.find("搜索按钮")` 应自动寻找最可靠的元素。

如果一种定位方式失败：

```text
retry → alternate locator → vision → coordinate
```

---

## 13. Basic Browser API（Navigation）

```text
browser.open(url)
browser.back()
browser.forward()
browser.refresh()
browser.new_tab()
browser.close_tab()
browser.switch_tab(tab_id)
```

---

## 14. Mouse API

```text
browser.click(target)
browser.double_click(target)
browser.right_click(target)
browser.hover(target)
browser.drag(source, target)
```

---

## 15. Keyboard API

```text
browser.type(target, text)
browser.fill(target, text)
browser.clear(target)
browser.press(key)
```

---

## 16. Form API

```text
browser.select(target, value)
browser.check(target)
browser.uncheck(target)
```

---

## 17. Scroll API

```text
browser.scroll(direction, amount)
```

支持：up / down / left / right / page / element

---

## 18. Wait API

```text
browser.wait()
browser.wait_for_element(target)
browser.wait_for_text(text)
browser.wait_for_url(url)
browser.wait_for_load()
browser.wait_until(condition)
```

**禁止在动态页面中大量使用固定长时间 sleep，优先使用状态等待。**

---

## 19. File API

```text
browser.upload(target, file)
browser.download(target)
browser.get_downloads()
```

上传文件前必须检查：文件路径 / 文件类型 / 文件大小 / 当前任务权限

---

## 20. Screenshot API

```text
browser.screenshot()
```

支持：page screenshot / element screenshot / full page screenshot

截图用于：Vision / Debug / Replay / Audit / Human Takeover

---

## 21. Extraction

```text
browser.extract(target)
```

可提取：文本 / 属性 / 表格 / 链接 / 图片 / 页面结构 / JSON-like 数据

**优先直接读取 DOM，而不是 OCR。**

---

## 22. JavaScript

```text
browser.evaluate(script)
```

默认限制权限。JavaScript 不得用于：

- 绕过权限
- 绕过认证
- 窃取 Cookie
- 修改安全机制
- 绕过网站访问控制

---

## 23. Agent Task Engine

Agent Browser 内部采用：

```text
GOAL → OBSERVE → UNDERSTAND → PLAN → ACT → OBSERVE → VERIFY
 → SUCCESS? → YES → FINISH
 └→ NO → RECOVERY → RE-PLAN
```

每次操作后必须根据页面反馈判断是否成功。**禁止假设 click = success。**

---

## 24. Task Limits

每个 Task 必须设置：

```text
max_steps, max_time, max_retries,
max_llm_calls, max_vision_calls, max_tabs
```

超过限制：STOP → save state → report failure。**禁止无限重试。**

---

## 25. Recovery Engine

常见错误：

```text
element_not_found, page_timeout, network_error, page_changed,
popup_blocked, login_expired, tab_closed, browser_crashed,
server_error, rate_limit, captcha
```

恢复顺序：

```text
observe → retry locator → wait → refresh → reopen
→ restore session → re-plan → human takeover
```

---

## 26. Vision Fallback

当 DOM 无法完成任务：

```text
screenshot → vision → identify element → bounding box → action → verify
```

Vision 返回：element / description / bounding_box / confidence

**低置信度操作不得直接执行高风险行为。**

---

## 27. OCR

OCR 用于：图片文字 / Canvas / 图表 / 截图 / 扫描文件

**OCR 只负责识别，不负责破解验证码。**

---

## 28. Human-in-the-loop

```text
browser.pause()
browser.resume()
browser.takeover()
browser.release()
browser.ask_user()
browser.confirm()
```

遇到验证码 / 双因素认证 / 需要用户判断 / 高风险操作时可以暂停任务：

```text
Agent → Pause → Human 完成操作 → Agent 检测页面状态 → Resume
```

---

## 29. Risk Engine

| 等级 | 操作 | 处理 |
| :--- | :--- | :--- |
| **LOW** | 打开网页/搜索/阅读/翻页/提取公开数据/截图/下载公开文件 | 自动执行 |
| **MEDIUM** | 填表单/上传文件/创建内容/发送普通消息 | 按 Agent 权限 |
| **HIGH** | 付款/转账/股票交易/下单/删数据/改账户/发敏感信息 | **必须人工确认** |

---

## 30. Permission System

权限：`READ / NAVIGATE / SEARCH / CLICK / INPUT / UPLOAD / DOWNLOAD / MESSAGE / PURCHASE / TRADE / DELETE / ACCOUNT_CHANGE`

权限必须与 Agent 绑定。示例：

- **行情 Agent**：READ / NAVIGATE / SEARCH
- **交易 Agent**：READ / NAVIGATE / SEARCH / INPUT / TRADE（TRADE = Human Confirmation）

---

## 31. Website Memory

记录网站长期操作经验：

```text
website, page, element, locator,
successful_action, failed_action,
login_flow, popup_behavior, page_structure
```

流程：New Website → Explore → Successful Operation → Save Knowledge → Next Task → Reuse

---

## 32. Website Adapter

高频网站可以建立 Adapter，只保存：

```text
site identity, page identity, important elements,
common actions, login detection, special behaviors
```

Adapter 不得复制整个 Browser Runtime。

---

## 33. Multi-Agent Isolation

每个 Agent 默认拥有独立：Browser / Profile / Session / Task / Permission / Logs

```text
Agent A → Profile A → Session A
Agent B → Profile B → Session B
```

除非明确配置，否则禁止不同 Agent 共享 Session。

---

## 34. Cron Integration

Cron 不应该直接操作 Chrome。正确方式：

```text
Cron → Create Browser Task → Task Queue → Agent Browser → Execute → Return Result
```

---

## 35. Task Queue

支持优先级：HIGH / MEDIUM / LOW

操作：submit / cancel / pause / resume / retry / timeout

建议：交易/风控 → HIGH，实时行情 → HIGH，业务任务 → MEDIUM，资料搜索 → LOW

---

## 36. Concurrency

必须设置：

```text
max_browsers, max_sessions, max_tabs,
max_tasks, max_cpu, max_memory
```

超过限制：**排队**，而不是无限创建 Browser。

---

## 37. Logging

每个任务必须记录：

```text
task_id, agent_id, session_id, browser_id, url,
action, target, result, error,
retry_count, duration, token_usage, vision_usage
```

---

## 38. Browser Replay

重要任务保存：Screenshot / DOM Snapshot / Action / URL / Result / Error，支持 Task Replay，用于调试、审计、错误分析、Agent 优化。

---

## 39. Cost Monitoring

统计：LLM Tokens / Vision Tokens / Screenshot Count / Page Count / Action Count / Execution Time / Browser Resource Usage

支持按 Agent / Task / Website / Date 统计成本。

---

## 40. Safety Rules

Agent Browser 不得用于：

- 破解验证码
- 绕过身份认证
- 绕过访问控制
- 窃取 Cookie
- 窃取账号
- 绕过网站安全机制
- 未授权访问

遇到安全验证：PAUSE → HUMAN TAKEOVER → USER COMPLETES → RESUME

---

## 41. Business Skill Integration

所有业务 Skill 必须优先调用 Agent Browser。例如：

```text
基金 Agent → Agent Browser → 读取基金网站
交易 Agent → Agent Browser → 读取行情 / 操作模拟账户
报价 Agent → Agent Browser → 查询供应商 / 市场价格
```

业务 Skill 不得重复实现：Browser 启动 / Chrome 管理 / Playwright / DOM 解析 / Screenshot / Session / Profile / Browser Recovery

---

## 42. Standard Interface

业务 Agent 推荐只使用：

```text
browser.open()
browser.observe()
browser.find()
browser.click()
browser.type()
browser.fill()
browser.scroll()
browser.extract()
browser.screenshot()
browser.wait()
browser.upload()
browser.download()
browser.new_tab()
browser.switch_tab()
browser.close_tab()
browser.pause()
browser.resume()
browser.ask_user()
browser.confirm()
```

底层实现对业务 Agent 隐藏。

---

## 43. Default Behavior

```text
Browser Mode:    headed
Profile:         isolated
Session:         isolated
Risk:            strict
Vision:          fallback
OCR:             fallback
Retry:           limited
Human Confirmation: required for HIGH risk
Logging:         enabled
Replay:          enabled for important tasks
```

---

## 44. Execution Rules

每个任务必须：

1. 明确 Goal
2. 创建或恢复 Session
3. Observe 页面
4. 判断页面状态
5. Plan
6. 执行 Action
7. Verify
8. 失败则 Recovery
9. 达到目标后结束
10. 保存 Task Result

禁止：无目标无限浏览 / 无限重试 / 无验证连续操作 / 高风险操作自动执行 / 把密码交给 LLM / 绕过验证码或安全机制

---

## 45. Recommended Directory

```text
agent-browser/
│
├── SKILL.md
├── core/          (browser, session, profile, tab, window)
├── perception/    (dom, accessibility, element, screenshot, vision, ocr, page_state)
├── action/        (navigation, mouse, keyboard, form, scroll, upload, download, javascript)
├── agent/         (planner, observer, executor, verifier, recovery, task)
├── safety/        (permission, risk, confirmation, secret, human_control)
├── memory/        (session_memory, website_memory, task_history)
├── adapters/      (generic)
├── scheduler/     (queue, priority, concurrency)
├── monitoring/    (logs, metrics, replay, cost)
└── config/        (browser.yaml)
```

---

## 46. Future Roadmap

- **V1.1**：Vision 定位优化 / Website Memory / 自动 Recovery / Human Takeover / Browser Replay
- **V1.2**：多 Agent Browser Pool / Remote Browser / Browser Queue / Cost Monitoring / Website Adapter
- **V2.0**：自动学习网站操作流程 / 跨网站工作流 / Browser Skill Marketplace / Browser Task Template / Browser Knowledge Base / 多浏览器协同 / 长时间 Browser Agent / 自主网页任务规划

---

## 47. Final Architecture

```text
 OpenClaw
 │
 Main Agent
 │
 ┌──────────────┼──────────────┐
 ↓              ↓              ↓
财务Agent    交易Agent     报价Agent
 │              │              │
 └──────────────┼──────────────┘
                ↓
   ┌───────────────┐
   │ Agent Browser │
   └───────┬───────┘
           │
   ┌───────┼───────┐
   ↓       ↓       ↓
Perception Action  Safety
   │       │       │
 DOM  Click  Risk
 ARIA Input Permission
 Vision Scroll Confirmation
 OCR  Upload Human
 Screenshot Download
           │
           ↓
    Agent Runtime
           ↓
    Playwright / CDP
           ↓
  Chrome / Chromium / Edge
           ↓
        Internet
```

**核心原则最终只有一句话：**

> 「Agent 负责"想做什么"，Agent Browser 负责"怎么在网页上可靠地做到"，Browser Runtime 负责"真正执行"，Safety Layer 负责"什么情况下不能自动做"。」

---

## 48. OpenClaw 本地落地对接（实现说明）

> 本 Skill 是接口规范层。OpenClaw 内置的 `browser` 工具（基于 Playwright + Chrome + CDP）是本 Skill 的实际运行时。业务 Skill 通过 `browser` agent tool 调用，禁止直接调 Playwright。

### 命令映射（标准 API → OpenClaw browser 工具）

| agent-browser 标准 API | OpenClaw browser 工具调用 |
| :--- | :--- |
| `browser.open(url)` | `browser(profile="openclaw", action="open", url=url)` 或 `openclaw browser open <url>` |
| `browser.observe()` | `browser(action="snapshot", targetId=...)` 返回含 ref 的 UI 树 |
| `browser.click(target)` | `browser(action="act", action="click", ref=...)` |
| `browser.type/fill(target, text)` | `browser(action="act", action="type"/"fill", ref=..., text=...)` |
| `browser.new_tab(url)` | `browser(action="open", url=url, label="task")` |
| `browser.close_tab(tab_id)` | `browser(action="close", targetId=tab_id)` |
| `browser.switch_tab(tab_id)` | `browser(action="snapshot", targetId=tab_id)` 后用该 targetId |
| `browser.screenshot()` | `browser(action="screenshot")` |
| `browser.refresh()` | `browser(action="navigate", url=当前url, reload=true)` |
| `browser.ask_user(prompt)` | 停止并明确报告需要人工干预（登录/验证码/2FA） |
| `browser.wait_for_element(target)` | `browser(action="act", action="wait", ...)` 或 `openclaw browser wait` |

### 落地步骤（首次使用前）

```bash
# 1. 检查浏览器底层是否就绪
openclaw browser --browser-profile openclaw doctor

# 2. 启动浏览器
openclaw browser --browser-profile openclaw start

# 3. 打开页面并观察
openclaw browser --browser-profile openclaw open https://example.com
openclaw browser --browser-profile openclaw snapshot
```

### CLI 实测命令（2026-08-15 实测验证）

> ⚠️ OpenClaw browser CLI 的交互命令是**位置参数**格式，不是 `--ref/--text` 选项。以下均为已实测可用的正确写法：

```bash
# 打开页面（返回 tab，如 t1）
openclaw browser open https://example.com

# 观察页面（返回带 ref 的 UI 树，如搜索框 ref=e36）
openclaw browser snapshot --target-id t1

# 输入文字（位置参数：ref 在前，text 在后）
openclaw browser type e36 "OpenClaw"

# 按键（Enter/Backspace 等）
openclaw browser press Enter

# 点击元素（位置参数：ref）
openclaw browser click e36

# 全列表命令：doctor/start/status/open/close/snapshot/screenshot/navigate/type/press/click/fill/hover/drag/scroll/evaluate/wait/pdf/download/upload
```

**已实测闭环**：open → snapshot → type → press Enter → snapshot 验证 → 页面跳转成功（GOAL→OBSERVE→ACT→VERIFY）。

### Profile 选择

- `openclaw`：隔离托管浏览器（默认，安全，不影响日常浏览器）
- `user`：附着已登录的真实 Chrome 会话（需人在电脑前批准）
- `chrome`：通过浏览器扩展驱动真实 Chrome（人不在电脑前也能用已登录会话）

### 运维

- 配置：`~/.openclaw/openclaw.json` 的 `browser` 块
- 状态：`openclaw browser status` / `doctor`
- 故障排查：先 `doctor`，再 `start`，再 `tabs`，最后 `open` 分级定位
