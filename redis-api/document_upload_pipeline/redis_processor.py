import struct
import time
from datetime import UTC, datetime

import redis
from redis.commands.search.field import NumericField, TagField, TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from document import Document, SearchResult


class RedisProcessor:
    """
    A class to handle Redis operations: index setup, saving documents and
    vector similarity search with RediSearch.
    """

    def __init__(self, client: redis.Redis, index_name: str = "documents"):
        """
        Initialize the RedisProcessor.

        Args:
            client: Connected Redis client, created with decode_responses=True;
                the caller owns it and closes it
            index_name: RediSearch index over the document hashes
        """
        self.client = client
        self.index_name = index_name
        # Each document is a hash at "<index_name>:<filename>"; the index covers
        # every hash whose key starts with this prefix
        self.key_prefix = f"{index_name}:"

    def create_index(self, embedding_dimensions: int) -> None:
        """
        Create the RediSearch index, if it doesn't exist.

        Unlike Postgres, Redis has no table to create: hashes are stored as-is,
        and the index tells RediSearch which hash fields to index and how.

        Args:
            embedding_dimensions: Vector size; must match the embeddings model's
                dimensions (EmbeddingsProcessor.embedding_dimensions). To change
                it, drop the index first: FT.DROPINDEX documents DD
        """
        try:
            self.client.ft(self.index_name).info()
            return  # already exists
        except redis.ResponseError:
            pass  # "Unknown index name"

        schema = (
            TagField("filename"),  # exact match, not tokenised like TextField
            TextField("content"),
            NumericField("uploaded_at"),  # Unix timestamp
            # COSINE matches the similarity used in pg-api; HNSW is the same
            # approximate nearest-neighbour index type as the pgvector index
            VectorField(
                "embedding",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": embedding_dimensions,
                    "DISTANCE_METRIC": "COSINE",
                },
            ),
        )
        definition = IndexDefinition(
            prefix=[self.key_prefix], index_type=IndexType.HASH
        )
        self.client.ft(self.index_name).create_index(schema, definition=definition)

    def upsert_documents(self, documents: list[Document]) -> int:
        """
        Save documents, replacing any already saved with the same filename.

        Args:
            documents: Documents with embeddings

        Returns:
            Number of documents saved
        """
        missing = [doc.filename for doc in documents if doc.embedding is None]
        if missing:
            raise ValueError(f"Documents have no embedding: {', '.join(missing)}")

        # The filename is part of the key, so re-running the upload overwrites
        # the hash instead of adding a duplicate; RediSearch re-indexes it
        # automatically. A pipeline sends all the writes in one round trip.
        # transaction=False: the default wraps the pipeline in MULTI/EXEC, which
        # Azure Managed Redis (clustered) rejects when the keys are on different
        # shards (CROSSSLOT). Each HSET is independent, so no transaction is needed.
        pipe = self.client.pipeline(transaction=False)
        for doc in documents:
            pipe.hset(
                f"{self.key_prefix}{doc.filename}",
                mapping={
                    "filename": doc.filename,
                    "content": doc.content,
                    "uploaded_at": time.time(),
                    "embedding": self._to_bytes(doc.embedding),
                },
            )
        pipe.execute()
        return len(documents)

    def vector_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        similarity_threshold: float | None = None,
    ) -> list[SearchResult]:
        """
        Find the documents closest to the query embedding.

        Args:
            query_embedding: Embedding of the question, from the same model and
                dimensions as the stored documents
            top_k: Maximum number of results
            similarity_threshold: Minimum cosine similarity (0-1); None = no filter

        Returns:
            Results ordered from most to least similar
        """
        # "*" = all documents, then the top_k nearest by embedding; the distance
        # is returned as "distance". DIALECT 2 is needed for $params.
        # paging() is required: RediSearch returns at most 10 results by default.
        query = (
            Query("*=>[KNN $top_k @embedding $vector AS distance]")
            .return_fields("filename", "content", "uploaded_at", "distance")
            .sort_by("distance")
            .paging(0, top_k)
            .dialect(2)
        )
        params = {"top_k": top_k, "vector": self._to_bytes(query_embedding)}
        response = self.client.ft(self.index_name).search(query, query_params=params)

        results = []
        for doc in response.docs:
            # COSINE distance is 1 - cosine similarity (0 = identical, 2 = opposite),
            # the same as pgvector's <=>, so similarity = 1 - distance
            similarity = 1 - float(doc.distance)
            # Results are sorted by distance, so the rest are all below the threshold
            if similarity_threshold is not None and similarity < similarity_threshold:
                break
            results.append(
                SearchResult(
                    filename=doc.filename,
                    content=doc.content,
                    uploaded_at=datetime.fromtimestamp(float(doc.uploaded_at), UTC),
                    similarity=similarity,
                )
            )
        return results

    @staticmethod
    def _to_bytes(embedding: list[float]) -> bytes:
        """
        Pack an embedding as little-endian FLOAT32 bytes, the format RediSearch
        expects for a FLOAT32 vector field (both when storing and querying).
        """
        return struct.pack(f"<{len(embedding)}f", *embedding)
