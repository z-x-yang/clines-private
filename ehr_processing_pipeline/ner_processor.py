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
    def parse_ner_result_text(self, string, original_ehr_text, chunk_offset=0):
        """Processes the raw NER output string to update tags and extract entities with positions."""
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
            return [], [], updated_string, []

        entities = [match.group(2) for match in valid_matches]
        old_tags = [match.group(1) for match in valid_matches]
        new_tags = [str(i + 1) for i in range(len(valid_matches))]

        # Calculate positions of entities in the original EHR text
        entity_positions = []
        for match in valid_matches:
            entity_text = match.group(2).strip()

            # First try to find in the current chunk to get relative position
            # Remove all tags from chunk
            chunk_string = re.sub(r'<[^>]+>', '', string)
            chunk_pos = chunk_string.lower().find(entity_text.lower())

            if chunk_pos != -1:
                # Calculate absolute position by adding chunk offset
                absolute_start_pos = chunk_offset + chunk_pos
                absolute_end_pos = absolute_start_pos + len(entity_text)

                # Verify the position is correct in the original text
                if (absolute_start_pos >= 0 and
                    absolute_end_pos <= len(original_ehr_text) and
                        original_ehr_text[absolute_start_pos:absolute_end_pos].lower() == entity_text.lower()):
                    entity_positions.append(
                        (absolute_start_pos, absolute_end_pos))
                    self.logger.debug(
                        f"Found entity '{entity_text}' at position {absolute_start_pos}-{absolute_end_pos} in original document")
                else:
                    # Fallback: search in the original document directly
                    fallback_pos = original_ehr_text.lower().find(entity_text.lower())
                    if fallback_pos != -1:
                        fallback_end = fallback_pos + len(entity_text)
                        entity_positions.append((fallback_pos, fallback_end))
                        self.logger.warning(
                            f"Used fallback search for entity '{entity_text}' at position {fallback_pos}-{fallback_end}")
                    else:
                        self.logger.warning(
                            f"Could not find position for entity '{entity_text}' in original text")
                        entity_positions.append((-1, -1))  # Mark as not found
            else:
                # If not found in chunk, try direct search in original
                start_pos = original_ehr_text.lower().find(entity_text.lower())
                if start_pos != -1:
                    end_pos = start_pos + len(entity_text)
                    entity_positions.append((start_pos, end_pos))
                    self.logger.debug(
                        f"Found entity '{entity_text}' at position {start_pos}-{end_pos} via direct search")
                else:
                    self.logger.warning(
                        f"Could not find exact position for entity '{entity_text}' in original text")
                    entity_positions.append((-1, -1))  # Mark as not found

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

        return entities, new_tags, updated_string, entity_positions

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

    def process_ner(self, ehr_text: str, original_ehr_text: str = None, chunk_offset: int = 0) -> NERData:
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

        # Use original_ehr_text if provided, otherwise use the current chunk text
        text_for_position_calculation = original_ehr_text or ehr_text

        # parse_ner_result_text replaces the old parse_ner_result from PipelineCoordinator
        parsed_entities, parsed_tags, ner_results_text_updated, entity_positions = self.parse_ner_result_text(
            ner_results_raw, text_for_position_calculation, chunk_offset)
        self.logger.debug(
            f"Parsed entities from NER: {pprint.pformat(parsed_entities)}")
        self.logger.debug(
            f"Parsed tags from NER: {pprint.pformat(parsed_tags)}")
        self.logger.debug(
            f"Entity positions: {pprint.pformat(entity_positions)}")
        self.logger.debug(
            f"Updated NER results text:\n{ner_results_text_updated}")

        if not parsed_tags:
            self.logger.info("No entities found by NER processor.")
            return NERData(ner_results=ner_results_raw, parsed_results=[], parsed_tags=[], parsed_context=[], parsed_positions=[])

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
            parsed_context=parsed_context,
            parsed_positions=entity_positions
        )
