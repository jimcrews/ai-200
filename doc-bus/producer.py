"""Send every document in ./documents to the summarize-jobs queue, then exit."""

import json
import os
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from dotenv import load_dotenv

load_dotenv()  # settings come from .env (see .env.example)

NAMESPACE = os.environ[
    "SERVICEBUS_FULLY_QUALIFIED_NAMESPACE"
]  # e.g. jimsbusai200.servicebus.windows.net
QUEUE_NAME = os.environ.get("SERVICEBUS_QUEUE_NAME", "summarize-jobs")
DOCUMENTS_DIR = Path(__file__).parent / "documents"


def build_messages() -> list[ServiceBusMessage]:
    messages = []
    for path in sorted(DOCUMENTS_DIR.glob("*.txt")):
        job = {"doc_id": path.stem, "filename": path.name, "text": path.read_text()}
        messages.append(
            ServiceBusMessage(
                json.dumps(job), content_type="application/json", message_id=path.stem
            )
        )
    return messages


def main() -> None:
    messages = build_messages()

    # The 'with' blocks close the sender and the connection when we're done
    with (
        ServiceBusClient(NAMESPACE, DefaultAzureCredential()) as client,
        client.get_queue_sender(QUEUE_NAME) as sender,
    ):
        sender.send_messages(messages)  # a list is sent as a single batch

    for message in messages:
        print(f"sent {message.message_id}")
    print(f"{len(messages)} jobs sent to {QUEUE_NAME}")


if __name__ == "__main__":
    main()
