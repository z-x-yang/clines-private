import logging
import re
import demjson3
import pprint

from data_types import NERData
# Import utility functions
from .processing_utils import parse_result, safe_json_decode, process_llm_query

# LLMManager, PROMPT will be passed during __init__


class NERProcessor:
    def __init__(self, model, prompt_ner, prompt_json_debug):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model = model  # LLMManager instance
        self.prompt_ner = prompt_ner
        self.prompt_json_debug = prompt_json_debug  # Used by utility process_llm_query

    # Removed duplicated helper methods: parse_result, safe_json_decode, _process_llm_query

    # Moved from PipelineCoordinator
    def parse_ner_result_text(self, string):
        """Processes the raw NER output string to update tags and extract entities."""
        # This method was originally parse_ner_result in PipelineCoordinator
        # It doesn't use the common helpers, so it remains here.
        matches = list(re.finditer(r'<([^<>]+)>(.*?)</\1>', string, re.DOTALL))
        valid_matches = []
        updated_string = string

        for match in matches[::-1]:  # Iterate backwards to handle string modifications
            if match.group(2).lower() not in ['none', 'null', '']:
                valid_matches.insert(0, match)
            else:
                # If entity is None/null, remove the tags and keep the content (which is None/null)
                start, end = match.span()
                content = match.group(2)
                updated_string = updated_string[:start] + \
                    content + updated_string[end:]

        if not valid_matches:
            return [], [], updated_string

        entities = [match.group(2) for match in valid_matches]
        old_tags = [match.group(1) for match in valid_matches]
        new_tags = [str(i + 1) for i in range(len(valid_matches))]

        # Create a list of replacements to apply them in reverse order of start position
        # to avoid index shifts due to tag length changes.
        replacements = []
        current_offset = 0
        temp_string_for_offsets = string  # original string to calculate offsets

        # First, just get the spans from the original string for accurate replacement later.
        # The valid_matches are already sorted by appearance.
        original_spans = [(match.start(), match.end(), match.group(
            1), new_tags[i]) for i, match in enumerate(valid_matches)]

        # Replace tags from right to left (or end of string to start)
        # The updated_string is modified in place.
        for start, end, old_tag_val, new_tag_val in reversed(original_spans):
            # Replace closing tag first
            updated_string = updated_string[:end - len(
                old_tag_val) - 3] + f'</{new_tag_val}>' + updated_string[end:]
            # Replace opening tag
            updated_string = updated_string[:start] + f'<{new_tag_val}>' + updated_string[start + len(
                old_tag_val) + 2: end - len(old_tag_val) - 3] + f'</{new_tag_val}>' + updated_string[end:]

        # A simpler way to reconstruct the string with new tags, if the above is too complex or buggy:
        # Iterate through valid_matches (which are in order of appearance)
        # Build the new string piece by piece.
        # This is less efficient but might be more robust if tag content itself can change length significantly.
        # For now, assuming the direct replacement approach works.

        # Re-verify updated_string construction if issues arise.
        # The critical part is that `updated_string` must reflect the text with `<new_tag>entity</new_tag>`
        # Let's refine the replacement logic to be safer.
        # We will build the string from parts based on original match locations.
        last_end = 0
        final_string_parts = []
        for i, match in enumerate(valid_matches):
            start, end = match.span()
            final_string_parts.append(string[last_end:start])
            final_string_parts.append(
                f'<{new_tags[i]}>{entities[i]}</{new_tags[i]}>')
            last_end = end
        final_string_parts.append(string[last_end:])
        updated_string = "".join(final_string_parts)

        changes_made = any(old != new for old, new in zip(old_tags, new_tags))
        if changes_made:
            self.logger.info("Tag corrections made in parse_ner_result_text:")
            for old, new in zip(old_tags, new_tags):
                if old != new:
                    self.logger.info(f"  Tag {old} -> {new}")

        return entities, new_tags, updated_string

    # Moved from PipelineCoordinator
    def parse_ner_context(self, ner_results_text_with_updated_tags: str, tag_list: list):
        """Extracts context around specified tags from the NER processed string."""
        # This method was originally parse_ner_context in PipelineCoordinator
        # It doesn't use the common helpers, so it remains here.
        result = []
        all_matches = {}

        # Find all entities based on the new, sequential tags
        for match in re.finditer(r'<(\d+)>(.*?)</\1>', ner_results_text_with_updated_tags, re.DOTALL):
            tag = match.group(1)
            if tag not in all_matches:  # Only consider the first occurrence if tags were duplicated before renumbering
                all_matches[tag] = match

        for tag_to_find in tag_list:  # tag_list contains the new, sequential tags
            # Ensure tag_to_find is a string for lookup
            match = all_matches.get(str(tag_to_find))
            if match:
                start, end = match.span()
                # Define context window more carefully
                context_start = max(0, start - 200)
                context_end = min(
                    len(ner_results_text_with_updated_tags), end + 200)

                # Extract raw context first
                context_segment = ner_results_text_with_updated_tags[context_start:context_end]

                # Remove *all* HTML-like tags from the context segment to clean it up
                cleaned_context = re.sub(r'<[^>]+>', '', context_segment)
                cleaned_context = cleaned_context.replace('\n', ' ').strip()
                result.append(cleaned_context)
            else:
                self.logger.warning(
                    f"Tag '{tag_to_find}' not found in NER output for context extraction.")
                result.append("")  # Append empty string if tag not found
        return result

    def process_ner(self, ehr_text: str) -> NERData:
        """Processes EHR text to identify named entities and their contexts."""
        # Use the utility function, passing self.model, self.logger, and self.prompt_json_debug
        ner_results_raw = process_llm_query(
            model=self.model,
            prompt_obj=self.prompt_ner,
            template_vars={'note': ehr_text},
            # Pass along for safe_json_decode in process_llm_query
            prompt_json_debug=self.prompt_json_debug,
            logger=self.logger,
            parse_json=False,  # NER endpoint for findentity returns tagged text, not JSON
            new_chat=True
        )
        self.logger.debug(f"Raw NER results:\n{ner_results_raw}")

        # parse_ner_result_text replaces the old parse_ner_result from PipelineCoordinator
        parsed_entities, parsed_tags, ner_results_text_updated = self.parse_ner_result_text(
            ner_results_raw)
        self.logger.debug(
            f"Parsed entities from NER: {pprint.pformat(parsed_entities)}")
        self.logger.debug(
            f"Parsed tags from NER: {pprint.pformat(parsed_tags)}")
        self.logger.debug(
            f"Updated NER results text:\n{ner_results_text_updated}")

        if not parsed_tags:
            self.logger.info("No entities found by NER processor.")
            return NERData(ner_results=ner_results_raw, parsed_results=[], parsed_tags=[], parsed_context=[])

        # parse_ner_context also moved from PipelineCoordinator
        parsed_context = self.parse_ner_context(
            ner_results_text_updated, parsed_tags)
        self.logger.debug(
            f"Parsed context from NER: {pprint.pformat(parsed_context)}")

        return NERData(
            # Store the text with corrected sequential tags
            ner_results=ner_results_text_updated,
            parsed_results=parsed_entities,
            parsed_tags=parsed_tags,  # These are the corrected sequential tags
            parsed_context=parsed_context
        )
