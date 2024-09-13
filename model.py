import os

# def openai_chat(inputs_message):
#     import requests
#     import base64
    
#     # Configuration
#     GPT4V_KEY = os.getenv("OPENAIKEY")
#     GPT4V_ENDPOINT = os.getenv("OPENAIENDPOINT")
#     print(GPT4V_KEY, GPT4V_ENDPOINT)
#     headers = {
#         "Content-Type": "application/json",
#         "api-key": GPT4V_KEY,
#     }
#     payload = {
#       "messages": inputs_message, 
#       "temperature": 0.,
#       "top_p": 0.95
#     }
#     # Send request
#     try:
#         response = requests.post(GPT4V_ENDPOINT, headers=headers, json=payload)
#         response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
#     except requests.RequestException as e:
#         raise SystemExit(f"Failed to make the request. Error: {e}")
#     # Handle the response as needed (e.g., print or process)
#     return response.json()['choices'][0]['message']['content']


def openai_chat(inputs_message):
    print(inputs_message)
    from openai import AzureOpenAI
    GPT4V_KEY = os.getenv("OPENAIKEY")
    GPT4V_ENDPOINT = os.getenv("OPENAIENDPOINT")
    client = AzureOpenAI(azure_endpoint=GPT4V_ENDPOINT,
                        api_version="2024-02-01",
                        api_key=GPT4V_KEY)
    engine_name = "gpt-4o"
    
    response = client.chat.completions.create(model=engine_name,  
                                                messages=inputs_message,
                                                max_tokens=4096,
                                                temperature=0.,
                                                top_p=1,
                                                frequency_penalty=0,
                                                presence_penalty=0)
    
    return response.choices[0].message.content.strip()
    
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

            self.message_buffer.append({
                                          "role": "system",
                                          "content": "You are an AI assistant that follows people's instructions."
                                        })

        elif self.model_name in ['gemini']:

            NotImplementedError

        elif self.model_name in ['claude']:

            NotImplementedError

        elif self.model_name in ['llama', 'mistral']:

            NotImplementedError
        

    def __call__(self, query):
                
        self.message_buffer.append({'role': 'user', 'content': query})
        response = self.chat_func(self.message_buffer)
        self.message_buffer.append({'role': 'assistant', 'content': response})

        return response

    
class Retriever():

    def __init__(self, path):

        import transformers
        import torch

        self.tokenizer = transformers.AutoTokenizer.from_pretrained(path, use_fast=True, do_lower_case=True)
        self.encoder = transformers.AutoModel.from_pretrained(path, trust_remote_code=True)
        if torch.cuda.is_available():
            self.encoder = self.encoder.cuda()

    def load_dictionary(self, file_path):
        
        self.dict_map = {}
        self.term_list = []
        with open(file_path, 'r') as f:
            for item in f.readlines():
                code, term = item.split('||')
                self.dict_map[term] = code
                self.term_list.append(term)
        self.term_list = list(set(self.term_list))

    def embed_terms(self, names, batch_size = 2048):

        self.encoder.eval() 
        dense_embeds = []
        
        with torch.no_grad():
            
            iterations = tqdm(range(0, len(names), batch_size))
                
            for start in iterations:
                end = min(start + batch_size, len(names))
                batch = names[start:end]
                batch_tokenized_names = self.tokenizer.batch_encode_plus(
                        batch, add_special_tokens=True, 
                        truncation=True, max_length=25, 
                        padding="max_length", return_tensors='pt')
                batch_tokenized_names_cuda = {}
                for k,v in batch_tokenized_names.items(): 
                    batch_tokenized_names_cuda[k] = v.cuda()
                
                batch_dense_embeds = self.encoder(**batch_tokenized_names_cuda).last_hidden_state[:,0,:] 
                # batch_dense_embeds = batch_dense_embeds.cpu().detach().numpy()
                dense_embeds.append(batch_dense_embeds)
                
        dense_embeds = torch.concat(dense_embeds, dim=0)

        return dense_embeds
        
    def embed_dictionary(self, batch_size = 2048):

        self.encoder.eval() 
        self.dense_embeds = self.embed_terms(self.term_list, batch_size)

    def faiss_setup(self):
        
        import faiss
        res = faiss.StandardGpuResources()  # use a single GPU
        index = faiss.IndexFlatL2(self.dense_embeds.shape[-1])   # build the index
        self.gpu_index_flat = faiss.index_cpu_to_gpu(res, 0, index)
        self.gpu_index_flat.add(self.dense_embeds)  

    def embedding_retrieval(self, term, batch_size=2048):

        embed_for_test = self.embed_terms(term, batch_size)
        D, I = gpu_index_flat.search(embed_for_test, 1)  # actual search
        preds_fortest = {}
        for i, (idx, ds) in enumerate(zip(I, D)):
            preds_fortest[term[i]] = {self.term_list[j]: d for j, d in zip(idx, ds)}
            
        return preds_fortest
    
        
        

        





            