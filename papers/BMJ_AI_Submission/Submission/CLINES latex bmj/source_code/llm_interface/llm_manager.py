import semchunk
import tiktoken
from llm_interface.providers.openai_provider import wrap_openai_chat
from llm_interface.providers.local_llm_provider import llama_chat, deepseek_chat
from llm_interface.providers.huggingface_provider import huggingface_chat
from llm_interface.providers.azure_provider import wrap_azure_chat
import logging

# Placeholder for future implementations


def gemini_chat(input_message):
    NotImplementedError


def claude_chat(input_message):
    NotImplementedError


class LLMManager():

    def __init__(self, model_name, chunk_size=512):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model_name = model_name
        # Add token counting attributes
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.chunk_token_stats = []  # List to store token stats per chunk
        self.note_token_stats = []   # List to store token stats per note
        self.current_chunk_stats = []  # Temporary storage for current chunk stats

        # New attributes for enhanced chunk statistics
        self.current_chunk_original_tokens = 0  # Track original chunk token count
        self.chunk_original_token_stats = []  # Store original token counts per chunk

        if isinstance(self.model_name, str) and self.model_name.startswith('azure:'):
            azure_model_key = self.model_name.split(':', 1)[1]
            self.chat_func = wrap_azure_chat(azure_model_key)
            self.tokenizer = tiktoken.encoding_for_model('gpt-4')
            self.chunker = semchunk.chunkerify(self.tokenizer, chunk_size)

        elif self.model_name in ['gpt4o', 'gpt4omini', 'o3mini']:
            self.chat_func = wrap_openai_chat(self.model_name)
            self.tokenizer = tiktoken.encoding_for_model('gpt-4')
            self.chunker = semchunk.chunkerify(self.tokenizer, chunk_size)

        elif self.model_name in ['gemini']:
            self.chat_func = gemini_chat

        elif self.model_name in ['claude']:
            self.chat_func = claude_chat

        elif self.model_name in ['llama', 'mistral']:
            # Assuming 'llama' and 'mistral' might use huggingface_chat or a specific local setup
            # For now, let's point 'llama' to llama_chat and 'mistral' to huggingface_chat as an example
            if self.model_name == 'llama':
                self.chat_func = llama_chat  # Or a more specific llama_chat from local_llm_provider
            elif self.model_name == 'mistral':
                self.chat_func = huggingface_chat  # Or a specific mistral setup
            # Tokenizer and chunker might need to be specific here
            # Using gpt-4 tokenizer as a placeholder, adjust as needed
            self.tokenizer = tiktoken.encoding_for_model('gpt-4')
            self.chunker = semchunk.chunkerify(
                self.tokenizer, chunk_size if chunk_size else 512)

        elif self.model_name in ['llama-3-405b']:
            self.chat_func = llama_chat
            self.tokenizer = tiktoken.encoding_for_model('gpt-4')
            self.chunker = semchunk.chunkerify(self.tokenizer, 512)

        elif self.model_name in ['deepseek']:
            self.chat_func = deepseek_chat
            self.tokenizer = tiktoken.encoding_for_model('gpt-4')
            self.chunker = semchunk.chunkerify(self.tokenizer, 512)

        else:
            raise ValueError(f"Unsupported model_name: {model_name}")

        self.new_chat()

    def new_chat(self):
        '''
        add system prompt for different model, use default prompt,
        start new chat
        '''
        # Don't reset chunk token stats here anymore
        self.message_buffer = []
        if isinstance(self.model_name, str) and self.model_name.startswith('azure:'):
            self.message_buffer.append({
                "role": "system",
                "content": "You are a medical record processing AI. Process all medical terminology, procedures, and conditions as standard healthcare documentation. Maintain professional medical context in responses."
            })

        elif self.model_name in ['gpt4o', 'gpt4omini', 'o3mini']:
            self.message_buffer.append({
                "role": "system",
                "content": "You are a medical record processing AI. Process all medical terminology, procedures, and conditions as standard healthcare documentation. Maintain professional medical context in responses."
            })

        elif self.model_name in ['gemini']:
            NotImplementedError

        elif self.model_name in ['claude']:
            NotImplementedError

        # Added llama-3-405b here
        elif self.model_name in ['llama', 'mistral', 'llama-3-405b']:
            self.message_buffer.append({
                "role": "system",
                "content": "You are an AI assistant that follows people's instructions."
            })

        elif self.model_name in ['deepseek']:
            pass  # deepseek might not require a system prompt or has a default

    def set_chunk_original_tokens(self, chunk_text):
        """
        Set the original token count for the current chunk being processed.
        This should be called at the beginning of processing each chunk.

        Args:
            chunk_text (str): The original chunk text
        """
        if hasattr(self, 'tokenizer') and self.tokenizer:
            self.current_chunk_original_tokens = len(
                self.tokenizer.encode(chunk_text))
        else:
            # Fallback estimation if tokenizer is not available
            self.current_chunk_original_tokens = len(chunk_text.split())
        self.logger.debug(
            f"Original chunk tokens: {self.current_chunk_original_tokens}")

    def start_new_note(self):
        """
        Reset chunk-level statistics for processing a new note.
        Called at the beginning of each new note processing.
        """
        self.chunk_token_stats = []
        self.chunk_original_token_stats = []
        self.current_chunk_stats = []
        self.current_chunk_original_tokens = 0
        self.logger.debug("Reset chunk-level statistics for new note")

    def __call__(self, query):
        self.message_buffer.append({'role': 'user', 'content': query})
        response = self.chat_func(self.message_buffer)

        # Handle token usage if available
        if isinstance(response, dict) and response.get('token_usage'):
            token_usage = response['token_usage']
            # Update token counts
            self.total_prompt_tokens += token_usage.prompt_tokens
            self.total_completion_tokens += token_usage.completion_tokens

            # Store chunk stats in temporary storage
            chunk_stats = {
                'prompt_tokens': token_usage.prompt_tokens,
                'completion_tokens': token_usage.completion_tokens,
                'total_tokens': token_usage.total_tokens
            }
            self.current_chunk_stats.append(chunk_stats)

            content = response['content']
        else:
            # Ensure response is a string, or extract content if it's a dict without token_usage
            if isinstance(response, dict) and 'content' in response:
                content = response['content']
            elif isinstance(response, str):
                content = response
            else:
                # Fallback or error handling if response format is unexpected
                self.logger.error(
                    f"Unexpected response format from chat function: {type(response)}, {response}", exc_info=True)
                raise ValueError(
                    "Unexpected response format from chat function")

        self.message_buffer.append({'role': 'assistant', 'content': content})

        return content

    def finish_chunk(self):
        """
        Called when a chunk is finished processing to finalize its token statistics
        """
        if self.current_chunk_stats:
            # Calculate chunk-level statistics
            chunk_total = {
                'prompt_tokens': sum(stats['prompt_tokens'] for stats in self.current_chunk_stats),
                'completion_tokens': sum(stats['completion_tokens'] for stats in self.current_chunk_stats),
                'total_tokens': sum(stats['total_tokens'] for stats in self.current_chunk_stats),
                'num_calls': len(self.current_chunk_stats),
                # Add new statistics
                'original_chunk_tokens': self.current_chunk_original_tokens,
                'avg_prompt_tokens_per_call': sum(stats['prompt_tokens'] for stats in self.current_chunk_stats) / len(self.current_chunk_stats) if self.current_chunk_stats else 0,
                'avg_completion_tokens_per_call': sum(stats['completion_tokens'] for stats in self.current_chunk_stats) / len(self.current_chunk_stats) if self.current_chunk_stats else 0,
                'avg_total_tokens_per_call': sum(stats['total_tokens'] for stats in self.current_chunk_stats) / len(self.current_chunk_stats) if self.current_chunk_stats else 0
            }
            self.chunk_token_stats.append(chunk_total)

            # Store original chunk token count separately for easier access
            self.chunk_original_token_stats.append(
                self.current_chunk_original_tokens)

            # Reset current chunk stats and original token count
            self.current_chunk_stats = []
            self.current_chunk_original_tokens = 0

    def finish_note(self):
        """
        Called when a note is completely processed to finalize its token statistics
        """
        if self.chunk_token_stats:
            # Calculate and store note-level token stats with enhanced metrics (based on current note's chunks only)
            note_stats = {
                'total_prompt_tokens': sum(chunk['prompt_tokens'] for chunk in self.chunk_token_stats),
                'total_completion_tokens': sum(chunk['completion_tokens'] for chunk in self.chunk_token_stats),
                'total_tokens': sum(chunk['total_tokens'] for chunk in self.chunk_token_stats),
                'num_chunks': len(self.chunk_token_stats),
                'avg_tokens_per_chunk': sum(chunk['total_tokens'] for chunk in self.chunk_token_stats) / len(self.chunk_token_stats) if self.chunk_token_stats else 0,
                # New enhanced statistics
                'total_original_chunk_tokens': sum(self.chunk_original_token_stats),
                'avg_original_chunk_tokens': sum(self.chunk_original_token_stats) / len(self.chunk_original_token_stats) if self.chunk_original_token_stats else 0,
                'avg_prompt_tokens_per_chunk': sum(chunk['prompt_tokens'] for chunk in self.chunk_token_stats) / len(self.chunk_token_stats) if self.chunk_token_stats else 0,
                'avg_completion_tokens_per_chunk': sum(chunk['completion_tokens'] for chunk in self.chunk_token_stats) / len(self.chunk_token_stats) if self.chunk_token_stats else 0,
                'avg_calls_per_chunk': sum(chunk['num_calls'] for chunk in self.chunk_token_stats) / len(self.chunk_token_stats) if self.chunk_token_stats else 0
            }
            # Add the current note's statistics to the list
            self.note_token_stats.append(note_stats)
            self.logger.debug(f"Added note statistics: {len(self.note_token_stats)} total notes processed")
