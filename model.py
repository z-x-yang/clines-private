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

import torch
from tqdm import tqdm
import semchunk
import json

def openai_chat(inputs_message):
    # print(inputs_message)
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
                                                temperature=0.,)
    # print(response)
    return response.choices[0].message.content.strip()

def llama_chat(inputs_message):
    import openai
    client = openai.Client(
        base_url="http://127.0.0.1:30000/v1", api_key="EMPTY")

    # Chat completion
    response = client.chat.completions.create(
        model="default",
        messages=inputs_message,
        temperature=0,
        max_tokens=4096,
    )
    
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
            
            import tiktoken
            self.chat_func = openai_chat
            self.tokenizer = tiktoken.encoding_for_model('gpt-4')
            self.chunker = semchunk.chunkerify(self.tokenizer, 512)

        elif self.model_name in ['gemini']:

            self.chat_func = gemini_chat

        elif self.model_name in ['claude']:

            self.chat_func = claude_chat

        elif self.model_name in ['llama', 'mistral']:

            self.chat_func = huggingface_chat
        
        elif self.model_name in ['llama-3-405b']:
            import tiktoken
            self.chat_func = llama_chat
            self.tokenizer = tiktoken.encoding_for_model('gpt-4')
            self.chunker = semchunk.chunkerify(self.tokenizer, 512)

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
            
        elif self.model_name in ['llama-3-405b']:
            
            self.message_buffer.append({
                                          "role": "system",
                                          "content": "You are an AI assistant that follows people's instructions."
                                        })
        

    def __call__(self, query):
                
        self.message_buffer.append({'role': 'user', 'content': query})
        response = self.chat_func(self.message_buffer)
        self.message_buffer.append({'role': 'assistant', 'content': response})

        return response

    
class Retriever():

    def __init__(self, path, use_gpu=True):

        import transformers
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(path, use_fast=True, do_lower_case=True)
        self.encoder = transformers.AutoModel.from_pretrained(path, trust_remote_code=True)
        self.use_gpu = use_gpu
        if torch.cuda.is_available() and use_gpu:
            self.encoder = self.encoder.cuda()

    def load_dictionary_all(self, file_path):
        
        self.dict_map = {}
        self.term_list_all = []
        with open(file_path, 'r') as f:
            for item in f.readlines():
                code, term = item.split('||')
                self.dict_map[term] = code
                self.term_list_all.append(term)
        self.term_list_all = list(set(self.term_list_all))

    def load_dictionary_bodyloc(self, file_path):
        
        self.term_list_bodyloc = []
        with open(file_path, 'r') as f:
            for item in f.readlines():
                code, term = item.split('||')
                self.term_list_bodyloc.append(term)
        self.term_list_bodyloc = list(set(self.term_list_bodyloc))

    def embed_term(self, names, batch_size = 512):
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
                batch_dense_embeds = batch_dense_embeds / torch.norm(batch_dense_embeds, p=2, dim=-1, keepdim=True)
                batch_dense_embeds = batch_dense_embeds.cpu()#.detach().numpy()
                dense_embeds.append(batch_dense_embeds)
                
        dense_embeds = torch.concat(dense_embeds, dim=0)

        return dense_embeds
        
    def embed_dictionary(self, batch_size = 2048):
        import os
        import torch

        cache_file = './cache/'
        
        print(f"Checking if cache file exists at {cache_file + '/dense_embed_all.pt'}")
        if os.path.exists(cache_file + '/dense_embed_all.pt'):
            print("Cache file found. Loading dense embeddings from cache.")
            self.dense_embeds_all = torch.load(cache_file + '/dense_embed_all.pt')
            self.term_list_all = json.load(open(cache_file + '/term_list_all.jsonl', 'r'))
        else:
            print("Cache file not found. Embedding terms and saving to cache.")
            
            self.encoder.eval()
            self.dense_embeds_all = self.embed_term(self.term_list_all, batch_size)
            json.dump(self.term_list_all, open(cache_file + '/term_list_all.jsonl', 'w'))
            torch.save(self.dense_embeds_all, cache_file + '/dense_embed_all.pt')
            print("Dense embeddings saved to cache.")

        print(f"Checking if cache file exists at {cache_file + '/dense_embed_bodyloc.pt'}")
        if os.path.exists(cache_file + '/dense_embed_bodyloc.pt'):
            print("Cache file found. Loading dense embeddings from cache.")
            self.term_list_bodyloc = json.load(open(cache_file + '/term_list_bodyloc.jsonl', 'r'))
            self.dense_embeds_bodyloc = torch.load(cache_file + '/dense_embed_bodyloc.pt')
        else:
            print("Cache file not found. Embedding terms and saving to cache.")
            self.encoder.eval()
            self.dense_embeds_bodyloc = self.embed_term(self.term_list_bodyloc, batch_size)
            torch.save(self.dense_embeds_bodyloc, cache_file + '/dense_embed_bodyloc.pt')
            json.dump(self.term_list_bodyloc, open(cache_file + '/term_list_bodyloc.jsonl', 'w'))
            print("Dense embeddings saved to cache.")

    def faiss_setup(self):
        import faiss
        if self.use_gpu:
            res = faiss.StandardGpuResources()  # use a single GPU
            index = faiss.IndexFlatIP(self.dense_embeds_all.shape[-1])   # build the index
            self.index_flat_all = faiss.index_cpu_to_gpu(res, 0, index)
            self.index_flat_all.add(self.dense_embeds_all)

            res = faiss.StandardGpuResources()  # use a single GPU
            index = faiss.IndexFlatIP(self.dense_embeds_bodyloc.shape[-1])   # build the index
            self.index_flat_bodyloc = faiss.index_cpu_to_gpu(res, 0, index)
            self.index_flat_bodyloc.add(self.dense_embeds_bodyloc)
            
        else:
            self.index_flat_all = faiss.IndexFlatIP(self.dense_embeds_all.shape[-1])
            self.index_flat_all.add(self.dense_embeds_all)

            self.index_flat_bodyloc = faiss.IndexFlatIP(self.dense_embeds_bodyloc.shape[-1])
            self.index_flat_bodyloc.add(self.dense_embeds_bodyloc)


    def embedding_retrieval_all(self, term, batch_size=256):
        if term and all(x is None for x in term):
            return []
        embed_for_test = self.embed_term(term, batch_size)
        D, I = self.index_flat_all.search(embed_for_test, 1)  # actual search
        preds_fortest = []
        for i, (idx, ds) in enumerate(zip(I, D)):
            preds_fortest.append(json.dumps({self.dict_map[self.term_list_all[j]]: self.term_list_all[j].strip() for j, d in zip(idx, ds)}))
            
        return preds_fortest

    def embedding_retrieval_bodyloc(self, term, batch_size=256):
        
        if term and all(x is None for x in term):
            return []
        _term = [item for item in term if item is not None]
        embed_for_test = self.embed_term(_term, batch_size)
        D, I = self.index_flat_bodyloc.search(embed_for_test, 1)  # actual search
        _preds_fortest = []
        for i, (idx, ds) in enumerate(zip(I, D)):
            _preds_fortest.append(json.dumps({self.dict_map[self.term_list_bodyloc[j]]: self.term_list_bodyloc[j].strip() for j, d in zip(idx, ds)}))
        preds_fortest = []
        for item in term:
            if item is None:
                preds_fortest.append(item)
            else:
                preds_fortest.append(_preds_fortest.pop(0))
    
        return preds_fortest

    
        
        

        





            