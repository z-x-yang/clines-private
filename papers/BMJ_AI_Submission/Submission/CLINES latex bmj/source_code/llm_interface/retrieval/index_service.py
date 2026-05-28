import faiss
import numpy as np
import torch
import logging


class IndexService:
    def __init__(self, use_faiss_gpu=True, use_ivf=True, ivf_threshold=50000):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.use_faiss_gpu = use_faiss_gpu
        self.use_ivf = use_ivf
        self.ivf_threshold = ivf_threshold
        self.index_flat_all = None
        self.index_flat_bodyloc = None
        self.d = None  # Dimension of vectors, to be set during setup

    def _setup_faiss_index(self, dense_embeds_np, term_list_len, gpu_id=0):
        if self.d is None:
            self.d = dense_embeds_np.shape[1]
        elif self.d != dense_embeds_np.shape[1]:
            raise ValueError(
                "Dimension mismatch in embeddings for FAISS setup.")

        use_ivf_current = self.use_ivf and term_list_len > self.ivf_threshold
        index_type_description = f"IVF index with {min(4096, max(int(term_list_len / 50), 256))} clusters" if use_ivf_current else "FlatIP index"
        self.logger.info(
            f"Creating FAISS {index_type_description} for {term_list_len} terms.")

        actual_index = None

        if self.use_faiss_gpu:
            try:
                self.logger.info(
                    f"Attempting to use GPU for FAISS setup ({index_type_description}).")
                res = faiss.StandardGpuResources()
                if use_ivf_current:
                    nlist = min(4096, max(int(term_list_len / 50), 256))
                    quantizer = faiss.IndexFlatIP(self.d)
                    cpu_index = faiss.IndexIVFFlat(
                        quantizer, self.d, nlist, faiss.METRIC_INNER_PRODUCT)
                    gpu_index = faiss.index_cpu_to_gpu(res, gpu_id, cpu_index)
                    # Train on subset if very large
                    if dense_embeds_np.shape[0] > 1000000:
                        train_size = min(1000000, int(
                            dense_embeds_np.shape[0] * 0.2))
                        indices = np.random.choice(
                            dense_embeds_np.shape[0], train_size, replace=False)
                        gpu_index.train(dense_embeds_np[indices])
                    else:
                        gpu_index.train(dense_embeds_np)
                    actual_index = faiss.index_gpu_to_cpu(
                        gpu_index)  # Keep on CPU for adding
                    actual_index.add(dense_embeds_np)  # Add on CPU
                    actual_index = faiss.index_cpu_to_gpu(
                        res, gpu_id, actual_index)  # Move back to GPU
                else:
                    cpu_index = faiss.IndexFlatIP(self.d)
                    actual_index = faiss.index_cpu_to_gpu(
                        res, gpu_id, cpu_index)
                    actual_index.add(dense_embeds_np)
                self.logger.info(
                    f"Successfully created FAISS index on GPU ({index_type_description}).")
            except Exception as e:
                self.logger.error(
                    f"Error setting up FAISS on GPU for {index_type_description}: {e}. Falling back to CPU is handled by caller.", exc_info=True)
                # Fallback to CPU is handled by re-calling with use_faiss_gpu=False if needed by coordinator
                # For now, we just re-raise to indicate failure at this level
                raise e
        else:
            self.logger.info(
                f"Using CPU for FAISS setup ({index_type_description}).")
            if use_ivf_current:
                nlist = min(4096, max(int(term_list_len / 50), 256))
                quantizer = faiss.IndexFlatIP(self.d)
                actual_index = faiss.IndexIVFFlat(
                    quantizer, self.d, nlist, faiss.METRIC_INNER_PRODUCT)
                if dense_embeds_np.shape[0] > 1000000:
                    train_size = min(1000000, int(
                        dense_embeds_np.shape[0] * 0.2))
                    indices = np.random.choice(
                        dense_embeds_np.shape[0], train_size, replace=False)
                    actual_index.train(dense_embeds_np[indices])
                else:
                    actual_index.train(dense_embeds_np)
            else:
                actual_index = faiss.IndexFlatIP(self.d)
            actual_index.add(dense_embeds_np)
            self.logger.info(
                f"Successfully created FAISS index on CPU ({index_type_description}).")
        return actual_index

    def setup_all_terms_index(self, dense_embeds_all_np, term_list_all_len, gpu_id=0):
        self.logger.info("Setting up FAISS index for ALL terms.")
        try:
            self.index_flat_all = self._setup_faiss_index(
                dense_embeds_all_np, term_list_all_len, gpu_id)
        except Exception as e:
            if self.use_faiss_gpu:  # If GPU failed, try CPU
                self.logger.warning(
                    "Retrying FAISS setup for ALL terms on CPU due to GPU failure.", exc_info=True)
                self.use_faiss_gpu = False  # Temporarily disable for this attempt
                self.index_flat_all = self._setup_faiss_index(
                    dense_embeds_all_np, term_list_all_len, gpu_id)
                self.use_faiss_gpu = True  # Restore original preference
            else:
                self.logger.error(
                    "FAISS setup for ALL terms failed on CPU as well.", exc_info=True)
                raise e  # If CPU also fails, or was the original attempt
        self.logger.info("FAISS setup for ALL terms completed.")

    def setup_bodyloc_terms_index(self, dense_embeds_bodyloc_np, term_list_bodyloc_len, gpu_id=0):
        self.logger.info("Setting up FAISS index for BODYLOC terms.")
        try:
            self.index_flat_bodyloc = self._setup_faiss_index(
                dense_embeds_bodyloc_np, term_list_bodyloc_len, gpu_id)
        except Exception as e:
            if self.use_faiss_gpu:  # If GPU failed, try CPU
                self.logger.warning(
                    "Retrying FAISS setup for BODYLOC terms on CPU due to GPU failure.", exc_info=True)
                self.use_faiss_gpu = False  # Temporarily disable for this attempt
                self.index_flat_bodyloc = self._setup_faiss_index(
                    dense_embeds_bodyloc_np, term_list_bodyloc_len, gpu_id)
                self.use_faiss_gpu = True  # Restore original preference
            else:
                self.logger.error(
                    "FAISS setup for BODYLOC terms failed on CPU as well.", exc_info=True)
                raise e  # If CPU also fails, or was the original attempt
        self.logger.info("FAISS setup for BODYLOC terms completed.")

    def search(self, index, query_embeddings_np, top_k):
        if index is None:
            raise ValueError(
                "FAISS index is not initialized. Call setup methods first.")
        if not isinstance(query_embeddings_np, np.ndarray):
            query_embeddings_np = query_embeddings_np.numpy()  # Ensure numpy array
        if query_embeddings_np.dtype != np.float32:
            query_embeddings_np = query_embeddings_np.astype(
                np.float32)  # Ensure float32

        if hasattr(index, 'nprobe'):  # Check if IVF index
            index.nprobe = min(
                32, index.nlist if hasattr(index, 'nlist') else 32)
        return index.search(query_embeddings_np, top_k)

    def search_all(self, query_embeddings_np, top_k=1):
        return self.search(self.index_flat_all, query_embeddings_np, top_k)

    def search_bodyloc(self, query_embeddings_np, top_k=1):
        return self.search(self.index_flat_bodyloc, query_embeddings_np, top_k)
