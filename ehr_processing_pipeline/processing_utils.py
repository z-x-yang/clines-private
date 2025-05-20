import re
import demjson3
import logging  # Added for safe_json_decode and process_llm_query

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


def process_llm_query(model, prompt_obj, template_vars, prompt_json_debug, logger, parse_json=True, new_chat=True):
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
