"""Receive jobs from the summarize-jobs queue, 'summarize' each one, and settle it.

The worker keeps listening until no message has arrived for WAIT_SECONDS, then exits.
Start it before or after producer.py - messages wait in the queue either way.
"""

import json
import os
import re

from azure.identity import DefaultAzureCredential
from azure.servicebus import (
    ServiceBusClient,
    ServiceBusReceivedMessage,
    ServiceBusReceiver,
)
from dotenv import load_dotenv

load_dotenv()  # settings come from .env (see .env.example)

NAMESPACE = os.environ["SERVICEBUS_FULLY_QUALIFIED_NAMESPACE"]  # e.g. jimsbusai200.servicebus.windows.net
QUEUE_NAME = os.environ.get("SERVICEBUS_QUEUE_NAME", "summarize-jobs")
WAIT_SECONDS = 30  # stop after this long with no new messages


class TransientError(Exception):
    """A failure that might succeed if retried, e.g. a downstream service timing out.

    To try the redelivery path, add `raise TransientError("boom")` at the top of summarize().
    """


def summarize(text: str) -> str:
    """Fake summary: the first sentence of the document, after its title line."""
    body = text.strip().split("\n", 1)[-1]  # drop the title line
    return re.split(r"(?<=[.!?])\s", body.strip(), maxsplit=1)[0]


def handle(receiver: ServiceBusReceiver, message: ServiceBusReceivedMessage) -> None:
    # delivery_count goes up each time this message is handed out again (abandoned or lock expired).
    # When it reaches the queue's maxDeliveryCount (5 in the bicep), Service Bus dead-letters it for us.
    print(f"received {message.message_id} (delivery {message.delivery_count})")

    try:
        job = json.loads(str(message))  # str() gives the message body as text
        doc_id, text = job["doc_id"], job["text"]
    except (json.JSONDecodeError, KeyError) as e:
        # A "poison" message: retrying will never fix bad data, so dead-letter it straight away.
        # It moves to summarize-jobs/$deadletterqueue, where you can inspect it in the portal.
        receiver.dead_letter_message(message, reason="InvalidJob", error_description=str(e))
        print(f"  dead-lettered: {e}")
        return

    try:
        summary = summarize(text)
    except TransientError as e:
        # Something went wrong that might work next time: release the lock so the message
        # becomes visible again and can be redelivered (to this or another worker).
        # Any other exception crashes the worker without settling; the lock then expires
        # and the message is redelivered anyway - peek-lock means nothing is lost.
        receiver.abandon_message(message)
        print(f"  abandoned: {e}")
        return

    print(f"  {doc_id}: {summary}")

    # Completing deletes the message from the queue. Until we do this, the message is only
    # locked to us (for lockDuration, 1 minute in the bicep) - not removed.
    receiver.complete_message(message)


def main() -> None:
    with (
        ServiceBusClient(NAMESPACE, DefaultAzureCredential()) as client,
        # The default receive mode is PEEK_LOCK: receiving a message locks it rather than removing it,
        # and we settle it ourselves (complete / abandon / dead-letter). If the worker crashes before
        # settling, the lock expires and the message is redelivered - nothing is lost.
        # (The alternative, RECEIVE_AND_DELETE, removes it on receipt: faster, but a crash loses the job.)
        client.get_queue_receiver(QUEUE_NAME, max_wait_time=WAIT_SECONDS) as receiver,
    ):
        print(f"listening on {QUEUE_NAME} (exits after {WAIT_SECONDS}s with no messages)")
        count = 0
        # Iterating the receiver blocks waiting for messages, and the loop ends once
        # max_wait_time passes without a new one arriving.
        for message in receiver:
            handle(receiver, message)
            count += 1

    print(f"no messages for {WAIT_SECONDS}s - processed {count}, exiting")


if __name__ == "__main__":
    main()
