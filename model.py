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


def openai_chat(inputs_message, retry=True):
    from openai import AzureOpenAI
    GPT4V_KEY = os.getenv("OPENAIKEY")
    GPT4V_ENDPOINT = os.getenv("OPENAIENDPOINT")
    client = AzureOpenAI(azure_endpoint=GPT4V_ENDPOINT,
                         api_version="2024-02-01",
                         api_key=GPT4V_KEY)
    engine_name = "gpt-4o"

    try:
        response = client.chat.completions.create(model=engine_name,
                                                  messages=inputs_message,
                                                  max_tokens=4096,
                                                  temperature=0.6)

        if not response or not response.choices or not response.choices[0].message:
            print(response)
            raise ValueError("Invalid response format from API")

        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in openai_chat: {e}")
        print(response)
        if retry:
            print("Retrying...")
            return openai_chat(inputs_message, retry=False)
        else:
            raise Exception(f"Failed after retry: {e}")


def llama_chat(inputs_message):
    import openai
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
    import openai
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

    def __init__(self, model_name, chunk_size=512):

        self.model_name = model_name
        if self.model_name in ['gpt3.5', 'gpt4', 'gpt4o', 'gpt4omini']:

            import tiktoken
            self.chat_func = openai_chat
            self.tokenizer = tiktoken.encoding_for_model('gpt-4')
            self.chunker = semchunk.chunkerify(self.tokenizer, chunk_size)

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

        elif self.model_name in ['deepseek']:
            import tiktoken
            self.chat_func = deepseek_chat
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

        elif self.model_name in ['deepseek']:
            pass

    def __call__(self, query):

        self.message_buffer.append({'role': 'user', 'content': query})
        response = self.chat_func(self.message_buffer)
        self.message_buffer.append({'role': 'assistant', 'content': response})

        return response


class Retriever():

    def __init__(self, path, use_gpu=True, use_faiss_gpu=None):

        import transformers
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            path, use_fast=True, do_lower_case=True)
        self.encoder = transformers.AutoModel.from_pretrained(
            path, trust_remote_code=True)
        self.use_gpu = use_gpu
        self.use_faiss_gpu = use_faiss_gpu if use_faiss_gpu is not None else use_gpu
        if torch.cuda.is_available() and self.use_gpu:
            self.encoder = self.encoder.cuda()
        else:
            self.encoder = self.encoder.cpu()

    def load_dictionary_all(self, file_path):

        self.dict_map = {}
        self.dict_map_sty = {}
        self.term_list_all = []
        with open(file_path, 'r') as f:
            for item in f.readlines():
                code, term, sty = item.strip().split('||')
                self.dict_map[term] = code
                self.dict_map_sty[term] = sty
                self.term_list_all.append(term)
        self.term_list_all = sorted(list(set(self.term_list_all)))

    def load_dictionary_bodyloc(self, file_path):

        self.term_list_bodyloc = []
        with open(file_path, 'r') as f:
            for item in f.readlines():
                code, term, _ = item.strip().split('||')
                self.term_list_bodyloc.append(term)
        self.term_list_bodyloc = sorted(list(set(self.term_list_bodyloc)))

    def embed_term(self, names, batch_size=256):
        self.encoder.eval()
        dense_embeds = []
        names = [str(item).lower() for item in names]
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
                for k, v in batch_tokenized_names.items():
                    if self.use_gpu:
                        batch_tokenized_names_cuda[k] = v.cuda()
                    else:
                        batch_tokenized_names_cuda[k] = v.cpu()

                batch_dense_embeds = self.encoder(
                    **batch_tokenized_names_cuda).last_hidden_state[:, 0, :]
                batch_dense_embeds = batch_dense_embeds / \
                    torch.norm(batch_dense_embeds, p=2, dim=-1, keepdim=True)
                batch_dense_embeds = batch_dense_embeds.cpu()  # .detach().numpy()
                dense_embeds.append(batch_dense_embeds)

        dense_embeds = torch.concat(dense_embeds, dim=0)

        return dense_embeds

    def embed_dictionary(self, batch_size=256):
        import os
        import torch
        cache_file = './cache'

        print(
            f"Checking if cache file exists at {cache_file + '/dense_embed_all.pt'}")
        if os.path.exists(cache_file + '/dense_embed_all.pt'):
            print("Cache file found. Loading dense embeddings from cache.")
            self.dense_embeds_all = torch.load(
                cache_file + '/dense_embed_all.pt', weights_only=True)
            self.term_list_all = torch.load(
                cache_file + '/term_list_all.pt', weights_only=True)
        else:
            print("Cache file not found. Embedding terms and saving to cache.")

            self.encoder.eval()
            self.dense_embeds_all = self.embed_term(
                self.term_list_all, batch_size)
            torch.save(self.dense_embeds_all,
                       cache_file + '/dense_embed_all.pt')
            torch.save(self.term_list_all,
                       cache_file + '/term_list_all.pt')
            print("Dense embeddings saved to cache.")

        print(
            f"Checking if cache file exists at {cache_file + '/dense_embed_bodyloc.pt'}")
        if os.path.exists(cache_file + '/dense_embed_bodyloc.pt'):
            print("Cache file found. Loading dense embeddings from cache.")
            self.dense_embeds_bodyloc = torch.load(
                cache_file + '/dense_embed_bodyloc.pt', weights_only=True)
            self.term_list_bodyloc = torch.load(
                cache_file + '/term_list_bodyloc.pt', weights_only=True)
        else:
            print("Cache file not found. Embedding terms and saving to cache.")
            self.encoder.eval()
            self.dense_embeds_bodyloc = self.embed_term(
                self.term_list_bodyloc, batch_size)
            torch.save(self.dense_embeds_bodyloc,
                       cache_file + '/dense_embed_bodyloc.pt')
            torch.save(self.term_list_bodyloc,
                       cache_file + '/term_list_bodyloc.pt')
            print("Dense embeddings saved to cache.")

        if self.use_gpu:
            self.dense_embeds_all = self.dense_embeds_all.cuda()
            self.dense_embeds_bodyloc = self.dense_embeds_bodyloc.cuda()
        else:
            self.dense_embeds_all = self.dense_embeds_all.cpu()
            self.dense_embeds_bodyloc = self.dense_embeds_bodyloc.cpu()

    def faiss_setup(self, gpu_id=0):
        import faiss
        import numpy as np

        # Convert PyTorch tensors to numpy arrays
        dense_embeds_all_np = self.dense_embeds_all.cpu().numpy()
        dense_embeds_bodyloc_np = self.dense_embeds_bodyloc.cpu().numpy()

        if self.use_faiss_gpu:
            print("Using GPU for FAISS setup")
            res = faiss.StandardGpuResources()  # 使用单个GPU资源
            # 为所有术语的索引指定GPU
            index = faiss.IndexFlatIP(dense_embeds_all_np.shape[-1])
            self.index_flat_all = faiss.index_cpu_to_gpu(res, gpu_id, index)
            self.index_flat_all.add(dense_embeds_all_np)
            # 为身体位置术语的索引指定GPU
            index = faiss.IndexFlatIP(dense_embeds_bodyloc_np.shape[-1])
            self.index_flat_bodyloc = faiss.index_cpu_to_gpu(
                res, gpu_id, index)
            self.index_flat_bodyloc.add(dense_embeds_bodyloc_np)
        else:
            print("Using CPU for FAISS setup")
            self.index_flat_all = faiss.IndexFlatIP(
                dense_embeds_all_np.shape[-1])
            self.index_flat_all.add(dense_embeds_all_np)
            self.index_flat_bodyloc = faiss.IndexFlatIP(
                dense_embeds_bodyloc_np.shape[-1])
            self.index_flat_bodyloc.add(dense_embeds_bodyloc_np)
        print("FAISS setup completed")

    def embedding_retrieval_all(self, term, batch_size=256):
        if term and all(x is None for x in term):
            return []
        embed_for_test = self.embed_term(term, batch_size)
        embed_for_test_np = embed_for_test.numpy()
        D, I = self.index_flat_all.search(
            embed_for_test_np, 1)  # actual search
        preds_fortest = []
        for i, (idx, ds) in enumerate(zip(I, D)):
            # preds_fortest.append(json.dumps({self.dict_map[self.term_list_all[j]]: [self.term_list_all[j].strip(), float(d)] for j, d in zip(idx, ds)}))
            preds_fortest.append(json.dumps({self.dict_map[self.term_list_all[j]]: [
                                 self.term_list_all[j].strip(), self.dict_map_sty[self.term_list_all[j]]] for j, d in zip(idx, ds)}))
        return preds_fortest

    def embedding_retrieval_bodyloc(self, term, batch_size=256):
        if term and all(x is None for x in term):
            return []
        _term = [item for item in term if item is not None]
        embed_for_test = self.embed_term(_term, batch_size)
        embed_for_test_np = embed_for_test.numpy()
        D, I = self.index_flat_bodyloc.search(
            embed_for_test_np, 1)  # actual search
        _preds_fortest = []
        for i, (idx, ds) in enumerate(zip(I, D)):
            # _preds_fortest.append(json.dumps({self.dict_map[self.term_list_bodyloc[j]]: [self.term_list_bodyloc[j].strip(), float(d)] for j, d in zip(idx, ds)}))
            _preds_fortest.append(json.dumps({self.dict_map[self.term_list_bodyloc[j]]: [
                                  self.term_list_bodyloc[j].strip(), self.dict_map_sty[self.term_list_bodyloc[j]]] for j, d in zip(idx, ds)}))
        preds_fortest = []
        for item in term:
            if item is None:
                preds_fortest.append(item)
            else:
                preds_fortest.append(_preds_fortest.pop(0))

        return preds_fortest
