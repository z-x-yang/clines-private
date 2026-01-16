"""
Start a shared RetrieverCoordinator service so multiple note-processing workers
can reuse the same encoder/FAISS indexes (GPU or CPU).

Usage example:
python -m llm_interface.retrieval.retrieval_server --host 0.0.0.0 --port 50000 \
    --use_gpu --use_faiss_gpu --authkey retriever
"""
import argparse
import logging
import os
from multiprocessing.managers import BaseManager

from llm_interface.retrieval.retriever_coordinator import RetrieverCoordinator


def build_retriever(args) -> RetrieverCoordinator:
    retriever = RetrieverCoordinator(
        args.model_path,
        use_gpu=not args.cpu and args.use_gpu,
        use_faiss_gpu=args.use_faiss_gpu,
        fp16=args.fp16,
        use_ivf=args.use_ivf,
        ivf_threshold=args.ivf_threshold,
    )
    # Load dictionaries relative to project root by default
    dict_all_path = args.dictionary_all
    dict_bodyloc_path = args.dictionary_bodyloc
    retriever.load_dictionary_all(dict_all_path)
    retriever.load_dictionary_bodyloc(dict_bodyloc_path)
    retriever.embed_dictionary(args.embed_batch_size)
    retriever.faiss_setup()
    return retriever


def main():
    parser = argparse.ArgumentParser(description="Shared RetrieverCoordinator server")
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Bind host')
    parser.add_argument('--port', type=int, default=50000, help='Bind port')
    parser.add_argument('--authkey', type=str, default='retriever', help='Auth key for BaseManager')
    parser.add_argument('--model_path', type=str, default='cambridgeltl/SapBERT-from-PubMedBERT-fulltext',
                        help='HF model path for retriever')
    parser.add_argument('--dictionary_all', type=str, default='./umls_dictionary.txt',
                        help='Path to UMLS dictionary file')
    parser.add_argument('--dictionary_bodyloc', type=str, default='./umls_body_loc_dictionary.txt',
                        help='Path to body location dictionary file')
    parser.add_argument('--embed_batch_size', type=int, default=256, help='Batch size for embedding dictionaries')
    parser.add_argument('--use_gpu', action='store_true', help='Enable GPU for encoder if available')
    parser.add_argument('--use_faiss_gpu', action='store_true', help='Enable GPU for FAISS')
    parser.add_argument('--cpu', action='store_true', help='Force CPU even if GPU is available')
    parser.add_argument('--fp16', action='store_true', help='Use FP16 encoder (GPU only)')
    parser.add_argument('--use_ivf', action='store_true', help='Use IVF index')
    parser.add_argument('--ivf_threshold', type=int, default=50000, help='IVF threshold')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("retrieval_server")

    # Ensure relative paths resolve from project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if not os.path.isabs(args.dictionary_all):
        args.dictionary_all = os.path.join(project_root, args.dictionary_all)
    if not os.path.isabs(args.dictionary_bodyloc):
        args.dictionary_bodyloc = os.path.join(project_root, args.dictionary_bodyloc)

    logger.info(f"Loading retriever (GPU={not args.cpu and args.use_gpu}, FAISS_GPU={args.use_faiss_gpu})")
    retriever = build_retriever(args)
    logger.info("Retriever ready; starting server")

    class RetrieverManager(BaseManager):
        pass

    RetrieverManager.register('get_retriever', callable=lambda: retriever)
    manager = RetrieverManager(address=(args.host, args.port), authkey=args.authkey.encode())
    server = manager.get_server()
    logger.info(f"Serving retrieval on {args.host}:{args.port} (authkey='{args.authkey}')")
    server.serve_forever()


if __name__ == "__main__":
    main()
