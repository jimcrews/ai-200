import uuid
from datetime import UTC, datetime
from typing import Any

from azure.core.exceptions import AzureError


class VectorStoreError(Exception):
    """Raised when a Cosmos DB upload or query fails."""


class CosmosDBVectorStore:
    """
    A class to handle document storage and vector search operations in Cosmos DB.

    This class provides methods to upload documents with embeddings, perform vector
    similarity searches, and manage the vector index in Cosmos DB.
    """

    def __init__(
        self,
        container_client: Any,
        partition_key: str = "partitionKey",
    ):
        """
        Initialize the CosmosDBVectorStore.

        Args:
            container_client: An instance of Cosmos DB container client
            partition_key: Name of the partition key field (default: "partitionKey")
        """
        self.container_client = container_client
        self.partition_key = partition_key

    def _upload_document(
        self,
        document: dict[str, Any],
        partition_key_value: str = "global",
    ) -> dict[str, Any]:
        """
        Upload a single document with its embedding to Cosmos DB.

        Args:
            document: The document data (text, etc.)
            embedding: The vector embedding for the document (if None, document must already have 'embedding' field)
            partition_key_value: Value for the partition key (default: "global")

        Returns:
            The created document with ID and partition key

        Raises:
            ValueError: If document is missing required fields
        """
        # Create a copy to avoid modifying the original
        doc_to_upload = document.copy()

        # Ensure embedding exists
        if "embedding" not in doc_to_upload:
            raise ValueError(
                "Document must contain an 'embedding' field or provide embedding parameter"
            )

        # Add partition key if not present
        if self.partition_key not in doc_to_upload:
            doc_to_upload[self.partition_key] = partition_key_value

        # Add unique ID if not present
        if "id" not in doc_to_upload:
            doc_to_upload["id"] = str(uuid.uuid4())

        # Add timestamp if not present
        if "timestamp" not in doc_to_upload:
            doc_to_upload["timestamp"] = datetime.now(UTC).isoformat()

        # Upload to Cosmos DB
        try:
            created_doc = self.container_client.upsert_item(body=doc_to_upload)
            print(
                f"✅ Uploaded document: {doc_to_upload['id']} (partition: {doc_to_upload[self.partition_key]})"
            )
            return created_doc
        except AzureError as e:
            raise VectorStoreError(f"Failed to upload document: {e!s}") from e

    def upload_documents(
        self,
        documents: list[dict[str, Any]],
        partition_key_value: str = "global",
    ) -> list[dict[str, Any]]:
        """
        Upload multiple documents with their embeddings to Cosmos DB one at a time.

        Args:
            documents: List of document data
            embeddings: List of embeddings corresponding to each document
            partition_key_value: Value for the partition key (default: "global")

        Returns:
            List of created documents
        """
        uploaded_docs = []

        for idx, doc in enumerate(documents):
            try:
                created_doc = self._upload_document(
                    document=doc,
                    partition_key_value=partition_key_value,
                )
                uploaded_docs.append(created_doc)
            except (VectorStoreError, ValueError) as e:
                print(f"⚠️ Failed to upload document at index {idx}: {e!s}")
                continue

        print(f"\n✅ Uploaded {len(uploaded_docs)} of {len(documents)} documents")
        return uploaded_docs

    def vector_search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        similarity_threshold: float | None = None,
        partition_key_value: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform a vector similarity search.

        Args:
            query_embedding: The query vector to search for
            top_k: Number of top results to return (default: 10)
            similarity_threshold: Minimum similarity score (0-1) for results (default: None)
            partition_key_value: Filter by partition key (default: None)

        Returns:
            List of matching documents with similarity scores
        """
        # Always include the vector distance calculation
        select_clause = f"""
            SELECT TOP {top_k} 
                c.id, 
                c.content,
                c.filename,
                c.timestamp,
                VectorDistance(c.embedding, @query_embedding) AS similarity_score
        """

        # Build WHERE clause
        where_parts = []

        # Partition key filter
        if partition_key_value:
            where_parts.append(f"c.{self.partition_key} = @partition_key")

        # Build the complete query
        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        # returns the most similar results first. don't add ASC or DESC to order.
        query = f"""
            {select_clause}
            FROM c
            {where_clause}
            ORDER BY VectorDistance(c.embedding, @query_embedding)
        """

        # Prepare parameters
        parameters = [{"name": "@query_embedding", "value": query_embedding}]

        if partition_key_value:
            parameters.append({"name": "@partition_key", "value": partition_key_value})

        # Execute the query
        try:
            items = list(
                self.container_client.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=(partition_key_value is None),
                )
            )

            # Apply similarity threshold if specified
            if similarity_threshold is not None:
                items = [
                    item
                    for item in items
                    if item.get("similarity_score", 0) >= similarity_threshold
                ]

            print(f"✅ Found {len(items)} results")
            return items

        except AzureError as e:
            raise VectorStoreError(f"Vector search failed: {e!s}") from e

    def hybrid_search(
        self,
        query_embedding: list[float],
        text_query: str | None = None,
        top_k: int = 10,
        partition_key_value: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform a hybrid search combining vector and text search.

        Args:
            query_embedding: The query vector to search for
            text_query: Optional text query for keyword search
            top_k: Number of top results to return
            partition_key_value: Filter by partition key

        Returns:
            List of matching documents with similarity scores
        """
        # Build the vector search part
        vector_results = self.vector_search(
            query_embedding=query_embedding,
            top_k=top_k * 2,  # Get more results for hybrid ranking
            partition_key_value=partition_key_value,
        )

        # If no text query, return vector results
        if not text_query:
            return vector_results[:top_k]

        # Perform text search using Azure Cosmos DB's full-text search
        text_results = self.text_search(
            text_query=text_query,
            top_k=top_k * 2,
            partition_key_value=partition_key_value,
        )

        # Combine and rank results (simple merge for now)
        # In production, you might want more sophisticated ranking
        combined_results = self._merge_search_results(
            vector_results, text_results, top_k
        )

        return combined_results

    def text_search(
        self,
        text_query: str,
        top_k: int = 10,
        partition_key_value: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform a text search using CONTAINS (for keyword matching).

        Args:
            text_query: The text to search for
            top_k: Number of top results to return
            partition_key_value: Filter by partition key

        Returns:
            List of matching documents
        """
        # Build the query for text search
        where_parts = ["CONTAINS(c.content, @text_query)"]

        if partition_key_value:
            where_parts.append(f"c.{self.partition_key} = @partition_key")

        where_clause = f"WHERE {' AND '.join(where_parts)}"

        query = f"""
            SELECT TOP {top_k}
                c.id,
                c.content,
                c.filename,
                c.timestamp
            FROM c
            {where_clause}
        """

        parameters = [{"name": "@text_query", "value": text_query}]

        if partition_key_value:
            parameters.append({"name": "@partition_key", "value": partition_key_value})

        try:
            items = list(
                self.container_client.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=(partition_key_value is None),
                )
            )

            print(f"✅ Found {len(items)} text search results")
            return items

        except AzureError as e:
            raise VectorStoreError(f"Text search failed: {e!s}") from e

    def _merge_search_results(
        self,
        vector_results: list[dict[str, Any]],
        text_results: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """
        Merge and rank vector and text search results.

        This is a simple merge strategy. For production, consider using
        Reciprocal Rank Fusion (RRF) or similar algorithms.
        """
        # Create a dictionary to combine results
        combined = {}

        # Add vector results with score
        for rank, item in enumerate(vector_results):
            doc_id = item.get("id")
            if doc_id:
                combined[doc_id] = {
                    "doc": item,
                    "vector_rank": rank,
                    "text_rank": None,
                    "combined_score": None,
                }

        # Add text results with rank
        for rank, item in enumerate(text_results):
            doc_id = item.get("id")
            if doc_id:
                if doc_id in combined:
                    combined[doc_id]["text_rank"] = rank
                else:
                    combined[doc_id] = {
                        "doc": item,
                        "vector_rank": None,
                        "text_rank": rank,
                        "combined_score": None,
                    }

        # Calculate combined score (reciprocal rank fusion)
        k = 60  # RRF constant
        for doc_id, data in combined.items():
            vector_rank = data.get("vector_rank")
            text_rank = data.get("text_rank")

            vector_score = 1 / (k + vector_rank + 1) if vector_rank is not None else 0
            text_score = 1 / (k + text_rank + 1) if text_rank is not None else 0

            # Weighted combination (adjust weights as needed)
            combined[doc_id]["combined_score"] = (0.7 * vector_score) + (
                0.3 * text_score
            )

        # Sort by combined score and return top_k
        sorted_results = sorted(
            combined.values(),
            key=lambda x: x["combined_score"] if x["combined_score"] is not None else 0,
            reverse=True,
        )

        result_items = [item["doc"] for item in sorted_results[:top_k]]

        # Add combined score to results
        for item in result_items:
            doc_id = item.get("id")
            if doc_id in combined:
                item["combined_score"] = combined[doc_id]["combined_score"]

        return result_items
