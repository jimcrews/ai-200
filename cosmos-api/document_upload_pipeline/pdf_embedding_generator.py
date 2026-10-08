from pathlib import Path
from typing import Any

import pymupdf4llm
from openai import OpenAIError


class PDFExtractionError(Exception):
    """Raised when text can't be extracted from a PDF."""


class EmbeddingError(Exception):
    """Raised when the embedding model call fails."""


class PDFEmbeddingGenerator:
    """
    A class to handle PDF document processing and embedding generation using OpenAI.

    This class reads PDF files from a specified folder, extracts text content,
    and generates vector embeddings using OpenAI's embedding models.
    Assumes all PDFs are of reasonable size (under the token limit for embedding).
    """

    def __init__(
        self,
        openai_client,
        embedding_model_name,
        max_text_length: int = 8191,
        embedding_dimensions: int = 512,
    ):
        """
        Initialize the PDFEmbeddingGenerator.

        Args:
            openai_client: Authenticated OpenAI client instance
            embedding_model_name: Name of the embedding model deployment to use
            max_text_length: Maximum characters allowed by the embedding model
            embedding_dimensions: Vector size to request; must match the Cosmos
                container's vectorEmbeddingPolicy (512 in deploy_cosmosdb.bicep)
        """
        self.openai_client = openai_client
        self.embedding_model_name = embedding_model_name
        self.max_text_length = max_text_length
        self.embedding_dimensions = embedding_dimensions

    def read_pdf_folder(self, folder_path: str) -> list[dict[str, Any]]:
        """
        Read all PDF files from a folder and extract their text content.

        Args:
            folder_path: Path to the folder containing PDF files

        Returns:
            List of dictionaries containing documents and text
        """
        documents = []
        folder = Path(folder_path)

        if not folder.exists():
            raise ValueError(f"Folder path does not exist: {folder_path}")

        pdf_files = list(folder.glob("*.pdf"))

        if not pdf_files:
            print(f"No PDF files found in {folder_path}")
            return documents

        print(f"Found {len(pdf_files)} PDF file(s) in {folder_path}")

        for pdf_path in pdf_files:
            print(f"Extracting: {pdf_path.name}")
            try:
                doc_content = self._extract_text_from_pdf(pdf_path)
                documents.append(
                    {
                        "filename": pdf_path.name,
                        "filepath": str(pdf_path),
                        "content": doc_content,
                    }
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

    def _generate_embedding(self, text: str) -> list[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: The text to embed

        Returns:
            List of floating-point numbers representing the embedding
        """
        if not text or not text.strip():
            raise ValueError("Empty text provided for embedding generation")

        # Truncate text if it exceeds the maximum length
        if len(text) > self.max_text_length:
            text = text[: self.max_text_length]
            print(f"  ⚠ Text truncated to {self.max_text_length} characters")

        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model_name,
                input=text,
                encoding_format="float",
                dimensions=self.embedding_dimensions,
            )
            embedding = response.data[0].embedding
            return embedding
        except OpenAIError as e:
            raise EmbeddingError(f"Failed to generate embedding: {e!s}") from e

    def process_documents(
        self, folder_path: str, generate_embeddings: bool = True
    ) -> list[dict[str, Any]]:
        """
        Process all PDFs in a folder and generate embeddings.

        Args:
            folder_path: Path to folder containing PDFs
            generate_embeddings: Whether to generate embeddings (default: True)

        Returns:
            List of processed documents with embeddings
        """
        # Step 1: Read all PDFs
        documents = self.read_pdf_folder(folder_path)

        if not documents:
            return []

        # Step 2: Process each document
        processed_docs = []

        for doc in documents:
            print(f"\nEmbedding: {doc['filename']}")
            doc_content = doc["content"]

            if not doc_content:
                print(f"  ⚠ No text extracted from {doc['filename']}")
                processed_docs.append({**doc, "embedding": None, "processed_at": None})
                continue

            # Generate embedding if requested
            embedding = None
            if generate_embeddings:
                try:
                    embedding = self._generate_embedding(doc_content)
                    print(f"  ✓ Generated embedding (dimensions: {len(embedding)})")
                except (EmbeddingError, ValueError) as e:
                    print(f"  ✗ Failed to generate embedding: {e!s}")

            # Create document entry
            doc_entry = {
                "filename": doc["filename"],
                "filepath": doc["filepath"],
                "content": doc_content,
                "embedding": embedding,
                "processed_at": str(__import__("datetime").datetime.now()),
            }

            processed_docs.append(doc_entry)
            print(f"  ✅ Completed processing: {doc['filename']}")

        print(f"\n✓ Processed {len(processed_docs)} document(s)")
        return processed_docs
