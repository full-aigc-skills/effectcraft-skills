# EffectCraft Skills

Independent EffectCraft skills. Implementation is in progress; this repository is not a completed plugin release.

The `effectcraft-use` skill contains a self-contained Python 3.11+ bootstrap installer for the pinned official macOS arm64 CLI. It verifies the archive and executable, retains license files, atomically installs a new version, and reuses an intact installation without downloading again.

Run tests with `python3 -m unittest discover -s tests -v`. Full creative workflow and host acceptance remain pending.

Normative requirements and implementation tracking: [EffectCraft plugin OpenSpec](https://github.com/full-aigc-plugins/effectcraft-plugin/tree/main/openspec/changes/establish-v1-plugin).

[简体中文](README.zh-CN.md)

The executable workflow now covers native project round trips, transparent PNG previews, H.264 export and text revisions preserving unrelated layers and keyframes. See [workflow guidance](skills/effectcraft-use/references/workflow.md). Run live tests with `CRAFT_LIVE_TEST=1 /opt/anaconda3/bin/python3 -m unittest discover -s tests -v`; Pillow and ffprobe are required by the test suite, not the workflow helper.

The 15-test suite also verifies native media collection, moved-delivery revision and footage replacement while retaining layer animation. Collected native references are absolute; the workflow relinks verified media when revising a moved delivery.

Development version `0.1.0-dev.1` fixes concurrent first-use/reuse install-lock contention: wait up to 120 seconds, then verify and reuse; timeout preserves installations and never replays editing tasks.

Development version dev.2 includes hash-bound exchange-loss.json with every native delivery. Reports distinguish format losses, observed structure and unknown font/effect fidelity; exported derivatives never replace the retained native project.

## CLI and task skill suite

[EffectCraft Skill Suite Architecture](docs/EffectCraft-Skill-Suite-Architecture.md)

| Skill | Purpose |
| :--- | :--- |
| `effectcraft-use` | use |
| `effectcraft-cli` | cli |
| `effectcraft-cli-setup` | cli setup |
| `effectcraft-cli-project` | cli project |
| `effectcraft-cli-footage` | cli footage |
| `effectcraft-cli-composition` | cli composition |
| `effectcraft-cli-layers` | cli layers |
| `effectcraft-cli-animation` | cli animation |
| `effectcraft-cli-effects` | cli effects |
| `effectcraft-cli-masks` | cli masks |
| `effectcraft-cli-expressions` | cli expressions |
| `effectcraft-cli-camera` | cli camera |
| `effectcraft-cli-export` | cli export |

`npx skills add full-aigc-skills/effectcraft-skills --skill <skill-name>`

## Focused task skills: clean first use

Version 0.1.0-dev.4 includes required camera creation/3D-view prerequisites and tested RGB-preview versus RGBA-export guidance. Ten focused task skills passed with only one skill copied and a fresh runtime per case; the full suite passed 35 tests with no skips. [Evidence](docs/evidence/task-skill-first-use.json). All commands, advanced 3D appearance, model dispatch and final creative acceptance remain unverified.

```bash
CRAFT_TASK_FIRST_USE=1 CRAFT_LIVE_TEST=1 CRAFT_LIVE_SUITE=1 python3 -B -m unittest discover -s tests -v
```

Commands use `SKILL_DIR`, the absolute directory of the `SKILL.md` actually loaded by the host. User/project `.agents/skills` and plugin-internal/cache layouts are supported; the CLI runtime is installed separately in the user data directory. Each skill was copied alone into all three layouts, including paths with spaces, and its documented script entry points ran `--help`. [Path verification](docs/evidence/installed-skill-paths.json). Existing host caches need an explicit update to receive the corrected documentation.

Skill suite dev.6 adds a self-contained editable-mask example and public mask vertex-edit/removal workflow commands. Default public-download native regression: 39 passed, zero skipped. Each task installs alone into an empty runtime; mask revision preserves the source project and non-target title, and actual RGBA pixels verify boundary changes. [Evidence](docs/evidence/task-skill-first-use.json). Runtime remains 0.2.0; model/GUI, creative and arbitrary mask fidelity acceptance remain pending.

[Actual transparent handoff to FilmCraft](docs/EffectCraft-FilmCraft-Alpha-Handoff-Acceptance.md): one installed two-domain empty-runtime case passes, preserving title animation and compositing native RGBA PNG over a video background with verified foreground pixels. Complete color and animated-alpha-video acceptance remain open.

Installed animation skill temporal first use passed: four native RGBA samples and 12 decoded video frames verify the fade; text revision preserves badge/key properties and original deliveries. [Temporal acceptance](docs/EffectCraft-Temporal-Animation-Acceptance.md). Full creative/animated-alpha acceptance remains open.

Independent EffectCraft source dev.7 maps matching effect/mask plan parameter validation errors to unsupported_mapping; native CLI stays at 0.2.0. Actual rejected creation/revision preserves prior deliveries. All 44 native source tests pass with zero skips (182.083s); fixed new plugin installed acceptance is recorded below. [Architecture](docs/EffectCraft-Parameter-Errors-Architecture.md) · [Evidence](docs/evidence/parameter-mapping-repair-20261006.json).

Fixed plugin dev.8 / source dev.7 installed acceptance passes: five plugins, 58 skills, zero loading errors; independent effect/mask skills cold-verify valid creation and rejected new/revision parameters (1 test, 24.714s), all 13 skills pass separate public cold first use, and all host-installed hashes remain intact. [Release-bound evidence](docs/evidence/codex-effectcraft8-parameter-first-use-20261006.json). ArtCraft bundle/domain-code propagation and complete V1 gates remain open.

Dynamic RGBA PNG sequences now retain the editable ecproj and every frame digest, rate and duration in craft-image-sequence/v1. Source cold installation and actual Film handoff pass; fixed new-plugin and Art acceptance remain pending. [Architecture](docs/EffectCraft-Dynamic-Sequence-Architecture.md).

Fixed Effect dev.9 and Film dev.10 installed-first-use dynamic handoff now passes: three native tests, all 58 skills discovered without loading errors, and all installed hashes unchanged after each execution. [Evidence](docs/evidence/codex-effectcraft9-filmcraft10-dynamic-first-use-20261006.json). Art dynamic integration remains pending.

Source dev.9 adds whole-plan effect/mask field preflight before source reads or native installation, with pinned binary-bound reflection and a live schema match before any project edit. Unknown/missing fields retain unsupported_mapping; object/property/value checks remain native. Immutable publication and installed acceptance are recorded separately.
