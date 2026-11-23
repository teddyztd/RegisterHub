<h1 align="center">RegisterHub</h1>

<p align="center">
  <b>工业级万能账号自动化注册框架与生命周期测试引擎</b><br>
  <i>A deterministic, stealth automation framework for universal account registration and agentic workflows.</i>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-22272e.svg?style=flat-square" alt="License"></a>
  <a href="DISCLAIMER.zh.md"><img src="https://img.shields.io/badge/Disclaimer-Legal%20Terms-red.svg?style=flat-square" alt="Disclaimer"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776ab.svg?style=flat-square&logo=python&logoColor=white" alt="Python Version"></a>
  <a href="https://playwright.dev/"><img src="https://img.shields.io/badge/Playwright-Engine-2EAD33.svg?style=flat-square&logo=playwright&logoColor=white" alt="Playwright"></a>
  <a href="https://opencv.org/"><img src="https://img.shields.io/badge/OpenCV-CV%20Engine-5C3EE8.svg?style=flat-square&logo=opencv&logoColor=white" alt="OpenCV"></a>
  <a href="tests/"><img src="https://img.shields.io/badge/Tests-Passing-brightgreen.svg?style=flat-square" alt="Tests"></a>
  <a href="https://bitwarden.com/"><img src="https://img.shields.io/badge/Export-Bitwarden%2FCSV-175DDC.svg?style=flat-square&logo=bitwarden&logoColor=white" alt="Bitwarden Export"></a>
</p>

<p align="center">
  <a href="./README.md">简体中文</a> | <a href="./README_EN.md">English</a>
</p>

---

## 项目概述

RegisterHub 是一个面向工程研发的现代化 Web 自动化框架，旨在彻底解决传统无头脚本在复杂前端交互中的脆弱性问题。框架基于 Playwright 运行时、OpenCV 离线计算机视觉算子及 Chrome DevTools Protocol (CDP) 架构构建，为现代单页应用 (SPA)、响应式受控表单以及自动化测试提供确定性的交互与状态编排能力。

### 核心工程支柱

- **运行环境自洽性 (Runtime Environment Parity)**：通过原生 Chrome 二进制接入与底层自动化特征消除，保持 JavaScript 原型链纯净（`[native code]`），消除自动化标记对现代 Web 应用的异常干扰。
- **离线视觉算法求解器 (Algorithmic Vision Solver)**：内置双通 Canny 边缘轮廓计算与三次贝塞尔拟人手部动力学模型，纯本地离线执行，零第三方付费 API 依赖。
- **CDP 会话桥接架构 (CDP Bridge Architecture)**：深度支持外部指纹浏览器（AdsPower、比特浏览器等）与本地已登录 Chrome 会话无缝接入，复用既有干净住宅网络与登录状态。
- **AI 代理原生集成规范 (Agentic Co-Pilot Protocol)**：仓库根目录内置工业级 `AGENTS.md` 交互契约，深度适配 Cursor、Claude Code、Windsurf 与 Gemini CLI，支持 AI 自主嗅探表单、装配适配器并完成闭环验证。

---

## 架构拓扑

```text
RegisterHub/
├── core/
│   ├── adapter.py         # 抽象适配器基类 (BaseSiteAdapter) 与生命周期契约
│   ├── pilot.py           # 拟人按键动力学 (human_type) 与智能交互守门员
│   ├── stealth.py         # 原生环境自洽引擎与 CDP 会话桥接器
│   ├── inspector.py       # 启发式 DOM 表单探测器 (FormInspector)
│   ├── solver.py          # OpenCV 缺口匹配计算与贝塞尔轨迹规划器
│   ├── identity.py        # 高熵多国身份与合规密码发生器
│   ├── mail_client.py     # 毫秒级自适应退避邮箱轮询客户端
│   ├── runner.py          # 调度引擎、黑匣子快照抓取与原子台账持久化
│   ├── scaffold.py        # 适配器自动派生与预装配代码生成引擎
│   └── exporter.py        # Bitwarden、1Password、CSV 及 JSON 资产导出器
├── sites/                 # 业务与示范适配器池
│   ├── _template.py       # 工业级标准适配器实现模板
│   ├── demo_site.py       # 自包含离线 Base64 靶场适配器
│   ├── quanticdata.py     # OpenCV 拼图滑块与贝塞尔拖拽验证适配器
│   ├── deepgram.py        # Deepgram $200 免费额度与 API Key 直出适配器
│   ├── amd.py             # AMD AI 开发者计划官方注册适配器
│   ├── coarena.py         # 谷歌登录后纯协议注册与提 Key 适配器
│   ├── milionseek.py      # 100milionseek 每日 1 亿 Token 一键领 Key 与 Turnstile 穿透适配器
│   └── automation_exercise.py # 国际两步式向导交互基准适配器
├── tests/                 # 单元与回归自动化测试套件
├── config.json            # 全局浏览器运行配置
├── pytest.ini             # Pytest 测试隔离规范
├── main.py                # 统一命令行调度入口
├── run.bat                # Windows 交互引导脚本 (CRLF 规范)
└── requirements.txt       # 核心生产依赖清单
```

---

## 内置示范适配器矩阵

RegisterHub 开箱内置涵盖不同前端技术栈与复杂交互范式的经典实战适配器：

| 适配器标识 | 目标应用 | 技术实现特性 | 核心评测与验证重点 |
| :--- | :--- | :--- | :--- |
| `demo` | 内置离线 Base64 靶场 | 零配置全离线管道 | 3 秒快速环境自洽性与生命周期端到端自检 |
| `quanticdata` | Quantic Data 服务 | OpenCV 缺口识别 + 贝塞尔动力学 | 纯本地算子秒破拼图滑块挑战，零第三方打码依赖 |
| `deepgram` | Deepgram 语音 AI 平台 | 谷歌人机主动穿透 + REST 协议闭环 | 官方赠送 $200 免费额度，100ms 原子直出 40 位 API Key |
| `amd` | AMD AI 开发者计划 | Akamai 遥测自洽 + OneTrust 穿透 | 顶级大厂官方 AI 算力开发者计划注册与凭据获取 |
| `coarena` | Coarena AI 平台 | **谷歌登录后纯协议注册与提 Key** | 示范 Google OAuth 会话捕获后 100% 协议确认条款并秒级直出 Key |
| `milionseek` | 100milionseek 平台 | **每日 1 亿 Token 免费算力** + Turnstile 穿透 | 填邮箱秒级直出 Key（免收激活信），内置母号裂变接力管理 |
| `automation_exercise` | 标准测试基准靶场 | 多阶段向导向注册流 | 复杂下拉联动与多选框状态硬断言 |
| `apirf` | [APIrf](https://apirf.ru) | 纯 HTTP 会话 + 严格激活链接提取 | 单账号注册、邮箱激活与身份态二次校验 |

---

## 官方独立开箱即用衍生工程 (Standalone Showcase Ecosystem)

> **矩阵互联与互相引流说明**：  
> 为了方便仅需针对**单一特定平台**进行自动化落地的开发者，本项目特将核心高频实战案例**全量解耦为 100% 自包含的独立 GitHub 开源工程**。  
> 每个独立工程均自带 Windows 一键启动引导 `run.bat`、专属 `main.py` 调度入口与自包含运行底座，无需配置母港即可独立运行。你也可以直接在本主框架中通过 `python main.py --run <site>` 统一调度：

| 独立开源项目 | 核心福利与架构亮点 | 独立工程直达 |
| :--- | :--- | :--- |
| **[Deepgram Register](https://github.com/waw666waw666/deepgram-register)** | 官方赠送 **$200 美元真金使用额度** + 谷歌 reCAPTCHA v2 主动穿透 + 纯 REST 协议秒级提 Key | [GitHub 仓库](https://github.com/waw666waw666/deepgram-register) |
| **[100MilionSeek Register](https://github.com/waw666waw666/100milionseek-register)** | **每天免费 1 亿 Tokens** + Turnstile 穿透 + 免收信页面卡片秒出 Key + 母号裂变接力 | [GitHub 仓库](https://github.com/waw666waw666/100milionseek-register) |
| **[AMD AI Dev Register](https://github.com/waw666waw666/amd-register)** | AMD 官方 AI 开发者计划注册 + Akamai 遥测自洽 + OneTrust 模态弹窗穿透 | [GitHub 仓库](https://github.com/waw666waw666/amd-register) |
| **[Coarena Register](https://github.com/waw666waw666/coarena-register)** | **谷歌登录后 100% 协议提 Key** + OAuth 会话捕获 + 条款签署与每日额度秒验 | [GitHub 仓库](https://github.com/waw666waw666/coarena-register) |

---

## 快速上手

### 1. 一键部署与验证（推荐）

本地部署的目标是可运行 RegisterHub CLI 的 Python 环境，不是发布服务器或监听端口。准备 Python 3.10+ 后，从干净检出执行一条命令：

```bash
git clone https://github.com/waw666waw666/RegisterHub.git
cd RegisterHub
python scripts/deploy_check.py
```

检查器会创建或复用项目内 `.venv`，使用该环境的解释器继续执行，并按以下顺序验收：

| 阶段 | 实际行为 |
| :--- | :--- |
| `install` | 安装 `requirements.txt` 依赖与 Playwright Chromium 回退浏览器 |
| `config` | 保留已有 `config.json`；仅在文件缺失时从 `config.example.json` 派生，并设置 `browser.headless=true` |
| `doctor` | 执行 `main.py doctor`，检查依赖、配置与浏览器环境 |
| `pytest` | 执行完整 `pytest tests/` 测试套件 |
| `demo` | 在隔离的临时工作目录执行 `main.py --run demo`，并要求临时 `results/accounts.txt` 含非空凭据数据 |

- **浏览器策略**：运行时优先使用已安装的 Google Chrome；Chrome 不可用时回退到 Playwright Chromium，因此不强制安装 Chrome。
- **失败语义**：任一阻塞阶段失败即停止，输出失败阶段并以非零状态退出。Demo 子进程退出码为零还不够，隔离台账为空同样判定失败。
- **数据隔离**：Demo 强制无头模式与临时 `output_dir`，验证后删除临时目录和凭据，不写入正常的 `results/accounts.txt`，也不改动已有代理、邮箱或浏览器配置。

### 2. 已准备机器：跳过安装

依赖和浏览器已就绪时，可避免重复安装：

```bash
python scripts/deploy_check.py --skip-install
```

`--skip-install` **只跳过**依赖与 Playwright Chromium 安装；配置保留或派生、`doctor`、完整测试、隔离 Demo 及非空台账门禁仍全部执行。环境未准备好时，后续对应阶段会失败，不会产生假成功。

### 3. 手动分步执行（可选）

只需单独诊断、跑测试或体验离线靶场时，可在已准备好的项目虚拟环境中执行：

```bash
python main.py doctor
python -m pytest tests/
python main.py --run demo
```

手动运行 Demo 会将凭据原子写入正常的 `results/accounts.txt`。它只验证离线适配器流程，**不等同于完整部署验收**；一键检查器还会验证诊断、测试以及隔离台账的非空结果。

### 4. AI 助手协同使用指南 (Cursor / Claude Code / Windsurf / Gemini)

本项目为 AI 编程助手深度优化，仓库根目录自带专属 [AGENTS.md](AGENTS.md) 行为约束与 [SETUP_FOR_AI.md](SETUP_FOR_AI.md) 环境协议。

**前置操作**：使用你的 AI 编程客户端（如 Cursor、Windsurf、VS Code 搭配 Claude Code / Gemini CLI），将 **`RegisterHub` 项目文件夹作为工作区根目录打开**。

工作区载入后，支持通过以下两种方式让 AI 协助开发新站点的注册适配器：

#### 方法一：极简直接丢（快捷交互模式）
直接在 AI 对话框中把目标网站注册地址发给 AI：
```text
请参考本项目规范与 AGENTS.md，为我编写该网站的自动化注册适配器：https://example.com/signup
```
AI 会自动读取根目录规则与模板，自主嗅探表单字段、生成代码骨架并尝试本地实测。

#### 方法二：人工自跑流程给步骤（强烈推荐，成号最稳健）
面对复杂的现代 Web 应用、多步向导或带交互验证的站点，**最稳健的做法是：你自己先在浏览器中手动注册成功一次**。  
把你在真实操作中经历的**核心网址、点击按钮、表单字段、验证码类型及关键截图**直接发给 AI，例如：
```text
请参考本项目规范与 AGENTS.md，帮我把刚才手动跑通的注册流程写成自动化适配器：
目标网址：https://example.com/signup

我的手动操作步骤如下（附关键界面截图）：
1. 打开注册页，填入邮箱和密码，点击“Create Account”；
2. 页面弹出了 Cloudflare 人机验证框，手动点一下绿勾；
3. 去邮箱查收 6 位数字验证码，回填到页面的 OTP 输入框中；
4. 进入控制台仪表盘，点击右上角“API Keys”菜单，点击“Create New Key”；
5. 复制弹出的 sk-xxxx 密钥，完成流程。

请根据我的真实操作路径编写 sites/example_site.py，并进行本地试跑验收！
```
AI 将直接对照你跑通的真实人类行为路径进行精确代码装配与接口逆向，避免无头盲测走弯路，一击必中！

### 5. APIrf 纯 HTTP 单账号注册

`apirf` 适配器的唯一目标是 **https://apirf.ru**。它使用同一个 HTTP 会话完成访客创建、账号绑定、邮件确认、登录和身份校验，不启动浏览器。

在本地 `config.json` 中配置 `apirf.mail.im215_api_key`，或改用环境变量 `APIRF_215_API_KEY`；不要把真实密钥写入仓库。PowerShell 示例：

```powershell
$env:APIRF_215_API_KEY = "<your-215.im-api-key>"
python main.py --run apirf --count 1
```

`config.example.json` 提供了空密钥与以下默认设置：

| 配置项 | 默认值 | 含义 |
| :--- | :--- | :--- |
| `apirf.mail.im215_api_key` | 空字符串 | 215.im 密钥；也可由 `APIRF_215_API_KEY` 提供 |
| `apirf.mail.http_timeout_secs` | `20` | 单次 APIrf 或邮箱 HTTP 请求超时（秒） |
| `apirf.mail.confirmation_timeout_secs` | `300` | 等待确认邮件的总超时（秒） |

目标域名固定为 `https://apirf.ru`，不能通过配置替换；APIrf 的邮箱路由固定为 `215.im` 单一通道，不可通过配置改写。

APIrf 从不向 `mail.tm`、`tempmail.io`、`guerrillamail` 这类公共临时邮箱域名投递确认信，因此这些通道在 APIrf 场景不是可用回退：未提供 215.im 密钥时，适配器会在构造阶段（任何 APIrf HTTP 请求之前）立即失败并在 `failed.txt` 记录明确原因，而不是创建邮箱后白等确认超时。地址一经提交给 APIrf，后续收信固定使用同一邮箱，不会换号重试。

产物写入 `output_dir`（默认 `./results`）：

| 产物 | 写入条件与内容 |
| :--- | :--- |
| `results/accounts.txt` | 严格校验通过后追加 `email----password----login` |
| `results/cookies/<login>.json` | 成功台账写入前导出的非空会话 Cookie，包含 `name`、`value`、`domain`、`path`、`expires`、`httpOnly`、`secure`、`sameSite` |
| `results/pending_activation/<login>.json` | 激活未完成时保存恢复信息，并标明 `confirmation` 或 `identity` 阶段；不会同时写入成功台账或 Cookie |

**严格成功门禁**：确认链接必须属于 `https://apirf.ru` 的官方确认路径；随后使用同一会话执行登录，`GET /api/auth/me` 的 `user` 对象必须返回严格的 `email_verified: true` 与 `is_guest: false`，且会话 Cookie 非空，才判定成功。登录响应本身不作为成功依据。遇到人机验证、访问拒绝、HTTP 403/429 或频控信号时立即停止，不做重试风暴。

**默认仅授权上述单账号验收；批量账号生命周期测试与压力测试均未获默认授权，必须另行明确批准。** `results/` 中的账号、Cookie 与待激活记录属于本地敏感产物，不得提交到仓库。

---

## 关于邮箱与验证码接收策略 (Email Strategies)

不同目标平台对注册邮箱的风控规则各异，RegisterHub 为开发者提供了三级透明收信策略：

1. **零收信门槛站点（即时秒出，新手首选）**：
   - 示范项目：`100milionseek`
   - **完全不需要接收任何验证码或激活信**！填入任意合规格式邮箱，过完 Turnstile 人机验证后，页面卡片 10 秒内直接渲染出明文 API Key。

2. **协议接管站点（OAuth 凭据换票）**：
   - 示范项目：`coarena`
   - 依托真机 Chrome 捕获 Google 登录态，浏览器仅充当瞬态取票器；会话捕获后 100% 纯协议签署条款、签发 API Key 并验活额度。

3. **需收码 / 高风控大额站点（如 Deepgram $200 美元真金赠金、AMD 开发者计划）**：
   - **默认方式（公网免费临时邮箱，全自动）**：
     默认 `use_disposable_mail: true`，框架通过三通道公网接口（mail.tm 等）全自动接收 6 位验证码。适合轻量功能验证。
   - **自备真实邮箱模式（强烈推荐，100% 成功保底）**：
     Deepgram、AMD 等官方大厂具备反欺诈黑名单库，公网部分免费临时域名可能被拦截。**强烈建议在 `config.json` 中填入自备的 Outlook / Hotmail / Gmail 个人邮箱**。脚本自动完成表单装配与人机穿透，并在终端提示输入验证码，回车即可 **100% 稳稳领走 $200 满额 API Key**！
   - **工业级自建中枢（高级扩展）**：
     支持开发者挂载自建 MailHub 容器池、Cloudflare Email Routing (Catch-all) 或 IMAP 协议，实现多通道批量无人值守收信。

---

## 命令行接口 (CLI)

### 查看已装载适配器
列出所有已注册的适配器及其技术规格：
```bash
python main.py --list
```

### 自动化脚手架生成
输入目标网页 URL，自动嗅探 DOM 输入字段并生成类型完整的适配器骨架代码：
```bash
# 智能探测目标网页并生成适配器代码
python main.py --scaffold target_service --url https://target-service.com/signup

# 执行生成的新适配器
python main.py --run target_service
```

### 外部指纹浏览器 CDP 桥接
直接附加至已在运行的外部指纹浏览器（AdsPower、比特浏览器）或开启调试端口的 Chrome 实例：
```bash
python main.py --run demo --cdp http://127.0.0.1:9222
```

### APIrf 实跑前只读预检 (preflight)
在启动 APIrf 真实注册之前，用一条命令确认本机已就绪：控制台 UTF-8 编码、215.im 凭据（只读接口探测）、APIrf 网络路径（只读端点探测）。全程只发 GET 请求，绝不创建访客、升级或注册任何账号；出现阻断性问题时以非零码退出：
```bash
python main.py preflight
```
探测端点与超时可在 `config.json` 的 `apirf.preflight` 中调整（见 `config.example.json`）。

### 密码库资产标准导出
将测试产出的账号资产一键转换为标准格式：
```bash
# 导出为 Bitwarden / 1Password 兼容 JSON
python main.py export --export bitwarden

# 导出为通用 CSV
python main.py export --export csv

# 导出为原始 JSON
python main.py export --export json
```

---

## AI 代理协作规范 (`AGENTS.md`)

RegisterHub 针对自主编程智能体进行了全流程规范定义。根目录的 `AGENTS.md` 约束以下核心纪律：

- **默认单并发纪律**：默认按单线程串行执行，避免无节制多开撕裂用户桌面；仅在单路稳定且等信占比超 50% 时主动提醒提速。
- **阶段守门员断言**：严禁无目的的时间等待 (`time.sleep`)，必须通过 URL 状态、DOM 属性或凭据落盘事实进行强校验。
- **宿主进程零干扰**：退出钩子严格基于明确的子进程树清理，严禁全局通杀系统进程，严禁全局抢占用户桌面焦点。

---

## 测试套件执行

运行完整单元测试集以验证核心启发式探针、OpenCV 计算引擎与代码生成逻辑：

```bash
pytest tests/
```

### 开发门禁：CI 与本地 pre-commit 钩子

- **持续集成**：`.github/workflows/tests.yml` 在每次 `push` / `pull_request` 上于 Python 3.10–3.13 矩阵运行同一套 `python -m pytest`，测试失败即阻断合并。
- **本地钩子（可选）**：仓库自带 `.githooks/pre-commit`，一次性启用后，每次 `git commit` 前自动运行同一测试门禁（仅写入本仓库 `.git/config`，不改全局配置）：

  ```bash
  git config core.hooksPath .githooks
  ```

  需要时可用 `git commit --no-verify` 显式绕过。详见 [docs/development.md](docs/development.md)。

---

## 免责声明与开源协议

1. **开源许可证**：本项目基于标准的 [Apache License 2.0](LICENSE) 许可协议发布。
2. **免责与合规说明**：本项目定位为**授权环境下的自动化流程走查与 Web 工程研究工具**。所有代码仅供技术交流与学术验证参考，完整法律声明与技术中立性说明请参阅：
   - [DISCLAIMER.zh.md](DISCLAIMER.zh.md) (中文版)
   - [DISCLAIMER.md](DISCLAIMER.md) (English)

---

## 开发者社区与交流

如果你在账号工程自动化、协议逆向、云端风控自洽或 API Key 提取落地中有任何技术疑问、适配需求或交流想法，欢迎加入我们的开发者社群：

- **QQ 交流群**：1130324020
- **Discord 社区**：[点击加入 Discord](https://discord.gg/USnVJ9YQX)
