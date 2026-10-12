# redis-api

Retrieval-Augmented Generation (RAG): find the documents relevant to a question, then
have the LLM answer from those documents only.

1. **Upload** (`--process upload`): each PDF in `document_upload_pipeline/documents` is
   converted to text, embedded with `text-embedding-3-small` (512 dimensions), and stored
   in Redis as one hash (`documents:<filename>`) holding the full text and its embedding.

2. **Search** (`--process query --question "..."`): the question is embedded with the
   same model, and a RediSearch KNN query (cosine similarity, HNSW index) returns the closest
   documents, limited by `APP_VECTOR_SEARCH_TOP_K` and
   `APP_VECTOR_SEARCH_SIMILARITY_THRESHOLD`.
   
3. **Answer**: the full text of the returned documents is sent to `gpt-4.1-mini` with
   the question, and a system prompt telling it to answer only from those documents.


## Getting Started

``` shell
# clone the repo, then
uv sync                          # create .venv and install all dependencies
cp -n .env.example .env          # local settings (-n: never overwrite an existing .env); fill in the Azure values (see "Configure .env")
uv run redis-api                    # API not built yet - only prints a hello message
```

## Tests and Linting

``` shell
uv run pytest                 # run tests
uv run ruff check .           # lint
uv run ruff format .          # format
```

## Recreate From Scratch

``` shell
# creates the project folder 'redis-api' with a src/ layout
uv init --package --python 3.14 redis-api
cd redis-api

uv add pydantic-settings
uv add openai
uv add pymupdf4llm # PDF extract to Markdown
uv add redis       # includes the RediSearch (FT.*) commands
uv add --dev pytest ruff
```

## Export uv Dependencies to requirements.txt

The Dockerfile installs dependencies with plain `pip`, so it needs a `requirements.txt`.

``` shell
uv export --no-dev --no-emit-project --format requirements-txt -o requirements.txt
```

## Azure Foundry and Redis Deployment

``` shell
az login --use-device-code

az group create --name rg-redis-api --location australiaeast
```

## Create Foundry

``` shell
az deployment group create \
--resource-group rg-redis-api \
--template-file deploy_foundry.bicep \
--parameters aiFoundryName=jimfoundryai200
```

## Create Redis

``` shell
az deployment group create \
--resource-group rg-redis-api \
--template-file deploy_redis.bicep \
--parameters redisName=jimredisai200
```

## Configure .env

Copy the example file, then fill in the `APP_AZURE_*`, `APP_*_DEPLOYMENT_NAME` and
`APP_REDIS_*` values from the commands below.

``` shell
cp -n .env.example .env   # -n: never overwrite an existing .env

# Deployment outputs: endpoint and deployment names, then Redis host and port
az deployment group show -g rg-redis-api -n deploy_foundry --query properties.outputs
az deployment group show -g rg-redis-api -n deploy_redis --query properties.outputs


# Secrets (not in the outputs, so they don't end up in deployment history)
az cognitiveservices account keys list -n jimfoundryai200 -g rg-redis-api --query key1 -o tsv
az redisenterprise database list-keys --cluster-name jimredisai200 -g rg-redis-api --query primaryKey -o tsv
```

## Testing Document Upload Pipeline

Run from the `redis-api/` folder: `.env` is read from the current directory.

``` shell
# upload documents
uv run document_upload_pipeline --process upload

# test using query
uv run document_upload_pipeline --process query \
  --question "How much did we spend on Azure for September 2026"

uv run document_upload_pipeline --process query \
  --question "What changes are being made to our cloud platform"
```

The query prints the similarity score of each result. Comment out
`APP_VECTOR_SEARCH_SIMILARITY_THRESHOLD` in `.env` for the first run to see the real
scores (`text-embedding-3-small` typically scores 0.3-0.6 for relevant matches), then
set it to filter out weak matches.

## Clean Up

``` shell
az group delete --name rg-redis-api --yes

# View recently deleted Cognitive Services accounts in the region (to confirm deletion)
az cognitiveservices account list-deleted --output table

# The following commands permanently delete the soft-deleted accounts.
az cognitiveservices account purge --location australiaeast --resource-group rg-redis-api --name jimfoundryai200

# NetworkWatcherRG is created automatically, one per subscription, and shared by
# everything in it. Only delete it if this demo created it and nothing else uses it.
# az group delete --name NetworkWatcherRG --yes
```
