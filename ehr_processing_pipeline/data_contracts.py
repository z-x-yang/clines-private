from dataclasses import dataclass
from typing import Any, List, Dict, Callable, Optional, Union
import logging
import re
import demjson3
import json
from copy import deepcopy


@dataclass
class PromptContract:
    """Data contract definition to ensure type safety of LLM outputs"""
    expected_output_type: str  # 'list_of_dicts', 'single_dict', 'text', 'date_array'
    required_fields: List[str]
    optional_fields: List[str]
    validator: Callable[[Any], bool]
    normalizer: Callable[[Any, List[str]], Any]
    fallback_generator: Callable[[str, List[str]], Any]


class OutputValidator:
    """Output type validators"""
    
    @staticmethod
    def validate_list_of_dicts(data: Any) -> bool:
        """Validate if data is a list of dictionaries"""
        if not isinstance(data, list):
            return False
        return all(isinstance(item, dict) for item in data)
    
    @staticmethod
    def validate_single_dict(data: Any) -> bool:
        """Validate if data is a single dictionary"""
        return isinstance(data, dict)
    
    @staticmethod
    def validate_text(data: Any) -> bool:
        """Validate if data is text"""
        return isinstance(data, str)
    
    @staticmethod
    def validate_date_array(data: Any) -> bool:
        """Validate if data is a date array"""
        if not isinstance(data, list):
            return False
        return len(data) == 2  # Should be an array of two dates


class OutputNormalizer:
    """Output format normalizers"""
    
    @staticmethod
    def normalize_to_list_of_dicts(data: Any, parsed_ner_tags: List[str] = None) -> List[Dict]:
        """Normalize various inputs to a list of dictionaries"""
        if isinstance(data, list):
            # If already a list, ensure all elements are dictionaries
            result = []
            for item in data:
                if isinstance(item, dict):
                    result.append(item)
                elif isinstance(item, str):
                    # Try to parse string as dictionary
                    try:
                        parsed_item = demjson3.decode(item)
                        if isinstance(parsed_item, dict):
                            result.append(parsed_item)
                    except:
                        pass
            return result
        elif isinstance(data, dict):
            # If single dictionary, wrap as list
            return [data]
        elif isinstance(data, str):
            # Try to parse string
            try:
                parsed = demjson3.decode(data)
                if isinstance(parsed, list):
                    return OutputNormalizer.normalize_to_list_of_dicts(parsed, parsed_ner_tags)
                elif isinstance(parsed, dict):
                    return [parsed]
            except:
                pass
        
        # If all attempts fail, return empty list
        return []
    
    @staticmethod
    def normalize_to_single_dict(data: Any, parsed_ner_tags: List[str] = None) -> Dict:
        """Normalize various inputs to a single dictionary"""
        if isinstance(data, dict):
            return data
        elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            return data[0]  # Take the first dictionary
        elif isinstance(data, str):
            try:
                parsed = demjson3.decode(data)
                if isinstance(parsed, dict):
                    return parsed
                elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                    return parsed[0]
            except:
                pass
        
        return {}
    
    @staticmethod
    def normalize_to_text(data: Any, parsed_ner_tags: List[str] = None) -> str:
        """Normalize various inputs to text"""
        if isinstance(data, str):
            return data
        elif isinstance(data, (dict, list)):
            return json.dumps(data, ensure_ascii=False)
        else:
            return str(data)
    
    @staticmethod
    def normalize_to_date_array(data: Any, parsed_ner_tags: List[str] = None) -> List[str]:
        """Normalize various inputs to date array"""
        if isinstance(data, list) and len(data) == 2:
            return [str(item) if item is not None else None for item in data]
        elif isinstance(data, str):
            try:
                parsed = demjson3.decode(data)
                if isinstance(parsed, list):
                    return OutputNormalizer.normalize_to_date_array(parsed, parsed_ner_tags)
            except:
                pass
        
        return [None, None]


class FallbackGenerator:
    """Fallback strategy generators"""
    
    @staticmethod
    def generate_status_fallback(input_text: str, parsed_ner_tags: List[str]) -> List[Dict]:
        """Generate fallback results for findstatus"""
        if not parsed_ner_tags:
            return []
        
        # Generate default "Present" status for each entity
        return [{"tag": tag, "assertion_status": "Present"} for tag in parsed_ner_tags]
    
    @staticmethod
    def generate_info_fallback(input_text: str, parsed_ner_tags: List[str]) -> List[Dict]:
        """Generate fallback results for findinfo"""
        if not parsed_ner_tags:
            return []
        
        # Generate minimal structure for each entity
        return [{"tag": tag} for tag in parsed_ner_tags]
    
    @staticmethod
    def generate_related_fallback(input_text: str, parsed_ner_tags: List[str]) -> List[Dict]:
        """Generate fallback results for findrelated"""
        if not parsed_ner_tags:
            return []
        
        # Generate entity list with no relationships
        return [{"tag": tag, "related": {}} for tag in parsed_ner_tags]
    
    @staticmethod
    def generate_date_fallback(input_text: str, parsed_ner_tags: List[str]) -> List[Dict]:
        """Generate fallback results for finddate"""
        if not parsed_ner_tags:
            return []
        
        # Generate unknown dates for each entity
        return [{"tag": tag, "date": [None, None], "inferred": [False, False]} for tag in parsed_ner_tags]
    
    @staticmethod
    def generate_entity_fallback(input_text: str, parsed_ner_tags: List[str]) -> List[Dict]:
        """Generate fallback results for recoverentity"""
        if not parsed_ner_tags:
            return []
        
        # Generate cleaned labels for each entity
        return [{"TAG": tag, "CLEAN": f"Entity_{tag}"} for tag in parsed_ner_tags]
    
    @staticmethod
    def generate_basic_info_fallback(input_text: str, parsed_ner_tags: List[str]) -> Dict:
        """Generate fallback results for basic_info"""
        return {
            "admission_date": None,
            "discharge_date": None,
            "gender": None,
            "death_date": None,
            "birth_date": None,
            "race": None,
            "ethnicity": None,
            "zip_code": None
        }


class ContractRegistry:
    """Registry of predefined data contracts"""
    
    @staticmethod
    def get_findstatus_contract() -> PromptContract:
        return PromptContract(
            expected_output_type="list_of_dicts",
            required_fields=["tag", "assertion_status"],
            optional_fields=[],
            validator=OutputValidator.validate_list_of_dicts,
            normalizer=OutputNormalizer.normalize_to_list_of_dicts,
            fallback_generator=FallbackGenerator.generate_status_fallback
        )
    
    @staticmethod
    def get_findinfo_contract() -> PromptContract:
        return PromptContract(
            expected_output_type="list_of_dicts",
            required_fields=["tag"],
            optional_fields=["body_location", "value", "unit", "infer", "note", "route", "freq", "other"],
            validator=OutputValidator.validate_list_of_dicts,
            normalizer=OutputNormalizer.normalize_to_list_of_dicts,
            fallback_generator=FallbackGenerator.generate_info_fallback
        )
    
    @staticmethod
    def get_findrelated_contract() -> PromptContract:
        return PromptContract(
            expected_output_type="list_of_dicts",
            required_fields=["tag", "related"],
            optional_fields=[],
            validator=OutputValidator.validate_list_of_dicts,
            normalizer=OutputNormalizer.normalize_to_list_of_dicts,
            fallback_generator=FallbackGenerator.generate_related_fallback
        )
    
    @staticmethod
    def get_finddate_contract() -> PromptContract:
        return PromptContract(
            expected_output_type="list_of_dicts",
            required_fields=["tag", "date", "inferred"],
            optional_fields=[],
            validator=OutputValidator.validate_list_of_dicts,
            normalizer=OutputNormalizer.normalize_to_list_of_dicts,
            fallback_generator=FallbackGenerator.generate_date_fallback
        )
    
    @staticmethod
    def get_recoverentity_contract() -> PromptContract:
        return PromptContract(
            expected_output_type="list_of_dicts",
            required_fields=["TAG", "CLEAN"],
            optional_fields=[],
            validator=OutputValidator.validate_list_of_dicts,
            normalizer=OutputNormalizer.normalize_to_list_of_dicts,
            fallback_generator=FallbackGenerator.generate_entity_fallback
        )
    
    @staticmethod
    def get_basic_info_contract() -> PromptContract:
        return PromptContract(
            expected_output_type="single_dict",
            required_fields=["admission_date", "discharge_date", "gender", "death_date", "birth_date", "race", "ethnicity", "zip_code"],
            optional_fields=[],
            validator=OutputValidator.validate_single_dict,
            normalizer=OutputNormalizer.normalize_to_single_dict,
            fallback_generator=FallbackGenerator.generate_basic_info_fallback
        )


class ProgressiveDegradationEngine:
    """Progressive degradation processing engine"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def process_with_degradation(self, raw_output: Any, contract: PromptContract, 
                                input_text: str, parsed_ner_tags: List[str] = None,
                                max_levels: int = 4) -> Any:
        """
        Process output using progressive degradation strategy
        
        Level 0: Normal validation passes
        Level 1: Attempt normalization
        Level 2: Partial data extraction
        Level 3: Use fallback generator
        Level 4: Return minimal structure
        """
        
        # Level 0: Normal validation
        if contract.validator(raw_output):
            self.logger.debug("Output validation passed at Level 0 (perfect)")
            return raw_output
        
        # Level 1: Attempt normalization
        try:
            normalized = contract.normalizer(raw_output, parsed_ner_tags)
            if contract.validator(normalized):
                self.logger.info("Output recovered at Level 1 (normalization)")
                return normalized
        except Exception as e:
            self.logger.warning(f"Level 1 normalization failed: {e}")
        
        # Level 2: Attempt partial extraction
        try:
            partial_result = self._extract_partial_data(raw_output, contract, parsed_ner_tags)
            if partial_result and contract.validator(partial_result):
                self.logger.warning("Output recovered at Level 2 (partial extraction)")
                return partial_result
        except Exception as e:
            self.logger.warning(f"Level 2 partial extraction failed: {e}")
        
        # Level 3: Use fallback generator
        try:
            fallback_result = contract.fallback_generator(input_text, parsed_ner_tags or [])
            if contract.validator(fallback_result):
                self.logger.error("Output recovered at Level 3 (fallback generation)")
                return fallback_result
        except Exception as e:
            self.logger.error(f"Level 3 fallback generation failed: {e}")
        
        # Level 4: Return minimal structure
        self.logger.critical("All recovery levels failed, returning minimal structure")
        return self._get_minimal_structure(contract.expected_output_type)
    
    def _extract_partial_data(self, raw_output: Any, contract: PromptContract, 
                             parsed_ner_tags: List[str]) -> Any:
        """Attempt to extract partial useful data from corrupted output"""
        if isinstance(raw_output, str):
            # Try to extract JSON fragments from string
            json_fragments = re.findall(r'\{[^{}]*\}|\[[^\[\]]*\]', raw_output)
            for fragment in json_fragments:
                try:
                    parsed = demjson3.decode(fragment)
                    normalized = contract.normalizer(parsed, parsed_ner_tags)
                    if normalized:
                        return normalized
                except:
                    continue
        
        return None
    
    def _get_minimal_structure(self, output_type: str) -> Any:
        """Return minimal usable structure"""
        if output_type == "list_of_dicts":
            return []
        elif output_type == "single_dict":
            return {}
        elif output_type == "text":
            return ""
        elif output_type == "date_array":
            return [None, None]
        else:
            return None 