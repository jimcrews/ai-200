import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg import sql
from psycopg.rows import class_row

from document import Document, SearchResult


class PgProcessor:
    """
    A class to handle Postgres operations: table setup, saving documents and
    vector similarity search with pgvector.
    """

    def __init__(self, conn: psycopg.Connection, table_name: str = "documents"):
        """
        Initialize the PgProcessor and enable pgvector on the connection.

        Args:
            conn: Open psycopg connection; the caller owns it and closes it
            table_name: Table that holds the documents and embeddings
        """
        self.conn = conn
        # Identifier quotes the names, so they're safe to put in SQL
        self.table = sql.Identifier(table_name)
        self.index = sql.Identifier(f"{table_name}_embedding_idx")
        self._enable_pgvector()

    def _enable_pgvector(self) -> None:
        """
        Create the pgvector extension if needed and register its types.

        The extension must be allow-listed on the server (azure.extensions=VECTOR
        in deploy_postgres.bicep), and creating it needs the admin user.
        register_vector looks up the vector type, so it has to run after
        CREATE EXTENSION; it lets us pass pgvector.Vector values as parameters.
        """
        self.conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        self.conn.commit()
        register_vector(self.conn)

    def create_table(self, embedding_dimensions: int) -> None:
        """
        Create the documents table and its HNSW index, if they don't exist.

        Args:
            embedding_dimensions: Vector size; must match the embeddings model's
                dimensions (EmbeddingsProcessor.embedding_dimensions)
        """
        # filename is the primary key, so re-running the upload updates rows
        # instead of adding duplicates
        create_table_sql = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {table} (
                filename TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                embedding VECTOR({dims}) NOT NULL,
                uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """).format(table=self.table, dims=sql.Literal(embedding_dimensions))

        # vector_cosine_ops matches the <=> operator used in vector_search;
        # the index is only used when the operator and ops class match
        create_index_sql = sql.SQL("""
            CREATE INDEX IF NOT EXISTS {index}
            ON {table} USING hnsw (embedding vector_cosine_ops)
        """).format(index=self.index, table=self.table)

        with self.conn.cursor() as cur:
            cur.execute(create_table_sql)
            cur.execute(create_index_sql)
        self.conn.commit()

    def upsert_documents(self, documents: list[Document]) -> int:
        """
        Insert documents, or update them if a row with the same filename exists.

        Args:
            documents: Documents with embeddings

        Returns:
            Number of documents saved
        """
        missing = [doc.filename for doc in documents if doc.embedding is None]
        if missing:
            raise ValueError(f"Documents have no embedding: {', '.join(missing)}")

        upsert_sql = sql.SQL("""
            INSERT INTO {table} (filename, content, embedding)
            VALUES (%s, %s, %s)
            ON CONFLICT (filename) DO UPDATE SET
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                uploaded_at = now()
        """).format(table=self.table)

        rows = [(doc.filename, doc.content, Vector(doc.embedding)) for doc in documents]

        with self.conn.cursor() as cur:
            cur.executemany(upsert_sql, rows)
        self.conn.commit()
        return len(rows)

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
        # <=> is cosine distance (0 = identical, 2 = opposite), so similarity = 1 - distance
        where = sql.SQL("")
        if similarity_threshold is not None:
            where = sql.SQL("WHERE 1 - (embedding <=> %(embedding)s) >= %(threshold)s")

        search_sql = sql.SQL("""
            SELECT filename, content, uploaded_at,
                   1 - (embedding <=> %(embedding)s) AS similarity
            FROM {table}
            {where}
            ORDER BY embedding <=> %(embedding)s
            LIMIT %(top_k)s
        """).format(table=self.table, where=where)

        params = {
            "embedding": Vector(query_embedding),
            "threshold": similarity_threshold,
            "top_k": top_k,
        }

        # class_row builds a SearchResult from each row, matching on column names
        with self.conn.cursor(row_factory=class_row(SearchResult)) as cur:
            cur.execute(search_sql, params)
            return cur.fetchall()
