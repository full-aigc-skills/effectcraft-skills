import importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load():
 p=ROOT/'skills/effectcraft-use/scripts/commands.py';spec=importlib.util.spec_from_file_location('bridge_gateway',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class BridgeToolsTests(unittest.TestCase):
 def test_ui_inspect_allowed_only_in_bridge_preflight(self):
  m=load();plan={'schema':'craft-command-plan/v1','operations':[{'tool':'ui_inspect','params':{}}]};m.validate(plan,mode='bridge')
  with self.assertRaisesRegex(ValueError,'bridge_tool_requires_bridge'):m.validate(plan)
 def test_live_schema_drift_fails_before_ui_call(self):
  m=load();rows=m.bridge_tools();m.verify_bridge_tools(rows,{'ui_inspect'})
  changed=json.loads(json.dumps(rows));next(r for r in changed if r['name']=='ui_inspect')['inputSchema']['required']=['injected']
  with self.assertRaisesRegex(RuntimeError,'bridge_tool_schema_drift'):m.verify_bridge_tools(changed,{'ui_inspect'})
 def test_bridge_catalog_identity_mutation_rejected(self):
  m=load()
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'references').mkdir();(root/'scripts').mkdir();original=ROOT/'skills/effectcraft-use'
   for name in ['native-command-snapshot.json','bridge-tools.json']:(root/'references'/name).write_bytes((original/'references'/name).read_bytes())
   (root/'scripts/desktop.lock.json').write_bytes((original/'scripts/desktop.lock.json').read_bytes());p=root/'references/bridge-tools.json';x=json.loads(p.read_text());x['runtimeSha256']='0'*64;p.write_text(json.dumps(x))
   with patch.object(m,'ROOT',root),self.assertRaisesRegex(ValueError,'bridge_tools_identity'):m.bridge_tools()
