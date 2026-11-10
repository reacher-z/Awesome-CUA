from pathlib import Path
import re
import struct
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
PNG = ROOT / ".github/social-preview.png"
SVG = ROOT / ".github/social-preview.svg"


def chunks(data):
    offset = 8
    while offset < len(data):
        length, kind = struct.unpack(">I4s", data[offset:offset + 8])
        body = data[offset + 8:offset + 8 + length]
        crc = struct.unpack(">I", data[offset + 8 + length:offset + 12 + length])[0]
        yield kind, body, crc
        offset += 12 + length


class RepositorySocialPreviewTests(unittest.TestCase):
    def test_png_has_githubs_recommended_size(self):
        data = PNG.read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        parsed = list(chunks(data))
        self.assertEqual(parsed[0][0], b"IHDR")
        self.assertEqual(struct.unpack(">II", parsed[0][1][:8]), (1280, 640))
        self.assertEqual(parsed[-1][0], b"IEND")
        for kind, body, crc in parsed:
            self.assertEqual(zlib.crc32(kind + body), crc, kind)
        self.assertLess(len(data), 1_000_000)

    def test_svg_source_matches_the_png_canvas(self):
        root = re.search(r"<svg\b[^>]*>", SVG.read_text(encoding="utf-8"))[0]
        self.assertIn('width="1280"', root)
        self.assertIn('height="640"', root)
        self.assertIn('viewBox="0 0 1280 640"', root)

    def test_preview_names_the_repository_and_has_no_stale_counts(self):
        text = re.sub(r"<[^>]+>", " ", SVG.read_text(encoding="utf-8"))
        self.assertIn("github.com/reacher-z/Awesome-CUA", text)
        self.assertIn("Computer-Use Agents", text)
        self.assertNotRegex(text, r"\d[\d,]{2,}")

    def test_maintenance_docs_explain_regeneration_and_upload(self):
        docs = (ROOT / "docs/maintenance.md").read_text(encoding="utf-8")
        self.assertIn(".github/social-preview.svg", docs)
        self.assertIn("1280×640", docs)
        self.assertIn("Settings → General → Social preview", docs)


if __name__ == "__main__":
    unittest.main()
