# Open AI API

A FastAPI Application calling Open AI


## Getting Started

``` shell
# clone the repo, then
uv sync                          # create .venv and install all dependencies
cp .env.example .env             # optional: local settings (turns on auto-reload)
uv run openai-api         # start the server

curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/run -H "Content-Type: application/json" -d '{"prompt": "Explain FastAPI in one sentence."}'
```

## Tests and Linting

``` shell
uv run pytest                 # run tests
uv run ruff check .           # lint
uv run ruff format .          # format
```

## Export uv Dependencies to requirements.txt

The Dockerfile installs dependencies with plain `pip`, so it needs a `requirements.txt`.
Export the lock file whenever dependencies change:

``` shell
uv export --no-dev --no-emit-project --format requirements-txt -o requirements.txt
```

## Docker

``` shell
docker build -t openai-api .
docker run --rm -p 8000:8000 openai-api

curl http://127.0.0.1:8000/health    # {"status":"ok","environment":"production"}

# Settings come from APP_* environment variables; -e overrides the image's defaults
docker run --rm -p 8000:8000 -e APP_ENVIRONMENT=staging -e APP_LOG_LEVEL=DEBUG openai-api
```

## Azure Deployment

### Deploy Foundry and Test API locally

``` shell
# Resource Group

az group create --name rg-openai-api --location australiaeast
```

``` shell
# Deploy the Bicep file for Foundry
az deployment group create \
--resource-group rg-openai-api \
--template-file resource_deployment.bicep \
--parameters appPrefix=jimapp001ai200

# Get your deployment outputs
az deployment group show \
--resource-group rg-openai-api \
--name resource_deployment \
--query properties.outputs
```

``` shell
# Update .env

APP_AZURE_OPENAI_ENDPOINT=https://jimapp001ai200.services.ai.azure.com/openai/v1
APP_AZURE_OPENAI_API_KEY=<#response from bicep output>
APP_LLM_MODEL_DEPLOYMENT_NAME=jimapp001ai200-llm-deploy

# Run the application locally
uv run openai-api
curl -X POST http://127.0.0.1:8000/run -H "Content-Type: application/json" -d '{"prompt": "Explain FastAPI in one sentence."}'
```

### Deploy API to Azure

``` shell
# Create ACR
az acr create \
--name acrjc20261002 \
--resource-group rg-openai-api \
--sku Basic \
--admin-enabled true

# Build to container and push to ACR
az acr build \
--registry acrjc20261002 \
--image ai-agent-api:v1 \
--file Dockerfile .
```

``` shell
# Create Container App Environment
az containerapp env create \
--name openai-api-env \
--resource-group rg-openai-api \
--location australiaeast

# Create Container App. Update with values from .env
az containerapp create \
--name ai-agent-service \
--resource-group rg-openai-api \
--image acrjc20261002.azurecr.io/ai-agent-api:v1 \
--environment openai-api-env \
--target-port 8000 \
--ingress external \
--registry-server acrjc20261002.azurecr.io \
--env-vars \
APP_AZURE_OPENAI_ENDPOINT=https://jimapp001ai200.services.ai.azure.com/openai/v1 \
APP_AZURE_OPENAI_API_KEY=xxx \
APP_LLM_MODEL_DEPLOYMENT_NAME=jimapp001ai200-llm-deploy
```

### Test
``` shell
curl https://ai-agent-service.salmonmoss-c6d9629a.australiaeast.azurecontainerapps.io/health

curl -X POST https://ai-agent-service.salmonmoss-c6d9629a.australiaeast.azurecontainerapps.io/run -H "Content-Type: application/json" -d '{"prompt": "Explain photosynthesis in one sentence."}'
```

### Cleanup

``` shell
# Delete the entire deployment (So no more costs)
az group delete --name rg-openai-api --yes

# View recently deleted Cognitive Services accounts in the region (to confirm deletion)
az cognitiveservices account list-deleted --output table

# The following commands permanently delete the soft-deleted accounts.
az cognitiveservices account purge --location australiaeast --resource-group rg-openai-api --name jimapp001ai200
```