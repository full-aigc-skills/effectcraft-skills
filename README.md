# EffectCraft Independent Skills

Create editable `.ecproj` projects, dependencies and media from text, graphics and footage. This is a development release; full V1 remains open. Published releases and local documentation candidates have separate evidence.

Current source: `0.1.0-dev.60`; consuming plugin: `0.1.0-dev.62`; 15 independent skills.

| Field | Value |
| --- | --- |
| Metadata version | 0.1.0-dev.60 |
| Skills source | effectcraft-skills / v0.1.0-dev.60 |
| Acceptance | Development; full V1 OPEN |


## First use

Invoke **`effectcraft-use`** in the host. For direct invocation, set `SKILL_DIR` to the absolute directory containing the actually loaded `SKILL.md`. Launchers prepare and verify pinned Python and EffectCraft in user data; system Python, global PATH and readonly skill files are preserved. Offline use requires pinned official archives or an intact verified cache.

<!-- CRAFT_FIRST_USE_START -->
```bash
: "${SKILL_DIR:?Set to the actual loaded skill directory}"
sh "$SKILL_DIR/scripts/launch.sh" doctor
sh "$SKILL_DIR/scripts/launch.sh" run --plan "$SKILL_DIR/examples/brand-intro.json" --output "$PWD/effectcraft-result"
```
<!-- CRAFT_FIRST_USE_END -->

```powershell
$env:SKILL_DIR = "<actual loaded skill directory>"
& (Join-Path $env:SKILL_DIR "scripts/launch.ps1") doctor
```

[Workflow and delivery](skills/effectcraft-use/references/workflow.md) · [Setup and diagnostics](skills/effectcraft-cli-setup/SKILL.md). Generic Skills CLI installation and fixed-host natural-language dispatch retain separate acceptance gates.


## Current capabilities and evidence

The maintainer-generated [current matrix](docs/current-capabilities.json) binds the complete skill payload, Python/native artifacts and original report digest. Published source53 macOS arm64 technical samples passed. The dev.54 receipt-identity changes invalidate that report for the current payload; its generated matrix stays NOT_RUN until rebound to current evidence. Other architecture, browser, FreeBSD, creative and host gates stay NOT_RUN until verified. Portable CI contracts do not establish native creative acceptance.

The source53/plugin55 [15-skill report](docs/evidence/native-smoke-source53-20261009.json) passes native reopen and 12 decoded frames per case, using verified caches (zero cold installs). It does not prove 15 domain scenarios or model dispatch. [Cancellation recovery and family barriers](docs/evidence/cancel-family-candidate-20261009.json) preserve unknown edits; the full crash/GUI matrix remains open.


## Skill entry points

| Skill | Purpose |
| --- | --- |
| [effectcraft-use](skills/effectcraft-use/SKILL.md) | Task routing and delivery |
| [effectcraft-cli](skills/effectcraft-cli/SKILL.md) | General command planning |
| [effectcraft-cli-setup](skills/effectcraft-cli-setup/SKILL.md) | Runtime setup and diagnostics |
| [effectcraft-cli-project](skills/effectcraft-cli-project/SKILL.md) | Projects and native save/reopen |
| [effectcraft-cli-footage](skills/effectcraft-cli-footage/SKILL.md) | Footage and dependencies |
| [effectcraft-cli-composition](skills/effectcraft-cli-composition/SKILL.md) | Compositions |
| [effectcraft-cli-layers](skills/effectcraft-cli-layers/SKILL.md) | Layers and properties |
| [effectcraft-cli-animation](skills/effectcraft-cli-animation/SKILL.md) | Animation and keyframes |
| [effectcraft-cli-effects](skills/effectcraft-cli-effects/SKILL.md) | Effects |
| [effectcraft-cli-masks](skills/effectcraft-cli-masks/SKILL.md) | Masks |
| [effectcraft-cli-expressions](skills/effectcraft-cli-expressions/SKILL.md) | Expressions |
| [effectcraft-cli-camera](skills/effectcraft-cli-camera/SKILL.md) | Cameras and 3D scenes |
| [effectcraft-cli-export](skills/effectcraft-cli-export/SKILL.md) | Rendering and export |
| [effectcraft-cli-tracking](skills/effectcraft-cli-tracking/SKILL.md) | Tracking |
| [effectcraft-cli-puppet](skills/effectcraft-cli-puppet/SKILL.md) | Puppet pins and recording |

Each skill includes its own runtime resources and installs independently. Bundled references describe parameters, ownership and modes for 655 commands; catalog coverage does not prove every command was executed.


## Inspect, recover and cancel

Use `inspect` for the original task, `reconcile` to verify original receipts, and `resume` only for proven recoverable work. `cancel` persists intent; parents wait for descendants and unknown edits retain reconciling. Never replay unknown edits with a new task ID/output directory. Tasks retain their bound runtimes; corrupt or missing evidence is preserved and blocks further writes.

[Managed execution](skills/effectcraft-use/references/managed-execution.md)


## Maintenance and version history

The skill source owns execution code; the plugin consumes pinned tags, commits and whole-skill digests. The incremental authority is plugin `openspec/changes/establish-v1-plugin`; incomplete gates prevent archival. ArtCraft owns public `craft-task/v1` and `craft-artifact/v1`; EffectCraft consumes them.

[Version records and complete prior README](RELEASE-HISTORY.md) · [Plugin specifications](https://github.com/full-aigc-plugins/effectcraft-plugin/tree/main/openspec/changes/establish-v1-plugin)

The dev.54 [public interface acceptance](docs/evidence/managed-public-interface-candidate-20261009.json) completes task 9.3.5: receipt identity/orphan guards and nine management roles, with actual native recovery and Codex-observed local revision. Source54/plugin56 distribute this increment; source53/plugin55 remain historical releases. Other native platforms and fixed-host dispatch remain open; subsequent local three-mode composition evidence is below. The [source52 report](docs/evidence/native-smoke-source52-20261009.json) is historical evidence.

Local [three-mode public composition acceptance](docs/evidence/managed-three-mode-composition-20261009.json) completes task 9.3.6 against unchanged released source54/plugin56 payloads: workflow, command plans and actual owned desktop sessions pass installation/adapters/ledger/receipts/recovery, with original-plan replay refusal and legacy CLI compatibility. Default regression: 586 tests, 545 passed, 41 conditional skips; three native conditional cases separately pass. This test/evidence increment is distributed in source55/plugin57; its original native payload binding remains source54/plugin56. Full crash/GUI, other native targets, fixed-host dispatch and full V1 remain open.


Source dev.55 / plugin dev.57 distribute [default managed routing](docs/evidence/managed-default-routing-20261009.json): all 15 skills document workflow/commands/desktop writes; 45 readonly preflights and 18 legacy-action cases pass. Regression: 589 tests, 548 passed, 41 conditional skips. Tasks9.3.1 and9.3.6 are complete; 70 tasks remain open. Native evidence reuses only 105 unchanged execution resources; three guidance files differ. No new model dispatch or full-platform acceptance is claimed. Candidate reports retain their original validation timestamp; release bindings are recorded separately.


Source56/plugin58 fix Windows default-encoding dependence in the new routing tests by reading UTF-8 explicitly. Source55 failed Windows CI and original tags are retained. Skill execution payloads are unchanged; no new native or host acceptance is claimed.


Unpublished [source revision conflict protection](docs/evidence/source-revision-conflict-candidate-20261009.json) rechecks the source before each operation intent and final delivery. An external native save blocks the next edit while preserving the new source and existing receipts. Regression: 595 tests, 553 passed, 42 conditional skips; the explicit native save-conflict case also passes. Full task9.3.2 GUI/session/cross-state-root gates remain open; published source56/plugin58 snapshots are unchanged.


Unpublished [cross-store project claims](docs/evidence/shared-project-claims-candidate-20261009.json) coordinate source paths/file objects for new tasks. Missing, corrupt or unknown owners are not automatically cleared. Two real processes select only one owner; the native owner continues and saves/reopens after a competing store is rejected. Regression: 606 tests, 563 passed, 43 conditional skips; all 15 private resource copies match. GUI, complete sessions, parallel old runtimes and platform/host task9.3.2 gates remain open. Published snapshots are unchanged.

Local inode-generation repair candidate: project claims bind creation time in addition to device/inode, distinguish recycled file numbers, preserve legacy unknown claims, and fail closed when creation identity is unavailable. [Candidate evidence](docs/evidence/project-creation-generation-candidate-20261009.json) records the exact source and validation scope. Published source57/plugin59 remain unchanged; task9.3.2, desktop in-memory conflict and full V1 remain open.

Local desktop revision candidate: owned managed sessions persist project/editor context and atomically guard execute_command, batch, open/save and run_script. Unmapped helpers are refused before sending; confirmed read tools are checked again afterward. [Evidence](docs/evidence/desktop-native-revision-candidate-20261009.json) separates native mapping, owned desktop control edits and installed public-entry checks from model dispatch and physical GUI input. Old published snapshots remain unchanged; full9.3.2 and V1 remain open.

Desktop atomic-conflict reconciliation candidate: `docs/evidence/desktop-conflict-reconcile-candidate-20261009.json`. Versioned proofs bind the task, operation arguments, original session baseline and stopped owned desktop. Public reconcile/resume can identify an individual operation as not executed while preserving attempted intents and successful receipts. Legacy proofs, non-atomic changes and missing stop evidence remain unknown; unresolved tasks block replacement task IDs. This increment is unpublished; full 9.3.3/9.3.4 and V1 remain open.

Source59 / plugin61 development release includes atomic desktop conflict reconciliation and versioned command completion seals. Recovery verifies original results before registering delivery; missing or changed evidence refuses recovery, and cancellation prevents late delivery. Earlier candidate reports retain their historical scope; see `docs/evidence/release59-validation-20261009.json` for this release. Full fault/recovery, other native platforms, host acceptance and V1 remain open.

Historical unpublished [real worker crash candidate](docs/evidence/command-completion-crash-candidate-20261009.json): commands and owned desktop cover SIGKILL before the proof, between proof and reference, and after both are durable. Only a complete original proof permits delivery registration after owned-process stop, isolated native reopen and actual PNG decode; missing or orphan proofs stay unknown and repeated resume does not replay edits. Malformed ownership returns structured failure without treating corruption as absence. Source59/plugin61 remain unchanged; full 9.3.3/9.3.4, other native platforms and fixed-host gates remain open.

Source60 / plugin62 release distributes the real worker crash increment and strict ownership validation. Candidate reports retain their original unpublished observation context; release binding is recorded in `docs/evidence/release60-validation-20261009.json`. Full V1 remains open (70 tasks).
