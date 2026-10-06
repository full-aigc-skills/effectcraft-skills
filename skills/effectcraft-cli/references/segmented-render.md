# 分段生产候选

工作区候选入口 `scripts/segmented_sequence.py` 随独立技能资源分发，当前固定源 dev.9／插件 dev.10 尚未包含此候选。单段仍受 512 MiB 解码预算约束；检查点不是原 Film／Art 已支持的素材合同。

已有原生工程与从 native.json 提取的 composition.json 时：

```bash
python3 -I -B "$SKILL_DIR/scripts/segmented_sequence.py" --project /absolute/project.ecproj --composition /absolute/composition.json --output /absolute/segments --chunk-frames 60
```

以实际加载的技能目录设置 SKILL_DIR。入口自动安装及核验固定 CLI。相同参数再次调用会重新核验已有段，仅重跑坏段；原生版本、工程或设置改变时用新目录。不要改动 checkpoint.json、verified.json 或完成段。失败不是交付完成；不直接将 segments.json 交给既有 v1 消费路径。

该候选核验透明 RGBA、精确帧范围、像素与文件摘要、源工程及安装技能保全；不自动判断创作质量。公开固定发行、完整 1080p 长片头和 Film／Art 联调仍开放。
