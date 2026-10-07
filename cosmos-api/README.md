# cosmos-api

Retrieval-Augmented Generation (RAG): find the documents relevant to a question, then
have the LLM answer from those documents only.

1. **Upload** (`--process upload`): each PDF in `document_upload_pipeline/documents` is
   converted to text, embedded with `text-embedding-3-small` (512 dimensions), and stored
   in the Cosmos DB container as one item holding the full text and its embedding.
2. **Search** (`--process query`): the question is embedded with the same model, and a
   Cosmos DB vector search (cosine similarity, DiskANN index) returns the closest
   documents, limited by `APP_VECTOR_SEARCH_TOP_K` and
   `APP_VECTOR_SEARCH_SIMILARITY_THRESHOLD`.
3. **Answer**: the full text of the returned documents is sent to `gpt-4.1-mini` with
   the question, and a system prompt telling it to answer only from those documents.


## Getting Started

``` shell
# clone the repo, then
uv sync                          # create .venv and install all dependencies
cp .env.example .env             # local settings; fill in the Azure values (see "Configure .env")
uv run cosmos-api           # start the server

curl http://127.0.0.1:8000/health

```

## Tests and Linting

``` shell
uv run pytest                 # run tests
uv run ruff check .           # lint
uv run ruff format .          # format
```

## Recreate From Scratch

``` shell
# creates the project folder 'cosmos-api' with a src/ layout
uv init --package --python 3.14 cosmos-api
cd cosmos-api

uv add fastapi "uvicorn[standard]" pydantic-settings
uv add openai
uv add azure-cosmos
uv add pymupdf4llm # PDF extract to Markdown
uv add --dev pytest httpx2 ruff
```

## Configuration

All settings are read from `APP_*` environment variables, or from a `.env` file in the
directory you run from. Real environment variables take precedence over `.env`.

| Variable          | Default           | Purpose                                         |
| ----------------- | ----------------- | ----------------------------------------------- |
| `APP_APP_NAME`    | `Cosmos API`      | App title (shown in the OpenAPI docs)           |
| `APP_ENVIRONMENT` | `local`           | Environment name, reported by `/health`         |
| `APP_LOG_LEVEL`   | `INFO`            | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `APP_HOST`        | `127.0.0.1`       | Interface to bind to *                          |
| `APP_PORT`        | `8000`            | Port to listen on *                             |
| `APP_RELOAD`      | `false`           | Restart automatically on code change *          |

\* Used only by `uv run cosmos-api`. The Docker image starts uvicorn directly with
fixed options. The image also sets `APP_ENVIRONMENT=production` by default.

Azure settings, filled in from the deployment outputs (see [Configure .env](#configure-env)):

| Variable                                  | Default | Purpose                                              |
| ----------------------------------------- | ------- | ---------------------------------------------------- |
| `APP_AZURE_OPENAI_ENDPOINT`               |         | Foundry OpenAI endpoint (`.../openai/v1`)            |
| `APP_AZURE_OPENAI_API_KEY`                |         | Foundry API key                                      |
| `APP_LLM_MODEL_DEPLOYMENT_NAME`           |         | Chat model deployment (`gpt-4.1-mini`)               |
| `APP_LLM_MAX_TOKENS`                      | `150`   | Max tokens in a chat response                        |
| `APP_LLM_TEMPERATURE`                     | `0.7`   | Chat randomness; lower is more focused               |
| `APP_LLM_TOP_P`                           | `0.9`   | Chat nucleus sampling                                |
| `APP_EMBEDDING_MODEL_DEPLOYMENT_NAME`     |         | Embedding model deployment (`text-embedding-3-small`) |
| `APP_COSMOS_DB_ENDPOINT`                  |         | Cosmos DB account endpoint                           |
| `APP_COSMOS_PRIMARY_KEY`                  |         | Cosmos DB primary key                                |
| `APP_COSMOS_DB_NAME`                      |         | Cosmos DB database name                              |
| `APP_COSMOS_CONTAINER_NAME`               |         | Cosmos DB container name                             |
| `APP_VECTOR_SEARCH_TOP_K`                 | `5`     | Number of vector search results                      |
| `APP_VECTOR_SEARCH_SIMILARITY_THRESHOLD`  | none    | Minimum cosine similarity (0-1); unset = no filter   |

``` shell
# Local development with auto-reload, without a .env file
APP_RELOAD=true uv run cosmos-api
```

## Export uv Dependencies to requirements.txt

The Dockerfile installs dependencies with plain `pip`, so it needs a `requirements.txt`.

``` shell
uv export --no-dev --no-emit-project --format requirements-txt -o requirements.txt
```

## Azure Foundry and Cosmos Deployment

``` shell
az login --use-device-code

# one time setup
az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights


az group create --name rg-cosmos-api --location australiaeast
```

## Create Foundry

``` shell
az deployment group create \
--resource-group rg-cosmos-api \
--template-file deploy_foundry.bicep \
--parameters aiFoundryName=jimfoundryai200
```

## Create CosmosDB

``` shell
az deployment group create \
--resource-group rg-cosmos-api \
--template-file deploy_cosmosdb.bicep \
--parameters cosmosDbName=jimcosmosai200
```

## Configure .env

Copy the example file, then fill in the `APP_AZURE_*`, `APP_*_DEPLOYMENT_NAME` and
`APP_COSMOS_*` values from the commands below.

``` shell
cp .env.example .env

# Endpoints and names (deployment names default to the template file name)
az deployment group show -g rg-cosmos-api -n deploy_foundry --query properties.outputs
az deployment group show -g rg-cosmos-api -n deploy_cosmosdb --query properties.outputs

# Keys (not in the outputs, so they don't end up in deployment history)
az cognitiveservices account keys list -n jimfoundryai200 -g rg-cosmos-api --query key1 -o tsv
az cosmosdb keys list -n jimcosmosai200-cosmos -g rg-cosmos-api --query primaryMasterKey -o tsv
```

## Testing Document Upload Pipeline

Run from the `cosmos-api/` folder: `.env` and `document_upload_pipeline/documents` are
found relative to the current directory.

``` shell
# upload documents
uv run document_upload_pipeline --process upload

# test using query
uv run document_upload_pipeline --process query
```

The query prints the similarity score of each result. Leave
`APP_VECTOR_SEARCH_SIMILARITY_THRESHOLD` unset for the first run to see the real
scores (`text-embedding-3-small` typically scores 0.3-0.6 for relevant matches), then
set it in `.env` to filter out weak matches.

## Clean Up

``` shell
az group delete --name rg-cosmos-api --yes

# View recently deleted Cognitive Services accounts in the region (to confirm deletion)
az cognitiveservices account list-deleted --output table

# The following commands permanently delete the soft-deleted accounts.
az cognitiveservices account purge --location australiaeast --resource-group rg-cosmos-api --name jimfoundryai200

# Delete other resource group created
az group delete --name NetworkWatcherRG --yes
```
