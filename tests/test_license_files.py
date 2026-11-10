import contextlib
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import catalog


def gnu(title, version, year="2007"):
    """Opening lines of a verbatim FSF license text, as GitHub's templates indent them."""
    return f"                    {title}\n                       Version {version}\n\n Copyright (C) {year} Free Software Foundation, Inc. <https://fsf.org/>\n Everyone is permitted to copy and distribute verbatim copies\n"


def cc(title):
    return f"{title} 4.0 International\n\n=======================================================================\n\nCreative Commons Corporation (\"Creative Commons\") is not a law firm and\n"


GPL3 = gnu("GNU GENERAL PUBLIC LICENSE", "3, 29 June 2007")
AGPL3 = gnu("GNU AFFERO GENERAL PUBLIC LICENSE", "3, 19 November 2007")
MPL2 = "Mozilla Public License Version 2.0\n==================================\n\n1. Definitions\n--------------\n\n1.1. \"Contributor\"\n"
ISC = "ISC License\n\nCopyright (c) 2024 Example\n\nPermission to use, copy, modify, and/or distribute this software for any\npurpose with or without fee is hereby granted, provided that the above\n"
UNLICENSE = "This is free and unencumbered software released into the public domain.\n\nAnyone is free to copy, modify, publish, use, compile, sell, or\ndistribute this software, either in source code form or as a compiled\n"


class DetectCodeLicenseTests(unittest.TestCase):
    def test_standard_headers(self):
        cases = [
            ("GPL-2.0", gnu("GNU GENERAL PUBLIC LICENSE", "2, June 1991", "1989, 1991")),
            ("GPL-3.0", GPL3),
            ("AGPL-3.0", AGPL3),
            ("LGPL-2.1", gnu("GNU LESSER GENERAL PUBLIC LICENSE", "2.1, February 1999", "1991, 1999")),
            ("LGPL-3.0", gnu("GNU LESSER GENERAL PUBLIC LICENSE", "3, 29 June 2007")),
            ("GPL-3.0", "GNU GENERAL PUBLIC LICENSE\r\nVersion 3, 29 June 2007\r\n\r\nCopyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>\r\n"),
            ("MPL-2.0", MPL2),
            ("MPL-2.0", "Mozilla Public License Version 2.0\n\n1. Definitions\n\n1.1. \"Contributor\" means"),
            ("ISC", ISC),
            ("ISC", "The ISC License\r\n\r\nCopyright (c) 2010 A\r\nCopyright (c) 2020 B\r\n\r\nPermission to use, copy, modify, and distribute this software for any\r\npurpose with or without fee is hereby granted"),
            ("Unlicense", UNLICENSE),
            ("CC-BY-4.0", cc("Attribution")),
            ("CC-BY-4.0", cc("Attribution").replace("\n", "\r\n")),
            ("CC-BY-SA-4.0", cc("Attribution-ShareAlike")),
            ("CC-BY-NC-4.0", cc("Attribution-NonCommercial")),
            ("CC-BY-NC-ND-4.0", cc("Attribution-NonCommercial-NoDerivatives")),
            ("CC-BY-NC-SA-4.0", cc("Attribution-NonCommercial-ShareAlike")),
        ]
        for expected, text in cases:
            with self.subTest(expected=expected, text=text[:40]):
                self.assertEqual(catalog.detect_code_license(text), expected)

    def test_notices_composites_and_altered_texts_stay_unknown(self):
        cases = {
            "project notice under a GNU title": "GNU AFFERO GENERAL PUBLIC LICENSE\nVersion 3, 19 November 2007\n\nCopyright (c) 2025 Example Inc.\n\nThis program is free software: you can redistribute it\n",
            "GNU notice without the license text": "Copyright (C) 2025 Example\n\nThis program is free software: you can redistribute it and/or modify\nit under the terms of the GNU General Public License as published by\n",
            "dual-license preamble": "This project is dual-licensed under the AGPL-3.0 and a commercial license.\n\n" + AGPL3,
            "custom exception first": "Linking exception: you may link this library with proprietary code.\n\n" + GPL3,
            "unknown GNU version": GPL3.replace("Version 3, 29 June 2007", "Version 4, 1 April 2030"),
            "Library GPL is not LGPL-2.1": gnu("GNU LIBRARY GENERAL PUBLIC LICENSE", "2, June 1991", "1991"),
            "MPL title over custom terms": "Mozilla Public License Version 2.0\n\nThis software may only be used for research.\n",
            "MPL 1.1": "Mozilla Public License Version 1.1\n\n1. Definitions.\n",
            "ISC title over a non-commercial grant": ISC.replace("for any\npurpose with or without fee", "for non-commercial\npurposes"),
            "Unlicense sentence over custom terms": "This is free and unencumbered software released into the public domain.\n\nCommercial use requires a separate agreement.\n",
            "CC title without the legal code": "Attribution 4.0 International\n\nThe models in this repository are released for research only.\n",
            "CC 3.0": cc("Attribution").replace("4.0 International", "3.0 Unported"),
            "CC title not first": "Code is MIT licensed; the dataset is:\n\n" + cc("Attribution"),
            "plain-text mention": "This repository is released under the GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007.\n",
        }
        for label, text in cases.items():
            with self.subTest(label):
                self.assertIsNone(catalog.detect_code_license(text))


def sha(body):
    return hashlib.sha256(body).hexdigest()


class LicenseFileProbeTests(unittest.TestCase):
    URL, PRIMARY = "https://github.com/example/tool", "https://raw.githubusercontent.com/example/tool/HEAD/README.md"
    README = b"# Tool\n"

    def setUp(self):
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(mock.patch.object(catalog, "DATA", directory / "data"))
        self.enterContext(mock.patch.object(catalog, "CACHE", directory / "cache"))

    def enrich(self, files):
        """files: license filename -> body served with HTTP 200; every other name is a 404."""
        rid = catalog.canonical(self.URL)[0]
        catalog.write_json(catalog.DATA / "editorial.json", [{"url": self.URL, "kind": "framework", "name": "Tool"}])
        catalog.write_jsonl(catalog.DATA / "primary-evidence.jsonl", [{"id": rid, "url": self.PRIMARY, "content_matched": True,
            "sha256": sha(self.README), "retrieved_at": "2026-10-17T00:00:00Z"}])
        requested = []
        def fetch(url, refresh=False):
            name = url.rsplit("/", 1)[1]
            requested.append(name)
            if name not in files:
                return {"url": url, "ok": False, "status": 404, "error": "HTTP Error 404"}, b""
            body = files[name].encode()
            return {"url": url, "ok": True, "status": 200, "sha256": sha(body), "retrieved_at": "2026-10-17T01:00:00Z"}, body
        with mock.patch.object(catalog, "cached_body", return_value=self.README), mock.patch.object(catalog, "fetch", side_effect=fetch), \
                contextlib.redirect_stdout(io.StringIO()):
            catalog.enrich(types.SimpleNamespace(refresh=False))
        return requested, {r["id"]: r for r in catalog.read_jsonl(catalog.DATA / "enrichment.jsonl")}[rid]

    def test_each_additional_filename_is_probed_in_order(self):
        for filename in ("LICENSE.rst", "LICENCE", "COPYING"):
            with self.subTest(filename=filename):
                requested, row = self.enrich({filename: ISC})
                self.assertEqual(requested, list(catalog.LICENSE_FILES[:catalog.LICENSE_FILES.index(filename) + 1]))
                self.assertEqual(row["licenses"]["code"]["declared"], "ISC")
                self.assertEqual(row["licenses"]["code"]["url"], f"https://raw.githubusercontent.com/example/tool/HEAD/{filename}")
                self.assertEqual(row["licenses"]["code"]["basis"], "repository LICENSE header")
                self.assertEqual([e["url"] for e in row["evidence"] if e["method"] == "license_header"], [row["licenses"]["code"]["url"]])
        requested, row = self.enrich({})
        self.assertEqual(requested, ["LICENSE", "LICENSE.md", "LICENSE.txt", "LICENSE.rst", "LICENCE", "COPYING"])
        self.assertEqual(row["licenses"], {})

    def test_first_license_file_found_decides_even_when_unknown(self):
        requested, row = self.enrich({"LICENSE": "Custom research-only license.\n", "COPYING": GPL3})
        self.assertEqual(requested, ["LICENSE"])
        self.assertEqual(row["licenses"], {})
        self.assertEqual(row["evidence"], [])

    def test_gnu_declaration_records_that_the_version_scope_is_unstated(self):
        requested, row = self.enrich({"COPYING": AGPL3})
        self.assertEqual(row["licenses"]["code"]["declared"], "AGPL-3.0")
        self.assertEqual(row["licenses"]["code"]["basis"], "repository LICENSE header; GNU text names no -only or -or-later variant")


if __name__ == "__main__":
    unittest.main()
