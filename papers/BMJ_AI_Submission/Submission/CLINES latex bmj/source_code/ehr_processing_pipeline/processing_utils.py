import re
import demjson3
import logging  # Added for safe_json_decode and process_llm_query
from typing import Any, Optional, List, Dict, Union

# Import the new data contracts system
from .data_contracts import (
    PromptContract, ProgressiveDegradationEngine, 
    OutputNormalizer, ContractRegistry
)

# No longer part of a class, so self is not used.
# model, prompt_json_debug, and logger will be passed as arguments where needed.


def parse_result(string):
    results = re.findall('```[^`]+```', string)
    if len(results) == 0:
        return string
    result = results[-1]
    result = result.strip('```').lstrip('json')
    result = result.replace('None', 'null')
    result = result.replace('"null"', 'null')
    result = result.replace('"NA"', 'null')
    result = result.replace('```', '')
    result = re.sub(r'\s*#.*$', '', result, flags=re.MULTILINE)
    result = re.sub(r'//.*?$|/\*.*?\*/', '', result,
                    flags=re.MULTILINE | re.DOTALL)
    return result


def safe_json_decode(json_string, model, prompt_json_debug, logger, max_retries=3):
    if max_retries > 0:
        try:
            output = demjson3.decode(json_string)
            return output
        except Exception as e:
            logger.error(f"Error decoding JSON: {e}")
            logger.debug(f"Problematic JSON string: {json_string}")
            logger.info(
                f"Retrying JSON decode... (remaining retries: {max_retries - 1})")
            debug_query = prompt_json_debug.apply_template(
                {'error_message': str(e), 'json_content': json_string})
            # model is now passed as an argument
            corrected_json_raw = model(debug_query)
            # Calls the utility parse_result
            corrected_json = parse_result(corrected_json_raw)
            logger.info(
                f"Attempting to decode corrected JSON: {corrected_json}")
            # Recursive call passes all necessary arguments
            return safe_json_decode(corrected_json, model, prompt_json_debug, logger, max_retries - 1)
    else:
        logger.error("Failed to decode JSON after multiple retries")
        raise Exception("Failed to decode JSON after multiple retries")


def smart_normalize_output(raw_output: Any, expected_type: str = "list_of_dicts", 
                          parsed_ner_tags: List[str] = None) -> Any:
    """
    Intelligently normalize LLM output, handling various exceptional cases
    
    Args:
        raw_output: Raw LLM output
        expected_type: Expected output type ('list_of_dicts', 'single_dict', 'text', 'date_array')
        parsed_ner_tags: List of parsed NER tags
        
    Returns:
        Normalized output
    """
    if expected_type == "list_of_dicts":
        return OutputNormalizer.normalize_to_list_of_dicts(raw_output, parsed_ner_tags)
    elif expected_type == "single_dict":
        return OutputNormalizer.normalize_to_single_dict(raw_output, parsed_ner_tags)
    elif expected_type == "text":
        return OutputNormalizer.normalize_to_text(raw_output, parsed_ner_tags)
    elif expected_type == "date_array":
        return OutputNormalizer.normalize_to_date_array(raw_output, parsed_ner_tags)
    else:
        return raw_output


def progressive_error_recovery(raw_output: Any, contract: PromptContract, 
                              input_text: str, parsed_ner_tags: List[str],
                              logger: logging.Logger) -> Any:
    """
    Recover from erroneous LLM output using progressive degradation strategy
    
    Args:
        raw_output: Raw LLM output
        contract: Data contract
        input_text: Input text
        parsed_ner_tags: Parsed NER tags
        logger: Logger instance
        
    Returns:
        Recovered output
    """
    engine = ProgressiveDegradationEngine(logger)
    return engine.process_with_degradation(
        raw_output, contract, input_text, parsed_ner_tags
    )


def process_llm_query(model, prompt_obj, template_vars, prompt_json_debug, logger, parse_json=True, new_chat=True):
    """
    Original process_llm_query function, maintaining backward compatibility
    """
    if new_chat:
        model.new_chat()
    query = prompt_obj.apply_template(template_vars)
    result = model(query)
    if parse_json:
        # Calls the utility parse_result
        parsed_result = parse_result(result)
        # Calls the utility safe_json_decode, passing necessary arguments
        return safe_json_decode(parsed_result, model, prompt_json_debug, logger)
    return result


def process_llm_query_with_contract(model, prompt_obj, template_vars, contract: PromptContract,
                                   prompt_json_debug, logger, parsed_ner_tags: List[str] = None,
                                   max_retry_levels: int = 3, new_chat: bool = True) -> Any:
    """
    Enhanced LLM query processing function using data contracts
    
    Args:
        model: LLM model instance
        prompt_obj: Prompt object
        template_vars: Template variables dictionary
        contract: Data contract
        prompt_json_debug: JSON debug prompt
        logger: Logger instance
        parsed_ner_tags: List of parsed NER tags
        max_retry_levels: Maximum retry levels
        new_chat: Whether to start new chat
        
    Returns:
        Type-safe processing result
    """
    logger.debug(f"Processing LLM query with contract: {contract.expected_output_type}")
    
    if new_chat:
        model.new_chat()
    
    # Execute LLM query
    query = prompt_obj.apply_template(template_vars)
    raw_result = model(query)
    
    # First attempt standard JSON parsing (if needed)
    if contract.expected_output_type in ["list_of_dicts", "single_dict", "date_array"]:
        try:
            parsed_result = parse_result(raw_result)
            decoded_result = safe_json_decode(parsed_result, model, prompt_json_debug, logger)
            
            # Use progressive degradation processing
            final_result = progressive_error_recovery(
                decoded_result, contract, template_vars.get('note', ''), 
                parsed_ner_tags, logger
            )
            
            logger.debug(f"Successfully processed with contract validation")
            return final_result
            
        except Exception as e:
            logger.error(f"Standard JSON processing failed: {e}")
            # Even if JSON parsing fails, attempt progressive degradation
            final_result = progressive_error_recovery(
                raw_result, contract, template_vars.get('note', ''), 
                parsed_ner_tags, logger
            )
            return final_result
    
    # For text type, return directly
    elif contract.expected_output_type == "text":
        return contract.normalizer(raw_result, parsed_ner_tags)
    
    # Default return raw result
    return raw_result


def get_contract_for_prompt(prompt_name: str) -> Optional[PromptContract]:
    """
    Get corresponding data contract based on prompt name
    
    Args:
        prompt_name: Prompt name (e.g., 'findstatus', 'findinfo')
        
    Returns:
        Corresponding data contract, or None if not found
    """
    contract_map = {
        'findstatus': ContractRegistry.get_findstatus_contract,
        'findinfo': ContractRegistry.get_findinfo_contract,
        'findrelated': ContractRegistry.get_findrelated_contract,
        'finddate_single': ContractRegistry.get_finddate_contract,
        'finddate_multi': ContractRegistry.get_finddate_contract,
        'recoverentity': ContractRegistry.get_recoverentity_contract,
        'basic_info': ContractRegistry.get_basic_info_contract,
    }
    
    if prompt_name in contract_map:
        return contract_map[prompt_name]()
    else:
        return None


def safe_deduplication_input(data: Any, logger: logging.Logger) -> List[Dict]:
    """
    Provide safe input validation and conversion for deduplication method
    
    Args:
        data: Input data
        logger: Logger instance
        
    Returns:
        Safe list of dictionaries
    """
    if isinstance(data, list):
        # Validate that all elements in the list are dictionaries
        safe_list = []
        for i, item in enumerate(data):
            if isinstance(item, dict):
                safe_list.append(item)
            else:
                logger.warning(f"Skipping non-dict item at index {i}: {type(item)}")
        return safe_list
    elif isinstance(data, dict):
        # Convert single dictionary to list
        logger.info("Converting single dict to list for deduplication")
        return [data]
    elif data is None:
        logger.warning("Received None input for deduplication, returning empty list")
        return []
    else:
        logger.error(f"Unsupported input type for deduplication: {type(data)}, returning empty list")
        return []
