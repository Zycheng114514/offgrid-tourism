# Offgrid Tourism

English version: [README.md](README.md)

为网络连接较差的地方提供本地餐饮和住宿信息。小商户**用任意手机发短信，以自己的语言**上报自己提供的内容。游客**在手机上搜索商户条目，无需网络连接**；有信号但没有流量时，可以发短信询问。

为世界银行 **Small AI for Development** 黑客松的旅游赛道开发（2026 年 10 月 3–4 日）。

**在线演示**：<https://offgrid-tourism.vercel.app>（永久地址，部署在 Vercel 上）。商户端演示和短信模拟器会保存对话，所以它们运行在我们自己的服务器上；Vercel 上的 `/host` 会转发到那里（<https://emotions-auburn-carried-divide.trycloudflare.com>，临时地址，该服务器重启时会变）。

| 页面 | 展示的内容 |
|---|---|
| [`/pipeline`](https://offgrid-tourism.vercel.app/pipeline) | 一条短信在管道中经过的每一步，由服务器实时计算 |
| [`/host`](https://offgrid-tourism.vercel.app/host) | 商户端：一部功能机，以及服务器对每条短信做了什么 |
| [`/app/`](https://offgrid-tourism.vercel.app/app/) | 游客端应用：下载一次，然后离线搜索；或者发短信询问 |

> **演示数据**。每个商户、价格和电话号码都是编造的；村名是真实的（OpenStreetMap）。**演示中没有运行语言模型**：对于示例短信，模型输出是预先写好的，页面上凡是出现这些输出的地方都有说明。其他任何短信只由固定规则和追问处理。

## 问题

主要旅游中心以外的小型民宿、小吃摊、船只经营者和导游，常常没有出现在地图和订房网站上，他们的店主可能只有一部功能机。去那里的游客无法得知在哪里吃饭或住宿。他们本来会在当地花的钱流向别处，或者没有花出去。

在 OpenStreetMap 上对我们的测试地区——印度尼西亚多巴湖上的萨摩西县（Samosir）——做了测量（快照 2026-10-03，`scripts/osm_gap.py`）：

| 指标 | 数值 |
|---|---|
| 已列出的餐饮和住宿地点 | 228 |
| …其中距主要旅游村 Tuk Tuk 3 公里以内的 | 141（62%） |
| …有电话或 WhatsApp 号码的 | 17（7%） |
| …有营业时间的 | 12（5%） |
| 2 公里内没有已列出的餐饮或住宿地点的村庄 | 132 个中的 76 个（58%） |

在 OpenStreetMap 中一个地点都没有的村庄，没有公开记录；这不表示该村庄没有餐饮或住宿。这份缺失的记录，正是本项目要填补的。详情和来源：[docs/REAL_WORLD_DATA.zh.md](docs/REAL_WORLD_DATA.zh.md)。

## 它做什么

**商户**（本地商户）发一条短信，例如 `MAKAN Warung Bu Sinaga di Garoga, nasi ikan 25rb, buka 7-21`（“餐饮 Warung Bu Sinaga 在 Garoga，米饭和鱼 25k，营业 7–21”）。服务器把它转成结构化的商户条目，对缺少的内容用一条简短的短信追问，发回一份摘要让商户回复 `1` 确认，并询问是否可以向游客显示该电话号码。`BUKA` / `TUTUP`（“营业” / “关门”）用来标记今天的状态。

**游客**在有网络连接时下载某个地区的商户条目（20 条演示商户条目约 28 KB），然后在手机上无需网络连接即可搜索：按类别、村庄、“便宜”、“正在营业”。有信号但没有流量时，他们发短信 `SEARCH food Garoga`、`CARI makan Garoga` 或 `搜索 吃 Garoga`，通过短信收到前三条结果。他们也可以用自己的话提问（Ask 页）：联网时由服务器根据商户条目回答；有信号但没有流量时，同样的问题可以用短信问；完全没有网络时，下载到手机里的小语言模型（Qwen2.5-0.5B-Instruct，在浏览器里运行）把问题转成搜索。

![商户端：左边是一部功能机，右边是服务器所做的处理](docs/img/host-demo.jpg)

![中文界面的游客端应用，正在离线搜索 Tomok 附近便宜的住宿](docs/img/traveller-app-zh.jpg)

## 管道如何工作

```
店主的手机 ──短信──► 插了 SIM 卡的安卓手机（短信网关应用）──webhook──► 服务器
  服务器：1 判断语言和消息类型 → 2 固定规则 → 3 语言模型（可选）→ 4 核对
          → 5 用短信追问缺的信息 → 6 店主确认 → SQLite（连同原始短信）
          → 地区数据包（JSON）──下载──► 游客端应用：离线搜索
有信号、没有流量的游客 ──短信──► 同一个服务器 ──短信──► 前 3 条结果
游客用自己的话提问 ──应用或短信──► 服务器：规则挑出商户条目 → 模型只根据它们回答 → 核对
完全没有网络的游客 ──► 手机上的小模型：问题 → 搜索条件 → 离线搜索
```

| 步骤 | 做什么 | 是否用 AI？ |
|---|---|---|
| 语言和短信类型 | 各语言的词表决定短信的语言；固定规则决定它是上报、搜索、状态更新还是闲聊 | 否 |
| 固定规则 | 带货币词的价格（`25rb`、`Rp 25.000`、`1,5jt`）、带时间词的营业时间、房间数或人数、来自该地区村名表的村名 | 否 |
| 语言模型 | 读取规则无法读取的内容：商户名称、所提供的内容、路线说明、英文翻译 | 是（演示中为模拟） |
| 核对 | 模型给出的值，只有能追溯到短信才会保留：名称必须出现在短信中，数字必须与短信相符，村庄必须在村名表中 | 否 |
| 追问 | 每个缺少的字段发一条短信提问，而不是猜测 | 否 |
| 确认与同意 | 商户回复 `1`；只有经同意才显示电话号码 | 否 |
| 地区数据包和搜索 | 只含已确认的商户条目；搜索在手机上运行 | 否 |
| 游客提问（应用、短信） | 规则挑出候选商户条目；模型只根据它们回答；回答里点名的每个商户都必须是引用的候选，且不能出现其他名字，否则不用 | 是（演示中为模拟输出） |
| 没有网络时提问 | 手机上的小模型把问题转成搜索条件；答案由商户条目生成，所以编不出不存在的地点 | 是（在浏览器里运行） |

[`/pipeline`](https://offgrid-tourism.vercel.app/pipeline) 页面用真实的服务器代码让任意一条短信走完这些步骤，并显示每一步的输出，不保存任何内容。其中一个示例显示模型编造了一个商户名称，核对把它拒绝了。

![管道演示页：一条巴塔克托巴语短信经过的 11 个步骤](docs/img/pipeline-steps.jpg)

![短信中每条规则读取到的词被高亮显示](docs/img/pipeline-rules.jpg)

模型通过同一个模型接口调用，因此只需修改设置，就可以接入任何提供方：任何兼容 OpenAI 的服务器（Ollama、vLLM、llama.cpp、托管 API）、Anthropic API、`simulated`，或 `none`（只用规则和追问）。

在游客的手机上，应用可以从 Hugging Face 下载 Qwen2.5-0.5B-Instruct（Apache-2.0 许可），用 transformers.js 在浏览器里运行：有显卡（WebGPU）时约 790 MB，没有时（WebAssembly）约 520 MB。它只输出 JSON 格式的搜索条件，在手机上回答的问题不会离开手机。我们在一台 Mac 笔记本上测试，用显卡时每个问题约 1 秒，不用显卡时 3.5–8.6 秒。

## 语言

| 对象 | Samosir 地区配置文件中的语言 | 回复所用语言 |
|---|---|---|
| 商户 | 印尼语、巴塔克托巴语（当地语言）、英语 | 商户的语言；巴塔克托巴语回退为印尼语（国家通用语言） |
| 游客 | 英语、印尼语、中文 | 游客的语言 |

- 每条短信的语言由固定规则根据地区的词表决定；中文的匹配不依赖空格。同一批词表也决定命令、类别词、价格单位和时间词。
- 商户的语言会被记住，所以追问仍使用这种语言。
- 游客端应用的界面可以在英语、印尼语和中文之间切换。当读者与商户使用相同的语言时，条目显示商户自己的原话；否则显示英文翻译，原文放在其下方。
- 巴塔克托巴语的词是凭一般知识写的，**尚未经母语者核对**。

## 任何地区

代码中没有任何与 Samosir 有关的内容。所有因地点而异的内容（语言及其词表、货币和价格简写、村名表、回复文本、时区）都在地区配置文件 [regions/samosir.json](regions/samosir.json) 中。添加一个地区的步骤：

1. `python scripts/osm_gap.py --area-name "<name>" --admin-level <n>` 下载该地区的村庄并测量缺口。
2. 编写 `regions/<id>.json`，写入该地区的语言、词表和回复文本。
3. 用 `REGION_PROFILE=regions/<id>.json` 启动服务器。

## 运行

需要 Python 3.10 或更新版本；无需安装任何包（只用标准库）。

```bash
cd server
python -m offgrid seed                                  # load the 20 invented listings
LLM_PROVIDER=simulated python -m offgrid serve          # http://127.0.0.1:8000
python -m unittest discover tests                       # 24 tests, no network
```

部署到服务器、各项设置，以及连接 Android 短信网关手机：[docs/RUNBOOK.zh.md](docs/RUNBOOK.zh.md)。

## 仓库结构

```
server/offgrid/   HTTP 服务器、规则、模型接口、对话、游客提问、搜索、地区数据包、管道追踪
server/offgrid/static/   首页、商户端演示、管道演示页
server/tests/     用模拟输出跑的端到端测试
mobile/pwa/       游客端应用：可离线使用的网页应用，含搜索、提问和可选的手机端模型
regions/          每个地区一个配置文件
models/           信息提取的提示词；演示用的模拟模型输出和示例
schemas/          商户条目的 JSON Schema
scripts/          osm_gap.py：统计任意地区在 OpenStreetMap 上的信息缺口
data/real/        测试地区的 OpenStreetMap 数据（ODbL 许可）
data/synthetic/   编造的预置商户数据，已标明是编造的
deploy/           deploy.sh：通过 SSH 复制到服务器，启动应用和 Cloudflare 临时通道
api/, vercel.json  Vercel 入口，用于不保存状态的部分（server/offgrid/wsgi.py）
docs/             计划、真实数据、运行手册、提交材料、视频脚本
```

## 现状与局限

- **演示中服务器上的模型是模拟的**。示例短信和示例问题的模型输出是预先写好的；其他短信和问题由规则处理。游客手机上的模型是真实的模型，下载后在浏览器里运行。我们在一台 1 核 CPU 服务器上只试了一次 Qwen3-1.7B：每条短信耗时 54–73 秒，在 JSON-schema 模式下返回空输出；没有继续推进。
- **没有准确率数字**。给我们自己写的输出打分，什么也测不出来；测试只能说明管道可以端到端运行。
- **还没有真实用户**。所有商户都是编造的。Android 短信网关已经实现，但尚未连接到手机；演示使用的是短信模拟器。没有语音上报。
- **巴塔克托巴语未经验证**（见上文）。
- **影响未知**。我们的文献综述没有找到任何因果研究表明，在发展中国家把小商户放到网上会提高其收入；应在试点中测量。

## 相关工作

最接近的重叠项排在前面。标有（未重新核对）的条目来自一般知识。

- 世界银行的印度尼西亚旅游发展项目为超过 20,000 家商户建立了线上档案（未报告收入结果）。
- 政府的旅游村名录，例如印度尼西亚的 Jadesta（未重新核对）。
- Google Maps、订房网站和 OpenStreetMap 列出了游客众多的旅游中心；Organic Maps 和 OsmAnd 等离线地图应用可以在没有网络连接时显示 OpenStreetMap 上的地点（未重新核对）。
- 通过短信把信息众包到数据库或地图中：Ushahidi、FrontlineSMS（未重新核对）。
- 通过短信访问云端 AI 服务，已在医疗领域部署：Jacaranda Health PROMPTS（肯尼亚）、Babyl（卢旺达）。

我们的不同之处在细节上，并且尚未经过检验：商户通过短信、以自己的语言自行登记；每条商户条目都由商户确认并标注日期；游客获得可离线使用的数据包；同一条管道通过地区配置文件服务于任何地区。

## 文档

| 文件 | 内容 |
|---|---|
| [docs/PLAN.zh.md](docs/PLAN.zh.md) | 计划、管道、范围、演示脚本、风险 |
| [docs/REAL_WORLD_DATA.zh.md](docs/REAL_WORLD_DATA.zh.md) | 测试地区、已测量的数字、数据来源、哪些可以声称、哪些不可以声称 |
| [docs/RUNBOOK.zh.md](docs/RUNBOOK.zh.md) | 运行、测试、部署、连接短信网关手机 |
| [docs/SUBMISSION.zh.md](docs/SUBMISSION.zh.md) | 黑客松提交材料：核对清单、提交文本、视频脚本 |
| [docs/demo_video_script.zh.txt](docs/demo_video_script.zh.txt)、[docs/tech_video_script.zh.txt](docs/tech_video_script.zh.txt) | 演示视频和技术视频脚本：点哪里、旁白、时长 |

## 致谢

地图数据 © OpenStreetMap contributors，依据 Open Database License（ODbL）提供。关于多巴湖旅游的背景资料来自世界银行项目文件，链接见 [docs/REAL_WORLD_DATA.zh.md](docs/REAL_WORLD_DATA.zh.md)。

尚未选定许可证，因此默认保留所有权利。
