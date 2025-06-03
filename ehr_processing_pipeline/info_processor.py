import logging
import re
import demjson3
import pprint
import json
from core.data_types import InfoData
# Import utility functions
from .processing_utils import parse_result, safe_json_decode, process_llm_query

# LLMManager, PROMPT, RetrieverCoordinator, deduplication_fn will be passed during __init__


class InfoProcessor:
    def __init__(self, model, prompt_status, prompt_info, prompt_json_debug, retriever, deduplication_fn):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model = model  # LLMManager instance
        self.prompt_status = prompt_status
        self.prompt_info = prompt_info
        self.prompt_json_debug = prompt_json_debug  # Used by utility process_llm_query
        self.retriever = retriever  # RetrieverCoordinator instance
        self.deduplication = deduplication_fn  # Function from PipelineCoordinator

    # Removed duplicated helper methods: parse_result, safe_json_decode, _process_llm_query

    # Moved from PipelineCoordinator and renamed
    def process_information(self, ner_results_text: str, parsed_ner_tags: list) -> InfoData:
        # status_results
        status_results = process_llm_query(
            model=self.model,
            prompt_obj=self.prompt_status,
            template_vars={'note': ner_results_text},
            prompt_json_debug=self.prompt_json_debug,
            logger=self.logger,
            parse_json=True,
            new_chat=True
        )
        status_results = self.deduplication(
            status_results, 'tag', parsed_ner_tags)
        self.logger.debug(f"Status results:\n{pprint.pformat(status_results)}")

        # info_results
        info_results = process_llm_query(
            model=self.model,
            prompt_obj=self.prompt_info,
            template_vars={'note': ner_results_text},
            prompt_json_debug=self.prompt_json_debug,
            logger=self.logger,
            parse_json=True,
            new_chat=True
        )
        info_results = self.deduplication(info_results, 'tag', parsed_ner_tags)
        self.logger.debug(
            f"Info results before linking:\n{pprint.pformat(info_results)}")

        # Entity linking for body_location
        if len(info_results) > 0:
            clean_entities_bodyloc = []
            term_indices_bodyloc = []
            for i, item in enumerate(info_results):
                if 'body_location' in item and item['body_location'] is not None:
                    clean_entities_bodyloc.append(item['body_location'])
                    term_indices_bodyloc.append(i)

            if clean_entities_bodyloc:
                linking_result_bodyloc = self.retriever.embedding_retrieval_bodyloc(
                    clean_entities_bodyloc)
                if len(linking_result_bodyloc) != len(clean_entities_bodyloc):
                    self.logger.warning(
                        "Bodyloc linking result length mismatch.")
                else:
                    for idx, result_idx in enumerate(term_indices_bodyloc):
                        if idx < len(linking_result_bodyloc) and linking_result_bodyloc[idx] is not None:
                            info_results[result_idx]['body_code'] = linking_result_bodyloc[idx]
            self.logger.debug(
                f"Info results after linking:\n{pprint.pformat(info_results)}")
        else:
            self.logger.info(
                "Info results is empty, skipping bodyloc linking.")
        return InfoData(status_results=status_results, info_results=info_results)
