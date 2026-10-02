import os
import yaml

from dotenv import load_dotenv
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from classes.refund_agent import RefundAgent

# =============================================================================
# CONFIGURATION
# =============================================================================

load_dotenv()

azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
model_deployment_name = os.getenv("LLM_MODEL_DEPLOYMENT_NAME")

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

# =============================================================================
# AUTHENTICATION
# =============================================================================

credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")
openai_client = OpenAI(
    base_url=azure_openai_endpoint,
    api_key=token_provider,
)

# =============================================================================
# INSTANTIATE CLASSES
# =============================================================================

# Instantiate RefundAgent class
refund_agent = RefundAgent(
    openai_client=openai_client,
    model_deployment_name=model_deployment_name,
    config=config,
)

# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================


def interactive_loop():
    print("Interactive mode started. Type 'exit' or 'quit' to stop.")
    message_count = 0
    while True:
        try:
            user_message_text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting interactive mode.")
            break

        if not user_message_text:
            continue
        if user_message_text.lower() in ("exit", "quit"):
            print("Exiting interactive mode.")
            break

        # Process with BasicAgent
        print("\n[REFUND AGENT] Processing message with agent...")
        reply = refund_agent.process_message(
            user_message=user_message_text,
        )

        # Check if we got a valid response
        if reply is None:
            print("ERROR: Failed to get response from model.")
            continue

        print("\n" + "=" * 50)
        print("ASSISTANT REPLY:")
        print("=" * 50)
        print(reply)
        print("=" * 50)

        message_count += 1


if __name__ == "__main__":
    interactive_loop()
