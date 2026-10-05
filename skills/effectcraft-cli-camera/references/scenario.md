# 三维图层与摄像机操作指南

## 目标与前置

设置已有合成中的摄像机、灯光和材质参数。先核对图层三维开关、视角及对应渲染支持；不能用参数存在证明视觉结果。

先检查需求中的工程格式、目标对象、素材摘要、字体与输出约束。输入不完整时继续只读调查，但不猜测依赖它的参数。

## 当前版本命令入口

`commands --filter <关键词> --json` 核对参数；属性读写用 props/get/set，命令用 `exec <id> --params <JSON>` 或成对的 `run <id> <JSON> ...`；用 --save-as 保留新工程。

| 命令 ID | 目录标签 |
| :--- | :--- |
| `camera.fromView` | Create Camera from 3D View |
| `camera.orbit` | Orbit Camera |
| `camera.pan` | Pan Camera |
| `camera.dolly` | Dolly Camera |
| `material.set` | Material Options |
| `material.revealSource` | Reveal Material Source in Project |
| `material.reset` | Reset Material |
| `material.duplicateAssign` | Duplicate and Assign Material |

完整候选参数见本技能 commands.json；enabled 是空会话观察，打开目标工程后必须重查。命令参数 schema 存在不证明它在全部素材与平台有效。

## 执行与验收

1. 保存原生检查点、读取对象 ID 和参数值；已有素材先核验引用。
2. 构造当前版本命令参数；一次只改变请求的属性或对象。连续创建 ID 使用实际回执或同一会话。
3. 保存新原生工程、重新打开，比较目标参数和未修改对象。需要输出时检查帧、像素、音频或矢量结构。
4. 原生工程、素材清单、预览/导出及交换报告交付；技术核验和视觉审核分开记录。

首次组合实例采用本技能 examples 与 references/workflow.md。此实例验证组合能力，不替代所有候选命令的逐项验收。失败保留检查点，不将无损原生交付替换成扁平结果。

## 从默认二维视角开始的已验证操作

`camera.fromView` 要求当前视角已是三维，默认二维视角会返回参数错误。已有普通合成需要先用 `layer.newCamera` 建立相机，再用 `view.set3DView` 切到 `activeCamera`，然后才执行 camera.orbit/pan/dolly；同一 `run` 会话保留新建对象和视角状态。修改普通图层的三维开关使用 `layer.setSwitch`，创建灯光使用 `layer.newLight`。这些前置命令已纳入本技能 commands.json。

以下位置示例针对 320×180 合成；先读取真实尺寸、既有相机和图层，避免重复创建或覆盖已有设置。项目路径替换成用户授权的绝对路径，技能挂载路径替换成实际安装目录：

以下 `SKILL_DIR` 沿用本技能 `SKILL.md` 的实际加载目录，脚本和示例均来自同一技能。

```bash
python3 "$SKILL_DIR/scripts/cli.py" -- run \
  layer.newCamera '{"name":"Primary camera","position":[160,90,-400],"poi":[160,90,0]}' \
  view.set3DView '{"view":"activeCamera"}' \
  camera.dolly '{"amount":50}' \
  --project /absolute/path/source.ecproj \
  --save-as /absolute/path/revised.ecproj --json
```

用真实回执中的相机 layer ID，通过 `get <comp> <layer> transform/position --project <新工程> --json` 检查保存重开后的坐标。上述示例的 position 为 `[160,90,-350]`。保留源工程摘要；二维视角的失败操作不得产生成功工程。相机参数和原生保存通过不等于高级三维材质、阴影或最终画面均已验收。
