# EffectCraft Skills

Independent EffectCraft skills. Implementation is in progress; this repository is not a completed plugin release.

The `effectcraft-use` skill contains a self-contained Python 3.11+ bootstrap installer for the pinned official macOS arm64 CLI. It verifies the archive and executable, retains license files, atomically installs a new version, and reuses an intact installation without downloading again.

Run tests with `python3 -m unittest discover -s tests -v`. Full creative workflow and host acceptance remain pending.

Normative requirements and implementation tracking: [EffectCraft plugin OpenSpec](https://github.com/full-aigc-plugins/effectcraft-plugin/tree/main/openspec/changes/establish-v1-plugin).

[简体中文](README.zh-CN.md)

The executable workflow now covers native project round trips, transparent PNG previews, H.264 export and text revisions preserving unrelated layers and keyframes. See [workflow guidance](skills/effectcraft-use/references/workflow.md). Run live tests with `CRAFT_LIVE_TEST=1 /opt/anaconda3/bin/python3 -m unittest discover -s tests -v`; Pillow and ffprobe are required by the test suite, not the workflow helper.

The 15-test suite also verifies native media collection, moved-delivery revision and footage replacement while retaining layer animation. Collected native references are absolute; the workflow relinks verified media when revising a moved delivery.

Development version `0.1.0-dev.1` fixes concurrent first-use/reuse install-lock contention: wait up to 120 seconds, then verify and reuse; timeout preserves installations and never replays editing tasks.
