# EffectCraft Skills

Development source dev.39 adds actual video frame/timestamp/alpha and asset checks, isolated current-project reopening, and independent engineering/technical/creative/user acceptance states. Regression: 287 passed / 38 conditional skips out of 325. Complete V1 and other-platform/host acceptance remain open. [Evidence](docs/evidence/engineering-review-candidate-20261008.json).

Segmented first-use guidance now matches native acceptance of fixed Film40 / Effect38 / Art117, including HD full frames, revision, recovery and relocation. Installation qualification of this new guide snapshot is recorded separately. [Evidence](docs/evidence/craft-fixed-segmented-hd-refresh-20261008.json).

> **Development release dev.39 (2026-10-08):** pinned isolated Python 3.13.16 and EffectCraft 0.4.0; managed execution, owned segment recovery and shared retry accounting. Local macOS evidence does not establish all platforms or hosts. See [implementation and open gates](docs/managed-optimization-20261008.md) and the [platform matrix](docs/current-capabilities.json).


Turn text, graphics and footage into an editable `.ecproj`, dependencies and rendered media.

Current source: `0.1.0-dev.39`; consuming plugin: `0.1.0-dev.41`; 15 independent skills.

Verified first-use platform: macOS arm64 and Python 3.11+. Pinned runtimes install into the user data directory; skill files stay in their host-loaded directory. These are development releases; complete V1 acceptance and generic Skills CLI installation remain open.

## First use

Invoke **`effectcraft-use`** in your host. For direct CLI use, set `SKILL_DIR` to the absolute directory of the `SKILL.md` actually loaded by that host. It may be under user/project `.agents/skills`, the plugin, or a host cache; use the actual path. Each entry below installs/verifies its locked runtime before invoking it.

<!-- CRAFT_FIRST_USE_START -->
```bash
: "${SKILL_DIR:?Set to the actual loaded skill directory}"
sh "$SKILL_DIR/scripts/launch.sh" doctor
sh "$SKILL_DIR/scripts/launch.sh" run --plan "$SKILL_DIR/examples/brand-intro.json" --output "$PWD/effectcraft-result"
```
<!-- CRAFT_FIRST_USE_END -->

Read the [editable workflow](skills/effectcraft-use/references/workflow.md) for inputs, native projects and targeted revisions. [Setup and skill entry](skills/effectcraft-use/SKILL.md) · [version-bound history](RELEASE-HISTORY.md). Command/version queries verify installation and discovery; they do not constitute creative completion.

[First-use navigation evidence](docs/evidence/craft-readme-first-use-navigation-20261007.json).

Fixed installed path acceptance: standalone skills and Art mixed work pass native creation/reopen, targeted revision and export under Chinese-and-space paths; Art also verifies moved delivery. Skills/runtime identities stay unchanged. This is bounded macOS arm64 first-use evidence. [Path acceptance evidence](docs/evidence/craft-fixed-unicode-path-first-use-20261007.json).

Historical source candidate before the fixed release: structurally invalid runtime/Node locks now return local setup diagnostics before runtime writes/downloads. Five candidate native first-use checks pass; published plugin snapshots remain unchanged until separate immutable release acceptance. [Lock diagnostics candidate](docs/EffectCraft-Lock-Shape-Architecture.md).

---

Fixed native first-use and complete-command recovery acceptance passed:58 standalone cold installations, ten Art all-domain cold installations, four partial-download SSL EOF recoveries,72 post-save faults, four healthy command revisions and mixed HD revision/recovery/moved delivery. Installed identities remain unchanged. Only domain2.10/8.11 and Art4.10 close; exhaustive2639-command, GUI, model, generic Skills CLI and fullV1 gates remain open. [Version-bound evidence](docs/evidence/codex-native-download-first-use-20261007.json).

Historical candidate observation before fixed acceptance: Native download recovery candidate: up to three read-only attempts discard partial archives. Earlier fixed cold installs failed on SSL EOF; new fixed installed acceptance remains open.

Historical release record: Current standalone source: `0.1.0-dev.19`; native parenting/expression recipes included; 13 fixed installed expression/parent cold cases pass; Art bundle update pending; full V1 remains open.

Previous version-bound failed-stage acceptance: plugin dev.17, standalone source dev.15. All58 independent CLI cold starts,24 original-stage native fault cases and37 native scene tests plus6 contracts pass. Art77 bundle upgrade remains open. [Evidence](docs/evidence/codex-failed-stage-first-use-20261007.json).

Fixed domain-client first use: Film plugin dev.16 / source dev.15; Effect/Photo/Vector plugin dev.15 / source dev.14. Codex discovers 58 skills without errors. Actual installed copies pass 24 post-save faults and four healthy public workflows; the published Art engine with the installed Vector client passes six faults. All58 installed identities remain unchanged. Art dev.75 still bundles earlier domain sources; exhaustive command/GUI/model acceptance remains open. [Version-bound evidence](docs/evidence/codex-public-workflow-session-first-use-20261007.json).
Historical release record: Current standalone source: `0.1.0-dev.19`; native parenting/expression recipes included; 13 fixed installed expression/parent cold cases pass; Art bundle update pending; full V1 remains open.
Previous version-bound protocol recovery acceptance passed: 288 cases across 48 standalone source skills, 24 cases in actual installed copies, four healthy revision cases, and 58 unchanged installed skill identities. See [fixed evidence](docs/evidence/codex-protocol-fault-first-use-20261007.json). Exhaustive command/GUI acceptance and the Art domain-bundle upgrade remain open.

Protocol fault repair candidate: all 13 independently copied skills pass separate empty public-runtime installation and six faulty replies after real native save (78 cases; zero skips). Requests are not replayed; unknown receipts, saved-project reopening and delivery/skill preservation are checked. [Evidence](docs/evidence/protocol-fault-first-use-20261007.json). Fixed installed release and Art bundle upgrade remain separate gates.

Fixed plugin 0.1.0-dev.13 / skills 0.1.0-dev.12 installed revision acceptance passes: isolated Codex discovers all 58 skills without loading errors; this installed domain skill completes the documented cold creation/revision plans, saved-project reopening and non-target preservation. All58 installed digests remain unchanged; current fixed release CI passes. [Fixed revision evidence](docs/evidence/codex-complete-command-revision-first-use-20261007.json). Full command/GUI/model acceptance remains open.

All 13 domain skills pass the paired revision plans when copied alone and installed from separate empty public runtimes (145.856 seconds; zero skips). [Revision evidence](docs/evidence/complete-command-revision-first-use-20261007.json). Fixed installation of the updated snapshot remains a separate gate.

The complete-command entry now includes paired executable creation/revision recipes, explicit selection prerequisites after reopening, and native persisted-state/non-target checks. Each standalone skill includes both JSON plans. [Usage](skills/effectcraft-use/references/command-usage.md#7-可执行局部返工--executable-targeted-revision). Full per-command and GUI acceptance remains open.

Previous fixed Codex snapshot first use passes: five plugins / 58 skills discovered, independent public cold runtime installs for all 58 installed skills, four complete-command native samples, Art HD revision/recovery/package checks, unchanged installed digests and fixed release CI. [Evidence](docs/evidence/codex-complete-command-first-use-20261007.json). This remains bounded native acceptance; generic Skills CLI installation and exhaustive command/GUI acceptance are open.

## Complete native command entry

All 13 standalone skills now pass separate empty-runtime installation from locked public CLI archives, followed by native creation, save/reopen, domain assertions and rendered image checks (152.42 seconds; zero skips). [Cold-first-use evidence](docs/evidence/complete-commands-cold-first-use-20261007.json). This verifies this complete-command sample in every skill; exhaustive command/GUI and actual host installation remain separate.

Published development snapshot: skills dev.11 / plugin dev.12; bounded fixed-host first use passed.

All 640 commands now have verbatim parameters, skill routing, and same-session invocation through `commands.py list / describe / check / run`. Live enabled state is checked; the existing 21-operation delivery workflow remains bounded. GUI commands require explicit bridge mode. Complete registry coverage does not establish full command acceptance.

[Architecture and usage](docs/EffectCraft-Complete-Commands-Architecture.md) · [Complete reference](skills/effectcraft-use/references/command-reference.md) · [Runnable example](skills/effectcraft-use/examples/commands-advanced.json)

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

Fixed plugin dev.10 / source dev.9 installed acceptance passes: Codex discovers all 58 skills with zero loading errors; all 13 Effect skills cold-install the public CLI and reject invalid plans before installation/editing; four temporal/sequence/Film-handoff regressions and the 13-test Effect domain matrix pass with zero skips. All installed skill hashes remain unchanged. [Version-bound evidence](docs/evidence/codex-effectcraft10-preflight-first-use-20261006.json). Art domain bundle upgrade, actual Skills CLI installation and complete V1 remain open.

Working-tree segmented producer candidate: bounded native ranges, hash-bound recovery and per-frame checks; fixed plugin and Film/Art consumption remain pending. [Architecture](docs/EffectCraft-Segmented-Render-Architecture.md).

Current-source HD segmented candidate passes 1080p / 24 fps / five seconds and animated-title checks; immutable installed releases and Art HD remain pending. [Architecture and evidence](docs/EffectCraft-HD-Sequence-Architecture.md).

Skill source 0.1.0-dev.10 includes bounded segmented workflows and HD RGBA verification optimization. Native CLI identity is unchanged; corresponding immutable plugin and installed Art acceptance are recorded separately.

Public-workflow reply validation is synchronized in the domain source candidates and has bounded native/Art protocol evidence. Fixed updated domain and Art distributions are still pending. [Candidate architecture](docs/EffectCraft-Complete-Commands-Architecture.md) · [Evidence](docs/evidence/public-workflow-session-candidate-20261007.json).

Failed-stage candidate: public workflows retain original native staging paths, dependency hashes, last submitted requests and completed receipts; replay is prohibited. Fixed releases and installed-host acceptance remain open. [Architecture](docs/EffectCraft-Failed-Stage-Architecture.md).

Fixed domain failed-stage first use passes: Film plugin18/source16 and other domain plugins17/source15; five plugins/58 skills without loading errors; all58 independent empty-runtime CLI starts (417.646s); actual installed24 post-save faults reopen product-retained original projects and dependencies; four healthy native creation/revision cases pass. All installed identities and16 fixed plugin CI runs pass. Source repositories have no CI runs, only local regression. Only domain OpenSpec3.12 closes; Art77 bundles older domain sources, task4.9 and fullV1 remain open. [Evidence](docs/evidence/codex-failed-stage-first-use-20261007.json).

Fixed installed scene matrix passes37 native scenarios and6 contract checks with zero skips. The Photo fixture now resolves the maintained native version from the installed skill lock; the CLI and installed skills are unchanged. [Evidence](docs/evidence/codex-failed-stage-first-use-20261007.json).


Candidate complete-command inner JSON fix: nonfinite values, overflow and duplicate keys now retain unknown receipts before binding results. All nine real post-save fault classes pass with original reopen; this is candidate-source evidence, fixed releases and installed-copy acceptance are pending. Complete per-command/GUI acceptance stays open.

Parenting/expression:13 independent source-candidate cold native runs pass dynamic alpha, save/reopen and source revision; fixed install and Art distribution pending. [Architecture](docs/EffectCraft-Expression-Parent-Architecture.md).

Fixed parent/expression first use:13 independently installed skills pass dynamic alpha and source revision; all58 installed identities unchanged. Updated Art distribution remains pending. [Evidence](docs/evidence/codex-effectcraft-expression-first-use-20261007.json).

## Desktop installation component (source candidate)

The 48 standalone domain skills now have their own pinned official desktop installers. See the [installation architecture](docs/Craft-Desktop-First-Use-Architecture.md) and [48-skill installation evidence](docs/evidence/craft-desktop-source48-first-use-20261007.json). Existing release-tag skill copies do not yet contain this candidate component. Desktop startup, GUI edits/save/reopen and complete command execution remain open acceptance gates.

Source candidate now includes owned standalone desktop startup: 48/48 single-skill cold GUI save/reopen and cleanup cases passed. See [runtime evidence](docs/evidence/craft-owned-desktop-first-use-20261007.json). Fixed-release installation and complete command execution remain open.

Command-plan JSON source candidate: duplicate keys are rejected before installation and output creation. All 15 domain skills pass standalone-copy rejection and valid-plan checks. Three focused tests pass; fixed-plugin publication and installed acceptance remain NOT_RUN. [Evidence](docs/evidence/command-plan-json-candidate-20261007.json).

Fixed strict-plan installed verification passes: 64 CLI probes, 324 duplicate-key rejections across54 independently copied installed domain skills, 54 unique-plan structure checks and four cold native save/reopen/render samples. All64 installed skill hashes remain unchanged. Only the bounded strict-plan publication gate closes; generic Skills CLI, Art domain-bundle upgrade, exhaustive contexts and fullV1 remain open. [Evidence](docs/evidence/command-plan-json-fixed-first-use-20261007.json).

Six scenario directory examples were corrected across the four domains; this package’s runtime identity matches every bundled runtime lock. Native CLI archives are unchanged.

Fixed installed own-directory acceptance passes for the updated scenario skills; 64 host identities match. Complete V1 remains open. [Evidence / 证据](https://github.com/full-aigc-plugins/effectcraft-plugin/blob/main/docs/evidence/craft-scenario-paths-fixed-first-use-20261008.json).

Puppet recording/follow source candidate: ten representative commands, frame-aligned keys, native reopen, targeted revision and three rejection paths pass. Immutable installed-release acceptance remains separate. [Architecture](docs/EffectCraft-Puppet-Record-Follow-Architecture.md).

Fixed EffectCraft plugin dev.37 / source dev.33 acceptance passes: 64 installed skill identities/discovery, 15 fresh standalone Effect CLI installs, and native puppet recording/follow/reopen/targeted revision plus three failure paths. The other 49 cold records are historical and byte-identical. Full V1 stays open. [Fixed evidence](docs/evidence/effectcraft-puppet-record-follow-fixed-first-use-20261008.json).

Camera scene source candidate passes native Advanced 3D rendering, projection growth, reopen identity, camera-only revision and three rejection paths. [Architecture](docs/EffectCraft-Camera-Scene-Architecture.md). Fixed installed-release acceptance remains separate; full V1 stays open.

Fixed EffectCraft plugin dev.37 / source dev.34 passes 64 installed skill identities/discovery, 15 fresh standalone Effect CLI cold installs, and the native camera render/reopen/targeted revision plus three rejection paths. The other 49 cold records are retained byte-identical historical runs. Full V1 remains open. [Fixed camera evidence](docs/evidence/effectcraft-camera-scene-fixed-first-use-20261008.json).

Independent-install dependency boundary: current byte-identical cold-install records and 128 new fixed-copy bootstrap/CLI failure checks qualify four domain SK-002 requirements. Art and generic Skills CLI installation stay open. [Design and evidence](docs/Craft-Independent-Setup-Boundary-Architecture.md).

Current fixed protocol-reference release matrix (Film/Effect dev.37, Photo dev.37, Vector dev.34, Art dev.107) passes actual isolated Codex installation/discovery of 64 skills, 16 installed authority-file digest checks, and 64 independent public CLI probes using five fresh domain caches. Historical native scene proof is reused only for byte-identical skills; full V1 remains open. [Fixed release evidence](docs/evidence/craft-protocol-authority-fixed-first-use-20261008.json).
