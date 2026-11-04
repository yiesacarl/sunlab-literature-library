import unittest
from official_sources import feed_records,atom_records,merge,identity
class OfficialSourceTests(unittest.TestCase):
 def test_atom_version_identity_and_initial_date(self):
  xml=b'''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:a="http://arxiv.org/schemas/atom"><entry><id>http://arxiv.org/abs/2610.12345v3</id><title>A molecular qubit</title><published>2026-10-28T17:00:00Z</published><updated>2026-11-03T00:00:00Z</updated><summary>Experimental evidence</summary><a:doi>10.1234/X</a:doi></entry></feed>'''
  p,_=atom_records(xml,'https://export.arxiv.org/api/query');self.assertEqual(p[0]['arxivId'],'2610.12345');self.assertEqual(p[0]['publicationDate'],'2026-10-28');self.assertEqual(p[0]['doi'],'10.1234/x')
 def test_feed_teaser_not_full_abstract(self):
  xml=b'''<rss><channel><item><title>Quantum sensing</title><link>https://doi.org/10.1234/x</link><description>Interesting partial result...</description><pubDate>Tue, 03 Nov 2026 10:00:00 GMT</pubDate></item></channel></rss>'''
  p=feed_records(xml,dict(publisher='APS',name='PRA',feed='https://feeds.aps.org/rss/recent/pra.xml'))[0];self.assertFalse(p['abstractComplete']);self.assertEqual(p['abstract'],'');self.assertEqual(p['publicationDate'],'2026-11-03')
 def test_non_feed_rejected(self):
  with self.assertRaises(ValueError):feed_records(b'<html><body>blocked</body></html>',{})
 def test_rss_arxiv_announcement_not_submission(self):
  xml=b'''<rss><channel><item><title>Spin sensing</title><link>https://arxiv.org/abs/2610.12345</link><description>arXiv:2610.12345v2 Announce Type: replace Abstract: Real abstract.</description><pubDate>Tue, 03 Nov 2026 00:00:00 -0500</pubDate></item></channel></rss>'''
  p=feed_records(xml,dict(publisher='arXiv',name='arXiv',feed='https://rss.arxiv.org/rss/quant-ph'))[0];self.assertIn('announcement',p['dateBasis']);self.assertEqual(p['abstract'],'Real abstract.')
 def test_preprint_journal_merge_keeps_earliest_seen(self):
  a=dict(id='arxiv:2610.12345',arxivId='2610.12345',doi='10.1234/x',title='Preprint title',status='Preprint',metadataSource='arXiv API',firstSeenDate='2026-10-30')
  b=dict(id='doi:10.1234/x',doi='10.1234/x',title='Published title',status='Published',metadataSource='Crossref',firstSeenDate='2026-11-04')
  out=merge([a,b]);self.assertEqual(len(out),1);self.assertEqual(out[0]['firstSeenDate'],'2026-10-30');self.assertIn(a['id'],identity(out[0]));self.assertEqual(out[0]['title'],'Published title')
 def test_transitive_title_and_doi_merge(self):
  a=dict(id='a',title='Spin–phonon café',doi='10.1/a');b=dict(id='b',title='Spin phonon cafe',doi='10.1/b');c=dict(id='c',title='New title',doi='10.1/a')
  out=merge([a,b,c]);self.assertEqual(len(out),1);self.assertIn('doi:10.1/b',identity(out[0]))
 def test_verified_date_replaces_feed_date(self):
  a=dict(id='doi:10.1/a',title='Study',status='Published',metadataSource='ACS official RSS',publicationDate='2026-12-31',abstractComplete=True,abstract='Read abstract',evidenceUrl='https://example.org/feed',readingBasis='Publisher abstract via official RSS',sourceUrl='https://example.org/paper')
  b=dict(id=a['id'],title='Study',status='Published',metadataSource='Crossref',publicationDate='2026-10-30',abstractComplete=False,abstract='',sourceUrl='https://doi.org/10.1/a')
  out=merge([a,b])[0];self.assertEqual(out['publicationDate'],'2026-10-30');self.assertEqual(out['abstract'],'Read abstract');self.assertEqual(out['sourceUrl'],a['sourceUrl'])
if __name__=='__main__':unittest.main()
