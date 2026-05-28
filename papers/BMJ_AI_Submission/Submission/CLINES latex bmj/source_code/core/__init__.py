"""
Core module for CLINES: Clinical LLM‐based Information Extraction and Structuring Agent.

This module contains the core functionality including:
- Data types and schemas
- Configuration management
- Utility functions
- Schema processors
"""

from .data_types import NERData, EntityData, InfoData, DateData
from .schema import SchemaProcessor, SchemaName, OutputType
from .utils import process_lists_based_on_list1, get_tags_from_list1, clean_and_fill_list
from .config_manager import ConfigManager

__all__ = [
    'NERData', 'EntityData', 'InfoData', 'DateData',
    'SchemaProcessor', 'SchemaName', 'OutputType', 
    'process_lists_based_on_list1', 'get_tags_from_list1', 'clean_and_fill_list',
    'ConfigManager'
]

__version__ = '1.0.0' 