import os

def openai_chat(inputs_message):
    import requests
    import base64
    
    # Configuration
    GPT4V_KEY = os.getenv("OPENAIKEY")
    GPT4V_ENDPOINT = os.getenv("OPENAIENDPOINT")
    
    headers = {
        "Content-Type": "application/json",
        "api-key": GPT4V_KEY,
    }
    payload = {
      "messages": inputs_message, 
      "temperature": 0.,
      "top_p": 0.95
    }
    # Send request
    try:
        response = requests.post(GPT4V_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.RequestException as e:
        raise SystemExit(f"Failed to make the request. Error: {e}")
    # Handle the response as needed (e.g., print or process)
    return response.json()['choices'][0]['message']['content']

def huggingface_chat(input_message):
    
    import openai
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

def gemini_chat(input_message):

    NotImplementedError

def claude_chat(input_message):

    NotImplementedError

class LLM():

    def __init__(self, model_name):

        self.model_name = model_name
        if self.model_name in ['gpt3.5', 'gpt4', 'gpt4o', 'gpt4omini']:

            self.chat_func = openai_chat

        elif self.model_name in ['gemini']:

            self.chat_func = gemini_chat

        elif self.model_name in ['claude']:

            self.chat_func = claude_chat

        elif self.model_name in ['llama', 'mistral']:

            self.chat_func = huggingface_chat

        self.new_chat()

    def new_chat(self):
        '''
        add system prompt for different model, use default prompt,
        start new chat
        '''
        
        self.message_buffer = []
        if self.model_name in ['gpt3.5', 'gpt4', 'gpt4o', 'gpt4omini']:

            NotImplementedError

        elif self.model_name in ['gemini']:

            NotImplementedError

        elif self.model_name in ['claude']:

            NotImplementedError

        elif self.model_name in ['llama', 'mistral']:

            NotImplementedError
        

    def __call__(self, query):
                
        self.message_buffer.append({'user': query})
        response = self.chat_func(self.message_buffer)
        self.message_buffer.append({'assistant': response})

        return response

    
        





            