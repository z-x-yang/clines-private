import openai


def llama_chat(inputs_message):
    client = openai.Client(
        base_url="http://127.0.0.1:30000/v1", api_key="EMPTY")

    # Chat completion
    response = client.chat.completions.create(
        model="default",
        messages=inputs_message,
        temperature=0,
        max_tokens=8192,  # 4096,
    )

    return response.choices[0].message.content.strip()


def deepseek_chat(inputs_message):
    client = openai.Client(
        base_url="http://127.0.0.1:30000/v1", api_key="EMPTY")

    # Chat completion
    response = client.chat.completions.create(
        model="default",
        messages=inputs_message,
        temperature=0.6,
        max_tokens=32768,  # 4096,
    )

    output = response.choices[0].message.content.strip()
    # Remove the <think> section if present
    if "</think>" in output:
        think_end = output.find("</think>") + len("</think>")
        output = output[think_end:].strip()

    return output
