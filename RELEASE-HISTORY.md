# Version-bound release records

## dev.50 — 2026-10-09

修正 Windows PowerShell 启动描述缺失时的稳定 bound_entry_invalid 诊断；失败仍拒绝执行、不创建材料、不准备当前 Python。source dev.49 的 Windows CI 失败记录保留，由 source dev.50／plugin dev.52 替代；原发布标签及归档不改写。完整 V1、其他原生平台及宿主验收仍开放。

Fix stable PowerShell missing-entry diagnostics; execution remains fail-closed. Supersedes source dev.49 / plugin dev.51 without rewriting their tags or archives. Full V1 remains open.


## dev.49 — 2026-10-09

Source dev.49 / plugin dev.51: trusted v2 task dispatch before current Python preparation, plus CRAFT_RUNTIME_ARCHIVE offline native artifact selection without network fallback. Legacy v1 inspection remains compatible. Current macOS native reopen/decode revalidated; native Windows, fixed-host and full V1 remain open.

### Previous README status checkpoints

Unpublished task-entry candidate: trusted v2 tasks select and verify the original Python before any current-Python preparation. Actual macOS isolated3.13.15/native0.3.1 resume, project reopen and12-frame decode pass with an empty current cache, bad archive and corrupt current Python lock. Missing/tampered evidence rejects without repair. Source48/plugin50 snapshots are unchanged; nativeWindows entry and full9.29 remain open. [Evidence](docs/evidence/task-bound-entry-candidate-20261009.json).

Development source dev.48 / plugin dev.50 includes installation-receipt protection and bounded macOS isolated Python/native upgrade evidence: 490 regressions (452 passes / 38 conditional skips), plus 19 local PowerShell function cases. Native Windows and fixed-host acceptance remain open. A new-Python bootstrap failure still blocks old-task recovery (OpenSpec 9.29); 75 tasks and full V1 remain open. [Evidence](docs/evidence/isolated-python-upgrade-candidate-20261009.json).

Previous native-upgrade component validates installation receipts and actual macOS active-task isolation across official0.3.1→0.4.0;486 regressions (448 passes/38 conditional skips). Old tasks retain their original controller and external Python3.13.5 executable; new tasks use isolated Python3.13.16 and native0.4.0. External Python is not isolated-stdlib proof. Fixed source47/plugin49 excludes this installer increment; cleanup across state roots, other targets/hosts and fullV1 remain open. [Evidence](docs/evidence/runtime-upgrade-component-candidate-20261009.json).

Working-tree execution-binding candidate: task-private snapshots and original-controller recovery pass24 targeted tests and482 regressions (444 passes/38 conditional skips), plus bounded actual macOS recovery. Published source45/plugin47 excludes this candidate;74 implementation tasks and full V1 remain open. [Evidence](docs/evidence/task-execution-binding-candidate-20261009.json).

Development source45 completes readonly doctor/catalog task9.2.1: explicit verified native discovery, executable recovery argv and offline differences.420 regression passes/38 conditional skips;15 readonly single-skill probes and15 no-Python diagnostics pass. Development source47/plugin49 includes this increment;74 implementation tasks and full V1 remain open. [Evidence](docs/evidence/doctor-capabilities-candidate-20261008.json).

Segmented first-use guidance now matches native acceptance of fixed Film40 / Effect38 / Art117, including HD full frames, revision, recovery and relocation. Installation qualification of this new guide snapshot is recorded separately. [Evidence](docs/evidence/craft-fixed-segmented-hd-refresh-20261008.json).

> **Development release dev.48 (2026-10-09):** source dev.48 adds strict Python and CLI installation-receipt checks. Bounded native upgrade evidence is recorded; complete V1 and other platform/host qualification remain open.


## dev.48 — 2026-10-09

新增严格 Python／CLI 安装回执校验，15 个独立技能资源同步。490 项回归：452 通过／38 条件跳过；PowerShell 本机函数19例通过，macOS 完整隔离发行升级与原生工程／12帧解码通过。任务9.26–9.28为限定组件证据；9.29旧任务入口缺陷、75项开放任务、其他平台／宿主与完整V1未完成。

Strict Python/CLI receipt validation; bounded macOS upgrade and native decode evidence. 452 regression passes / 38 conditional skips; 19 local PowerShell function cases. Old-task bootstrap gap 9.29, 75 tasks and full V1 remain open.

## dev.47 — 2026-10-09

修正新增绑定测试读取中文JSON时的Windows默认编码问题，显式使用UTF-8。执行技能载荷与dev.46相同，保留其标签和失败CI记录；dev.46草稿由本版替代。

Fix Windows JSON test decoding with explicit UTF-8. Runtime payload is unchanged from dev.46; supersedes its draft without rewriting tags.

## Development release dev.46 — 2026-10-09

Adds task-private execution snapshots and original Python/controller/runtime binding to all 15 independent skills. 24 targeted tests and 482 regressions (444 passed / 38 conditional skips); bounded macOS native recovery evidence. Task9.25 component complete; 74 tasks, cross-version cleanup, target-platform and fixed-host acceptance, and full V1 remain open.

## Development release dev.45 — 2026-10-08

Fixes the Windows recovery-argv test to compare file identity across equivalent short/long paths. Skill payload is unchanged from dev.44; the original tag remains immutable.


## Development release dev.44 — 2026-10-08

Adds readonly doctor with verified native capability discovery, actionable recovery arguments, and offline command/schema diffs to all 15 independent skills. Runtime-binding drafts are excluded. Full V1, other target platforms and installed host acceptance remain open.


开发版 dev.43：命令／桌面PNG修订的共享资源记账、只读过期／取消核对和历史资源缺失保护；任务9.23限定范围完成。426项回归中388通过、38条件跳过；macOS两种模式真实局部修订通过。75项任务及完整V1继续开放。详见 docs/evidence/command-revision-resource-candidate-20261008.json。

Development source dev.42 adds scoped command/desktop local revision with native preservation receipts and known-not-executed reconciliation. 40 targeted tests; regression 365 passed / 38 conditional skips (403 total). Native command visual repair and imported-asset preservation passed; desktop interruption remains unaccepted. Task9.23 and full V1 stay open. [Evidence](docs/evidence/command-revision-candidate-20261008.json).

Source dev.41: managed command/desktop Judge v2 and immutable review ledger integration (task9.22). 10 targeted tests; 325 regression passes / 38 conditional skips. Native sampled multi-composition review and rejection gates passed on macOS arm64. Task9.23 local revision remains unfinished and excluded from this release; full V1 and fixed-host acceptance remain open.

Source dev.40: managed commands/owned desktop native observations, readonly saved-project and PNG review, native revision/actual-footage source binding. 28 targeted tests; 315 regression passes / 38 conditional skips. Full V1 and fixed-host acceptance stay open.

Source dev.38: Judge v2, immutable version review ledgers, ordinary/segmented sequence checks and public rejection diagnostics. Regression: 260 passed / 38 conditional skips. Historical native visual loops and current entry verification retain separate hashes; other platforms, fixed host acceptance and complete V1 stay open.

Source dev.37 fixes explicit UTF-8 contract/receipt I/O and deterministic LF generation across platforms. Windows CI exposed the default-codepage failure; added generator/runtime Unicode regression. Native skill resources change from dev.35/36, so their old evidence is historical and final native release verification is recorded separately.

Source dev.36 corrects the pipe-reader test fixture to emit exact binary LF bytes on Windows; skill payloads are identical to dev.35. The dev.35 Windows CI failure remains recorded; new target CI is verified separately.

Source dev.35: isolated Python bootstrap, durable managed execution, native segment recovery and shared retry budgets. Source regression: 213 passed / 38 conditional skips; native unpublished-segment recovery and 12-frame pixel comparison passed on macOS arm64. Other platforms/hosts and complete V1 remain open. [Evidence](docs/evidence/managed-orphan-retry-component-20261008.json).

These records were moved verbatim from the README preface. They describe their own versions and are not the current installation contract.

Fixed EffectCraft plugin dev.32/source dev.30 passes independent cold installation for every domain skill,7 installed guard tests and1 actual cold native create/reopen/revise/export case. Across the three updated domains:41 distinct empty caches,21 guards and3 native cases pass; all64 installed skill hashes remain unchanged. Art bundle upgrade and full V1 remain separate. [Evidence](docs/evidence/craft-three-domain-output-guards-fixed-first-use-20261007.json).

EffectCraft source dev.30 candidate protects public workflow output before native sessions:7 guard tests, 120 source regressions (32 explicit-environment skips), and1 actual cold native create/revise/reopen/export test pass. Completed records bind effective plans, source revisions and runtime SHA. Fixed plugin installation and Art bundle integration remain separate gates. [Evidence](docs/evidence/effectcraft-output-execution-candidate-20261007.json) · [Architecture](docs/EffectCraft-Output-Execution-Architecture.md).

Fixed plugin31/source29 tracking acceptance passed:15 skills discovered without errors, native cold task plus public-plan cold create/reopen,12 keys preserved, all15 installed hashes unchanged and both public archives verified. [Evidence / 证据](docs/evidence/effectcraft31-fixed-tracking-first-use-20261007.json).

Source dev.29 adds a local tracking decoding/result guide and records actual status before applying the tracking example. Source candidate cold command-plan creation/reopen passed with12 keys. Fixed plugin31/source29 distribution and tracking acceptance passed. [Candidate evidence](docs/evidence/effect-tracking-guide-candidate-20261007.json).

Domain scene acceptance now has **43 passed native tests / all 42 distinct domain scene skills**. The fixed-installed tracking case passed with supported H.264 High; the earlier lossless input is unsupported by the native decoder and its failed evidence remains historical. Art role-specific tasks, generic Skills CLI and complete V1 remain open. [Evidence / 证据](docs/evidence/craft-fixed-tracking-supported-input-20261007.json).

Additional scene acceptance: **42 native tests passed / 41 of 42 domain scene skills**. Multicam, timed transcript import, filters and Puppet passed. Effect tracking video texture is absent from its expected preview pixels, and analysis produced zero actual keys and remains unaccepted. All64 installed identities remain unchanged. Art role-specific tasks, automatic ASR, generic Skills CLI installation and complete V1 remain open. [Evidence](docs/evidence/craft-fixed-additional-task-scenes-20261007.json).

Installed task-scene first use: **38 native tests / 37 distinct domain scene skills pass** from independent cold runtime directories. Five domain scene skills (Film multicam/transcript, Photo filters, Effect puppet/tracking) remain outside this business gate; Art role-specific tasks and generic Skills CLI are separately open. All64 installed hashes remain unchanged. [Evidence](docs/evidence/craft-fixed-installed-task-scenes-first-use-20261007.json).

Current fixed V1 representative native baseline: four installed domain workflows pass with fresh public runtime caches, editable native projects, native reopen, targeted revision and export checks. Film subtitles/voice sync and relocation, Effect text animation preservation, Photo layers/masks/PSD/size variant, and Vector boolean/artboards/SVG-PDF-PNG/recolor all pass. All64 installed hashes stay unchanged. This is four representative tasks, not full V1 or every scene. [Evidence](docs/evidence/craft-fixed-v1-representative-native-baseline-20261007.json).

Every-skill cold first use: **64/64 passed** on macOS arm64 / Python3.13.5 (620.155s). Each single skill used its own empty runtime and default public downloads; locked native version and command discovery passed, installed hashes unchanged. Generic Skills CLI installation and complete V1 remain open. [Evidence](docs/evidence/craft-fixed64-every-skill-cold-first-use-20261007.json).

Current standalone source: `0.1.0-dev.29`. Strict command-plan JSON rejects duplicate keys before installation or edits. All standalone domain skills pass isolated-copy plan tests. Fixed domain-plugin installation, plan guards and representative native checks pass; complete native command and V1 acceptance remain open.

Pre-release candidate record: Unreleased source candidate adds `effectcraft-cli-puppet` for10 puppet commands. Two-pin native deformation, save/reopen state and rendered pixel identity passed; full pin-kind, recording/follow and creative-quality acceptance remain open. Fixed plugin28/source26 still contains14 skills. [Candidate evidence](docs/evidence/effect-puppet-candidate-20261007.json).

Fixed installation verification: five plugins / 62 skills discovered in isolated Codex, zero loading errors; all62 command/resource checks and248 setup-diagnostic checks passed. Four new specialized skills passed empty-runtime installation, version and command queries. Native creative, exhaustive-command and fullV1 acceptance remain separately scoped. [Evidence](docs/evidence/craft-fixed62-installation-20261007.json).

Historical release record: Current standalone source: `0.1.0-dev.26`. Standalone skills include pinned desktop+CLI installation, owned startup, full-command bridge plans and lifecycle receipts. Previous fixed releases passed 58 basic cold cases; current source passed four advanced desktop cases. Acceptance of this new fixed installed release is pending. Exhaustive commands and full V1 remain open. [Usage](docs/Craft-Desktop-First-Use-Architecture.md).

Historical release record: Current standalone source: `0.1.0-dev.25`. Standalone skills include pinned desktop+CLI installation, owned startup, full-command bridge plans and lifecycle receipts. Previous fixed releases passed 58 basic cold cases; current source passed four advanced desktop cases. Acceptance of this new fixed installed release is pending. Exhaustive commands and full V1 remain open. [Usage](docs/Craft-Desktop-First-Use-Architecture.md).

Fixed installed diagnostics: 58 skills discovered and 184 scoped checks passed. The four frozen domain copies still lack the additional missing-bootstrap-script repair; acceptance remains partial. Art plugin dev.92 pins source dev.66. [Evidence](docs/evidence/craft-first-use-diagnostics-installed-20261007.json).

Historical release record: Current standalone source: `0.1.0-dev.24`. Standalone skills include pinned desktop+CLI installation, owned startup, full-command bridge plans and lifecycle receipts. Previous fixed releases passed 58 basic cold cases; current source passed four advanced desktop cases. Acceptance of this new fixed installed release is pending. Exhaustive commands and full V1 remain open. [Usage](docs/Craft-Desktop-First-Use-Architecture.md).

Additional fixed native acceptance passed: ten Art cold cases, four domain GUI edit/save/reopen cases and mixed brand-color revision with dependency updates and packaging. Exhaustive commands, all GUI interactions and creative quality remain open. [Evidence](docs/evidence/craft-fixed-scene-guidance-20261007.json).

Fixed installed scene guidance: five plugins / 58 skills passed discovery, content identity, local example references and complete command queries. Domain runtime scripts, locks and fixtures retain their prior fixed identity. Art cold verification of its new distribution passed in ten cases; exhaustive commands and full V1 remain open. [Evidence](docs/evidence/craft-fixed-scene-guidance-20261007.json).

Historical release record: Current standalone source: `0.1.0-dev.23`. Standalone skills include pinned desktop+CLI installation, owned startup, full-command bridge plans and lifecycle receipts. Previous fixed releases passed 58 basic cold cases; current source passed four advanced desktop cases. Fixed installed scene guidance and bounded native representatives passed; exhaustive acceptance remains open. Exhaustive commands and full V1 remain open. [Usage](docs/Craft-Desktop-First-Use-Architecture.md).

Historical release record: Current standalone source: `0.1.0-dev.22`. Complete reflected-command entries and standalone CLI/desktop bootstrap are available. Fixed releases passed 58 standalone cold cases, four advanced GUI save/reopen/render cases and Art mixed revision. Exhaustive native command execution and full V1 remain open. [Fixed evidence](docs/evidence/craft-full-command-fixed-first-use-20261007.json).

Historical release record: Current standalone source: `0.1.0-dev.21`. Standalone skills include pinned desktop+CLI installation, owned startup, full-command bridge plans and lifecycle receipts. Previous 48-source-skill cold cases pass; acceptance of this fixed installed release is pending. Exhaustive commands and full V1 remain open. [Usage](docs/Craft-Desktop-First-Use-Architecture.md).

Historical release record: Current standalone source: `0.1.0-dev.20`. Standalone skills include pinned desktop+CLI installation, owned startup, full-command bridge plans and lifecycle receipts. Previous 48-source-skill cold cases pass; acceptance of this fixed installed release is pending. Exhaustive commands and full V1 remain open. [Usage](docs/Craft-Desktop-First-Use-Architecture.md).

Historical CLI-only acceptance (original pinned versions): All 58 current pinned skills pass independent cold CLI first use: one skill directory, empty runtime, public installation, version query and complete command discovery. This proves installation/discovery, not exhaustive execution of 2639 commands or full creative acceptance. [Evidence](docs/evidence/codex-current58-cold-cli-first-use-20261007.json).

Historical release record: Current first-use entry: plugin `0.1.0-dev.21`, skill source `0.1.0-dev.19`. Installation and command guides are checked against the current pinned releases; historical evidence retains its original version scope. [Guide](docs/Craft-Native-Gateway-Usage.md).

Fixed native gateway first use passes:48 independently installed domain skills and ten Art85/source58 public workflows cold-install, create/reopen/export, revise and preserve original deliveries. Art public Brief, all four gateway domains, five child nodes, selective Logo revision/icon reuse, moved package, native cancellation and six unknown faults pass. All58 installed identities are unchanged. Full2639-command/GUI/model/generic Skills CLI/V1 gates remain open. [Usage](docs/Craft-Native-Gateway-Usage.md) · [Fixed evidence](docs/evidence/codex-native-gateway-first-use-20261007.json).

Historical source-candidate note: Source candidate: complete native workflow gateway; immutable installed acceptance and full DAG gate6.51 remain pending. [Architecture](docs/Craft-Native-Workflow-Gateway-Architecture.md).

