import logging
import re
import demjson3
import pprint
import json
from core.data_types import InfoData
# Import utility functions
from .processing_utils import parse_result, safe_json_decode, process_llm_query, process_llm_query_with_contract, get_contract_for_prompt
from .data_contracts import ContractRegistry

# LLMManager, PROMPT, RetrieverCoordinator, deduplication_fn will be passed during __init__


class InfoProcessor:
    def __init__(self, model, prompt_status, prompt_info, prompt_json_debug, retriever, deduplication_fn,
                 disable_sapbert=False, disable_step4_reconcile=False):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model = model  # LLMManager instance
        self.prompt_status = prompt_status
        self.prompt_info = prompt_info
        self.prompt_json_debug = prompt_json_debug  # Used by utility process_llm_query
        self.retriever = retriever  # RetrieverCoordinator instance (may be None when SapBERT disabled)
        self.deduplication = deduplication_fn  # Function from PipelineCoordinator
        # EXP-G ablation flags
        self.disable_sapbert = bool(disable_sapbert)
        self.disable_step4_reconcile = bool(disable_step4_reconcile)

        # Get data contracts
        self.status_contract = ContractRegistry.get_findstatus_contract()
        self.info_contract = ContractRegistry.get_findinfo_contract()

    # Removed duplicated helper methods: parse_result, safe_json_decode, _process_llm_query

    # Moved from PipelineCoordinator and renamed
    def process_information(self, ner_results_text: str, parsed_ner_tags: list) -> InfoData:
        self.logger.debug(f"Processing information for {len(parsed_ner_tags)} entities")
        self.last_run_stats = {
            'status': 'success',
            'fallback_used': False,
            'error': None,
            'status_module': {'status': 'success', 'fallback_used': False, 'error': None},
            'info_module': {'status': 'success', 'fallback_used': False, 'error': None},
        }
        # status_results - use type-safe processing
        try:
            status_results = process_llm_query_with_contract(
                model=self.model,
                prompt_obj=self.prompt_status,
                template_vars={'note': ner_results_text},
                contract=self.status_contract,
                prompt_json_debug=self.prompt_json_debug,
                logger=self.logger,
                parsed_ner_tags=parsed_ner_tags,
                new_chat=True
            )
            
            # Deduplication processing - input is now safe list of dictionaries
            if self.disable_step4_reconcile:
                self.logger.info("EXP-G ablation: Step 4 reconcile DISABLED; skipping status-results dedup")
                from .processing_utils import safe_deduplication_input as _safe
                status_results = _safe(status_results, self.logger)
            else:
                status_results = self.deduplication(status_results, 'tag', parsed_ner_tags)
            self.logger.debug(f"Status results after deduplication:\n{pprint.pformat(status_results)}")
            
        except Exception as e:
            self.logger.error(f"Error processing status results: {e}", exc_info=True)
            # Use fallback strategy
            status_results = self.status_contract.fallback_generator(ner_results_text, parsed_ner_tags)
            self.logger.warning("Used fallback for status results")
            self.last_run_stats['status_module'] = {'status': 'partial', 'fallback_used': True, 'error': str(e)}
            self.last_run_stats['fallback_used'] = True

        # info_results - use type-safe processing
        try:
            info_results = process_llm_query_with_contract(
                model=self.model,
                prompt_obj=self.prompt_info,
                template_vars={'note': ner_results_text},
                contract=self.info_contract,
                prompt_json_debug=self.prompt_json_debug,
                logger=self.logger,
                parsed_ner_tags=parsed_ner_tags,
                new_chat=True
            )
            
            # Deduplication processing - input is now safe list of dictionaries
            if self.disable_step4_reconcile:
                from .processing_utils import safe_deduplication_input as _safe
                info_results = _safe(info_results, self.logger)
            else:
                info_results = self.deduplication(info_results, 'tag', parsed_ner_tags)
            self.logger.debug(f"Info results before linking:\n{pprint.pformat(info_results)}")
            
        except Exception as e:
            self.logger.error(f"Error processing info results: {e}", exc_info=True)
            # Use fallback strategy
            info_results = self.info_contract.fallback_generator(ner_results_text, parsed_ner_tags)
            self.logger.warning("Used fallback for info results")
            self.last_run_stats['info_module'] = {'status': 'partial', 'fallback_used': True, 'error': str(e)}
            self.last_run_stats['fallback_used'] = True

        # Entity linking for body_location
        if len(info_results) > 0:
            # EXP-G ablation (a): SapBERT OFF → write placeholder body_code,
            # skip embedding retrieval entirely.
            if self.disable_sapbert:
                self.logger.info("EXP-G ablation: SapBERT DISABLED for body_location linking; writing placeholder body_codes")
                for item in info_results:
                    bl = item.get('body_location')
                    if bl is not None:
                        item['body_code'] = json.dumps({f"NORM_OFF||{bl}": [bl, "NA"]})
                # Skip downstream retrieval entirely
                self.logger.debug(f"Completed processing (SapBERT off): {len(status_results)} status results, {len(info_results)} info results")
                if self.last_run_stats['status_module']['status'] != 'partial' and self.last_run_stats['info_module']['status'] != 'partial':
                    self.last_run_stats['status'] = 'success'
                else:
                    self.last_run_stats['status'] = 'partial'
                return InfoData(status_results=status_results, info_results=info_results)

            clean_entities_bodyloc = []
            term_indices_bodyloc = []
            for i, item in enumerate(info_results):
                if 'body_location' in item and item['body_location'] is not None:
                    clean_entities_bodyloc.append(item['body_location'])
                    term_indices_bodyloc.append(i)

            if clean_entities_bodyloc:
                try:
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
                except Exception as e:
                    self.logger.error(f"Error in body location linking: {e}", exc_info=True)
            else:
                self.logger.debug("No body locations found for linking")
        else:
            self.logger.info(
                "Info results is empty, skipping bodyloc linking.")
        
        self.logger.debug(f"Completed processing: {len(status_results)} status results, {len(info_results)} info results")
        if self.last_run_stats['status_module']['status'] != 'partial' and self.last_run_stats['info_module']['status'] != 'partial':
            self.last_run_stats['status'] = 'success'
        else:
            self.last_run_stats['status'] = 'partial'
        return InfoData(status_results=status_results, info_results=info_results)
