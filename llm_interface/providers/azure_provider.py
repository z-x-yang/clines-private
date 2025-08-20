import logging
import time
from typing import Callable

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI


logger = logging.getLogger(__name__)


# Fixed configuration per user specification
API_VERSION = "2024-02-15-preview"
AZURE_OPENAI_ENDPOINT = "https://mgb-verity-bioinformatics-ai-e2-private-openai-service.openai.azure.com/"
SCOPE = "https://cognitiveservices.azure.com/.default"


def wrap_azure_chat(model_key: str) -> Callable:
    """
    Create an Azure OpenAI chat function using AAD bearer token auth.

    Args:
        model_key: Logical model key (e.g., "gpt4o", "gpt4omini").

    Returns:
        A callable that accepts (inputs_message, retry=False, max_retries=0, retry_delay=1.0)
        and returns a dict with keys: {"content": str, "token_usage": usage|None}.
    """

    name_to_engine = {
        "gpt4o": "gpt-4o",
        "gpt4omini": "xx",
    }

    if model_key not in name_to_engine:
        raise ValueError(
            f"Unsupported model key: {model_key}. Supported keys are: {list(name_to_engine.keys())}")

    engine_name = name_to_engine[model_key]

    def azure_chat(inputs_message, retry: bool = False, max_retries: int = 0, retry_delay: float = 1.0):
        token_provider = get_bearer_token_provider(DefaultAzureCredential(), SCOPE)
        client = AzureOpenAI(
            api_version=API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_ad_token_provider=token_provider,
        )

        attempts = 0
        while True:
            try:
                # Use SDK defaults; do not override decoding params per user request
                response = client.chat.completions.create(
                    model=engine_name,
                    messages=inputs_message,
                    max_tokens=8192,
                    temperature=0.6
                )

                if not response:
                    raise ValueError("Empty response from API")
                if not getattr(response, "choices", None):
                    raise ValueError("No choices in API response")
                first_choice = response.choices[0]
                if not getattr(first_choice, "message", None):
                    raise ValueError("No message in API response")
                content = first_choice.message.content
                if not content:
                    raise ValueError("Empty content in API response")

                return {
                    "content": content.strip(),
                    "token_usage": response.usage if hasattr(response, "usage") else None,
                }

            except Exception as e:
                logger.error(
                    f"Error in azure_chat for model {model_key}: {e}", exc_info=True
                )
                if retry and attempts < max_retries:
                    attempts += 1
                    time.sleep(retry_delay)
                    continue
                raise

    return azure_chat


