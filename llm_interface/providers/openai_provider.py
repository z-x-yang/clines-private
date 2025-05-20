import os
import time
from openai import AzureOpenAI
import logging

logger = logging.getLogger(__name__)


def wrap_openai_chat(model_name):
    n2n_dict = {
        "gpt4o": "gpt-4o",
        "gpt4omini": "gpt-4o-mini",
        "o3mini": "o3-mini",
    }

    if model_name not in n2n_dict:
        raise ValueError(
            f"Unsupported model name: {model_name}. Supported models are: {list(n2n_dict.keys())}")

    engine_name = n2n_dict[model_name]
    api_version = "2024-05-01-preview" if model_name != "o3mini" else "2024-12-01-preview"

    def openai_chat(inputs_message, retry=True, max_retries=3, retry_delay=1):
        # Check environment variables
        GPT4V_KEY = os.getenv("OPENAIKEY")
        GPT4V_ENDPOINT = os.getenv("OPENAIENDPOINT")

        if not GPT4V_KEY or not GPT4V_ENDPOINT:
            raise ValueError(
                "Missing required environment variables: OPENAIKEY and/or OPENAIENDPOINT")

        client = AzureOpenAI(azure_endpoint=GPT4V_ENDPOINT,
                             api_version=api_version,
                             api_key=GPT4V_KEY)

        retries = 0
        while True:
            try:
                if model_name == "o3mini":
                    response = client.chat.completions.create(model=engine_name,
                                                              messages=inputs_message,
                                                              max_completion_tokens=8192,
                                                              reasoning_effort="low")
                else:
                    response = client.chat.completions.create(model=engine_name,
                                                              messages=inputs_message,
                                                              max_tokens=4096,
                                                              temperature=0.6)

                if not response:
                    raise ValueError("Empty response from API")

                if not response.choices:
                    raise ValueError("No choices in API response")

                if not response.choices[0].message:
                    raise ValueError("No message in API response")

                content = response.choices[0].message.content
                if not content:
                    if model_name == "o3mini" and response.choices[0].finish_reason == "length":
                        raise ValueError(
                            "Response exceeded token limit. Please reduce input size or increase token limit.")
                    raise ValueError("Empty content in API response")

                # Return both content and token usage
                return {
                    'content': content.strip(),
                    'token_usage': response.usage if hasattr(response, 'usage') else None
                }

            except Exception as e:
                logger.error(
                    f"Error in openai_chat for model {model_name}: {e}", exc_info=True)
                if 'response' in locals() and response:
                    try:
                        response_details = response.model_dump_json(indent=2) if hasattr(
                            response, 'model_dump_json') else str(response)
                        logger.error(f"Response details: {response_details}")
                    except Exception as log_e:
                        logger.error(
                            f"Error logging full response object: {log_e}. Response (str): {str(response)}")

                if retry and retries < max_retries:
                    retries += 1
                    logger.info(
                        f"Retrying openai_chat for model {model_name}... (attempt {retries}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(
                        f"Failed openai_chat for model {model_name} after {max_retries} retries.", exc_info=True)
                    raise Exception(f"Failed after {max_retries} retries: {e}")

    return openai_chat
