"""Document-input checks; no models, platforms or final-case content."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from builder.document_pack import load_pack, read_document


class DocumentPackTests(unittest.TestCase):
    def test_nested_paths_keep_duplicate_names_distinct_and_preserve_utf8(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('old', 'new'):
                (root / name).mkdir()
                (root / name / 'memo.txt').write_text('Türkçe ₺ ' + name, encoding='utf-8-sig')
            (root / 'diagram.png').write_bytes(b'not text')
            pack = load_pack(root)
            self.assertEqual([d['source'] for d in pack['documents']], ['new/memo.txt', 'old/memo.txt'])
            self.assertEqual(pack['documents'][0]['text'], 'Türkçe ₺ new')
            self.assertEqual(pack['unsupported'], ['diagram.png'])
            self.assertEqual(pack['documents'][0]['sha256'],
                             hashlib.sha256((root / 'new/memo.txt').read_bytes()).hexdigest())

    def test_email_retains_date_and_body_for_source_authority(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'memo.eml'
            path.write_text('Date: Mon, 12 Oct 2026 10:00:00 +0300\nSubject: Correction\n'
                            'Content-Type: text/plain; charset=utf-8\n\nReplace the earlier limit.', encoding='utf-8')
            text = read_document(path)
            self.assertIn('Date:', text)
            self.assertIn('Subject: Correction', text)
            self.assertIn('Replace the earlier limit.', text)

    def test_word_tables_remain_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'table.docx'
            xml = '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Heading</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Code</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Meaning</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('word/document.xml', xml)
            self.assertEqual(read_document(path), 'Heading\nCode | Meaning')

    def test_empty_source_is_rejected_not_silently_omitted(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'policy.txt').write_text('   ', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'empty document'):
                load_pack(folder)

    @unittest.skipUnless(importlib.util.find_spec('pypdf'), 'optional PDF reader not installed')
    def test_pdf_page_without_text_is_rejected(self):
        from pypdf import PdfWriter
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'scan.pdf'
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)
            with path.open('wb') as output:
                writer.write(output)
            with self.assertRaisesRegex(ValueError, 'OCR or visual input is required'):
                read_document(path)


if __name__ == '__main__':
    unittest.main()
