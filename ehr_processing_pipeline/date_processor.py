import json
import re
import logging
from core.data_types import DateData
import demjson3
import pprint
from typing import List, Dict, Any, Optional

# Import utility functions
from .processing_utils import parse_result, safe_json_decode, process_llm_query

# LLMManager, PROMPT objects, deduplication_fn will be passed during __init__


class DateProcessor:
    def __init__(self, model, prompt_basic_info, prompt_date_single,
                 prompt_date_multi, norm_date_prompt, prompt_json_debug, deduplication_fn):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model = model
        self.prompt_basic_info = prompt_basic_info
        self.prompt_date_single = prompt_date_single
        self.prompt_date_multi = prompt_date_multi
        self.norm_date_prompt = norm_date_prompt
        self.prompt_json_debug = prompt_json_debug  # Used by utility process_llm_query
        self.deduplication = deduplication_fn

        # These will be set during processing, potentially based on args to process_dates
        self.current_admission_date = None
        self.current_discharge_date = None

    # Removed duplicated helper methods: parse_result, safe_json_decode, _process_llm_query

    def _normalize_date_entry(self, date_entry):
        # This method now uses the utility function process_llm_query
        if date_entry.get('date') and date_entry['date'][0] is not None and date_entry['date'][1] is not None and len(re.findall(r'[0-9]+-[0-9]+-[0-9]+', date_entry['date'][0])) == 0:
            self.logger.info(f"Normalizing date: {date_entry['date'][0]}")
            self.logger.debug(
                f"Admission date anchor for normalization: {self.current_admission_date}")

            template_vars = {
                'date': date_entry['date'][0], 'anchor': self.current_admission_date}
            # Log the query that would be built by prompt_obj.apply_template for debugging
            # query_for_log = self.norm_date_prompt.apply_template(template_vars)
            # self.logger.debug(f"Generated query for date normalization (using norm_date_prompt):\n{query_for_log}")

            normalized_date = process_llm_query(
                model=self.model,
                # Use the specific prompt for date normalization
                prompt_obj=self.norm_date_prompt,
                template_vars=template_vars,
                prompt_json_debug=self.prompt_json_debug,
                logger=self.logger,
                # Expect JSON list like ["YYYY-MM-DD", "YYYY-MM-DD"]
                parse_json=True,
                new_chat=False  # Re-use existing chat session if possible
            )

            inferred_status = date_entry.get('inferred', [True, True])
            date_entry['date'] = normalized_date
            if 'inferred' not in date_entry:
                date_entry['inferred'] = inferred_status
            self.logger.info(f"Normalized date result: {normalized_date}")
        return date_entry

    def normalize_date_list(self, date_results_list):
        if not self.current_admission_date:
            self.logger.warning(
                "Cannot normalize dates without an admission date anchor.")
            return date_results_list

        normalized_list = []
        for item in date_results_list:
            normalized_list.append(self._normalize_date_entry(item))
        return normalized_list

    def _process_initial_dates(self, ehr: str, ner_results_text: str, parsed_ner_tags: list) -> DateData:
        basic_results = process_llm_query(
            model=self.model,
            prompt_obj=self.prompt_basic_info,
            template_vars={'note': ehr},
            prompt_json_debug=self.prompt_json_debug,
            logger=self.logger,
            parse_json=True,
            new_chat=True
        )

        self.current_admission_date = basic_results.get('admission_date')
        self.current_discharge_date = basic_results.get('discharge_date')
        self.logger.debug(
            f"Basic info results:\n{pprint.pformat(basic_results)}")

        date_results = process_llm_query(
            model=self.model,
            prompt_obj=self.prompt_date_single,
            template_vars={'note': ner_results_text},
            prompt_json_debug=self.prompt_json_debug,
            logger=self.logger,
            parse_json=True,
            new_chat=True
        )
        self.logger.debug(
            f"Initial date results (before deduplication and normalization):\n{pprint.pformat(date_results)}")
        date_results = self.deduplication(date_results, 'tag', parsed_ner_tags)
        date_results = self.normalize_date_list(date_results)
        return DateData(basic_results=basic_results, date_results=date_results)

    def _process_subsequent_dates(self, ner_results_text: str, prev_ehr: str, parsed_ner_tags: list) -> DateData:
        date_results = process_llm_query(
            model=self.model,
            prompt_obj=self.prompt_date_multi,
            template_vars={
                'note': ner_results_text, 'prev_note': prev_ehr,
                'adm_date': self.current_admission_date, 'dis_date': self.current_discharge_date
            },
            prompt_json_debug=self.prompt_json_debug,
            logger=self.logger,
            parse_json=True,
            new_chat=True
        )
        self.logger.debug(
            f"Subsequent date results (before deduplication and normalization):\n{pprint.pformat(date_results)}")
        date_results = self.deduplication(date_results, 'tag', parsed_ner_tags)
        date_results = self.normalize_date_list(date_results)
        return DateData(basic_results=None, date_results=date_results)

    def process_dates(self, ehr: str, ner_results_text: str, prev_ehr: str | None,
                      parsed_ner_tags: list,
                      current_admission_date: str | None = None,
                      current_discharge_date: str | None = None) -> DateData:
        """Main method to process dates for a given EHR segment."""
        if current_admission_date:
            self.current_admission_date = current_admission_date
        if current_discharge_date:
            self.current_discharge_date = current_discharge_date

        if prev_ehr is None:
            date_data = self._process_initial_dates(
                ehr, ner_results_text, parsed_ner_tags)
        else:
            if not self.current_admission_date:
                self.logger.warning(
                    "Processing subsequent dates without an initial admission date. Date normalization might be affected.")
                basic_info_fallback = process_llm_query(
                    model=self.model,
                    prompt_obj=self.prompt_basic_info,
                    template_vars={'note': ehr},
                    prompt_json_debug=self.prompt_json_debug,
                    logger=self.logger,
                    parse_json=True,
                    new_chat=True
                )
                self.current_admission_date = basic_info_fallback.get(
                    'admission_date')
                self.current_discharge_date = basic_info_fallback.get(
                    'discharge_date')
                self.logger.info(
                    f"Fallback basic info from chunk: Adm: {self.current_admission_date}, Dis: {self.current_discharge_date}")

            date_data = self._process_subsequent_dates(
                ner_results_text, prev_ehr, parsed_ner_tags)

        return date_data
