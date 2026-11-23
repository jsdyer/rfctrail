import importlib.util, json, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('refresh',ROOT/'scripts/refresh.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
CFG={'maximumSourceBytes':100000,'minimumRecords':1,'maximumRecords':100}
def xml(entries):return ('<rfc-index xmlns="https://www.rfc-editor.org/rfc-index">'+entries+'</rfc-index>').encode()
def item(n,title='A protocol',extra=''):return f'<rfc-entry><doc-id>RFC{n}</doc-id><title>{title}</title><date><month>February</month><year>1968</year></date>{extra}</rfc-entry>'
class RefreshTests(unittest.TestCase):
 def test_namespace_and_source_month_preserved(self):
  r=m.parse_source(xml(item(31)),CFG)[0];self.assertEqual(r['date'],'1968-02');self.assertEqual(r['status'],'UNKNOWN')
 def test_relationship_direction_and_draft(self):
  r=m.parse_source(xml(item(3,extra='<obsoletes><doc-id>RFC2</doc-id></obsoletes><updated-by><doc-id>RFC4</doc-id></updated-by><draft>draft-x-v1.0_test-00</draft>')),CFG)[0];self.assertEqual(r['obsoletes'],[2]);self.assertEqual(r['updatedBy'],[4])
 def test_duplicate_rejected(self):
  with self.assertRaisesRegex(ValueError,'Duplicate'):m.parse_source(xml(item(1)+item(1)),CFG)
 def test_non_index_and_dtd_rejected(self):
  for raw in [b'<html/>',b'<!DOCTYPE root><rfc-index/>']:
   with self.assertRaises(ValueError):m.parse_source(raw,CFG)
 def test_missing_date_rejected(self):
  with self.assertRaises(ValueError):m.parse_source(xml('<rfc-entry><doc-id>RFC1</doc-id><title>x</title></rfc-entry>'),CFG)
 def test_coverage_can_expand(self):self.assertEqual(len(m.parse_source(xml(item(1)+item(2)+item(3)),CFG)),3)
 def test_atomic_capture_and_unchanged_check(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'web').mkdir();config={**CFG,'sourceUrl':'https://www.rfc-editor.org/rfc-index.xml','retainedCaptures':2,'maximumDropFraction':0.1};(root/'web/config.json').write_text(json.dumps(config));source=root/'source.xml';source.write_bytes(xml(item(1)+item(2)))
   m.collect(root,source,'2026-11-23T01:00:00Z');m.collect(root,source,'2026-11-24T01:00:00Z');index=json.loads((root/'web/data/index.json').read_text());self.assertEqual(len(index['captures']),1);self.assertEqual(index['checkedAt'],'2026-11-24T01:00:00Z');before=(root/'web/data/index.json').read_bytes();source.write_bytes(xml(item(1)))
   with self.assertRaises(ValueError):m.collect(root,source,'2026-11-25T01:00:00Z')
   self.assertEqual((root/'web/data/index.json').read_bytes(),before)
