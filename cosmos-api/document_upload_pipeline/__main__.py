import argparse
from typing import Any

from azure.cosmos import ContainerProxy, CosmosClient
from cosmos_db_vector_store import CosmosDBVectorStore
from openai import OpenAI
from pdf_embedding_generator import PDFEmbeddingGenerator

from cosmos_api.config import Settings

# Reads APP_* environment variables, or .env in the directory you run from
settings = Settings()

AZURE_OPENAI_ENDPOINT = settings.azure_openai_endpoint
AZURE_OPENAI_API_KEY = settings.azure_openai_api_key
LLM_MODEL_DEPLOYMENT_NAME = settings.llm_model_deployment_name
EMBEDDING_MODEL_DEPLOYMENT_NAME = settings.embedding_model_deployment_name
COSMOS_DB_ENDPOINT = settings.cosmos_db_endpoint
COSMOS_PRIMARY_KEY = settings.cosmos_primary_key
COSMOS_DB_NAME = settings.cosmos_db_name
COSMOS_CONTAINER_NAME = settings.cosmos_container_name

MAX_TEXT_LENGTH = 8191
DOCUMENTS_FOLDER = "./document_upload_pipeline/documents"
PARTITION_KEY = "partitionKey"
PARTITION_KEY_VALUE = "global"

# TEST_QUERY_TEXT = "How much did we spend on Azure for September 2026"
TEST_QUERY_TEXT = "What changes are being made to our cloud platform"


def create_openai_client() -> OpenAI:
    return OpenAI(base_url=AZURE_OPENAI_ENDPOINT, api_key=AZURE_OPENAI_API_KEY)


def get_container_client() -> ContainerProxy:
    """Connect to Cosmos DB and check the database and container exist."""
    cosmos_db_client = CosmosClient(
        url=COSMOS_DB_ENDPOINT,
        credential=COSMOS_PRIMARY_KEY,
    )
    database_client = cosmos_db_client.get_database_client(COSMOS_DB_NAME)
    container_client = database_client.get_container_client(COSMOS_CONTAINER_NAME)

    # Raises CosmosResourceNotFoundError if either is missing
    database_client.read()
    container_client.read()

    return container_client


def generate_embeddings(openai_client: OpenAI) -> list[dict[str, Any]]:
    """Read the PDFs in DOCUMENTS_FOLDER and generate an embedding for each."""
    pdf_embedding_generator = PDFEmbeddingGenerator(
        openai_client=openai_client,
        embedding_model_name=EMBEDDING_MODEL_DEPLOYMENT_NAME,
        max_text_length=MAX_TEXT_LENGTH,
    )
    return pdf_embedding_generator.process_documents(
        folder_path=DOCUMENTS_FOLDER, generate_embeddings=True
    )


def upload_documents(
    container_client: ContainerProxy, documents: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Upload the processed documents to the Cosmos DB container."""
    vector_store = CosmosDBVectorStore(
        container_client=container_client, partition_key=PARTITION_KEY
    )
    return vector_store.upload_documents(
        documents=documents, partition_key_value=PARTITION_KEY_VALUE
    )


def upload(openai_client: OpenAI, container_client: ContainerProxy) -> None:
    processed_docs = generate_embeddings(openai_client)
    uploaded = upload_documents(container_client, processed_docs)

    print(f"Uploaded {len(uploaded)} of {len(processed_docs)} documents")


def query(openai_client: OpenAI, container_client: ContainerProxy) -> None:
    pdf_embedding_generator = PDFEmbeddingGenerator(
        openai_client=openai_client,
        embedding_model_name=EMBEDDING_MODEL_DEPLOYMENT_NAME,
        max_text_length=MAX_TEXT_LENGTH,
    )
    vector_store = CosmosDBVectorStore(
        container_client=container_client, partition_key=PARTITION_KEY
    )

    query_embedding = pdf_embedding_generator._generate_embedding(TEST_QUERY_TEXT)
    results = vector_store.vector_search(
        query_embedding=query_embedding,
        top_k=settings.vector_search_top_k,
        similarity_threshold=settings.vector_search_similarity_threshold,
    )

    for result in results:
        print(f"{result['similarity_score']:.3f}  {result['filename']}")

    answer = generate_answer(openai_client, TEST_QUERY_TEXT, results)
    print(f"\nQuestion: {TEST_QUERY_TEXT}\nAnswer: {answer}")


def generate_answer(
    openai_client: OpenAI, question: str, results: list[dict[str, Any]]
) -> str:
    """Ask the LLM to answer the question using only the retrieved documents."""
    if not results:
        return "No matching documents found."

    context = "\n\n".join(f"## {r['filename']}\n{r['content']}" for r in results)

    response = openai_client.chat.completions.create(
        model=LLM_MODEL_DEPLOYMENT_NAME,
        messages=[
            {
                "role": "system",
                "content": "Answer using only the provided documents. "
                "If the answer isn't in them, say so.",
            },
            {
                "role": "user",
                "content": f"Documents:\n{context}\n\nQuestion: {question}",
            },
        ],
        max_tokens=settings.llm_max_tokens,
        temperature=settings.llm_temperature,
        top_p=settings.llm_top_p,
    )
    return response.choices[0].message.content or ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--process", choices=["upload", "query"], required=True)
    args = parser.parse_args()

    openai_client = create_openai_client()
    container_client = get_container_client()

    if args.process == "upload":
        upload(openai_client, container_client)
    elif args.process == "query":
        query(openai_client, container_client)


if __name__ == "__main__":
    main()
