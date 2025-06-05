import json
import re
import logging
import demjson3
import pprint
from difflib import SequenceMatcher
from core.data_types import NERData
# Import utility functions
from .processing_utils import parse_result, safe_json_decode, process_llm_query
from typing import List, Tuple

# LLMManager, PROMPT will be passed during __init__


class NERProcessor:
    def __init__(self, model, prompt_ner, prompt_json_debug):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model = model  # LLMManager instance
        self.prompt_ner = prompt_ner
        self.prompt_json_debug = prompt_json_debug  # Used by utility process_llm_query
        
        # Strategy performance statistics
        self.strategy_stats = {
            'context_exact': {'attempts': 0, 'successes': 0},
            'context_fuzzy': {'attempts': 0, 'successes': 0},
            'direct_search': {'attempts': 0, 'successes': 0},
            'chunk_fallback': {'attempts': 0, 'successes': 0},
            'simple_fallback': {'attempts': 0, 'successes': 0},
            'total_entities': 0,
            'successful_matches': 0,
            # New multi-level statistics
            'normalization_levels': {
                1: {'attempts': 0, 'successes': 0},
                2: {'attempts': 0, 'successes': 0},
                3: {'attempts': 0, 'successes': 0},
                4: {'attempts': 0, 'successes': 0}
            },
            'punctuation_variants_used': 0
        }

    # Removed duplicated helper methods: parse_result, safe_json_decode, _process_llm_query

    def _create_normalized_mapping(self, text):
        """Create normalized text and position mapping for robust entity matching."""
        normalized_text = ''
        pos_mapping = {}
        orig_pos = 0
        norm_pos = 0
        
        # Build normalized text and position mapping
        for char in text:
            if not char.isspace():
                normalized_text += char
                pos_mapping[norm_pos] = orig_pos
                norm_pos += 1
            orig_pos += 1
            
        return normalized_text, pos_mapping

    def _normalize_text_for_matching(self, text, level=1):
        """
        Multi-level text normalization for robust entity matching.
        
        Args:
            text (str): Input text to normalize
            level (int): Normalization level (1-4)
                1: Remove whitespace only
                2: Remove whitespace + lowercase
                3: Remove whitespace + lowercase + remove punctuation
                4: Remove whitespace + lowercase + punctuation to space
        
        Returns:
            str: Normalized text
        """
        if not text:
            return ""
            
        if level == 1:
            # Level 1: Remove whitespace only (current implementation)
            return ''.join(char for char in text if not char.isspace())
            
        elif level == 2:
            # Level 2: Remove whitespace + lowercase
            return ''.join(char for char in text.lower() if not char.isspace())
            
        elif level == 3:
            # Level 3: Remove whitespace + lowercase + remove punctuation
            import string
            normalized = ''.join(char for char in text.lower() if not char.isspace())
            return normalized.translate(str.maketrans('', '', string.punctuation))
            
        elif level == 4:
            # Level 4: Remove whitespace + lowercase + punctuation to space
            import string
            # First replace common punctuation with spaces
            text_with_spaces = text.lower()
            for punct in '-_./\\':
                text_with_spaces = text_with_spaces.replace(punct, ' ')
            # Then remove remaining punctuation and normalize spaces
            cleaned = ''.join(char for char in text_with_spaces if not char.isspace())
            return cleaned
            
        else:
            # Default to level 1
            return self._normalize_text_for_matching(text, 1)

    def _smart_punctuation_handler(self, text):
        """
        Intelligent punctuation handling for medical terminology.
        
        Handles common patterns in medical text:
        - Hyphens in disease names: COVID-19 -> COVID 19
        - Underscores: vitamin_D -> vitamin D  
        - Multiple punctuation: diabetes-mellitus, -> diabetes mellitus
        - Medical abbreviations: type-2 -> type 2
        
        Args:
            text (str): Input text
            
        Returns:
            str: Text with smart punctuation handling
        """
        if not text:
            return ""
            
        # Create multiple variants of the text with different punctuation handling
        variants = []
        
        # Original text
        variants.append(text)
        
        # Replace hyphens and underscores with spaces
        variant1 = text.replace('-', ' ').replace('_', ' ')
        if variant1 != text:
            variants.append(variant1)
            
        # Replace hyphens with nothing (for cases like "type-2" -> "type2")
        variant2 = text.replace('-', '').replace('_', '')
        if variant2 != text and variant2 != variant1:
            variants.append(variant2)
            
        # Remove all punctuation except numbers and letters
        import string
        variant3 = ''.join(char if char.isalnum() or char.isspace() else ' ' for char in text)
        # Clean up multiple spaces
        variant3 = ' '.join(variant3.split())
        if variant3 not in variants:
            variants.append(variant3)
            
        return variants

    def _fuzzy_match_context(self, context, normalized_note, threshold=0.3):
        """Use fuzzy matching to find context in normalized note when exact match fails."""
        normalized_context = ''.join(char for char in context if not char.isspace())
        window_size = len(normalized_context)
        
        if window_size == 0:
            return -1, normalized_context
            
        best_ratio = 0
        best_pos = -1
        best_window = ''
        
        # Pre-process for case-insensitive comparison
        normalized_context_lower = normalized_context.lower()
        normalized_note_lower = normalized_note.lower()
        
        # Search for best matching window with case-insensitive comparison
        for i in range(len(normalized_note) - window_size + 1):
            window = normalized_note[i:i + window_size]
            window_lower = normalized_note_lower[i:i + window_size]
            
            # Try both case-sensitive and case-insensitive matching
            ratio_case_sensitive = SequenceMatcher(None, window, normalized_context).ratio()
            ratio_case_insensitive = SequenceMatcher(None, window_lower, normalized_context_lower).ratio()
            
            # Use the better ratio
            ratio = max(ratio_case_sensitive, ratio_case_insensitive)
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_pos = i
                best_window = window
        
        # Return results if above threshold
        if best_ratio >= threshold:
            self.logger.debug(f"Fuzzy match found with ratio {best_ratio:.3f} (threshold: {threshold})")
            return best_pos, best_window
        else:
            self.logger.debug(f"Fuzzy match ratio {best_ratio:.3f} below threshold {threshold}")
            return -1, normalized_context

    def _improved_position_verification(self, entity, original_text, start_pos, end_pos):
        """Enhanced position verification with better handling of special characters and punctuation."""
        if start_pos < 0 or end_pos < 0 or start_pos >= len(original_text) or end_pos > len(original_text):
            self.logger.debug(f"Position out of bounds: start={start_pos}, end={end_pos}, text_len={len(original_text)}")
            return False
            
        if start_pos >= end_pos:
            self.logger.debug(f"Invalid position range: start={start_pos} >= end={end_pos}")
            return False
            
        try:
            found_text = original_text[start_pos:end_pos]
            
            # Normalize both texts for comparison
            normalized_entity = ''.join(char for char in entity if not char.isspace())
            normalized_found = ''.join(char for char in found_text if not char.isspace())
            
            # Case-insensitive comparison
            if normalized_found.lower() == normalized_entity.lower():
                self.logger.debug(f"Position verification successful: '{found_text}' matches '{entity}'")
                return True
            
            # Handle potential punctuation differences
            # Remove common punctuation for comparison
            import string
            translator = str.maketrans('', '', string.punctuation)
            cleaned_entity = normalized_entity.translate(translator).lower()
            cleaned_found = normalized_found.translate(translator).lower()
            
            if cleaned_entity == cleaned_found:
                self.logger.debug(f"Position verification successful after punctuation removal: '{found_text}' matches '{entity}'")
                return True
                
            self.logger.debug(f"Position verification failed: '{found_text}' does not match '{entity}'")
            return False
            
        except Exception as e:
            self.logger.debug(f"Error in position verification: {e}")
            return False

    def _find_entity_in_context(self, entity, context, context_pos, pos_mapping):
        """Find entity position within the located context with improved verification and punctuation handling."""
        
        # Try multi-level matching within context
        entity_variants = self._smart_punctuation_handler(entity)
        
        for level in range(1, 4):  # Try levels 1-3 for context matching
            normalized_context = self._normalize_text_for_matching(context, level)
            
            for variant in entity_variants:
                normalized_entity = self._normalize_text_for_matching(variant, level)
                
                if not normalized_entity:
                    continue
                
                # Case-insensitive entity search in context
                entity_relative_pos = normalized_context.find(normalized_entity)
                
                if entity_relative_pos != -1:
                    self.logger.debug(f"Found entity variant '{variant}' in context using level {level}")
                    
                    try:
                        # Calculate absolute position
                        absolute_norm_pos = context_pos + entity_relative_pos
                        start_pos = pos_mapping[absolute_norm_pos]
                        
                        # Calculate end position by mapping from normalized to original text
                        end_norm_pos = absolute_norm_pos + len(normalized_entity) - 1
                        if end_norm_pos in pos_mapping:
                            end_pos = pos_mapping[end_norm_pos] + 1
                        else:
                            # Fallback: estimate end position
                            end_pos = start_pos + len(entity)
                        
                        return start_pos, end_pos
                        
                    except (KeyError, IndexError) as e:
                        self.logger.debug(f"Error calculating entity position: {e}")
                        continue
        
        # If multi-level approach fails, try the original approach
        normalized_entity = ''.join(char for char in entity if not char.isspace())
        normalized_context = ''.join(char for char in context if not char.isspace())
        
        entity_relative_pos = normalized_context.lower().find(normalized_entity.lower())
        
        if entity_relative_pos == -1:
            self.logger.debug(f"Entity '{entity}' not found in context (case-insensitive)")
            return -1, -1
            
        try:
            # Calculate absolute position
            absolute_norm_pos = context_pos + entity_relative_pos
            start_pos = pos_mapping[absolute_norm_pos]
            
            # Calculate end position by mapping from normalized to original text
            end_norm_pos = absolute_norm_pos + len(normalized_entity) - 1
            if end_norm_pos in pos_mapping:
                end_pos = pos_mapping[end_norm_pos] + 1
            else:
                # Fallback: estimate end position
                end_pos = start_pos + len(entity)
            
            return start_pos, end_pos
                    
        except (KeyError, IndexError) as e:
            self.logger.debug(f"Error calculating entity position: {e}")
            return -1, -1

    def _calculate_entity_position(self, entity, normalized_note, pos_mapping, original_text):
        """Calculate entity position using multi-level search with case-insensitive support."""
        
        # First try the new multi-level search
        start_pos, end_pos, level_used = self._multi_level_entity_search(entity, normalized_note, pos_mapping, original_text)
        
        if start_pos != -1 and end_pos != -1:
            self.logger.debug(f"Multi-level search successful using level {level_used}")
            return start_pos, end_pos
            
        # Fallback to original implementation
        self.logger.debug(f"Multi-level search failed, trying original method")
        normalized_entity = ''.join(char for char in entity if not char.isspace())
        
        # Case-insensitive direct search in normalized note
        entity_pos = normalized_note.lower().find(normalized_entity.lower())
        if entity_pos == -1:
            self.logger.debug(f"Entity '{entity}' not found in normalized text (case-insensitive)")
            return -1, -1
            
        try:
            start_pos = pos_mapping[entity_pos]
            
            # Calculate end position by counting non-space characters
            entity_chars = 0
            end_pos = start_pos
            
            while entity_chars < len(normalized_entity) and end_pos < len(original_text):
                if not original_text[end_pos].isspace():
                    entity_chars += 1
                end_pos += 1
                
            # Enhanced verification with case-insensitive comparison
            found_text = original_text[start_pos:end_pos]
            normalized_found = ''.join(char for char in found_text if not char.isspace())
            
            if normalized_found.lower() == normalized_entity.lower():
                self.logger.debug(f"Case-insensitive match verified for '{entity}'")
                return start_pos, end_pos
            else:
                self.logger.debug(f"Verification failed: found '{normalized_found}' instead of '{normalized_entity}' (case-insensitive)")
                return -1, -1
                
        except (KeyError, IndexError) as e:
            self.logger.debug(f"Error in direct position calculation: {e}")
            return -1, -1

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

        # Calculate positions of entities in the original EHR text using robust matching
        entity_positions = []
        
        # Create normalized mapping for the original text
        normalized_note, pos_mapping = self._create_normalized_mapping(original_ehr_text)
        
        # Extract clean chunk text for context-based matching
        chunk_string = re.sub(r'<[^>]+>', '', string)
        
        for i, match in enumerate(valid_matches):
            entity_text = match.group(2).strip()
            self.logger.debug(f"Processing entity '{entity_text}' using robust matching")
            
            # Improved context extraction around the entity from the chunk
            # Calculate exact position of entity text within the cleaned chunk
            entity_in_original_chunk = match.group(2)
            entity_start_in_original = match.start(2)  # Start of entity content (excluding tags)
            
            # Remove all tags to get clean chunk and calculate relative position
            clean_chunk = re.sub(r'<[^>]+>', '', string)
            
            # Calculate how much text was removed before this entity due to tag removal
            text_before_entity = string[:entity_start_in_original]
            tags_before = re.findall(r'<[^>]+>', text_before_entity)
            chars_removed = sum(len(tag) for tag in tags_before)
            entity_start_in_clean_chunk = entity_start_in_original - chars_removed
            
            # Extract context with improved boundaries
            context_window = 150  # Increased context window
            context_start = max(0, entity_start_in_clean_chunk - context_window)
            context_end = min(len(clean_chunk), entity_start_in_clean_chunk + len(entity_text) + context_window)
            context = clean_chunk[context_start:context_end]
            
            start_pos = -1
            end_pos = -1
            
            # Strategy 1: Context-based exact matching with improved context
            if context and len(context.strip()) > 0:
                self.strategy_stats['context_exact']['attempts'] += 1
                normalized_context = ''.join(char for char in context if not char.isspace())
                context_pos = normalized_note.find(normalized_context)
                
                if context_pos != -1:
                    self.logger.debug(f"Found context using exact matching")
                    start_pos, end_pos = self._find_entity_in_context(entity_text, context, context_pos, pos_mapping)
                    
                    # Verify position using improved verification
                    if start_pos != -1 and end_pos != -1:
                        if self._improved_position_verification(entity_text, original_ehr_text, start_pos, end_pos):
                            self.strategy_stats['context_exact']['successes'] += 1
                        else:
                            self.logger.debug(f"Position verification failed, trying next strategy")
                            start_pos, end_pos = -1, -1
                    
                # Strategy 2: Context-based fuzzy matching with improved parameters
                if start_pos == -1:
                    self.strategy_stats['context_fuzzy']['attempts'] += 1
                    self.logger.debug(f"Trying fuzzy context matching")
                    fuzzy_pos, fuzzy_context = self._fuzzy_match_context(context, normalized_note)
                    if fuzzy_pos != -1:
                        start_pos, end_pos = self._find_entity_in_context(entity_text, fuzzy_context, fuzzy_pos, pos_mapping)
                        
                        # Verify fuzzy match result
                        if start_pos != -1 and end_pos != -1:
                            if self._improved_position_verification(entity_text, original_ehr_text, start_pos, end_pos):
                                self.strategy_stats['context_fuzzy']['successes'] += 1
                            else:
                                self.logger.debug(f"Fuzzy match verification failed, trying next strategy")
                                start_pos, end_pos = -1, -1
            
            # Strategy 3: Direct entity search in normalized text
            if start_pos == -1:
                self.strategy_stats['direct_search']['attempts'] += 1
                self.logger.debug(f"Trying direct entity search")
                start_pos, end_pos = self._calculate_entity_position(entity_text, normalized_note, pos_mapping, original_ehr_text)
                
                # Verify direct search result
                if start_pos != -1 and end_pos != -1:
                    if self._improved_position_verification(entity_text, original_ehr_text, start_pos, end_pos):
                        self.strategy_stats['direct_search']['successes'] += 1
                    else:
                        self.logger.debug(f"Direct search verification failed, trying next strategy")
                        start_pos, end_pos = -1, -1
            
            # Strategy 4: Original fallback with chunk offset (for chunk-based processing)
            if start_pos == -1 and chunk_offset > 0:
                self.strategy_stats['chunk_fallback']['attempts'] += 1
                self.logger.debug(f"Trying chunk-based fallback")
                chunk_pos = clean_chunk.lower().find(entity_text.lower())  # Case-insensitive
                if chunk_pos != -1:
                    absolute_start_pos = chunk_offset + chunk_pos
                    absolute_end_pos = absolute_start_pos + len(entity_text)
                    
                    # Verify chunk-based position
                    if (absolute_start_pos >= 0 and absolute_end_pos <= len(original_ehr_text)):
                        if self._improved_position_verification(entity_text, original_ehr_text, absolute_start_pos, absolute_end_pos):
                            start_pos, end_pos = absolute_start_pos, absolute_end_pos
                            self.strategy_stats['chunk_fallback']['successes'] += 1
                         
            # Strategy 5: Simple fallback search with improved verification
            if start_pos == -1:
                self.strategy_stats['simple_fallback']['attempts'] += 1
                self.logger.debug(f"Trying simple fallback search")
                fallback_pos = original_ehr_text.lower().find(entity_text.lower())  # Case-insensitive
                if fallback_pos != -1:
                    potential_start = fallback_pos
                    potential_end = fallback_pos + len(entity_text)
                    
                    # Verify fallback position
                    if self._improved_position_verification(entity_text, original_ehr_text, potential_start, potential_end):
                        start_pos = potential_start
                        end_pos = potential_end
                        self.strategy_stats['simple_fallback']['successes'] += 1
            
            # Log results and update statistics
            self.strategy_stats['total_entities'] += 1
            
            if start_pos != -1 and end_pos != -1:
                entity_positions.append((start_pos, end_pos))
                self.strategy_stats['successful_matches'] += 1
                self.logger.debug(f"Successfully found entity '{entity_text}' at position {start_pos}-{end_pos}")
            else:
                entity_positions.append((-1, -1))
                self.logger.warning(f"Could not find position for entity '{entity_text}' using any strategy")

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

    def get_strategy_statistics(self):
        """Get detailed statistics about strategy performance."""
        stats = self.strategy_stats.copy()
        
        # Calculate success rates
        for strategy in ['context_exact', 'context_fuzzy', 'direct_search', 'chunk_fallback', 'simple_fallback']:
            attempts = stats[strategy]['attempts']
            successes = stats[strategy]['successes']
            stats[strategy]['success_rate'] = (successes / attempts * 100) if attempts > 0 else 0
        
        # Overall success rate
        total_entities = stats['total_entities']
        successful_matches = stats['successful_matches']
        stats['overall_success_rate'] = (successful_matches / total_entities * 100) if total_entities > 0 else 0
        
        return stats

    def log_strategy_statistics(self):
        """Log comprehensive strategy performance statistics."""
        stats = self.get_strategy_statistics()
        
        self.logger.info("=== Entity Matching Strategy Statistics ===")
        self.logger.info(f"Total entities processed: {stats['total_entities']}")
        self.logger.info(f"Successfully matched: {stats['successful_matches']}")
        self.logger.info(f"Overall success rate: {stats['overall_success_rate']:.1f}%")
        self.logger.info("")
        
        self.logger.info("Strategy-specific performance:")
        for strategy in ['context_exact', 'context_fuzzy', 'direct_search', 'chunk_fallback', 'simple_fallback']:
            attempts = stats[strategy]['attempts']
            successes = stats[strategy]['successes']
            rate = stats[strategy]['success_rate']
            self.logger.info(f"  {strategy.replace('_', ' ').title()}: {successes}/{attempts} ({rate:.1f}%)")
        
        self.logger.info("============================================")

    def _multi_level_entity_search(self, entity, normalized_note, pos_mapping, original_text):
        """
        Multi-level entity search with progressive normalization.
        
        Tries multiple normalization levels and punctuation variants.
        """
        # Get punctuation variants of the entity
        entity_variants = self._smart_punctuation_handler(entity)
        
        # Try different normalization levels
        for level in range(1, 5):
            self.logger.debug(f"Trying normalization level {level}")
            
            # For level 1, use existing normalized note and mapping
            if level == 1:
                note_normalized = normalized_note
                level_pos_mapping = pos_mapping
            else:
                # For higher levels, we need a different approach
                # Let's search in the original text using smart matching
                for variant in entity_variants:
                    # Apply the same normalization to both text and entity
                    original_normalized = self._normalize_text_for_matching(original_text, level)
                    variant_normalized = self._normalize_text_for_matching(variant, level)
                    
                    if not variant_normalized:
                        continue
                        
                    # Find position in normalized text
                    entity_pos = original_normalized.find(variant_normalized)
                    
                    if entity_pos != -1:
                        # Now we need to map back to original position
                        # Use a different approach: find the position by counting characters
                        start_pos = self._find_original_position(original_text, variant, level)
                        
                        if start_pos != -1:
                            end_pos = start_pos + len(variant)
                            
                            # Adjust end position to account for the actual text length
                            while end_pos < len(original_text) and original_text[end_pos].isspace():
                                end_pos += 1
                            if end_pos > start_pos + len(variant):
                                end_pos = start_pos + len(variant)
                                
                            # Verify the match
                            if self._improved_position_verification(entity, original_text, start_pos, end_pos):
                                self.logger.debug(f"Found '{variant}' using level {level} normalization")
                                return start_pos, end_pos, level
        
        return -1, -1, 0

    def _find_original_position(self, original_text, entity_variant, level):
        """
        Find the original position of entity variant in text using smart matching.
        """
        # Normalize both text and entity
        normalized_text = self._normalize_text_for_matching(original_text, level)
        normalized_entity = self._normalize_text_for_matching(entity_variant, level)
        
        # Find position in normalized text
        norm_pos = normalized_text.find(normalized_entity)
        if norm_pos == -1:
            return -1
            
        # Map back to original position by walking through the text
        char_count = 0
        for i, char in enumerate(original_text):
            if level == 1:
                if not char.isspace():
                    if char_count == norm_pos:
                        return i
                    char_count += 1
            elif level == 2:
                if not char.isspace():
                    if char_count == norm_pos:
                        return i
                    char_count += 1
            elif level >= 3:
                # For level 3+, we need to account for punctuation removal
                processed_char = char
                if level == 4:
                    # Replace punctuation with space first
                    if char in '-_./\\':
                        processed_char = ' '
                
                if level == 3:
                    import string
                    if not char.isspace() and char not in string.punctuation:
                        if char_count == norm_pos:
                            return i
                        char_count += 1
                elif level == 4:
                    if not processed_char.isspace():
                        if char_count == norm_pos:
                            return i
                        char_count += 1
                        
        return -1

    def _create_enhanced_normalized_mapping(self, text, level=1):
        """
        Create enhanced normalized text and position mapping for robust entity matching.
        
        Args:
            text (str): Input text to normalize
            level (int): Normalization level (1-4)
        
        Returns:
            tuple: (normalized_text, pos_mapping)
        """
        if level == 1:
            # Use existing implementation for level 1
            return self._create_normalized_mapping(text)
            
        # For higher levels, we need a more complex mapping approach
        normalized_text = ''
        pos_mapping = {}
        orig_pos = 0
        norm_pos = 0
        
        # Process text based on normalization level
        processed_text = self._normalize_text_for_matching(text, level)
        
        # Create a simple mapping for higher levels
        # This is a simplified approach - in practice, higher level mappings are more complex
        current_norm_pos = 0
        for orig_pos, char in enumerate(text):
            if current_norm_pos < len(processed_text):
                # Map each position in normalized text back to original
                pos_mapping[current_norm_pos] = orig_pos
                current_norm_pos += 1
                
        return processed_text, pos_mapping
