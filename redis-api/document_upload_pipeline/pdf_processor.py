from pathlib import Path

import pymupdf4llm

from document import Document


class PDFExtractionError(Exception):
    """Raised when text can't be extracted from a PDF."""


class PDFProcessor:
    """
    A class to extract text content from the PDF files in a folder.
    """

    def read_pdf_folder(self, folder_path: str | Path) -> list[Document]:
        """
        Read all PDF files from a folder and extract their text content.

        Args:
            folder_path: Path to the folder containing PDF files

        Returns:
            List of Documents, without embeddings
        """
        documents = []
        folder = Path(folder_path)

        if not folder.exists():
            raise ValueError(f"Folder path does not exist: {folder_path}")

        pdf_files = sorted(folder.glob("*.pdf"))

        if not pdf_files:
            print(f"No PDF files found in {folder_path}")
            return documents

        print(f"Found {len(pdf_files)} PDF file(s) in {folder_path}")

        for pdf_path in pdf_files:
            print(f"Extracting: {pdf_path.name}")
            try:
                doc_content = self._extract_text_from_pdf(pdf_path)
                documents.append(
                    Document(
                        filename=pdf_path.name,
                        filepath=str(pdf_path),
                        content=doc_content,
                    )
                )
                print(f"  ✓ Extracted {len(doc_content)} characters")
            except PDFExtractionError as e:
                print(f"  ✗ Error processing {pdf_path.name}: {e!s}")
                continue

        return documents

    def _extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extract text content from a single PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text content as a string
        """
        text = ""
        try:
            text = pymupdf4llm.to_markdown(pdf_path)
        # pymupdf raises FileDataError (a RuntimeError) for corrupt/empty files
        except (RuntimeError, ValueError, OSError) as e:
            raise PDFExtractionError(f"Failed to extract text from PDF: {e}") from e

        return text.strip()
