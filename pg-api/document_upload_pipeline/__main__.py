import argparse
from pathlib import Path

import psycopg
from openai import OpenAI

from embeddings_processor import EmbeddingError, EmbeddingsProcessor
from llm_processor import LlmError, LlmProcessor
from pdf_processor import PDFProcessor
from pg_api.config import Settings
from pg_processor import PgProcessor

# Reads APP_* environment variables, or .env in the directory you run from
settings = Settings()

AZURE_OPENAI_ENDPOINT = settings.azure_openai_endpoint
AZURE_OPENAI_API_KEY = settings.azure_openai_api_key
LLM_MODEL_DEPLOYMENT_NAME = settings.llm_model_deployment_name
EMBEDDING_MODEL_DEPLOYMENT_NAME = settings.embedding_model_deployment_name
MAX_TEXT_LENGTH = 8191

POSTGRES_HOST = settings.postgres_host
POSTGRES_DB = settings.postgres_db
POSTGRES_USER = settings.postgres_user
POSTGRES_PASSWORD = settings.postgres_password


DOCUMENTS_FOLDER = Path(__file__).parent / "documents"


def create_openai_client() -> OpenAI:
    return OpenAI(base_url=AZURE_OPENAI_ENDPOINT, api_key=AZURE_OPENAI_API_KEY)


def create_postgres_client() -> psycopg.Connection:
    return psycopg.connect(
        host=POSTGRES_HOST,
        port=5432,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        sslmode="require",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--process", choices=["upload", "query"], required=True)
    parser.add_argument(
        "--question", help="Question to ask; required with --process query"
    )
    args = parser.parse_args()

    if args.process == "query" and not args.question:
        parser.error("--question is required with --process query")

    openai_client = create_openai_client()
    embeddings_processor = EmbeddingsProcessor(
        openai_client=openai_client,
        embedding_model_name=EMBEDDING_MODEL_DEPLOYMENT_NAME,
        max_text_length=MAX_TEXT_LENGTH,
    )

    if args.process == "upload":
        # extract text from PDFs
        documents = PDFProcessor().read_pdf_folder(DOCUMENTS_FOLDER)
        # add embeddings
        embedded_docs = embeddings_processor.embed_documents(documents)
        if not embedded_docs:
            print("Nothing to save")
            return

        # save to Postgres; the with block closes the connection when done
        with create_postgres_client() as conn:
            pg_processor = PgProcessor(conn)
            pg_processor.create_table(embeddings_processor.embedding_dimensions)
            saved = pg_processor.upsert_documents(embedded_docs)
        print(f"✓ Saved {saved} document(s) to Postgres")
    elif args.process == "query":
        # embed the question with the same model as the documents
        try:
            question_embedding = embeddings_processor.generate_embedding(args.question)
        except (EmbeddingError, ValueError) as e:
            raise SystemExit(f"✗ {e!s}") from e

        # find the closest documents
        with create_postgres_client() as conn:
            results = PgProcessor(conn).vector_search(
                question_embedding,
                top_k=settings.vector_search_top_k,
                similarity_threshold=settings.vector_search_similarity_threshold,
            )

        print(f"Found {len(results)} matching document(s):")
        for result in results:
            print(f"  {result.similarity:.3f}  {result.filename}")

        # skip the LLM call if there's nothing to answer from
        if not results:
            print("No documents match the question")
            return

        # answer the question using the documents as context
        llm_processor = LlmProcessor(
            openai_client=openai_client,
            llm_model_name=LLM_MODEL_DEPLOYMENT_NAME,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
            top_p=settings.llm_top_p,
        )
        try:
            answer = llm_processor.answer_question(args.question, results)
        except LlmError as e:
            raise SystemExit(f"✗ {e!s}") from e

        print(f"\nAnswer:\n{answer}")


if __name__ == "__main__":
    main()
