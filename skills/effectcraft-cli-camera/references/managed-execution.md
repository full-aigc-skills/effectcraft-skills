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
2. 使用显式 `effectcraft-judge-request/v2` / `effectcraft-judge-receipt/v2`。回执原样绑定 `requestId`、`taskId`、`binding`、`criteriaHash`、`scopeHash`；实际观察请求的帧样本后填写 `capabilities`、`observations`（媒体路径/摘要、帧索引、方法及观察描述）、`status`、`score`、`passed`、`issues`、`temporalReviewed`。缺视觉/时序能力或样本覆盖时返回 NOT_RUN，不计分、不选最佳。具体宿主步骤见 [Codex Judge 适配](codex-judge.md)。
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


## 固定版本评价 / Settled version reviews

`review` 对同一版本复用原Judge请求。任务族的评价标准从首次请求起固定，重复导入同一回执不会再次计入停滞；同一请求的冲突评分拒绝。已结算请求、响应和报告保存在任务私有 `reviews/REQUEST_ID/`，根任务内部 `effectcraft-review-ledger/v1` 原子结算，子引用写入中断可由相同导入修复。`inspect` 返回的 `bestVerified` 绑定最佳工程/技术验证版本及不可覆盖的报告摘要。原产物改变、回执损坏、祖先取消或期限到达会拒绝新的评价状态变更。缺少评价账本的历史评分仅允许检查，不自动重置比较和停滞预算。

For a settled version, `review` reuses its original Judge request. A task family keeps the first criteria; identical imports are idempotent and conflicting responses are rejected. Immutable request/response/report files live in private `reviews/REQUEST_ID/` directories. The root `effectcraft-review-ledger/v1` commits each version once, and an interrupted child reference can be repaired by the same import. `bestVerified` binds the best engineering/technical verified version to its report digest. Changed artifacts, corrupt receipts, ancestor cancellation or deadline expiry prevent further review mutations. Historical scores without this ledger remain diagnostic; comparison and stagnation budgets are never reset automatically.

Judge v2仅验收`scope.coverage=sampled`列出的具体样本，不能据此声称全帧创作通过。旧v1请求/评分保留诊断读取，不自动升级或用于新的修订。无能力的回执保存在`review-attempts/`，不会消耗停滞次数。 / Judge v2 accepts only its declared sample coverage. It does not claim all-frame creative acceptance. Legacy v1 requests/scores remain diagnostic; NOT_RUN receipts are retained without scoring or consuming stagnation.

## 视频与素材复检 / Video and dependency verification

视频技术检查实际解码全部媒体，核对合成帧数、零起点及连续时间格；封装时长容差不能掩盖少一帧。声明alpha的视频须实际解码为带alpha的像素格式，不透明视频不能冒称透明保真。素材声明的包内路径与摘要必须同时匹配实际文件和交付文件表。缺解码器保留NOT_RUN；这些技术结果不能代替原生工程重开或创作评价。

Video checks decode the media and verify exact composition frame count, zero-based timestamps and continuous frame timing. Duration tolerance cannot hide a missing frame. Declared video alpha requires an actual decoded alpha pixel format; opaque media does not prove transparency. Each declared dependency must match both its actual package file and file-table digest. Missing decoders remain NOT_RUN. Technical results do not replace engineering reopen or creative judgment.

## 当前工程检查 / Current engineering verification

`review`每次都核验任务绑定的已安装原生运行时，在临时目录复制工程及声明素材，实际重开、执行缺失素材检查，并比较原生合成与图层。原工程和素材不保存、不修改；前后摘要变化会失败。缺运行时或重开超时保持工程NOT_RUN，不能沿用历史PASS；原生错误或结构差异为FAIL。已结算报告原样保留，当前检查不通过时创作NOT_RUN、不可接受，不生成新的视觉请求。`revise`在预算检查后、扣减轮数前再次执行同一工程核验。

Each `review` verifies the task-bound installed native runtime, copies the project and declared assets to a temporary package, reopens it, checks missing footage and compares the exact native composition/layers. It never saves or edits originals; changed original digests fail. Missing runtime or incomplete timeout is engineering NOT_RUN, while native errors/structural drift fail. Immutable historical reports remain intact but do not replace current verification. Failed current checks leave creative NOT_RUN, with no new visual request. `revise` repeats engineering verification before consuming a revision round.

质量回执兼容`accepted`布尔值，并增加独立`userAcceptance.status=NOT_RUN`；工程、技术和模型创作通过均不能代替明确的用户决定。 / The quality report retains the compatible `accepted` boolean and adds independent `userAcceptance.status=NOT_RUN`. Engineering, media and model judgments never substitute for an explicit user decision.

## 命令与桌面交付复检 / Command and desktop delivery review

受管理 `--mode commands` 和 `--mode desktop` 会在任务状态目录保存内部交付观察：保存/PNG渲染前读取全部原生合成与图层，返回后固定工程、媒体与素材摘要。`craft-command-plan/v1`、`craft-command-receipt/v1` 和用户输出文件名保持兼容；不向交付目录写入额外 manifest/native 文件。多次写入同一路径只把最后明确写出的文件列为当前交付，之前观察保留。

`review --task TASK --criteria CRITERIA.json` 核对原成功回执和完整输出清单，使用固定运行时隔离打开每个当前工程，检查全部合成、图层和素材。PNG按自身渲染时合成、实际解码尺寸及alpha核验；只有匹配保存版本的媒体才能通过来源关联。未保存渲染版本、未覆盖导出、缺运行时或观察记录变化不会被旧PASS覆盖。缺观察的历史命令任务仅供诊断，不补建基线、不重放。

当前命令与桌面候选在工程/技术PASS后产生既有Judge v2请求，复用不可覆盖账本。`scope.contexts`分别绑定每个合成/原生版本及素材身份、时间基准和所需帧；每个媒体通过`context`关联对应范围。必须分别满足各上下文样本并实际查看全部`requiredMediaPaths`，不同作品不能互补缺帧。缺视觉/时序/媒体覆盖保留NOT_RUN；冲突或过期回执拒绝，相同回执幂等。创作PASS不代签用户接受。命令视频/序列及自动局部修订整合仍待完成。

Managed commands and owned-desktop runs persist internal observations in task state, binding each saved project or named PNG to its native context and actual bytes. Public command schemas and user outputs stay compatible. Review checks the original receipt, full inventory, every saved composition/layer and dependency through isolated native reopening, and actual PNG dimensions/alpha against its own render context. A later project cannot stand in for an unsaved render version. Historical tasks without observations remain diagnostic-only. Video/sequence, Judge and automatic command revision integration remain open; engineering/technical PASS alone never sets creative or user acceptance to PASS.

Command/desktop review now emits the existing Judge v2 request after current engineering and technical gates. `scope.contexts` independently binds each composition/native version, dependency identity, timebase and required frames; media rows reference their context. Observe every required media path and meet each context’s sample coverage. Frames from different works cannot fill one another’s gaps. Missing visual/temporal/media evidence remains NOT_RUN; conflicting/stale receipts are rejected and identical imports are idempotent. User acceptance stays independent. Command video/sequence and local revision integration remain open.
