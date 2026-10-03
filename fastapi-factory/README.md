# fastapi-factory

A FastAPI demo managed with uv, built with the **application factory** pattern, configured from environment variables, and packaged as a Docker image


## Getting Started

``` shell
# clone the repo, then
uv sync                          # create .venv and install all dependencies
cp .env.example .env             # optional: local settings (turns on auto-reload)
uv run fastapi-factory           # start the server

curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/echo -H "Content-Type: application/json" -d '{"message": "hi", "repeat_count": 3}'
```

## Tests and Linting

``` shell
uv run pytest                 # run tests
uv run ruff check .           # lint
uv run ruff format .          # format
```

## How the Factory Pattern Works

- **`create_app(settings)` builds a new app each time it is called.**
- **Settings are attached to the app, not stored in a global.**
- **Tests pass their own settings.**
- **uvicorn calls the factory.** Pass `factory=True` so uvicorn calls `create_app()` instead of looking for an `app`.
- **Startup and shutdown go in `lifespan`.** Open database pools and HTTP clients.

## Project Structure

```
fastapi-factory/
├── pyproject.toml             # project metadata, dependencies, `fastapi-factory` script
├── uv.lock                    # exact dependency versions
├── requirements.txt           # exported from uv.lock, used by the Dockerfile
├── .python-version            # Python version for uv
├── .env.example               # every setting, with comments; copy to .env
├── .gitignore
├── .dockerignore
├── Dockerfile
├── src/fastapi_factory/
│   ├── __init__.py            # main(): entry point for `uv run`, starts uvicorn via the factory
│   ├── main.py                # create_app(): the factory (logging, lifespan, routers)
│   ├── config.py              # Settings: read from APP_* env vars and .env
│   ├── dependencies.py        # get_settings / SettingsDep: settings from app.state
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── health.py      # GET /health (one APIRouter per module)
│   └── models/
│       ├── __init__.py        # Pydantic request/response models go here
│       └── schemas.py         # Pydantic schemas
└── tests/
    ├── __init__.py
    ├── conftest.py            # `client` fixture: new app per test, test settings
    └── test_api.py
```

## Recreate From Scratch

``` shell
# creates the project folder 'fastapi-factory' with a src/ layout
uv init --package --python 3.14 fastapi-factory
cd fastapi-factory

uv add fastapi "uvicorn[standard]" pydantic-settings
uv add --dev pytest httpx2 ruff
```

## Configuration

All settings are read from `APP_*` environment variables, or from a `.env` file in the
directory you run from. Real environment variables take precedence over `.env`.

| Variable          | Default           | Purpose                                         |
| ----------------- | ----------------- | ----------------------------------------------- |
| `APP_APP_NAME`    | `FastAPI Factory` | App title (shown in the OpenAPI docs)           |
| `APP_ENVIRONMENT` | `local`           | Environment name, reported by `/health`         |
| `APP_LOG_LEVEL`   | `INFO`            | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `APP_HOST`        | `127.0.0.1`       | Interface to bind to *                          |
| `APP_PORT`        | `8000`            | Port to listen on *                             |
| `APP_RELOAD`      | `false`           | Restart automatically on code change *          |

\* Used only by `uv run fastapi-factory`. The Docker image starts uvicorn directly with
fixed options. The image also sets `APP_ENVIRONMENT=production` by default.

``` shell
# Local development with auto-reload, without a .env file
APP_RELOAD=true uv run fastapi-factory
```

## Export uv Dependencies to requirements.txt

The Dockerfile installs dependencies with plain `pip`, so it needs a `requirements.txt`.
Export the lock file whenever dependencies change:

``` shell
uv export --no-dev --no-emit-project --format requirements-txt -o requirements.txt
```

- `--no-dev` leaves out dev-only tools (pytest, ruff, httpx2) that the image doesn't need
- `--no-emit-project` leaves out the project itself (`-e .`); the Dockerfile copies `src/` instead
- The output pins exact versions **with hashes**, which is why the Dockerfile uses `pip install --require-hashes`

Commit `requirements.txt`, and re-run the export after any `uv add` / `uv remove`.


## Docker

``` shell
docker build -t fastapi-factory .
docker run --rm -p 8000:8000 fastapi-factory

curl http://127.0.0.1:8000/health    # {"status":"ok","environment":"production"}

# Settings come from APP_* environment variables; -e overrides the image's defaults
docker run --rm -p 8000:8000 -e APP_ENVIRONMENT=staging -e APP_LOG_LEVEL=DEBUG fastapi-factory
```

## Azure Deployment

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
az acr create \
--name acrjc20261002 \
--resource-group rg-fastapi \
--sku Basic \
--admin-enabled true
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
# Skip the auto-created Log Analytics workspace (fine for dev/testing)
az containerapp env create \
--name aiagent-env \
--resource-group rg-fastapi \
--location australiaeast \
--logs-destination none
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

Get the Container App URL from Azure.

``` shell
curl https://ai-agent-service-jc.yellowwave-35d84cc1.australiaeast.azurecontainerapps.io/health
```

## Clean Up

``` shell
az group delete --name rg-fastapi --yes
```

---

## Copy to a New Project

Make a new project from this one by copying the folder and renaming it. The examples use `openai-api` as the new name.

### 1. Copy the folder

``` shell
cd ~/repos/ai-200
cp -R fastapi-factory openai-api
cd openai-api
```

### 2. Delete the generated files

These were created by tools in the original folder. Don't reuse them in the copy:

``` shell
rm -rf .venv .pytest_cache .ruff_cache .DS_Store .env

# delete every __pycache__ directory under the current folder, recursively.
find . -name __pycache__ -type d -prune -exec rm -rf {} +
```

### 3. Rename the package folder

``` shell
mv src/fastapi_factory src/openai_api
```

### 4. Replace the name in the files

Replace `fastapi-factory` with `openai-api`, and `fastapi_factory` with `openai_api`:

| File                                   | What to change                                                                     |
| -------------------------------------- | ---------------------------------------------------------------------------------- |
| `pyproject.toml`                       | name, the script line, and description                                             |
| `src/openai_api/__init__.py`           | The import, the docstring, and the `"openai_api.main:create_app"` string           |
| `src/openai_api/main.py`               | The imports                                                                        |
| `src/openai_api/config.py`             | The comment on the server options; the default `app_name` (`"FastAPI Factory"`)   |
| `src/openai_api/dependencies.py`       | The import                                                                         |
| `src/openai_api/api/routes/*.py`       | The imports (`health.py`, `root.py`, `echo.py`, and any new routes)                |
| `tests/conftest.py`                    | The imports                                                                        |
| `tests/test_api.py`                    | The imports                                                                        |
| `Dockerfile`                           | The `PYTHONPATH` comment and the `CMD` line (`openai_api.main:create_app`)             |
| `.env.example`                         | The comments, and `APP_APP_NAME`                                                   |

Don't edit `uv.lock` or `requirements.txt` by hand. They're regenerated in step 5.

Check nothing was missed. The `.` in the pattern matches both `-` and `_`, so this
should print nothing:

``` shell
grep -rn "fastapi.factory" --exclude-dir=.venv --exclude=uv.lock --exclude=requirements.txt .
```

### 5. Rebuild and test

``` shell
uv sync                    # new .venv; updates the project name in uv.lock
uv export --no-dev --no-emit-project --format requirements-txt -o requirements.txt
cp .env.example .env
uv run pytest
uv run openai-api
curl http://127.0.0.1:8000/health
```
