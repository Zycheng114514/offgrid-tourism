# 视频脚本

English version: [VIDEO_SCRIPTS.md](VIDEO_SCRIPTS.md)

两个视频：**演示视频**展示产品能做什么，**技术视频**讲清楚做法。旁白先求讲清楚，时长按字数算出来。比赛要求英文，**旁白照英文原文念**；下面的画面操作用中文写。

**时长**（数了单词数；时长 = 单词数 ÷ 语速 + 等页面响应的时间）：

| 视频 | 单词数 | 每分钟 140 词（中速） | 每分钟 120 词（慢一点） |
|---|---|---|---|
| 演示视频 | 191 | 约 1 分 46 秒 | 约 2 分钟 |
| 技术视频 | 221 | 约 1 分 51 秒 | 约 2 分 06 秒 |

录之前先在提交页面看一下有没有时长限制。

## 录之前

- 用 Chrome，窗口宽约 1280 像素，缩放 100%–110%，隐藏书签栏，关掉其他标签页。
- 按顺序打开这几个标签页：
  1. https://github.com/Zycheng114514/offgrid-tourism#the-problem （README 里"问题"那张表）
  2. https://offgrid-tourism.vercel.app/host （会自动转到我们自己的服务器）。录之前点 **New host**，让对话从空白开始
  3. https://offgrid-tourism.vercel.app/app/
  4. https://emotions-auburn-carried-divide.trycloudflare.com/app/ ，先切到 **Ask by SMS** 页（短信模拟只在我们自己的服务器上有）
  5. https://offgrid-tourism.vercel.app/pipeline
- 断网：直接关 Wi-Fi（比 Chrome 开发者工具里的 Offline 画面干净）。
- Mac 录屏：按 Shift-Command-5 → 录整个屏幕或选定区域 → "选项"里选麦克风。也可以先录画面，后期再配音。
- 录之前确认标签页 2 和 4 能打开：我们自己服务器的地址重启后会变。

## 演示视频

| # | 画面操作 | 旁白（照英文念） | 时长 |
|---|---|---|---|
| 1 | 标签页 1：停在 "The problem" 那张表 | "In Samosir, on Lake Toba in Indonesia, small guesthouses and food stalls are hard to find online. On OpenStreetMap, 58 percent of villages have no food or lodging listed nearby, and only 7 percent of listings have a phone number. So we built a system that works with a basic phone and a weak connection." | 24–28 秒 |
| 2 | 标签页 2：点示例 "Free text, no business name…"，点 **Send**；等服务器追问；点建议回复 "Homestay Pelabuhan Indah"；等确认摘要；点 **1**，再点 **YA**。右边面板会显示每个字段的来源 | "A host sends one SMS, in their own words. The system reads the price, the rooms and the village, and asks by SMS for anything missing. Here, it asks for the business name. The host confirms with 1, and the listing goes live." | 26–30 秒 |
| 3 | 标签页 2：点 **New host**；点示例 "Batak Toba (local language)…"，点 **Send**；回复是印尼语 | "It also understands Batak Toba, the local language, and replies in Indonesian." | 8–9 秒 |
| 4 | 标签页 3：点 **Download listings**（显示 20 家、28 KB）；关掉 Wi-Fi；输入 `cheap room Tomok`；右上角语言切到 中文；点示例 `便宜 住宿` | "A traveller downloads the region's listings once. That's 28 kilobytes. Then, with no connection at all, they can still search for food, rooms, boats or guides, in English, Indonesian or Chinese." | 21–24 秒 |
| 5 | 打开 Wi-Fi。标签页 4：点示例 `SEARCH food Garoga`，等回复 | "With phone signal but no data, the same search works by SMS." | 8–9 秒 |
| 6 | 标签页 5：点示例 "The model invents a name…"，再点第 6 步 "Checks against the message"；停在显示 "rejected" 的表格 | "AI is used only where rules can't do the job, and everything the model gives is checked against the original message. In this demo, the model's outputs were prepared in advance, and all the businesses are made up." | 18–21 秒 |

## 技术视频

| # | 画面操作 | 旁白（照英文念） | 时长 |
|---|---|---|---|
| 1 | 标签页 1：往下滚到 "How the pipeline works"，停在流程图和表格 | "Here's how it works. A host's SMS reaches an Android phone with a local SIM, which forwards it to our server. The server is plain Python with a small database. Travellers use an offline web app." | 17–20 秒 |
| 2 | 标签页 5：点示例 "Keyword format: everything in one SMS"；点第 4 步 "Fixed rules read the clear parts"，短信里规则读到的词会高亮 | "Every message goes through the same steps. First, fixed rules detect the language and read what is clear: prices like 25 rb, opening hours, rooms, and village names. The highlighted words are what the rules found." | 18–21 秒 |
| 3 | 标签页 5：点示例 "The model invents a name…"；先点第 5 步（模型输出），再点第 6 步（核对，显示 "rejected"） | "Then a small language model reads what rules can't: the business name, the offer, and an English translation. Every value it gives must appear in the original message. Here it made up a name, so the system rejects it and asks the host instead." | 23–26 秒 |
| 4 | 新标签页打开 https://github.com/Zycheng114514/offgrid-tourism/blob/main/regions/samosir.json ，往下滚过 "languages" 和 "words"。回到标签页 5：输入 `搜索 便宜 住宿 Tomok`，点 **Run the pipeline**；第 3 步显示 "Chinese" | "Nothing is hard-coded for Samosir. Each region is one settings file: its languages, words, currency and villages. That's how one system handles Indonesian, Batak Toba, English and Chinese, and how a new region is added." | 18–21 秒 |
| 5 | 新标签页打开 https://github.com/Zycheng114514/offgrid-tourism/blob/main/server/offgrid/llm.py ，停在文件开头的说明（列着 openai_compatible、anthropic、simulated、none） | "The model plugs in through one interface: a small open model on our own server, a hosted one, or none. In this demo no model runs. Its outputs for the examples were written in advance." | 17–20 秒 |
| 6 | 标签页 3：做一次离线搜索；再回标签页 1，停在 README 的 "Status and limits" | "The traveller app works offline after one download, and the demo is live on Vercel. Next, we want to pilot it with a tourism village in Samosir, and test a small model on real messages." | 17–20 秒 |
