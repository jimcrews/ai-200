from dataclasses import replace

from openai import OpenAI, OpenAIError

from document import Document


class EmbeddingError(Exception):
    """Raised when the embedding model call fails."""


class EmbeddingsProcessor:
    """
    A class to generate vector embeddings using an OpenAI embedding model.

    Used for both documents (upload) and questions (query), so both are embedded
    with the same model and dimensions.
    """

    def __init__(
        self,
        openai_client: OpenAI,
        embedding_model_name: str,
        max_text_length: int = 8191,
        embedding_dimensions: int = 512,
    ):
        """
        Initialize the EmbeddingsProcessor.

        Args:
            openai_client: Authenticated OpenAI client instance
            embedding_model_name: Name of the embedding model deployment to use
            max_text_length: Maximum characters to send to the embedding model
            embedding_dimensions: Vector size to request; must match the Postgres
                vector(n) column the embeddings are stored in
        """
        self.openai_client = openai_client
        self.embedding_model_name = embedding_model_name
        self.max_text_length = max_text_length
        self.embedding_dimensions = embedding_dimensions

    def generate_embedding(self, text: str) -> list[float]:
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
        # text-embedding-3-small accepts at most 8,191 tokens per input
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
            return response.data[0].embedding
        except OpenAIError as e:
            raise EmbeddingError(f"Failed to generate embedding: {e!s}") from e

    def embed_documents(self, documents: list[Document]) -> list[Document]:
        """
        Generate an embedding for each document's content.

        Args:
            documents: Documents with extracted text

        Returns:
            Copies of the documents with embeddings; documents that are empty
            or fail to embed are left out
        """
        embedded_docs = []
        for doc in documents:
            print(f"\nEmbedding: {doc.filename}")

            if not doc.content:
                print("  ⚠ No text extracted, skipping")
                continue

            try:
                embedding = self.generate_embedding(doc.content)
            except EmbeddingError as e:
                print(f"  ✗ {e!s}")
                continue

            print(f"  ✓ Generated embedding (dimensions: {len(embedding)})")
            # replace() returns a copy, leaving the extracted documents unchanged
            embedded_docs.append(replace(doc, embedding=embedding))

        print(f"\n✓ Embedded {len(embedded_docs)} of {len(documents)} document(s)")
        return embedded_docs
