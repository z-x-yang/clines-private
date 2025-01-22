from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class NERData:
    """Container for NER processing results."""
    ner_results: str
    parsed_results: List[str]
    parsed_tags: List[str]
    parsed_context: List[str]


@dataclass
class EntityData:
    """Container for entity processing results."""
    relate_results: List[Dict[str, Any]]
    clean_results: List[Dict[str, Any]]


@dataclass
class InfoData:
    """Container for information extraction results."""
    status_results: List[Dict[str, Any]]
    info_results: List[Dict[str, Any]]


@dataclass
class DateData:
    """Container for date processing results."""
    basic_results: Optional[Dict[str, Any]]
    date_results: List[Dict[str, Any]]
