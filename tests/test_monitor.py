import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('monitor',Path(__file__).resolve().parents[1]/'collector/monitor.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class MonitorTest(unittest.TestCase):
 def job(self,body='Python RAG API开发；本科；2026届毕业生；经验不限；不要求英语四级证书'):
  return dict(company='测试企业',title='AI 应用开发工程师',city='深圳',url='https://example.org/jobs/1',description=body,employmentType='全职',source='test',sourceType='企业官方招聘API',publishedAt=m.now()[:10])
 def test_complete_evidence_high(self):
  self.assertEqual(m.score(self.job(),['深圳'])['category'],'高匹配')
 def test_unknown_not_high(self):
  j=self.job('Python RAG API开发；本科；经验不限');s=m.score(j,['深圳']);self.assertEqual(s['category'],'待核实');self.assertLess(s['score'],100)
 def test_hard_conflicts(self):
  for text in ['要求硕士学历','必须通过英语四级','3年以上工作经验','要求CRM相关经验','仅限2027届在校生','销售额为主要考核指标']:
   with self.subTest(text=text):self.assertEqual(m.score(self.job('Python RAG API开发；'+text),[])['category'],'不匹配')
 def test_preference_not_conflict(self):
  s=m.score(self.job('Python RAG API开发；本科；CRM相关经验优先；硕士优先；参与ERP API集成'),[])
  self.assertNotIn('CRM/ERP经验为必备',s['conflicts']);self.assertNotIn('硕士及以上硬要求',s['conflicts'])
 def test_enrolled_intern(self):
  j=self.job('RAG Python开发；本科；currently enrolled in university');j['employmentType']='实习'
  self.assertEqual(m.score(j,[])['category'],'不匹配')
 def test_title_only_not_enough(self):
  self.assertEqual(m.score(self.job('负责排班和日常行政事务'),[])['category'],'不匹配')
 def test_explicit_sales_body_excluded(self):
  j=self.job('Python AI API; This role owns all the sales and channels related to partnerships')
  self.assertEqual(m.score(j,[])['category'],'不匹配')
 def test_clean_encoded_html(self):
  self.assertEqual(m.clean('&lt;p&gt;Python&lt;/p&gt;'),'Python')
 def test_masters_preferred(self):
  self.assertNotIn('硕士及以上硬要求',m.score(self.job('Python RAG API开发；本科；硕士优先'),[])['conflicts'])
 def test_job_identifier_query_retained(self):
  self.assertEqual(m.safe_url('https://example.org/job/?gh_jid=123'),'https://example.org/job/?gh_jid=123')
 def test_certificate_and_experience_preferences(self):
  s=m.score(self.job('Python RAG API开发；英语四级证书优先；具备3年工作经验优先'),[])
  self.assertNotIn('英语证书硬要求',s['conflicts']);self.assertNotIn('多年工作经验要求',s['conflicts'])
 def test_english_cet_required(self):
  self.assertIn('英语证书硬要求',m.score(self.job('Python RAG API开发；CET-4 required'),[])['conflicts'])
 def test_url(self):
  for u in ['javascript:alert(1)','http://example.org','https://user:pass@example.org/']:
   with self.assertRaises(ValueError):m.safe_url(u)
 def test_dedup_change_and_recovery(self):
  j=self.job();stamp=m.now();a,e=m.reconcile([], [j,j], ['test'],stamp,[]);self.assertEqual(len(a),1);self.assertEqual(len(e),1)
  b,e=m.reconcile(a,[j],['test'],stamp,[]);self.assertEqual(e,[])
  j['salary']='6000-8000';b,e=m.reconcile(b,[j],['test'],stamp,[]);self.assertEqual(e[0]['type'],'updated')
  b,e=m.reconcile(b,[],[],stamp,[]);self.assertEqual(b[0]['missingCount'],0)
  b,e=m.reconcile(b,[],['test'],stamp,[]);self.assertEqual(e,[])
  b,e=m.reconcile(b,[],['test'],stamp,[]);self.assertEqual(e[0]['type'],'suspected_expired')
  b,e=m.reconcile(b,[j],['test'],stamp,[]);self.assertEqual(b[0]['status'],'open')
 def test_failure_preserves_feed(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);m.atomic(r/'config/sources.json',{'greenhouseBoards':['x']});m.atomic(r/'data/feed.json',{'jobs':[],'lastSuccessAt':'old'});before=(r/'data/feed.json').read_bytes()
   with patch.object(m,'greenhouse',side_effect=ValueError('blocked')):self.assertEqual(m.run(r),1)
   self.assertEqual((r/'data/feed.json').read_bytes(),before)
 def test_seed_has_real_urls(self):
  p=Path(__file__).resolve().parents[1]/'extension/seed.json'
  if p.exists():
   for j in json.loads(p.read_text())['jobs']:self.assertTrue(m.safe_url(j['url']).startswith('https://'))
if __name__=='__main__':unittest.main()
