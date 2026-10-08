"""逐技能单独复制后，公开失败入口必须保留完整进程停止证据。"""
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class IndependentGuardTests(unittest.TestCase):
    def test_every_skill_preserves_guarded_failure_without_siblings(self):
        override = os.environ.get('CRAFT_GUARD_SKILL_ROOT')
        sources = [Path(override)] if override else [
            entry.parent for entry in sorted((ROOT / 'skills').glob('*/SKILL.md'))]
        self.assertEqual(len(sources), 1 if override else 15)
        for source in sources:
            with self.subTest(skill=source.name), tempfile.TemporaryDirectory(prefix='独立 守护技能 ') as directory:
                copied = Path(directory) / '.agents' / 'skills' / source.name
                shutil.copytree(source, copied, ignore=shutil.ignore_patterns('__pycache__'))
                # 复用同一可观察合同；执行的是复制技能的真实 CLI 和子进程。
                spec = importlib.util.spec_from_file_location(
                    'independent_supervisor_contract', ROOT / 'tests' / 'test_managed_supervisor.py')
                contract = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(contract)
                contract.SCRIPT = copied / 'scripts' / 'managed.py'
                case = contract.ManagedSupervisorTests(
                    'test_source_conflict_before_worker_start_is_durably_failed')
                case.test_source_conflict_before_worker_start_is_durably_failed()


if __name__ == '__main__':
    unittest.main()
