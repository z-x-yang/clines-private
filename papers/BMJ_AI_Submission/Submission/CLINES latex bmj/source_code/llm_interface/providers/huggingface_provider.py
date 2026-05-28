import os
import openai


def huggingface_chat(input_message):

    client = openai.Client(
        base_url=os.getenv('MODELHOST'), api_key="EMPTY")

    # Chat completion
    response = client.chat.completions.create(
        model="default",
        messages=input_message,
        temperature=0,
        max_tokens=5000,
    )

    return response.json()['choices'][0]['message']['content']
