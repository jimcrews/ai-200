Demo scripts for a document-summary job queue. One script sends 'jobs' to Service Bus, and a separate worker script picks them up and processes them.

Create a Service Bus 'Standard' namespace, because I want to eventually demo topics.

The basic app (two scripts):

## producer.py 
sends messages like {"doc_id": 42, "text": "..."} to a queue called summarize-jobs.
Its job is to send message by getting sample documents, then sending them to service bus, then closing the connection, and exiting.

The message format will be similar to: 
(doc_id is the filename without the extension.):

``` json
{"doc_id": "report-03", "filename": "report-03.txt", "text": "..."}
```

## worker.py 
listens on the queue, 'summarizes' each message, and marks it complete. The summary will be fake (returning the first sentence).
the worker uses the SDK to wait for messages from the queue with a timeout.

## More details
Use the azure-servicebus and azure-identity packages, and connect with DefaultAzureCredential instead of a connection string.



## Application Create Steps

``` shell
uv init --bare --python 3.14 doc-bus
uv python pin 3.14

uv add azure-servicebus azure-identity
uv add python-dotenv

uv add --dev ruff

```

## Linting

``` shell
uv run ruff check .
uv run ruff format .
```

## Azure Deployment

``` shell
az group create --name rg-doc-bus --location australiaeast

MY_ID=$(az ad signed-in-user show --query id -o tsv)
echo $MY_ID

az deployment group create \
--resource-group rg-doc-bus \
--template-file resource_servicebus.bicep \
--parameters serviceBusName=jimsbus20261012ai200 principalId=$MY_ID

az deployment group show -g rg-doc-bus -n resource_servicebus --query properties.outputs

```

## Run Producer

``` shell
uv run uv run producer.py
```

## Run Worker

``` shell
uv run worker.py
```