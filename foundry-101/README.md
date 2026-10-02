=========================================
Foundation – Your First Agent Call
=========================================

This unit demonstrates how to call an Azure OpenAI model from Python using the OpenAI SDK with Azure Identity for authentication. It's designed for those who are new to building simple agent-style interactions with cloud LLMs.

Key Concepts
------------
- Azure OpenAI service: Cloud-hosted large language models (LLMs) accessed via an SDK or REST API.
- Secure authentication: Uses `azure-identity` (DefaultAzureCredential) to obtain a bearer token instead of embedding a static API key.
- Agent call pattern: The code wraps prompts and instructions in a small agent class and sends user messages to the model.
- Response handling: The SDK returns a structured response object; the script extracts and prints the model's answer.

What this repository contains
----------------------------
- `agent.py`: Top-level interactive script. Reads `config.yaml`, configures authentication, instantiates the `RefundAgent` class, and starts a simple REPL where you can type questions and receive answers from the model.
- `config.yaml`: Configuration file (model parameters, prompt templates, or other settings) used by the agent. Edit to change behavior without touching code.
- `classes/refund_agent.py`: The agent implementation (encapsulates model calls, prompt construction, and response parsing). This is where the core agent logic lives.
- `requirements.txt`: Python dependencies used by the project (install into a virtual environment before running).

Learning objectives
-------------------
- Understand how to authenticate securely to Azure-hosted models.
- See a simple agent pattern that separates prompt logic from the interactive shell.
- Learn how to extract and display model responses from the SDK's response object.
- Know how to adapt configuration via `config.yaml` and environment variables.

## Application Create Steps

``` shell
uv init --bare --python 3.14
uv python pin 3.14

uv add openai azure-identity pyyaml python-dotenv
```

Once `pyproject.toml` and `uv.lock` exist, anyone cloning the repo just runs:

``` shell
uv sync
uv run agent.py
```

## Create Azure Resources

``` shell
az login --use-device-code

az group create --name rg-aiagent-course --location australiaeast

# Deploy the Bicep file
az deployment group create \
--resource-group rg-aiagent-course \
--template-file resource_deployment.bicep \
--parameters appPrefix=jimapp001ai200

# Get your deployment outputs
az deployment group show \
--resource-group rg-aiagent-course \
--name resource_deployment \
--query properties.outputs


# Give access
# Your signed-in user's object ID
USER_ID=$(az ad signed-in-user show --query id -o tsv)

# Full resource ID of the Foundry account (includes the subscription ID)
FOUNDRY_ID=$(az cognitiveservices account show \
--resource-group rg-aiagent-course \
--name jimapp001ai200 \
--query id -o tsv)

az role assignment create \
--assignee "$USER_ID" \
--role "Cognitive Services OpenAI User" \
--scope "$FOUNDRY_ID"
```

Owner/Contributor only grants control-plane access (managing resources). Calling the model needs a data-plane role like **Cognitive Services OpenAI User**. Role assignments can take a few minutes to take effect.


## Configure Environment

Copy the deployment outputs into a `.env` file in the project root (it is git-ignored and loaded by `agent.py` via `python-dotenv`):

``` shell
AZURE_OPENAI_ENDPOINT=https://<appPrefix>.services.ai.azure.com/openai/v1
LLM_MODEL_DEPLOYMENT_NAME=<appPrefix>-llm-deploy
```

## Run App

``` shell
uv run agent.py
```


## Cleanup
``` shell
# Delete the entire deployment (So no more costs)
az group delete --name rg-aiagent-course --yes

# View recently deleted Cognitive Services accounts in the region (to confirm deletion)
az cognitiveservices account list-deleted --output table

# The following commands permanently delete the soft-deleted accounts.
az cognitiveservices account purge --location australiaeast --resource-group rg-aiagent-course --name jimapp001ai200
```