# EffectCraft parameter error architecture

## Scope and authority

OpenSpec EC-DM-004-PARAM owns this increment. Fixed plugin dev.7 / source dev.6 / native CLI 0.2.0 already rejects unknown effect/mask parameters. Actual public cold calls with effect.apply blurriness and mask.new feather confirm native rejection and no delivery. The gap is the helper exposing RuntimeError command_failed instead of the specified unsupported_mapping. This repair does not alter the native engine or silently remove unsupported fields.

```mermaid
sequenceDiagram
 participant S as Single installed skill
 participant W as Workflow
 participant E as Pinned native engine
 S->>W: New or source-revision plan
 W->>E: Execute effect or mask command with all fields
 E-->>W: Exact command-specific invalid parameters error
 W-->>S: unsupported_mapping plus native diagnostic
 Note over W: Discard temporary new delivery; preserve source files
```

## Error mapping and preservation

Only six bounded plan commands qualify: effect.apply, effect.remove, effect.toggle, mask.new, mask.setVertex and mask.remove. The MCP tool must be execute_command, and its single text error must begin with the same command's exact pinned-engine parameter-validation prefix. Other commands, mismatched identities, render/media errors and nonmatching failures retain command_failed. Raw cli.py execution remains the native CLI's explicit validation behavior; this helper classification applies to workflow.py plans.

No second execution strips or retries the parameter. The native command validates before applying its edit. Earlier plan operations can exist only in a private staged project: unsuccessful creation publishes no delivery, and failed source revision preserves every prior file. Existing asset collection failure records remain distinct. Valid creation saves/reopens .ecproj and continues previews/exports.

## Verification and release

The baseline records two actual native rejections with the wrong helper classification. New live acceptance fails with two subtest errors before the repair; two new unit cases also fail. After repair, seven unit tests pass and live effect/mask new/revision acceptance passes in 20.018s using independently copied role skills and empty public native runtimes. [Bound evidence](evidence/parameter-mapping-repair-20261006.json).

All thirteen skills vendor the helper from the independent source authority. Complete source regression, immutable new skill/plugin publication and installed-host verification remain pending at this source milestone. This does not validate every effect, feather animation, model dispatch, GUI or creative quality, and does not change the ArtCraft bundle until its own pinned source update.
