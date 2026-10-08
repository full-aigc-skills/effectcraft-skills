# 受管理任务 / Managed execution

从当前技能实际加载目录调用 `scripts/launch.sh`（macOS/Linux）或 `scripts/launch.ps1`（Windows）。启动器仅在用户缓存准备锁定 Python；脚本、工程与输出均不得写入技能目录。七个平台制品可用不等于七个平台已通过原生验收。

| 操作 | 参数与行为 |
| --- | --- |
| doctor | Python 入口只读环境与锁定能力，不安装 EffectCraft |
| plan | `--plan FILE --output NEW_DIR [--mode workflow/commands/desktop]`，不编辑工程 |
| run | 同上，可指定 `--task ID`；先持久化身份再执行 |
| inspect | `--task ID`，返回期限、步骤、未知结果、回执 |
| reconcile | `--task ID`，核对原交付，不发送原编辑 |
| resume | `--task ID`，继续确定尚未开始的任务或已核对的分段导出；未知编辑不重放 |
| cancel | `--task ID`，先阻止父子任务调度；监督器确认自有进程停止 |
| review | `--task ID --criteria FILE [--judge RECEIPT]`，实际解码与宿主评价 |
| revise | `--task ID --plan FILE --output NEW_DIR`，范围、版本、预算均校验 |

全局参数 `--state-root`、`--runtime-home` 放在操作前。环境变量 `CRAFT_STATE_HOME`、`CRAFT_RUNTIME_HOME`、`CRAFT_PYTHON_HOME` 可隔离不同安装。固定离线 Python 包使用 `CRAFT_PYTHON_ARCHIVE`；EffectCraft 的原始安装器支持 `--archive`，仍必须匹配锁定摘要。

`workflow` 计划沿用原生合成格式；`commands` / `desktop` 沿用 `craft-command-plan/v1`。不得把未解析的自然语言直接当作原生参数。输入通过 `--input name=/absolute/file` 指定；已有工程通过 `--source DELIVERY --expectedProjectSha256` 对应计划字段核对（摘要写在计划，非命令行参数）。

任务记录使用内部 `effectcraft-managed-task/v2`，公共 `craft-task/v1`、`craft-artifact/v1` 所有权不变。旧交付可以复核；旧 v1 状态可检查但不可恢复执行；缺少版本化状态的历史任务不能自动转成可执行任务。运行时改变时原任务拒绝切换，应保留原技能快照与旧缓存执行诊断。

## 宿主 Judge 与有限修订

计划默认保留透明预览契约。明确需要普通不透明背景预览时设置 `previewAlpha: false`；透明交付保持 true 并检查真实 alpha，不事后改写门禁来迁就成品。初始计划应根据用户已授权的文字、位置等范围填写 `revisionScope`（参考 brand-intro 模板）；不允许通过 `run --source` 为受管理工程换新任务绕过修订预算。

1. `review` 输出 `judgeRequest`，绑定任务、工程、全部产物与评价标准。实际打开请求列出的图片/视频；技术检查 PASS 不能代替视觉与时序观察。
2. 缺少视觉或时序能力时保持 NOT_RUN。可用时保存响应 JSON：`requestId`、`binding` 原样引用，`score` 为 0–1，`passed` 为布尔，`issues` 标注对象、属性、时间区间与观察结果，`temporalReviewed` 仅在实际查看对应时间样本后为 true；`evidence` 明确范围。
3. 再次 `review --judge RECEIPT` 导入回执。过期文件、摘要变化或技术失败均拒绝。`accepted` 保持 false，等待用户接受。
4. 初始计划声明 `revisionScope: [{"layer":"title","properties":["text/sourceText"]}]`。创作 FAIL 后可调用 `revise`，仅支持该范围内 `layer.setText` / `prop.set`，不开放任意命令网关；修订计划必须包含 `expectedProjectSha256`，不得新建 document 或扩大素材/对象范围。
5. 每轮先持久化预算，再基于原工程另存。完整比较非目标属性与关键帧，重开、渲染、再评估。最多 2 轮、任务总期限 1800 秒；连续两次无改善停止。`bestTask` 指向最佳已评价版本，失败现场保留。

工程 PASS、媒体 PASS、创作 PASS/FAIL/NOT_RUN、用户接受分别记录。取消进程后如果存在已尝试而无回执的编辑，状态保持 reconciling，终止成功不等于编辑未发生。

受管理执行通过独立 `process_guard.py` 持有生命周期锁。监督进程消失时控制管道关闭，守护器继续停止自有进程树并写入 `lifecycle.json`；reconcile 在生命周期锁被占用或停止证据不完整时拒绝核对续写。POSIX 使用独立进程组，Windows 使用带门控启动的 Job Object，Windows 原生验证仍待完成。没有生命周期证据的旧任务只能诊断，不能据 PID 推断可以恢复。

分段恢复：先 `reconcile` 核对原任务及自有进程停止证据，再 `resume`。工程、输入、运行时、执行资源及帧检查点必须一致；只续跑导出，完整已完成段和编辑回执保全。重复调用已交付任务返回原结果，不重发编辑。

共享资源：受管理 `workflow` 在预览/导出前将帧数和解码字节预占到根任务 `resources` 账本；父子共享10000帧、64GiB解码量与2GiB编码媒体上限，序列仍保留原有更严格的单次限制。初次输出及修订合计使用额度；恢复复用原预占，失败不自动归还。实际媒体字节按高水位记录，删文件或重启不会降低已用量。使用 `inspect --task ROOT_ID` 查看根任务账本；子任务的 `parent` 指向原任务族。缺少账本的历史任务仅可诊断；损坏或悬空预占保留现场并拒绝写入。命令计划、桌面、CPU/内存及跨平台资源计量仍待验收。

当前限制：管理入口不自动重放部分创作任务。Web 与 FreeBSD 不走 Linux 二进制；分别使用浏览器与源码通道，并单独记录验收。


## Web 与 FreeBSD 独立通道

`additional_platforms.py web-install --archive PINNED_ZIP` 验证并安装固定 Web 包，`web-serve --port 0` 只在回环地址提供带 COOP/COEP 的站点。浏览器载入后使用本技能 `web_adapter.mjs` 的 `discover/inspect/readArtifact`，读取上游公开的 `window.effectcraft` API。Web 的受管理写入与完整作品验收仍是独立开放项；不能把页面载入当成创作成功。

`additional_platforms.py freebsd-build` 只在实际 FreeBSD 上执行固定提交源码的 `cargo build --locked` 和引擎测试，要求已准备构建工具与锁文件列出的系统库。失败保留构建日志和源码，不借用 Linux 包或静默安装全局工具。当前主机没有 FreeBSD 目标环境，源码构建及原生任务验收未通过。
