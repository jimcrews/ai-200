
# Create API

``` shell
cd api
uv init --no-package # no src layout

uv add "fastapi[standard]"
uv add --dev pytest
```

## Local Testing

Test using curl:

``` shell
# Test
uv run fastapi dev main.py

curl http://127.0.0.1:8000/

curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/echo \
  -H "Content-Type: application/json" \
  -d '{"message": "hi", "repeat_count": 3}'
```

Test using unit tests (dev server doesnt need to be running)

``` shell
uv run pytest -v
```

## Docker Testing

The Docker image installs with plain pip, so export the locked (non-dev) dependencies from `uv.lock` to `requirements.txt`. Re-run this whenever you `uv add`/`uv remove` a package, and commit the result.

``` shell
cd api
uv export --format requirements.txt --no-dev --no-emit-project --frozen -o requirements.txt
```

- `--no-dev` leaves out pytest and other dev dependencies
- `--no-emit-project` leaves out the project itself (only its dependencies)
- `--frozen` exports exactly what's in `uv.lock` without re-resolving
- Hashes are included by default; the Dockerfile uses `pip install --require-hashes` to verify them

## Build and run the container locally

``` shell
# list images with docker image ls
docker build -t fastapi-azure .
# list containers with docker ps
docker run --rm -p 8000:8000 fastapi-azure

curl http://127.0.0.1:8000/health
```


# Create Azure Resources

``` shell
az login --use-device-code

# one time setup
az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights


az group create --name rg-fastapi --location australiaeast
```

## Create ACR 

``` shell
az deployment group create \
--resource-group rg-fastapi \
--template-file resource_deployment.bicep \
--parameters acrName=acrjc20261002
```

## Deploy to ACR

No local docker required

``` shell
az acr build \
--registry acrjc20261002 \
--image ai-agent-api:v1 \
--file Dockerfile .
```

## Create Container Environment

``` shell
az containerapp env create \
--name aiagent-env \
--resource-group rg-fastapi \
--location australiaeast
```

## Create Container App

``` shell
az containerapp create \
--name ai-agent-service-jc \
--resource-group rg-fastapi \
--environment aiagent-env \
--image acrjc20261002.azurecr.io/ai-agent-api:v1 \
--registry-server acrjc20261002.azurecr.io \
--ingress external \
--target-port 8000 \
--min-replicas 0 --max-replicas 1 \
--cpu 0.25 --memory 0.5Gi
```

## Test Container App

``` shell
curl https://ai-agent-service-jc.ambitioussea-f87ce343.australiaeast.azurecontainerapps.io/health
```

## Clean Up

``` shell
az group delete --name rg-fastapi --yes
```