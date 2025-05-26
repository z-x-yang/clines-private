#!/usr/bin/env python3
"""
Test script for enhanced token statistics functionality
"""

import logging
from llm_interface.llm_manager import LLMManager
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# Configure logging for test
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_token_stats():
    """Test the enhanced token statistics functionality"""

    # Create LLM manager (you can change model_name if needed)
    try:
        llm_manager = LLMManager('gpt4omini', chunk_size=512)
        logger.info("LLM Manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize LLM Manager: {e}")
        return

    # Test sample chunks
    test_chunks = [
        "This is a short test medical note about patient care.",
        "This is a longer medical note with more details about patient symptoms, diagnosis, and treatment plans. The patient presented with fever and cough.",
        "A very detailed medical record containing comprehensive information about the patient's medical history, current symptoms, examination findings, diagnostic results, and proposed treatment protocols."
    ]

    logger.info("\n=== Testing Enhanced Token Statistics ===")

    for i, chunk in enumerate(test_chunks, 1):
        logger.info(f"\n--- Processing Test Chunk {i} ---")
        logger.info(f"Chunk content: {chunk[:50]}...")

        # Set the original chunk tokens
        llm_manager.set_chunk_original_tokens(chunk)

        # Simulate some processing by adding a simple query
        # Note: This will only work if you have OpenAI credentials set up
        try:
            # Simple test query that should work with minimal tokens
            test_query = "Summarize this in one word: " + chunk
            response = llm_manager(test_query)
            logger.info(f"LLM Response: {response[:100]}...")

        except Exception as e:
            logger.warning(
                f"LLM call failed (this is expected if no API keys): {e}")
            # Manually add some test stats for demonstration
            llm_manager.current_chunk_stats.append({
                'prompt_tokens': 50 + len(chunk.split()) * 2,
                'completion_tokens': 10 + i * 5,
                'total_tokens': 60 + len(chunk.split()) * 2 + i * 5
            })

        # Finish the chunk to calculate statistics
        llm_manager.finish_chunk()

        # Display chunk statistics
        if llm_manager.chunk_token_stats:
            latest_chunk = llm_manager.chunk_token_stats[-1]
            logger.info(f"Chunk {i} Statistics:")
            logger.info(
                f"  Original chunk tokens: {latest_chunk['original_chunk_tokens']}")
            logger.info(f"  Prompt tokens: {latest_chunk['prompt_tokens']}")
            logger.info(
                f"  Completion tokens: {latest_chunk['completion_tokens']}")
            logger.info(f"  Total tokens: {latest_chunk['total_tokens']}")
            logger.info(f"  Number of calls: {latest_chunk['num_calls']}")
            logger.info(
                f"  Avg prompt tokens per call: {latest_chunk['avg_prompt_tokens_per_call']:.2f}")
            logger.info(
                f"  Avg completion tokens per call: {latest_chunk['avg_completion_tokens_per_call']:.2f}")

    # Display note-level statistics
    if llm_manager.note_token_stats:
        note_stats = llm_manager.note_token_stats[-1]
        logger.info(f"\n=== Final Note Statistics ===")
        logger.info(f"Total chunks processed: {note_stats['num_chunks']}")
        logger.info(
            f"Total original chunk tokens: {note_stats['total_original_chunk_tokens']}")
        logger.info(
            f"Average original chunk tokens: {note_stats['avg_original_chunk_tokens']:.2f}")
        logger.info(
            f"Total prompt tokens: {note_stats['total_prompt_tokens']}")
        logger.info(
            f"Total completion tokens: {note_stats['total_completion_tokens']}")
        logger.info(
            f"Average prompt tokens per chunk: {note_stats['avg_prompt_tokens_per_chunk']:.2f}")
        logger.info(
            f"Average completion tokens per chunk: {note_stats['avg_completion_tokens_per_chunk']:.2f}")
        logger.info(
            f"Average LLM calls per chunk: {note_stats['avg_calls_per_chunk']:.2f}")

    logger.info("\n=== Test Completed ===")


if __name__ == "__main__":
    test_token_stats()
