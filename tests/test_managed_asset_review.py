"""素材声明必须绑定包内实际文件，不能只信任清单的另一份摘要表。"""
import hashlib
import json
import unittest
import test_managed_review as fixtures

class AssetReviewTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ManagedReviewTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.review=self.fixture.module;self.manifest=self.fixture.manifest
        (self.root/'asset.bin').write_bytes(b'collected dependency')
        self.manifest['assets']={'footage':{'path':'asset.bin','sha256':self.review.sha(self.root/'asset.bin'),'item':1}}
        self.manifest['files']['asset.bin']=self.review.sha(self.root/'asset.bin');self.save()

    def save(self):
        (self.root/'manifest.json').write_text(json.dumps(self.manifest),encoding='utf-8')

    def test_collected_asset_is_verified_and_reported(self):
        report=self.review.inspect_delivery(self.root)
        self.assertEqual(report['technical']['status'],'PASS')
        self.assertEqual(report['technical'].get('verifiedAssets'),1)

    def test_asset_digest_cannot_disagree_with_matching_package_hash(self):
        self.manifest['assets']['footage']['sha256']='a'*64;self.save()
        report=self.review.inspect_delivery(self.root)
        self.assertEqual(report['technical']['status'],'FAIL',report)
        self.assertIn('asset_contract_mismatch',report['technical']['reason'])

    def test_unlisted_dependency_is_not_verified_by_file_existence(self):
        del self.manifest['files']['asset.bin'];self.save()
        self.assertEqual(self.review.inspect_delivery(self.root)['technical']['status'],'FAIL')

    def test_missing_dependency_is_rejected_even_when_removed_from_file_table(self):
        (self.root/'asset.bin').unlink();del self.manifest['files']['asset.bin'];self.save()
        self.assertEqual(self.review.inspect_delivery(self.root)['technical']['status'],'FAIL')

    def test_dependency_path_cannot_escape_delivery(self):
        self.manifest['assets']['footage']['path']='../asset.bin';self.save()
        self.assertEqual(self.review.inspect_delivery(self.root)['technical']['status'],'FAIL')
