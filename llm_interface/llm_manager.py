import semchunk
import tiktoken
from llm_interface.providers.openai_provider import wrap_openai_chat
from llm_interface.providers.local_llm_provider import llama_chat, deepseek_chat
from llm_interface.providers.huggingface_provider import huggingface_chat
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

        if self.model_name in ['gpt4o', 'gpt4omini', 'o3mini']:
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
        if self.model_name in ['gpt4o', 'gpt4omini', 'o3mini']:
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
                'num_calls': len(self.current_chunk_stats)
            }
            self.chunk_token_stats.append(chunk_total)

            # Calculate and store note-level token stats
            # This part seems to append a new entry to note_token_stats for every chunk.
            # It should likely be called once per note, not per chunk.
            # For now, I will keep the logic as is, but this is a point for review.
            note_stats = {
                'total_prompt_tokens': sum(chunk['prompt_tokens'] for chunk in self.chunk_token_stats),
                'total_completion_tokens': sum(chunk['completion_tokens'] for chunk in self.chunk_token_stats),
                'total_tokens': sum(chunk['total_tokens'] for chunk in self.chunk_token_stats),
                'num_chunks': len(self.chunk_token_stats),
                'avg_tokens_per_chunk': sum(chunk['total_tokens'] for chunk in self.chunk_token_stats) / len(self.chunk_token_stats) if self.chunk_token_stats else 0
            }
            # Append new or update last
            if not self.note_token_stats or self.note_token_stats[-1]['num_chunks'] < note_stats['num_chunks']:
                self.note_token_stats.append(note_stats)
            else:
                self.note_token_stats[-1] = note_stats

            # Reset current chunk stats
            self.current_chunk_stats = []
