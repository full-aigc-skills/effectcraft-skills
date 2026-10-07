# 木偶与局部变形动画 / Puppet deformation

## 输入与前置状态 / Input and state

输入为目标图层、变形区域、锚定区域、动画时间与交付范围。先建立或打开合成，导入真实素材或建立可渲染图层；Puppet支持素材、纯色、文字、形状、预合成图层。显式 layer.select 后查询 puppet.info，不把控制用空对象当作可变形素材。position 是图层空间[x,y]，不是合成空间；time为秒，frame为帧，按合成帧率对齐，图层时间还受其时间变换影响。不要猜测图层、网格或针脚ID。

Use an actual renderable layer and its returned ID. Pin coordinates are in layer space. Time in seconds and frame numbers are distinct; composition and layer timing must be checked.

## 场景与命令 / Tasks and commands

| 场景 | 命令 | 步骤与核验 |
| --- | --- | --- |
| 建立锚定和可动针脚 | `puppet.addPin` | 指定目标layer、kind及position；记录返回fx、mesh、pin。第一次建针会创建Puppet效果，后续针是否加入原网格需核对，不直接用newMesh制造重复网格 |
| 制作位置动画 | `puppet.movePin` | 使用实际pin与图层；在不同time/frame设置位置，检查关键帧和变形结果。固定针与移动针分别记录 |
| 高级形变与刚度 | `puppet.setPin` | scale为百分比、rotation为角度、extent为像素；支持的字段取决于针脚kind，查询后设置。starch/overlap与position/advanced/bend不是同一种动画能力 |
| 网格密度与覆盖 | `puppet.mesh` | 指定实际mesh并调整density、expansion、triangles；检查透明边界、覆盖区域和变形质量。showMesh仅控制显示，不证明导出成功 |
| 选择与检查 | `puppet.selectPins`、`puppet.info` | 提供实际pins，[]取消选择，add/toggle改变选择集合；info检查针脚、网格和指定时间。操作前后分别核对，不依赖未知旧选择 |
| 录制手动运动 | `puppet.recordOptions`、`puppet.recordPin` | samples中的t为拖动开始后的秒，start是合成起点；speed百分比和smoothing影响结果。先设置并记录选项，再提交samples，验收实际关键帧和运动时长 |
| 延迟跟随 | `puppet.follow` | 明确leader、跟随pins、delay秒、amount百分比和cascade；只修改授权针脚，检查延迟、位移和其他针脚未变 |
| 删除针脚 | `puppet.removePin` | 指定pin/pins，先另存工程；检查删除范围和剩余网格、针脚及关键帧，不把默认选中集合当成目标范围 |

Describe each command before constructing a plan. Returned IDs identify created objects. Mesh display, keyframe presence and rendered deformation are separate acceptance checks.

## 查询、执行与交付 / Query, execute and deliver

```bash
python3 -I -B "$SKILL_DIR/scripts/commands.py" list --filter puppet.
python3 -I -B "$SKILL_DIR/scripts/commands.py" describe puppet.addPin
python3 -I -B "$SKILL_DIR/scripts/commands.py" describe puppet.recordPin
python3 -I -B "$SKILL_DIR/scripts/commands.py" check /absolute/puppet-plan.json
python3 -I -B "$SKILL_DIR/scripts/commands.py" run /absolute/puppet-plan.json --output /absolute/new-puppet-result
```

使用本技能command-usage.md的计划合同；创建针脚返回值通过$ref连接下一步，同会话保存.ecproj。交付原生工程、素材、参数记录和需要的透明或视频渲染。重开后检查原始针脚ID、关键帧及目标时刻的实际渲染；局部返工保留锚定针与其他动画。禁用项先核对活动合成、选择和针脚状态；未知结果先检查原任务，不重复录制或删除。

## 验收边界 / Acceptance boundary

本指南将10条命令组织为场景操作；原生实现参考commands/puppet.rs的图层验证、网格和针脚属性变更。目录与计划检查不等于网格质量或全部针脚类型、录制、跟随及交付验收。

All10 commands have task guidance; full deformation quality, pin kinds, recording and follow acceptance remain separate runtime checks.

## 已执行代表实例 / Executed representative example

`examples/puppet-create.json` 不需要外部素材，建立96×64、12fps合成和64×48红色纯色图层，在图层空间[16,24]、[48,24]建立position针脚，通过返回moving.pin在0.5秒移动第二针到[48,8]。创建后渲染0和0.5秒，保存project.ecproj。`examples/puppet-reopen.json` 接收 `--input project=/absolute/project.ecproj`，查询Deform subject图层在0.5秒的木偶状态并渲染。两个计划均使用本技能commands.py run和新输出目录。真实工程必须适配图层名称、尺寸、坐标、动画范围和稳定锚点。

实例已核验一网格两针脚、帧像素变化、原生重开后木偶状态相同且渲染像素一致；不代表变形质量、全部针脚类型、录制和跟随命令已验收。

This self-contained fixture proves a rendered change and native reopening identity for two position pins. Adapt layer geometry and anchors for real artwork; production deformation quality remains a separate review.
