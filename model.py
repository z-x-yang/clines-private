import os
import torch
from tqdm import tqdm
import semchunk
import json
import faiss
import numpy as np


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
        from openai import AzureOpenAI
        import time

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
                print(f"Error in openai_chat: {e}")
                if response:
                    print(f"Response: {response}")

                if retry and retries < max_retries:
                    retries += 1
                    print(f"Retrying... (attempt {retries}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                else:
                    raise Exception(f"Failed after {retries} retries: {e}")

    return openai_chat


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
        # Add token counting attributes
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.chunk_token_stats = []  # List to store token stats per chunk
        self.note_token_stats = []   # List to store token stats per note
        self.current_chunk_stats = []  # Temporary storage for current chunk stats

        if self.model_name in ['gpt4o', 'gpt4omini', 'o3mini']:

            import tiktoken
            self.chat_func = wrap_openai_chat(self.model_name)
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
        # Don't reset chunk token stats here anymore
        self.message_buffer = []
        if self.model_name in ['gpt4o', 'gpt4omini', 'o3mini']:

            self.message_buffer.append({
                "role": "system",
                "content": "You are a medical record processing AI. Process all medical terminology, procedures, and conditions as standard healthcare documentation. Maintain professional medical context in responses."
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

        # Handle token usage if available
        if isinstance(response, dict) and response.get('token_usage'):
            token_usage = response['token_usage']
            # Update token counts
            self.total_prompt_tokens += token_usage.prompt_tokens
            self.total_completion_tokens += token_usage.completion_tokens

            # Store chunk stats in temporary storage
            chunk_stats = {
                'prompt_tokens': token_usage.prompt_tokens,
                'completion_tokens': token_usage.completion_tokens,
                'total_tokens': token_usage.total_tokens
            }
            self.current_chunk_stats.append(chunk_stats)

            content = response['content']
        else:
            content = response if isinstance(
                response, str) else response['content']

        self.message_buffer.append({'role': 'assistant', 'content': content})

        return content

    def finish_chunk(self):
        """
        Called when a chunk is finished processing to finalize its token statistics
        """
        if self.current_chunk_stats:
            # Calculate chunk-level statistics
            chunk_total = {
                'prompt_tokens': sum(stats['prompt_tokens'] for stats in self.current_chunk_stats),
                'completion_tokens': sum(stats['completion_tokens'] for stats in self.current_chunk_stats),
                'total_tokens': sum(stats['total_tokens'] for stats in self.current_chunk_stats),
                'num_calls': len(self.current_chunk_stats)
            }
            self.chunk_token_stats.append(chunk_total)

            # Calculate and store note-level token stats
            note_stats = {
                'total_prompt_tokens': sum(chunk['prompt_tokens'] for chunk in self.chunk_token_stats),
                'total_completion_tokens': sum(chunk['completion_tokens'] for chunk in self.chunk_token_stats),
                'total_tokens': sum(chunk['total_tokens'] for chunk in self.chunk_token_stats),
                'num_chunks': len(self.chunk_token_stats),
                'avg_tokens_per_chunk': sum(chunk['total_tokens'] for chunk in self.chunk_token_stats) / len(self.chunk_token_stats)
            }
            self.note_token_stats.append(note_stats)

            # Reset current chunk stats
            self.current_chunk_stats = []


class Retriever():

    def __init__(self, path, use_gpu=True, use_faiss_gpu=None, fp16=False, use_ivf=True, ivf_threshold=50000):
        import transformers
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            path, use_fast=True, do_lower_case=True)
        self.encoder = transformers.AutoModel.from_pretrained(
            path, trust_remote_code=True)
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.use_faiss_gpu = use_faiss_gpu if use_faiss_gpu is not None else self.use_gpu
        self.fp16 = fp16
        self.use_ivf = use_ivf
        self.ivf_threshold = ivf_threshold

        # Move model to appropriate device and optimize for memory
        if self.use_gpu:
            self.encoder = self.encoder.cuda()
            if self.fp16:
                self.encoder = self.encoder.half()  # Use half precision on GPU
        else:
            self.encoder = self.encoder.cpu()

        # Initialize dictionary containers
        self.dict_map = {}
        self.dict_map_sty = {}
        self.term_list_all = []
        self.term_list_bodyloc = []

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
        if not names:
            return torch.zeros((0, self.encoder.config.hidden_size))

        # Clean and prepare input
        names = [str(item).lower() for item in names if item is not None]
        if not names:
            return torch.zeros((0, self.encoder.config.hidden_size))

        # Determine optimal batch size based on input length and available memory
        if self.use_gpu:
            # Adjust batch size based on input length to optimize GPU memory usage
            avg_length = sum(len(name.split()) for name in names) / len(names)
            if avg_length > 15:
                batch_size = min(batch_size, 128)
            elif avg_length > 5:
                batch_size = min(batch_size, 192)

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

                # Move to appropriate device
                if self.use_gpu:
                    batch_tokenized_names = {
                        k: v.cuda() for k, v in batch_tokenized_names.items()}

                    # Use half precision for GPU if enabled
                    if self.fp16:
                        batch_tokenized_names = {k: v.half() if v.dtype == torch.float32 else v
                                                 for k, v in batch_tokenized_names.items()}

                # Get embeddings
                batch_dense_embeds = self.encoder(
                    **batch_tokenized_names).last_hidden_state[:, 0, :]

                # Normalize embeddings and move to CPU
                batch_dense_embeds = batch_dense_embeds / \
                    torch.norm(batch_dense_embeds, p=2, dim=-1, keepdim=True)
                batch_dense_embeds = batch_dense_embeds.cpu()

                dense_embeds.append(batch_dense_embeds)

                # Clear GPU cache if using GPU
                if self.use_gpu:
                    torch.cuda.empty_cache()

        # Concatenate all embeddings
        if dense_embeds:
            return torch.concat(dense_embeds, dim=0)
        else:
            return torch.zeros((0, self.encoder.config.hidden_size))

    def embed_dictionary(self, batch_size=256):
        import os
        import torch
        cache_file = './cache'
        os.makedirs(cache_file, exist_ok=True)

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
            torch.save(self.term_list_all, cache_file + '/term_list_all.pt')
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

        # Convert to half precision to save memory if enabled
        if self.fp16:
            self.dense_embeds_all = self.dense_embeds_all.half()
            self.dense_embeds_bodyloc = self.dense_embeds_bodyloc.half()

        # Move to appropriate device
        if self.use_gpu:
            self.dense_embeds_all = self.dense_embeds_all.cuda()
            self.dense_embeds_bodyloc = self.dense_embeds_bodyloc.cuda()

    def faiss_setup(self, gpu_id=0):
        # Convert embeddings to numpy arrays - use float32 for FAISS
        if self.use_gpu:
            dense_embeds_all_np = self.dense_embeds_all.cpu().float().numpy()
            dense_embeds_bodyloc_np = self.dense_embeds_bodyloc.cpu().float().numpy()
        else:
            dense_embeds_all_np = self.dense_embeds_all.float().numpy()
            dense_embeds_bodyloc_np = self.dense_embeds_bodyloc.float().numpy()

        d = dense_embeds_all_np.shape[1]  # dimension of vectors

        # Check if the dataset is large enough for IVF (and if IVF is enabled)
        use_ivf_all = self.use_ivf and len(
            self.term_list_all) > self.ivf_threshold
        use_ivf_bodyloc = self.use_ivf and len(
            self.term_list_bodyloc) > self.ivf_threshold

        print(
            f"Creating FAISS index for {len(self.term_list_all)} terms (using IVF: {use_ivf_all})")

        if self.use_faiss_gpu:
            try:
                print("Using GPU for FAISS setup")
                res = faiss.StandardGpuResources()

                # For all terms index
                if use_ivf_all:
                    # Use fewer clusters for faster training
                    nlist = min(
                        4096, max(int(len(self.term_list_all) / 50), 256))
                    print(f"Training IVF index with {nlist} clusters...")
                    quantizer = faiss.IndexFlatIP(d)
                    index = faiss.IndexIVFFlat(
                        quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
                    # Move to GPU for training
                    gpu_index = faiss.index_cpu_to_gpu(res, gpu_id, index)
                    # Train on a subset of data for speed if the dataset is extremely large
                    if len(dense_embeds_all_np) > 1000000:
                        train_size = min(1000000, int(
                            len(dense_embeds_all_np) * 0.2))
                        indices = np.random.choice(
                            len(dense_embeds_all_np), train_size, replace=False)
                        gpu_index.train(dense_embeds_all_np[indices])
                    else:
                        gpu_index.train(dense_embeds_all_np)
                    # Move back to CPU for adding vectors (can be more memory efficient)
                    self.index_flat_all = faiss.index_gpu_to_cpu(gpu_index)
                    # Add vectors on CPU
                    self.index_flat_all.add(dense_embeds_all_np)
                    # Move final index to GPU
                    self.index_flat_all = faiss.index_cpu_to_gpu(
                        res, gpu_id, self.index_flat_all)
                else:
                    # For smaller datasets, use flat index
                    index = faiss.IndexFlatIP(d)
                    self.index_flat_all = faiss.index_cpu_to_gpu(
                        res, gpu_id, index)
                    self.index_flat_all.add(dense_embeds_all_np)

                # For body location index
                if use_ivf_bodyloc:
                    nlist = min(
                        4096, max(int(len(self.term_list_bodyloc) / 50), 256))
                    print(
                        f"Training body location IVF index with {nlist} clusters...")
                    quantizer = faiss.IndexFlatIP(d)
                    index = faiss.IndexIVFFlat(
                        quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
                    gpu_index = faiss.index_cpu_to_gpu(res, gpu_id, index)
                    if len(dense_embeds_bodyloc_np) > 1000000:
                        train_size = min(1000000, int(
                            len(dense_embeds_bodyloc_np) * 0.2))
                        indices = np.random.choice(
                            len(dense_embeds_bodyloc_np), train_size, replace=False)
                        gpu_index.train(dense_embeds_bodyloc_np[indices])
                    else:
                        gpu_index.train(dense_embeds_bodyloc_np)
                    self.index_flat_bodyloc = faiss.index_gpu_to_cpu(gpu_index)
                    self.index_flat_bodyloc.add(dense_embeds_bodyloc_np)
                    self.index_flat_bodyloc = faiss.index_cpu_to_gpu(
                        res, gpu_id, self.index_flat_bodyloc)
                else:
                    index = faiss.IndexFlatIP(d)
                    self.index_flat_bodyloc = faiss.index_cpu_to_gpu(
                        res, gpu_id, index)
                    self.index_flat_bodyloc.add(dense_embeds_bodyloc_np)
            except Exception as e:
                print(
                    f"Error setting up FAISS on GPU: {e}. Falling back to CPU.")
                self.use_faiss_gpu = False
                self.faiss_setup()
                return
        else:
            print("Using CPU for FAISS setup")
            # Similar optimization for CPU
            if use_ivf_all:
                nlist = min(4096, max(int(len(self.term_list_all) / 50), 256))
                print(f"Training IVF index with {nlist} clusters...")
                quantizer = faiss.IndexFlatIP(d)
                self.index_flat_all = faiss.IndexIVFFlat(
                    quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
                # Train on subset if extremely large
                if len(dense_embeds_all_np) > 1000000:
                    train_size = min(1000000, int(
                        len(dense_embeds_all_np) * 0.2))
                    indices = np.random.choice(
                        len(dense_embeds_all_np), train_size, replace=False)
                    self.index_flat_all.train(dense_embeds_all_np[indices])
                else:
                    self.index_flat_all.train(dense_embeds_all_np)
            else:
                self.index_flat_all = faiss.IndexFlatIP(d)

            self.index_flat_all.add(dense_embeds_all_np)

            if use_ivf_bodyloc:
                nlist = min(
                    4096, max(int(len(self.term_list_bodyloc) / 50), 256))
                print(
                    f"Training body location IVF index with {nlist} clusters...")
                quantizer = faiss.IndexFlatIP(d)
                self.index_flat_bodyloc = faiss.IndexIVFFlat(
                    quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
                if len(dense_embeds_bodyloc_np) > 1000000:
                    train_size = min(1000000, int(
                        len(dense_embeds_bodyloc_np) * 0.2))
                    indices = np.random.choice(
                        len(dense_embeds_bodyloc_np), train_size, replace=False)
                    self.index_flat_bodyloc.train(
                        dense_embeds_bodyloc_np[indices])
                else:
                    self.index_flat_bodyloc.train(dense_embeds_bodyloc_np)
            else:
                self.index_flat_bodyloc = faiss.IndexFlatIP(d)

            self.index_flat_bodyloc.add(dense_embeds_bodyloc_np)

        print("FAISS setup completed")

    def embedding_retrieval_all(self, term, batch_size=256, top_k=1):
        """
        Retrieve entity codes for terms using embedding-based search.

        Args:
            term: List of terms to search for
            batch_size: Batch size for embedding
            top_k: Number of top results to return

        Returns:
            List of JSON strings with entity codes and terms
        """
        # Handle empty or None inputs
        if not term:
            return []

        # Filter None values and keep track of their positions
        filtered_term = []
        none_indices = []

        for i, item in enumerate(term):
            if item is None or item == "None" or (isinstance(item, str) and item.strip() == ""):
                none_indices.append(i)
            else:
                filtered_term.append(item)

        # If all items are None, return list of None values
        if not filtered_term:
            return [None] * len(term)

        try:
            # Generate embeddings for non-None terms
            embed_for_test = self.embed_term(filtered_term, batch_size)

            # Convert to correct format for search
            if self.use_gpu and self.fp16:
                embed_for_test = embed_for_test.float()  # FAISS requires float32

            embed_for_test_np = embed_for_test.numpy()

            # Check if using IVF index (in a version-independent way)
            if hasattr(self.index_flat_all, 'nprobe'):
                # This is an IVF index
                self.index_flat_all.nprobe = min(32, self.index_flat_all.nlist)

            D, I = self.index_flat_all.search(embed_for_test_np, top_k)

            # Process search results
            filtered_results = []
            for i, (idx, ds) in enumerate(zip(I, D)):
                results = {}
                for j, d in zip(idx, ds):
                    if j >= 0:  # Skip -1 indices (no match found)
                        try:
                            term_matched = self.term_list_all[j].strip()
                            results[self.dict_map[term_matched]] = [
                                term_matched, self.dict_map_sty[term_matched]]
                        except (IndexError, KeyError) as e:
                            print(f"Error retrieving term match: {e}")
                            continue
                filtered_results.append(json.dumps(results))

            # Reinsert None values at their original positions
            final_results = []
            filtered_idx = 0

            for i in range(len(term)):
                if i in none_indices:
                    final_results.append(None)
                else:
                    if filtered_idx < len(filtered_results):
                        final_results.append(filtered_results[filtered_idx])
                        filtered_idx += 1
                    else:
                        # Handle case where filtered_results is shorter than expected
                        print(
                            f"Warning: Missing result for term at position {i}")
                        final_results.append(None)

            return final_results

        except Exception as e:
            print(f"Error in embedding_retrieval_all: {e}")
            # Return None for all inputs as fallback
            return [None] * len(term)

    def embedding_retrieval_bodyloc(self, term, batch_size=256, top_k=1):
        """
        Retrieve body location entity codes for terms using embedding-based search.

        Args:
            term: List of terms to search for
            batch_size: Batch size for embedding
            top_k: Number of top results to return

        Returns:
            List of JSON strings with entity codes and terms
        """
        # Handle empty input
        if not term:
            return []

        # Filter None values and keep track of their positions
        filtered_term = []
        none_indices = []

        for i, item in enumerate(term):
            if item is None or item == "None" or (isinstance(item, str) and item.strip() == ""):
                none_indices.append(i)
            else:
                filtered_term.append(item)

        # If all items are None, return list of None values
        if not filtered_term:
            return [None] * len(term)

        try:
            # Generate embeddings for non-None terms
            embed_for_test = self.embed_term(filtered_term, batch_size)

            # Convert to correct format for search
            if self.use_gpu and self.fp16:
                embed_for_test = embed_for_test.float()

            embed_for_test_np = embed_for_test.numpy()

            # Check if using IVF index (in a version-independent way)
            if hasattr(self.index_flat_bodyloc, 'nprobe'):
                # This is an IVF index
                self.index_flat_bodyloc.nprobe = min(
                    32, self.index_flat_bodyloc.nlist)

            D, I = self.index_flat_bodyloc.search(embed_for_test_np, top_k)

            # Process search results
            filtered_results = []
            for i, (idx, ds) in enumerate(zip(I, D)):
                results = {}
                for j, d in zip(idx, ds):
                    if j >= 0:  # Skip -1 indices (no match found)
                        try:
                            term_matched = self.term_list_bodyloc[j].strip()
                            results[self.dict_map[term_matched]] = [
                                term_matched, self.dict_map_sty[term_matched]]
                        except (IndexError, KeyError) as e:
                            print(
                                f"Error retrieving body location term match: {e}")
                            continue
                filtered_results.append(
                    json.dumps(results) if results else None)

            # Reinsert None values at their original positions
            final_results = []
            filtered_idx = 0

            for i in range(len(term)):
                if i in none_indices:
                    final_results.append(None)
                else:
                    if filtered_idx < len(filtered_results):
                        final_results.append(filtered_results[filtered_idx])
                        filtered_idx += 1
                    else:
                        # Handle case where filtered_results is shorter than expected
                        print(
                            f"Warning: Missing body location result for term at position {i}")
                        final_results.append(None)

            return final_results

        except Exception as e:
            print(f"Error in embedding_retrieval_bodyloc: {e}")
            # Return None for all inputs as fallback
            return [None] * len(term)
