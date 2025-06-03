import logging
import re
import demjson3
import pprint
import json  # Added for entity_linking results
from core.data_types import EntityData
# Import utility functions
from .processing_utils import parse_result, safe_json_decode, process_llm_query

# LLMManager, PROMPT, RetrieverCoordinator will be passed during __init__


class EntityProcessor:
    def __init__(self, model, prompt_relate, prompt_clean, prompt_json_debug, retriever, deduplication_fn):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model = model  # LLMManager instance
        self.prompt_relate = prompt_relate
        self.prompt_clean = prompt_clean
        self.prompt_json_debug = prompt_json_debug  # Used by utility process_llm_query
        self.retriever = retriever  # RetrieverCoordinator instance
        self.deduplication = deduplication_fn  # Function from PipelineCoordinator

    # Removed duplicated helper methods: parse_result, safe_json_decode, _process_llm_query

    # Moved from PipelineCoordinator
    def entity_linking(self, results, type='all'):
        if not results:
            return results
        clean_entities = []
        term_indices = []
        for i, item in enumerate(results):
            if type == 'all':
                clean_entities.append(item.get('CLEAN'))
                term_indices.append(i)
            elif type == 'bodyloc':
                if 'body_location' in item and item['body_location'] is not None:
                    clean_entities.append(item['body_location'])
                    term_indices.append(i)
        if not clean_entities:
            return results

        linking_result = []
        if type == 'all':
            linking_result = self.retriever.embedding_retrieval_all(
                clean_entities)
        elif type == 'bodyloc':
            linking_result = self.retriever.embedding_retrieval_bodyloc(
                clean_entities)
        else:
            self.logger.warning(f"Unknown entity linking type: {type}")
            return results

        if len(linking_result) != len(clean_entities):
            self.logger.warning(
                f"Linking result length mismatch. Expected {len(clean_entities)}, got {len(linking_result)}")
            if len(linking_result) < len(clean_entities):
                linking_result.extend(
                    [None] * (len(clean_entities) - len(linking_result)))
            else:
                linking_result = linking_result[:len(clean_entities)]

        for idx, result_idx in enumerate(term_indices):
            try:
                if idx < len(linking_result) and linking_result[idx] is not None:
                    if type == 'all':
                        results[result_idx]['CODE'] = linking_result[idx]
                    elif type == 'bodyloc':
                        results[result_idx]['body_code'] = linking_result[idx]
            except IndexError:
                self.logger.error(
                    f"Error mapping linking result at index {idx}, result_idx {result_idx}")
                continue
        return results

    def process_entities(self, ner_results_text: str, parsed_ner_tags: list) -> EntityData:
        """Process entity relationships and cleaning."""
        # ner_results_text is the string output from NERProcessor with <1>entity</1> tags
        # parsed_ner_tags is the list of tags like ["1", "2", ...]

        relate_results = process_llm_query(
            model=self.model,
            prompt_obj=self.prompt_relate,
            template_vars={'note': ner_results_text},
            prompt_json_debug=self.prompt_json_debug,
            logger=self.logger,
            parse_json=True,  # Expect JSON output
            new_chat=True
        )
        # Use the passed deduplication function
        relate_results = self.deduplication(
            relate_results, 'tag', parsed_ner_tags)
        self.logger.debug(f"Relate results:\n{pprint.pformat(relate_results)}")

        clean_results = process_llm_query(
            model=self.model,
            prompt_obj=self.prompt_clean,
            template_vars={'note': ner_results_text},
            prompt_json_debug=self.prompt_json_debug,
            logger=self.logger,
            parse_json=True,  # Expect JSON output
            new_chat=True
        )
        clean_results = self.deduplication(
            clean_results, 'TAG', parsed_ner_tags)
        self.logger.debug(
            f"Clean results before linking:\n{pprint.pformat(clean_results)}")

        clean_results = self.entity_linking(clean_results, type='all')
        self.logger.debug(
            f"Clean results after linking:\n{pprint.pformat(clean_results)}")

        return EntityData(
            relate_results=relate_results,
            clean_results=clean_results
        )
