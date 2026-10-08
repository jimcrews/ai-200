# pg-api

Retrieval-Augmented Generation (RAG): find the documents relevant to a question, then
have the LLM answer from those documents only.

1. **Upload** (`--process upload`): each PDF in `document_upload_pipeline/documents` is
   converted to text, embedded with `text-embedding-3-small` (512 dimensions), and stored
   in the Postgres `documents` table as one row holding the full text and its embedding.

2. **Search** (`--process query --question "..."`): the question is embedded with the
   same model, and a pgvector search (cosine similarity, HNSW index) returns the closest
   documents, limited by `APP_VECTOR_SEARCH_TOP_K` and
   `APP_VECTOR_SEARCH_SIMILARITY_THRESHOLD`.
   
3. **Answer**: the full text of the returned documents is sent to `gpt-4.1-mini` with
   the question, and a system prompt telling it to answer only from those documents.


## Getting Started

``` shell
# clone the repo, then
uv sync                          # create .venv and install all dependencies
cp -n .env.example .env          # local settings (-n: never overwrite an existing .env); fill in the Azure values (see "Configure .env")
uv run pg-api                    # API not built yet - only prints a hello message
```

## Tests and Linting

``` shell
uv run pytest                 # run tests
uv run ruff check .           # lint
uv run ruff format .          # format
```

## Recreate From Scratch

``` shell
# creates the project folder 'pg-api' with a src/ layout
uv init --package --python 3.14 pg-api
cd pg-api

uv add fastapi "uvicorn[standard]" pydantic-settings
uv add openai
uv add "psycopg[binary]"
uv add pgvector
uv add pymupdf4llm # PDF extract to Markdown
uv add --dev pytest httpx2 ruff
```

## Export uv Dependencies to requirements.txt

The Dockerfile installs dependencies with plain `pip`, so it needs a `requirements.txt`.

``` shell
uv export --no-dev --no-emit-project --format requirements-txt -o requirements.txt
```

## Azure Foundry and Postgres Deployment

``` shell
az login --use-device-code

az group create --name rg-pg-api --location australiaeast
```

## Create Foundry

``` shell
az deployment group create \
--resource-group rg-pg-api \
--template-file deploy_foundry.bicep \
--parameters aiFoundryName=jimfoundryai200
```

## Create PostgresDB

``` shell
# Prompt securely for the password
# Azure requires 8–128 characters, using at least three of: 
#   uppercase, lowercase, digits, symbols.
read -s -p "Enter PostgreSQL Admin Password: " PG_PASS
echo

# Your public IPv4 address (firewall rules don't accept IPv6), added to the server
# firewall so you can connect locally. On a VPN/proxy, check it matches your real egress IP.
MY_IP=$(curl -4 -s https://ifconfig.me)

az deployment group create \
--resource-group rg-pg-api \
--template-file deploy_postgres.bicep \
--parameters \
  pgServername=jimpgai200server \
  pgDbname=jimpgai200db \
  passW="$PG_PASS" \
  clientIp="$MY_IP"
```

## Configure .env

Copy the example file, then fill in the `APP_AZURE_*`, `APP_*_DEPLOYMENT_NAME` and
`APP_POSTGRES_*` values from the commands below.

``` shell
cp -n .env.example .env   # -n: never overwrite an existing .env

# Deployment outputs: endpoint and deployment names, then host, database and user
az deployment group show -g rg-pg-api -n deploy_foundry --query properties.outputs
az deployment group show -g rg-pg-api -n deploy_postgres --query properties.outputs

# Secrets (not in the outputs, so they don't end up in deployment history)
az cognitiveservices account keys list -n jimfoundryai200 -g rg-pg-api --query key1 -o tsv
echo $PG_PASS   # only set in the terminal where you ran `read` above
```

## Testing Document Upload Pipeline

Run from the `pg-api/` folder: `.env` is read from the current directory.

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

# Stop the server when not in use to pause compute billing (auto-restarts after 7 days)
# az postgres flexible-server stop -g rg-pg-api -n jimpgai200server
# or delete everything (below)

az group delete --name rg-pg-api --yes

# View recently deleted Cognitive Services accounts in the region (to confirm deletion)
az cognitiveservices account list-deleted --output table

# The following commands permanently delete the soft-deleted accounts.
az cognitiveservices account purge --location australiaeast --resource-group rg-pg-api --name jimfoundryai200

# NetworkWatcherRG is created automatically, one per subscription, and shared by
# everything in it. Only delete it if this demo created it and nothing else uses it.
# az group delete --name NetworkWatcherRG --yes
```
