"""
Document Parser — Phase 5

Converts uploaded files (PDF, DOCX, TXT) into plain text that enters
the LangGraph workflow, identical to manually pasted complaint text.

Assignment explicitly states: production-grade OCR is NOT required.
This handles text-based (selectable text) documents only.
"""

import io
from fastapi import UploadFile, HTTPException


async def extract_text_from_upload(file: UploadFile) -> str:
    """
    Extract plain text from an uploaded file.

    Supported formats:
      - .txt  — direct UTF-8 read
      - .pdf  — text-based PDF (selectable text, no OCR)
      - .docx — Microsoft Word document

    Args:
        file: FastAPI UploadFile object

    Returns:
        Extracted plain text string.

    Raises:
        HTTPException 400: If file format is unsupported or empty.
        HTTPException 422: If PDF has no extractable text (scanned/image-only).
    """
    filename = file.filename or ""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # ── Plain Text ──────────────────────────────────────
    if extension in ("txt", "eml", ""):
        try:
            return content.decode("utf-8", errors="replace").strip()
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not read text file: {e}")

    # ── PDF ─────────────────────────────────────────────
    elif extension == "pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            pages_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text.strip())
            extracted = "\n\n".join(pages_text).strip()
            if not extracted:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "No selectable text found in this PDF. "
                        "Scanned/image-only PDFs are not supported in this MVP. "
                        "Please paste the complaint text manually."
                    ),
                )
            return extracted
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"PDF parsing failed: {e}")

    # ── DOCX ────────────────────────────────────────────
    elif extension == "docx":
        try:
            from docx import Document
            doc = Document(io.BytesIO(content))
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            extracted = "\n".join(paragraphs).strip()
            if not extracted:
                raise HTTPException(status_code=422, detail="No text found in DOCX file.")
            return extracted
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"DOCX parsing failed: {e}")

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: '.{extension}'. Supported: .txt, .pdf, .docx, .eml",
        )
