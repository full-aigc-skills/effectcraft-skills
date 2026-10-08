"""实际PowerShell函数的身份字节和语法验证；不冒充原生Windows创作验收。"""
import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]/'skills/effectcraft-use/scripts'
ENGINE=shutil.which('powershell.exe') or shutil.which('pwsh')
@unittest.skipUnless(ENGINE,'PowerShell unavailable; platform gate remains open')
class PowerShellEntryTests(unittest.TestCase):
    def run_ps(self,code):
        r=subprocess.run([ENGINE,'-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(code.encode('utf-16le')).decode()],capture_output=True,timeout=40)
        self.assertEqual(r.returncode,0,r.stderr.decode('utf-8',errors='replace'));return r.stdout.decode('utf-8-sig')

    def test_missing_entry_text_has_stable_bound_diagnostic(self):
        source=base64.b64encode(str(ROOT/'task_entry.ps1').encode()).decode()
        code="""$ErrorActionPreference='Stop';$tokens=$null;$errors=$null
$source=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('SOURCE'))
$ast=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
foreach($name in @('Fail-Entry','Read-EntryText')){
 $fn=$ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)|Where-Object {$_.Name -eq $name}
 Invoke-Expression $fn.Extent.Text
}
$missing=Join-Path ([IO.Path]::GetTempPath()) ([Guid]::NewGuid().ToString()+'.tsv')
$reason='';try{Read-EntryText $missing 16384}catch{$reason=$_.Exception.Message}
if($reason -notlike 'bound_entry_invalid:*'){throw ('unexpected diagnostic: '+$reason)}
if(Test-Path -LiteralPath $missing){throw 'missing entry was created'}
""".replace('SOURCE',source)
        self.run_ps(code)

    def test_launcher_and_selector_parse_without_syntax_errors(self):
        for name in ('launch.ps1','task_entry.ps1'):
            encoded=base64.b64encode(str(ROOT/name).encode()).decode()
            self.run_ps("$ErrorActionPreference='Stop';$tokens=$null;$errors=$null;$path=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+encoded+"'));[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)>$null;if($errors.Count){throw ($errors|Out-String)}")

    def test_real_identity_function_rejects_nested_duplicate_or_changed_fields(self):
        identity=json.dumps({'inputHashes':{'路径':'中文 space "quoted"'},'runtimeBinding':{'entrySha256':'a'*64}},ensure_ascii=False,sort_keys=True,separators=(',',':'))
        sha=hashlib.sha256(identity.encode()).hexdigest()
        state='{"createdAt":1,"identity":'+identity+',"identityHash":"'+sha+'","plan":{"identity":{"fake":true},"text":"\\\"identity\\\":fake"}}'
        cases=[{'state':state,'valid':True},{'state':state.replace(sha,'f'*64),'valid':False},{'state':state.replace('"identity":'+identity,'"identity":{}'),'valid':False},{'state':state[:-1],'valid':False},{'state':state[:1]+'"identity":{},'+state[1:],'valid':False},{'state':state[:1]+'"identityHash":"'+sha+'",'+state[1:],'valid':False},{'state':'{"plan":{"identity":'+identity+',"identityHash":"'+sha+'"}}','valid':False},{'state':state.replace('中文','中\u00a0文'),'valid':False}]
        fixture={'identity':identity,'sha':sha,'cases':cases};encoded=base64.b64encode(json.dumps(fixture,ensure_ascii=False).encode()).decode();source=base64.b64encode(str(ROOT/'task_entry.ps1').encode()).decode()
        code="""$ErrorActionPreference='Stop';$tokens=$null;$errors=$null
$source=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('SOURCE'))
$ast=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
foreach($name in @('Fail-Entry','Hash-EntryText','Assert-EntryIdentity')){
 $fn=$ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)|Where-Object {$_.Name -eq $name}
 Invoke-Expression $fn.Extent.Text
}
$data=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('DATA'))|ConvertFrom-Json
$passed=0
foreach($case in $data.cases){
 $accepted=$true;try{Assert-EntryIdentity $case.state $data.identity $data.sha}catch{$accepted=$false}
 if($accepted -ne $case.valid){throw ('unexpected identity decision '+$passed)};$passed++
}
@{status='PASS';cases=$passed}|ConvertTo-Json -Compress
""".replace('SOURCE',source).replace('DATA',encoded)
        result=json.loads(self.run_ps(code));self.assertEqual(result['cases'],8)

if __name__=='__main__':unittest.main()
