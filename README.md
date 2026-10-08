# EffectCraft Independent Skills

Create editable `.ecproj` projects, dependencies and media from text, graphics and footage. This is a development release; full V1 remains open. Published releases and local documentation candidates have separate evidence.

Current source: `0.1.0-dev.54`; consuming plugin: `0.1.0-dev.56`; 15 independent skills.

| Field | Value |
| --- | --- |
| Metadata version | 0.1.0-dev.54 |
| Skills source | effectcraft-skills / v0.1.0-dev.54 |
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

The dev.54 [public interface acceptance](docs/evidence/managed-public-interface-candidate-20261009.json) completes task 9.3.5: receipt identity/orphan guards and nine management roles, with actual native recovery and Codex-observed local revision. Source54/plugin56 distribute this increment; source53/plugin55 remain historical releases. Full three-mode adapter composition, other native platforms and fixed-host dispatch remain open. The [source52 report](docs/evidence/native-smoke-source52-20261009.json) is historical evidence.
