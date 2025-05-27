import os
import torch
import json
import numpy as np
import transformers
from .embedding_service import EmbeddingService
from .index_service import IndexService
import logging
import traceback


class RetrieverCoordinator():

    def __init__(self, path, use_gpu=True, use_faiss_gpu=None, fp16=False, use_ivf=False, ivf_threshold=50000):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            path, use_fast=True, do_lower_case=True)
        self.encoder = transformers.AutoModel.from_pretrained(
            path, trust_remote_code=True)

        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.fp16 = fp16
        # Move model to appropriate device
        if self.use_gpu:
            self.encoder = self.encoder.cuda()
            if self.fp16:
                self.encoder = self.encoder.half()
        else:
            self.encoder = self.encoder.cpu()

        self.embedding_service = EmbeddingService(
            self.tokenizer, self.encoder, self.use_gpu, self.fp16)
        self.index_service = IndexService(
            use_faiss_gpu if use_faiss_gpu is not None else self.use_gpu, use_ivf, ivf_threshold)

        # Initialize dictionary containers
        self.dict_map = {}
        self.dict_map_sty = {}
        self.term_list_all = []
        self.term_list_bodyloc = []
        self.dense_embeds_all = None
        self.dense_embeds_bodyloc = None

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

    def embed_dictionary(self, batch_size=256):
        cache_file = './cache'
        os.makedirs(cache_file, exist_ok=True)

        all_embed_path = os.path.join(cache_file, 'dense_embed_all.pt')
        all_list_path = os.path.join(cache_file, 'term_list_all.pt')
        bodyloc_embed_path = os.path.join(cache_file, 'dense_embed_bodyloc.pt')
        bodyloc_list_path = os.path.join(cache_file, 'term_list_bodyloc.pt')

        self.logger.info(f"Checking if cache file exists at {all_embed_path}")
        if os.path.exists(all_embed_path) and os.path.exists(all_list_path):
            self.logger.info(
                "Cache file found. Loading all_terms dense embeddings from cache.")
            self.dense_embeds_all = torch.load(
                all_embed_path, map_location='cpu')  # Load to CPU first
            self.term_list_all = torch.load(all_list_path)
        else:
            self.logger.info(
                "Cache file not found for all_terms. Embedding terms and saving to cache.")
            self.encoder.eval()  # Ensure encoder is in eval mode
            self.dense_embeds_all = self.embedding_service.embed_term(
                self.term_list_all, batch_size)
            torch.save(self.dense_embeds_all, all_embed_path)
            torch.save(self.term_list_all, all_list_path)
            self.logger.info("All_terms dense embeddings saved to cache.")

        self.logger.info(
            f"Checking if cache file exists at {bodyloc_embed_path}")
        if os.path.exists(bodyloc_embed_path) and os.path.exists(bodyloc_list_path):
            self.logger.info(
                "Cache file found. Loading bodyloc_terms dense embeddings from cache.")
            self.dense_embeds_bodyloc = torch.load(
                bodyloc_embed_path, map_location='cpu')  # Load to CPU first
            self.term_list_bodyloc = torch.load(bodyloc_list_path)
        else:
            self.logger.info(
                "Cache file not found for bodyloc_terms. Embedding terms and saving to cache.")
            self.encoder.eval()  # Ensure encoder is in eval mode
            self.dense_embeds_bodyloc = self.embedding_service.embed_term(
                self.term_list_bodyloc, batch_size)
            torch.save(self.dense_embeds_bodyloc, bodyloc_embed_path)
            torch.save(self.term_list_bodyloc, bodyloc_list_path)
            self.logger.info("Bodyloc_terms dense embeddings saved to cache.")

        if self.fp16:
            self.dense_embeds_all = self.dense_embeds_all.half()
            self.dense_embeds_bodyloc = self.dense_embeds_bodyloc.half()

        if self.use_gpu:  # Explicitly move to GPU if required, after loading/creating
            self.dense_embeds_all = self.dense_embeds_all.cuda()
            self.dense_embeds_bodyloc = self.dense_embeds_bodyloc.cuda()

    def faiss_setup(self, gpu_id=0):
        if self.dense_embeds_all is None or self.dense_embeds_bodyloc is None:
            raise ValueError(
                "Dense embeddings not loaded or generated. Call embed_dictionary first.")

        # FAISS expects numpy arrays on CPU for initial setup before potential GPU transfer by IndexService
        dense_embeds_all_np = self.dense_embeds_all.cpu().float().numpy()
        dense_embeds_bodyloc_np = self.dense_embeds_bodyloc.cpu().float().numpy()

        self.index_service.setup_all_terms_index(
            dense_embeds_all_np, len(self.term_list_all), gpu_id)
        self.index_service.setup_bodyloc_terms_index(
            dense_embeds_bodyloc_np, len(self.term_list_bodyloc), gpu_id)

    def _common_retrieval_logic(self, term_list_type, index_search_method, term, batch_size, top_k):
        if not term:
            return []

        filtered_term = []
        none_indices = []
        for i, item in enumerate(term):
            if item is None or item == "None" or (isinstance(item, str) and item.strip() == ""):
                none_indices.append(i)
            else:
                filtered_term.append(item)

        if not filtered_term:
            return [None] * len(term)

        try:
            embed_for_test = self.embedding_service.embed_term(
                filtered_term, batch_size)

            # IndexService search methods expect numpy float32 arrays
            query_embeddings_np = embed_for_test.cpu().float().numpy()

            D, I = index_search_method(query_embeddings_np, top_k)

            current_term_list = self.term_list_all if term_list_type == 'all' else self.term_list_bodyloc

            filtered_results = []
            for i_query, (indices_for_query, distances_for_query) in enumerate(zip(I, D)):
                results_for_query = {}
                for i_match, dist in zip(indices_for_query, distances_for_query):
                    if i_match >= 0:  # Valid match
                        try:
                            term_matched = current_term_list[i_match].strip()
                            # Ensure dict_map and dict_map_sty are up-to-date for the current_term_list context
                            results_for_query[self.dict_map[term_matched]] = [
                                term_matched, self.dict_map_sty[term_matched]]
                        except (IndexError, KeyError) as e:
                            self.logger.error(
                                f"Error retrieving term match for type '{term_list_type}': {e} (index: {i_match})", exc_info=True)
                            continue
                filtered_results.append(json.dumps(
                    results_for_query) if results_for_query else None)

            final_results = []
            filtered_idx = 0
            for i_orig in range(len(term)):
                if i_orig in none_indices:
                    final_results.append(None)
                else:
                    if filtered_idx < len(filtered_results):
                        final_results.append(filtered_results[filtered_idx])
                        filtered_idx += 1
                    else:
                        self.logger.warning(
                            f"Missing result for term at original position {i_orig} (type '{term_list_type}')")
                        final_results.append(None)
            return final_results

        except Exception as e:
            self.logger.error(
                f"Error in embedding_retrieval (type '{term_list_type}'): {e}", exc_info=True)
            return [None] * len(term)

    def embedding_retrieval_all(self, term, batch_size=256, top_k=1):
        return self._common_retrieval_logic('all', self.index_service.search_all, term, batch_size, top_k)

    def embedding_retrieval_bodyloc(self, term, batch_size=256, top_k=1):
        return self._common_retrieval_logic('bodyloc', self.index_service.search_bodyloc, term, batch_size, top_k)
