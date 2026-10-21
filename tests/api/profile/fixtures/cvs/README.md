# Synthetic CV fixtures (F1, M2 — Prompt 9 / item 9)

Test and demo inputs for `POST /api/v1/profile/cv`, so the endpoint can be exercised
without the intake UI. **Everything here is invented**: synthetic personas from
`docs/PROJECT_CONTEXT.md` plus made-up names, and every email is on `example.com`.
No real resume, no real contact detail. Never add one.

| File | What it proves | Parser result |
|---|---|---|
| `cv_aisyah.pdf` | Persona CV, same name/segment/skills as the seed CSVs | `customer-service`, `excel`, `process-mapping`, `risk-compliance` |
| `cv_weijie.pdf` | Persona CV | `python`, `sql` |
| `cv_ravi.pdf` | Persona CV | `logistics-planning`, `excel` |
| `cv_data_entry.pdf` | "data entry" is not a taxonomy alias | no skills (must not become `manual-data-entry`) |
| `cv_python_programming.pdf` | "Python programming" appears once | exactly one `python`, confidence `0.30` |
| `cv_java_javascript.pdf` | Word boundaries; nothing outside the catalogue | no skills |
| `cv_scanned.pdf` | Image-only page, no selectable text | raises `PdfNoText` → HTTP 422 `pdf_no_text` |
| `cv_long.txt` | 100,000 characters, no `@` | no skills, `truncated=false`, parses fast |

Covered by `tests/api/profile/test_cv_fixtures.py`. The PDF tests skip with an
install hint when PyMuPDF is absent — the parser then refuses the upload (501)
instead of decoding PDF bytes as text.

## Regenerate

The files are generated, never edited by hand. Generation is deterministic — no
timestamps, and the PDF trailer `/ID` is the MD5 of the file body — so a re-run
reproduces byte-identical output:

```powershell
uv run --no-project python src/scripts/generate_mock_cvs.py           # write the files
uv run --no-project python src/scripts/generate_mock_cvs.py --check   # CI: report drift, write nothing
uv run --no-project python src/scripts/generate_mock_cvs.py --verify  # re-parse with the real parser
```

The script writes PDFs itself (PDF 1.4, Helvetica text operators, one FlateDecode
`DeviceGray` image) so the repository needs no PDF-writing dependency. PyMuPDF is a
**read-only** dependency for the parser: `pymupdf>=1.24.0,<2` in `requirements.txt`.

## Upload one in Swagger

1. `make dev` (backend on `:8000`, frontend on `:3000`).
2. Open <http://localhost:8000/docs>, expand **POST /api/v1/profile/cv**, click
   **Try it out**.
3. Set the `file` field to any fixture above, set the `X-Demo-User` header to
   `aisyah` (or `weijie` / `ravi`), click **Execute**, and read the `skills` array
   plus the `truncated` flag in the response body.

The server never stores the upload: bytes are parsed in memory and dropped.

## Upload one from PowerShell

`curl.exe` (not the `curl` PowerShell alias) with the file path relative to the
repository root:

```powershell
curl.exe -F "file=@tests/api/profile/fixtures/cvs/cv_aisyah.pdf" -H "X-Demo-User: aisyah" http://localhost:8000/api/v1/profile/cv
```

`curl.exe` picks `application/pdf` from the extension; if your client does not, add
`;type=application/pdf` (or `;type=text/plain` for `cv_long.txt`) after the path.
Expected: `200` with the persona's skills for `cv_aisyah.pdf`, `422 pdf_no_text` for
`cv_scanned.pdf`, and `200` with an empty `skills` array for `cv_long.txt`.
