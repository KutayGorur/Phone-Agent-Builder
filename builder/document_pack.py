"""Read heterogeneous source folders without inventing a precedence order.

This is input handling only: documents remain evidence, not executable
instructions. JSON files are retained as documents rather than presumed to be
OpenAPI or customer data. The downstream parser must determine their roles.
"""
import argparse
import email
import email.policy
import hashlib
import json
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET


TEXT_TYPES = {'.md', '.txt', '.json', '.csv', '.yaml', '.yml'}
DOCUMENT_TYPES = TEXT_TYPES | {'.pdf', '.docx', '.eml'}


def read_document(path):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in TEXT_TYPES:
        return path.read_text(encoding='utf-8-sig')
    if suffix == '.eml':
        message = email.message_from_bytes(path.read_bytes(), policy=email.policy.default)
        headers = '\n'.join('%s: %s' % (key, message.get(key, ''))
                            for key in ('Date', 'From', 'To', 'Subject'))
        body = message.get_body(preferencelist=('plain',))
        if body is None:
            raise ValueError('%s: email has no plain-text body; cannot silently omit its content' % path)
        return headers + '\n\n' + body.get_content()
    if suffix == '.docx':
        with zipfile.ZipFile(path) as archive:
            root = ET.fromstring(archive.read('word/document.xml'))
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        lines = []
        body = root.find('w:body', ns)
        if body is None:
            raise ValueError('%s: Word document has no body' % path)
        for block in body:
            if block.tag.endswith('}tbl'):
                for row in block.findall('w:tr', ns):
                    lines.append(' | '.join('\n'.join(
                        ''.join(t.text or '' for t in paragraph.findall('.//w:t', ns))
                        for paragraph in cell.findall('w:p', ns))
                        for cell in row.findall('w:tc', ns)))
            elif block.tag.endswith('}p'):
                lines.append(''.join(t.text or '' for t in block.findall('.//w:t', ns)))
        return '\n'.join(lines)
    if suffix == '.pdf':
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError('PDF inputs require pypdf: install requirements-documents.txt') from exc
        reader = PdfReader(path)
        pages = []
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ''
            if not text.strip():
                raise ValueError('%s: PDF page %s has no extractable text; OCR or visual input is required'
                                 % (path, number))
            pages.append('[Page %s]\n%s' % (number, text))
        return '\n\n'.join(pages)
    raise ValueError('%s: unsupported document format' % path)


def load_pack(folder):
    """Return source text, hashes and unsupported files; never silently discard failures.

    Sorting is solely for repeatable output. It does not establish which source
    wins: amendments, timestamps and authority must be interpreted from evidence.
    """
    folder = Path(folder).resolve()
    if not folder.is_dir():
        raise ValueError('%s: not a document folder' % folder)
    documents, unsupported = [], []
    for path in sorted(folder.rglob('*'), key=lambda p: p.relative_to(folder).as_posix()):
        if path.is_dir():
            continue
        if not path.resolve().is_relative_to(folder):
            raise ValueError('%s: document link escapes the input folder' % path)
        relative = path.relative_to(folder).as_posix()
        if path.suffix.lower() not in DOCUMENT_TYPES:
            unsupported.append(relative)
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        text = read_document(path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('%s: source changed while being read; retry with a stable pack' % path)
        if not text.strip():
            raise ValueError('%s: empty document' % path)
        documents.append({'source': relative, 'sha256': digest, 'text': text})
    if not documents:
        raise ValueError('%s: no readable source documents' % folder)
    return {'documents': documents, 'unsupported': unsupported,
            'ordering': 'stable path order only; source authority is not inferred from file order'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder')
    parser.add_argument('--out', required=True, help='manifest with extracted source text, outside the input folder')
    args = parser.parse_args()
    output = Path(args.out).resolve()
    if output.is_relative_to(Path(args.folder).resolve()):
        parser.error('output must be outside the source folder to avoid becoming a future input')
    pack = load_pack(args.folder)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Read %s documents; %s unsupported files explicitly listed; wrote %s'
          % (len(pack['documents']), len(pack['unsupported']), output))


if __name__ == '__main__':
    main()
