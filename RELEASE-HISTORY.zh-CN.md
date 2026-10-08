# 版本绑定的历史发行记录

## dev.56 — 2026-10-09

修正新增派发测试在Windows cp1252下读取中文技能清单失败：显式UTF-8，不修改技能运行载荷。替代source55／plugin57发行配对，保留旧标签与失败CI。完整V1仍有70项开放。

Fix UTF-8 decoding in portable routing tests; original failed Windows CI is retained. Execution payloads unchanged, full V1 remains open.

## dev.55 — 2026-10-09

15个技能默认受管理三模式派发；只读预检和旧状态拒绝执行合同通过。源码589项548通过／41条件跳过；本机三模式原生组合证据绑定未变执行资源，完整平台及固定宿主门禁仍开放，V1剩余70项。插件消费技能源dev.55固定发行快照。

Managed routing guidance and native three-mode composition evidence. Full V1 and native platform/host gates remain open. [Routing evidence](docs/evidence/managed-default-routing-20261009.json) · [Native composition evidence](docs/evidence/managed-three-mode-composition-20261009.json).

## dev.54 — 2026-10-09

严格绑定操作回执的版本、任务、操作与参数身份，拒绝孤立材料和冲突覆盖。9.3.5管理入口验收完成：583项源码测试中545通过、38条件跳过；真实原生分段恢复及Codex观察后局部修订通过。完整V1剩余72项；其他平台原生、固定宿主派发及三模式完整组合仍开放。

Strict operation receipt binding and orphan/conflict protection. Management-interface task9.3.5 is verified with public entry tests and scoped native recovery/revision evidence. Full V1, native platform and fixed-host gates remain open. [Evidence](docs/evidence/managed-public-interface-candidate-20261009.json).

## dev.53 — 2026-10-09

完整载荷能力证据绑定与历史任务只读管理保护；直接取消使用原冻结控制器。技能源 dev.53／插件 dev.55 为预发行版，完整 V1 与平台／宿主门禁保持开放。

## dev.52 — 2026-10-09

取消恢复与父子终态屏障。等待全部后代停止；未知编辑保持 reconciling，不生成虚假业务退出或重放。27 项取消测试及真实 macOS 原生父子中断恢复通过；其他平台原生、宿主及完整 V1 仍开放。

Cancellation recovery and family completion barrier. Unknown edits remain reconciling; no invented business exit or editing replay. Native platform/host and full V1 gates remain open.

## dev.51 — 2026-10-09

开发版技能源 dev.51／插件 dev.53：POSIX 私有进程组归属及 nonce 绑定业务结果覆盖守护器丢失、孤儿后代和强制取消。当前回归及离线安装副本证据见 [发布验证](docs/evidence/group-ownership-release51-20261009.json)。下方历史检查点保留原摘要；跨平台原生、固定宿主、创作验收及完整 V1 仍开放。

## dev.50 — 2026-10-09

修正 Windows PowerShell 启动描述缺失时的稳定 bound_entry_invalid 诊断；失败仍拒绝执行、不创建材料、不准备当前 Python。source dev.49 的 Windows CI 失败记录保留，由 source dev.50／plugin dev.52 替代；原发布标签及归档不改写。完整 V1、其他原生平台及宿主验收仍开放。

Fix stable PowerShell missing-entry diagnostics; execution remains fail-closed. Supersedes source dev.49 / plugin dev.51 without rewriting their tags or archives. Full V1 remains open.


## dev.49 — 2026-10-09

技能源 dev.49／插件 dev.51：可信 v2 任务在当前 Python 安装前选择并校验原解释器；新增 CRAFT_RUNTIME_ARCHIVE 离线制品连接，显式参数优先，失败不回落联网。旧 v1 仍可检查，不自动重放。macOS 原生工程重开与完整解码已复核；Windows 原生、固定宿主及完整 V1 保持开放。

### Previous README status checkpoints

未发布的任务入口候选：可信 v2 任务在准备当前 Python 前选择并校验原解释器。当前缓存为空、归档错误且当前 Python 锁损坏时，macOS 隔离3.13.15／原生0.3.1实际恢复、工程重开和12帧解码通过；启动证据缺失／篡改则保留并拒绝执行。已发布 source48／plugin50 快照不变，真实 Windows 入口及完整9.29仍开放。[证据](docs/evidence/task-bound-entry-candidate-20261009.json)。

开发版技能源 dev.48／插件 dev.50 包含安装回执保护及 macOS 隔离 Python／原生版本升级的限定验证：490 项回归（452 通过／38 条件跳过），PowerShell 本机函数 19 例通过。真实 Windows 与固定宿主待验收；新 Python 准备失败仍阻止旧任务恢复（OpenSpec 9.29）。75 项任务及完整 V1 保持开放。[证据](docs/evidence/isolated-python-upgrade-candidate-20261009.json)。

上一原生升级组件：安装回执校验及macOS真实0.3.1→0.4.0活动任务隔离验证通过；486项回归（448通过／38条件跳过）。旧任务保留原代码与Python3.13.5执行文件，新任务使用隔离Python3.13.16及0.4.0；外部旧Python不作为隔离标准库证明。固定source47/plugin49不含此次安装器改动；跨状态根清理、其他平台／宿主及完整V1仍开放。[证据](docs/evidence/runtime-upgrade-component-candidate-20261009.json)。

工作区执行绑定候选：任务私有快照与原控制器恢复通过24项目标和482项回归（444通过／38条件跳过），并完成本机限定原生恢复。开发版source47/plugin49包含该组件；固定安装后的宿主验收仍开放；74项实施任务及完整V1仍开放。[证据](docs/evidence/task-execution-binding-candidate-20261009.json)。

开发版技能源45已完成只读doctor／目录任务9.2.1：显式已验证CLI能力发现、恢复argv和离线差异。回归420通过／38条件跳过，15个单技能实际诊断及15次无Python只读诊断通过。开发版source47/plugin49包含本增量，74项实施任务及完整V1仍开放。[证据](docs/evidence/doctor-capabilities-candidate-20261008.json)。

分段首用指南已根据固定 Film40／Effect38／Art117 的原生验收更新：覆盖 HD 全帧、返工、恢复和迁移。新指南快照的插件安装验收另行记录。[证据](docs/evidence/craft-fixed-segmented-hd-refresh-20261008.json)。

> **开发版 dev.48（2026-10-09）：**技能源 dev.48 新增 Python 和 CLI 安装回执严格校验，记录限定原生升级证据；完整 V1 及其他平台／宿主验收继续开放。


## dev.48 — 2026-10-09

新增严格 Python／CLI 安装回执校验，15 个独立技能资源同步。490 项回归：452 通过／38 条件跳过；PowerShell 本机函数19例通过，macOS 完整隔离发行升级与原生工程／12帧解码通过。任务9.26–9.28为限定组件证据；9.29旧任务入口缺陷、75项开放任务、其他平台／宿主与完整V1未完成。

Strict Python/CLI receipt validation; bounded macOS upgrade and native decode evidence. 452 regression passes / 38 conditional skips; 19 local PowerShell function cases. Old-task bootstrap gap 9.29, 75 tasks and full V1 remain open.

## dev.47 — 2026-10-09

修正新增绑定测试读取中文JSON时的Windows默认编码问题，显式使用UTF-8。执行技能载荷与dev.46相同，保留其标签和失败CI记录；dev.46草稿由本版替代。

Fix Windows JSON test decoding with explicit UTF-8. Runtime payload is unchanged from dev.46; supersedes its draft without rewriting tags.

## 开发版 dev.46 — 2026-10-09

15 个独立技能新增任务私有执行快照及原 Python／控制器／运行时绑定。24 项绑定测试及482项回归（444通过／38条件跳过），含本机 macOS 限定原生恢复证据。任务9.25组件完成；74项任务、跨版本清理、目标平台与固定宿主验收及完整V1仍开放。

## 开发版 dev.45 — 2026-10-08

Windows 恢复参数测试改为比较短/长路径对应的文件身份，技能载荷与 dev.44 相同。保留原始标签，不改写已发布历史。


## 开发版 dev.44 — 2026-10-08

15 个独立技能新增只读 doctor、已校验原生能力发现、可执行恢复参数及离线命令/schema 差异。未完成的运行时绑定草稿不纳入本版；完整 V1、其他目标平台及安装后宿主验收仍开放。


开发版 dev.43：命令／桌面PNG修订的共享资源记账、只读过期／取消核对和历史资源缺失保护；任务9.23限定范围完成。426项回归中388通过、38条件跳过；macOS两种模式真实局部修订通过。75项任务及完整V1继续开放。详见 docs/evidence/command-revision-resource-candidate-20261008.json。

开发版dev.42新增限定范围的命令／桌面局部修订、原生保全回执与已证明未执行的核对。40项目标测试；403项回归365通过、38条件跳过。原生命令视觉修订及素材保全通过；桌面中断尚未验收，9.23和完整V1继续开放。[证据](docs/evidence/command-revision-candidate-20261008.json)。

技能源dev.41：受管理命令／桌面Judge v2与不可变评价账本集成（任务9.22）。10项目标测试、325项回归通过／38项条件跳过；macOS arm64原生多合成抽样评价及拒绝门禁通过。任务9.23局部修订尚未完成，草稿不纳入本次发行；完整V1及固定宿主验收继续开放。

技能源dev.40：受管理命令/自有桌面原生观察、保存工程/PNG只读复检、原生修订号及真实素材来源绑定。28项目标测试；回归315通过/38条件跳过。完整V1及固定宿主验收保持开放。

技能源dev.38：Judge v2与不可覆盖版本评价账本、普通/分段序列复检、过期评价公开CLI拒绝诊断；298项回归260通过/38条件跳过。历史候选原生视觉闭环与本次入口复验分别绑定摘要，其他平台/固定宿主及完整V1保持开放。

技能源dev.37修正合同/回执的显式UTF-8读写及确定性LF生成。Windows CI暴露默认代码页失败，新增生成器与运行时中文回归。技能运行资源相对dev.35/36变化，旧证据保留为历史，最终固定发行原生验证单独记录。

技能源dev.36修正管道测试夹具，在Windows按原始二进制输出LF；技能内容与dev.35一致。保留dev.35的Windows CI失败记录，新目标CI独立核验。

技能源 dev.35：隔离 Python 启动、持久任务执行、原生分段恢复及共享重试预算。源码回归213通过、38条件跳过；macOS arm64未发布原生段恢复及12帧像素对照通过。其他平台/宿主与完整V1保持开放。[证据](docs/evidence/managed-orphan-retry-component-20261008.json)。

以下记录逐字移自 README 前部，描述各自版本，不作为当前安装合同。

固定EffectCraft插件dev.32／源dev.30通过本领域每个技能的独立冷安装、7项安装保护和1项冷原生创建／重开／返工／导出。三个更新领域合计41个独立空缓存、21项保护和3项原生验收通过，全部64安装摘要保持不变。Art捆绑升级与完整V1另行验收。[证据](docs/evidence/craft-three-domain-output-guards-fixed-first-use-20261007.json)。

EffectCraft 技能源dev.30候选在原生会话前保护公开工作流目标：7项保护测试、120项源回归（32项需显式环境的测试跳过）及1项实际冷原生创建／返工／重开／导出通过。完成记录绑定实际计划、原工程与运行时摘要。固定安装与Art捆绑升级分别验收。[证据](docs/evidence/effectcraft-output-execution-candidate-20261007.json) · [架构](docs/EffectCraft-Output-Execution-Architecture.zh_CN.md)。

固定插件31／源29跟踪验收通过：15技能发现零错误，原生冷任务与公开计划冷创建／重开通过，12关键帧保全，15安装摘要不变，两公开附件核验通过。 [Evidence / 证据](docs/evidence/effectcraft31-fixed-tracking-first-use-20261007.json).

技能源dev.29补充本地跟踪解码与实际结果指南，模板应用前记录track.status。单技能候选冷启动命令计划创建和重开通过，产生12个关键帧；固定插件31／源29分发及跟踪验收通过。[候选证据](docs/evidence/effect-tracking-guide-candidate-20261007.json)。

领域场景验收现为 **43项原生测试通过／全部42个不同场景技能**。固定安装跟踪用例使用受支持H.264 High通过；此前无损输入不受原生解码器支持，失败证据保留。Art角色专项、实际Skills CLI及完整V1仍开放。 [Evidence / 证据](docs/evidence/craft-fixed-tracking-supported-input-20261007.json).

追加专项验收：**累计42项原生测试通过，覆盖41／42个领域场景技能**。多机位、带时间文本转录、滤镜及Puppet补验通过；Effect跟踪视频纹理未出现在预期像素，分析实际关键帧为0，尚未验收。64个安装摘要保持。Art角色专项、自动ASR、实际Skills CLI和完整V1继续开放。[证据](docs/evidence/craft-fixed-additional-task-scenes-20261007.json)。

已安装专项技能首用：**38项原生测试／37个不同领域场景技能通过**，各自使用独立空运行时。Film多机位／转录、Photo滤镜、Effect Puppet／跟踪五项尚未纳入本业务门禁；Art角色专项任务与通用Skills CLI另行验收。全部64安装摘要不变。[证据](docs/evidence/craft-fixed-installed-task-scenes-first-use-20261007.json)。

当前固定版本首版代表任务通过：四领域已安装技能各自使用新公开运行时缓存，验证可编辑原生工程、重开、局部返工及导出。覆盖短片字幕／配音同步与素材移动、片头改字保留动画、海报图层／蒙版／PSD／尺寸变体、矢量布尔／多画板／SVG-PDF-PNG／改色。全部64安装摘要不变。本证据仅覆盖四个代表任务，不等于完整首版或所有专项场景。[证据](docs/evidence/craft-fixed-v1-representative-native-baseline-20261007.json)。

逐技能独立冷启动：**64／64通过**（macOS arm64、Python3.13.5，620.155秒）。每个单技能分别使用独立空运行时与默认公开下载；锁定原生版本和命令发现通过，安装技能摘要不变。通用Skills CLI安装及完整首版仍开放。[证据](docs/evidence/craft-fixed64-every-skill-cold-first-use-20261007.json)。

当前独立技能源：`0.1.0-dev.29`。严格命令计划 JSON 在安装或编辑前拒绝重复键；本领域全部独立技能的隔离副本计划测试通过。固定领域插件安装、计划拒绝及原生代表场景复验通过；逐命令原生与完整首版验收仍开放。

发行前候选记录：未发布候选新增 `effectcraft-cli-puppet`，负责10条木偶命令。两个位置针脚的原生变形、保存重开状态与渲染像素一致性通过；全部针脚类型、录制、跟随及创作质量验收仍开放。固定插件28／技能源26仍包含14技能。[候选证据](docs/evidence/effect-puppet-candidate-20261007.json)。

固定安装复验：五插件共62技能在隔离Codex宿主中加载成功，加载错误0；62技能完整命令查询与场景资源核对通过，248项安装失败诊断检查通过；四个新增专项技能的空运行时安装、版本与查询通过。原生创作、全量命令和完整V1按各自证据验收。[安装证据](docs/evidence/craft-fixed62-installation-20261007.json)。

历史发行记录：当前独立技能源：`0.1.0-dev.26`。独立技能现提供固定桌面与 CLI 安装、自动启动、同会话全命令入口及退出回执。此前固定版本58技能首次使用通过，当前源码四领域进阶桌面通过；本次新固定发布安装复验待完成，全量命令及完整V1仍开放。[使用指南](docs/Craft-Desktop-First-Use-Architecture.zh_CN.md)。

历史发行记录：当前独立技能源：`0.1.0-dev.25`。独立技能现提供固定桌面与 CLI 安装、自动启动、同会话全命令入口及退出回执。此前固定版本58技能首次使用通过，当前源码四领域进阶桌面通过；本次新固定发布安装复验待完成，全量命令及完整V1仍开放。[使用指南](docs/Craft-Desktop-First-Use-Architecture.zh_CN.md)。

固定安装诊断检查：58技能发现通过，184项诊断检查通过；四领域固定副本仍缺失安装脚本本身不存在时的补充修复，当前验收为部分完成。Art插件dev.92锁定技能源dev.66。[证据](docs/evidence/craft-first-use-diagnostics-installed-20261007.json)。

历史发行记录：当前独立技能源：`0.1.0-dev.24`。独立技能现提供固定桌面与 CLI 安装、自动启动、同会话全命令入口及退出回执。此前固定版本58技能首次使用通过，当前源码四领域进阶桌面通过；本次新固定发布安装复验待完成，全量命令及完整V1仍开放。[使用指南](docs/Craft-Desktop-First-Use-Architecture.zh_CN.md)。

本次固定版本追加原生验收：Art十项冷启动、四领域四项GUI编辑与保存重开，以及品牌色局部返工、依赖更新和交付打包通过；全量命令、全部GUI和创作质量仍待验收。[证据](docs/evidence/craft-fixed-scene-guidance-20261007.json)。

固定安装场景指引验收：五插件58技能发现与内容摘要、示例引用及完整命令查询通过；四领域运行脚本与锁和示例保持原固定版本身份。Art新分发十项实际冷启动复验通过，全量命令和完整V1仍开放。[证据](docs/evidence/craft-fixed-scene-guidance-20261007.json)。

历史发行记录：当前独立技能源：`0.1.0-dev.23`。独立技能现提供固定桌面与 CLI 安装、自动启动、同会话全命令入口及退出回执。此前固定版本58技能首次使用通过，当前源码四领域进阶桌面通过；本次固定安装发现、场景资料与代表原生任务复验通过，全量命令及完整V1仍开放。[使用指南](docs/Craft-Desktop-First-Use-Architecture.zh_CN.md)。

历史发行记录：当前独立技能源：`0.1.0-dev.22`。完整反射命令入口、独立CLI与桌面安装已提供；固定版本58项独立冷启动、四领域进阶GUI保存／重开／渲染及Art混合返工通过。逐条原生命令执行验收与完整V1保持开放。[固定验收记录](docs/evidence/craft-full-command-fixed-first-use-20261007.json)。

历史发行记录：当前独立技能源：`0.1.0-dev.21`。独立技能现提供固定桌面与 CLI 安装、自动启动、同会话全命令入口及退出回执。候选源码48项冷启动通过；本次固定发布安装复验待完成，全量命令及完整V1仍开放。[使用指南](docs/Craft-Desktop-First-Use-Architecture.zh_CN.md)。

历史发行记录：当前独立技能源：`0.1.0-dev.20`。独立技能现提供固定桌面与 CLI 安装、自动启动、同会话全命令入口及退出回执。候选源码48项冷启动通过；本次固定发布安装复验待完成，全量命令及完整V1仍开放。[使用指南](docs/Craft-Desktop-First-Use-Architecture.zh_CN.md)。

历史 CLI 验收（原固定版本范围）：当前固定版本的 58 个技能全部通过独立冷启动：单技能目录、空运行环境、公开安装、版本查询及完整命令发现。此证据不代表 2639 条命令全部执行通过或完整场景验收。 [Evidence](docs/evidence/codex-current58-cold-cli-first-use-20261007.json).

历史发行记录：当前首次使用入口：插件 `0.1.0-dev.21`，技能源 `0.1.0-dev.19`。中英文安装与命令指南按当前固定发行核验；历史样例证据保留原版本范围。 [Guide](docs/Craft-Native-Gateway-Usage.zh_CN.md).

固定原生命令网关首用通过：48项领域安装技能与十项 Art85／技能源58 的公开入口独立冷安装、创建／重开／导出、返工并保全原交付。公开 Brief、四领域网关、五子工程、Logo选择性更新／无关图标复用、移动包、真实取消和六类未知回复故障通过；58项安装摘要不变。全2639命令／GUI／模型／通用Skills CLI／完整V1门禁保持开放。[使用指南](docs/Craft-Native-Gateway-Usage.zh_CN.md) · [固定证据](docs/evidence/codex-native-gateway-first-use-20261007.json)。

Historical source-candidate note: Source candidate: complete native workflow gateway; immutable installed acceptance and full DAG gate6.51 remain pending. [Architecture](docs/Craft-Native-Workflow-Gateway-Architecture.md).



## 历史 README 原文 — 2026-10-09

[完整原文（保留原版本和证据边界）](README-HISTORY-20261009.zh-CN.md)
