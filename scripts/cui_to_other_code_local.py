import pandas as pd
import functools
from collections import defaultdict
import logging
from typing import List, Dict, Optional, Set, Tuple
import warnings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global cache structure
_cache = {
    'data_loaded': False,
    'mrconso_df': None,
    'system_indices': {},  # {SAB: {CUI: [records]}}
    'available_systems': set()
}

def _load_mrconso_data():
    """Lazily load MRCONSO data if not already loaded."""
    if _cache['data_loaded']:
        return _cache['mrconso_df']
    
    logger.info("Loading MRCONSO data...")
    try:
        mrconso = pd.read_csv(
            "/n/data1/hsph/biostat/celehs/lab/va67/UMLS/UMLS2021AB/MRCONSO.RRF",
            sep="|",
            names=[
                "CUI", "LAT", "TS", "LUI", "STT", "SUI", "ISPREF", "AUI",
                "SAUI", "SCUI", "SDUI", "SAB", "TTY", "CODE", "STR", "SRL",
                "SUPPRESS", "CVF"
            ],
            dtype=str,
            index_col=False
        )
        
        _cache['mrconso_df'] = mrconso
        _cache['available_systems'] = set(mrconso['SAB'].unique())
        _cache['data_loaded'] = True
        
        logger.info(f"MRCONSO data loaded: {len(mrconso)} records, {len(_cache['available_systems'])} systems")
        return mrconso
        
    except FileNotFoundError:
        logger.error("MRCONSO.RRF file not found. Please check the file path.")
        raise
    except Exception as e:
        logger.error(f"Error loading MRCONSO data: {str(e)}")
        raise

def _build_system_index(sab: str) -> Dict[str, List[Dict]]:
    """Build CUI index for a specific SAB system."""
    if sab in _cache['system_indices']:
        return _cache['system_indices'][sab]
    
    logger.info(f"Building index for system: {sab}")
    mrconso_df = _load_mrconso_data()
    
    # Filter for specific SAB
    system_data = mrconso_df[mrconso_df['SAB'] == sab].copy()
    
    # Build CUI-based index
    cui_index = defaultdict(list)
    for _, row in system_data.iterrows():
        cui_index[row['CUI']].append({
            'CODE': row['CODE'],
            'STR': row['STR'],
            'TTY': row['TTY'],
            'SUPPRESS': row['SUPPRESS']
        })
    
    _cache['system_indices'][sab] = dict(cui_index)
    logger.info(f"Index built for {sab}: {len(cui_index)} unique CUIs")
    
    return _cache['system_indices'][sab]

def _validate_inputs(cui_list: List[str], target_systems: List[str]) -> Tuple[List[str], List[str]]:
    """Validate input parameters and return cleaned versions."""
    # Validate CUI list
    if not isinstance(cui_list, list) or not cui_list:
        raise ValueError("cui_list must be a non-empty list")
    
    # Clean and validate CUIs
    valid_cuis = []
    for cui in cui_list:
        if isinstance(cui, str) and cui.strip():
            cui_clean = cui.strip().upper()
            if cui_clean.startswith('C') and len(cui_clean) == 8 and cui_clean[1:].isdigit():
                valid_cuis.append(cui_clean)
            else:
                logger.warning(f"Invalid CUI format: {cui}")
        else:
            logger.warning(f"Invalid CUI value: {cui}")
    
    if not valid_cuis:
        raise ValueError("No valid CUIs provided")
    
    # Validate target systems
    if not isinstance(target_systems, list) or not target_systems:
        raise ValueError("target_systems must be a non-empty list")
    
    available_systems = _get_available_systems()
    valid_systems = []
    for system in target_systems:
        if isinstance(system, str) and system.strip():
            system_clean = system.strip().upper()
            if system_clean in available_systems:
                valid_systems.append(system_clean)
            else:
                logger.warning(f"Unknown system: {system}. Available systems include: {sorted(list(available_systems))[:10]}...")
    
    if not valid_systems:
        raise ValueError("No valid target systems provided")
    
    return valid_cuis, valid_systems

def _get_available_systems() -> Set[str]:
    """Get set of available coding systems."""
    _load_mrconso_data()  # Ensure data is loaded
    return _cache['available_systems']

def map_cui_to_codes(cui_list: List[str], target_systems: List[str], 
                     include_metadata: bool = False, suppress_filter: bool = True) -> pd.DataFrame:
    """
    Map CUI codes to target coding systems.
    
    Parameters:
    -----------
    cui_list : List[str]
        List of CUI codes to map
    target_systems : List[str]
        List of target coding systems (e.g., ['ICD10CM', 'RXNORM', 'LNC'])
    include_metadata : bool, default False
        Whether to include description and term type information
    suppress_filter : bool, default True
        Whether to filter out suppressed records
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with columns: CUI, TARGET_SYSTEM, TARGET_CODE, MAPPING_STATUS
        Additional columns if include_metadata=True: DESCRIPTION, TERM_TYPE
    """
    
    # Input validation
    try:
        valid_cuis, valid_systems = _validate_inputs(cui_list, target_systems)
    except ValueError as e:
        logger.error(f"Input validation failed: {str(e)}")
        raise
    
    logger.info(f"Processing {len(valid_cuis)} CUIs for {len(valid_systems)} systems")
    
    # Ensure required system indices are built
    for system in valid_systems:
        _build_system_index(system)
    
    # Perform mapping
    results = []
    mapping_stats = {'total_queries': 0, 'successful_mappings': 0}
    
    for cui in valid_cuis:
        for system in valid_systems:
            mapping_stats['total_queries'] += 1
            system_index = _cache['system_indices'][system]
            
            if cui in system_index:
                records = system_index[cui]
                
                # Filter suppressed records if requested
                if suppress_filter:
                    records = [r for r in records if r['SUPPRESS'] != 'Y']
                
                if records:
                    for record in records:
                        result_row = {
                            'CUI': cui,
                            'TARGET_SYSTEM': system,
                            'TARGET_CODE': record['CODE'],
                            'MAPPING_STATUS': 'FOUND'
                        }
                        
                        if include_metadata:
                            result_row['DESCRIPTION'] = record['STR']
                            result_row['TERM_TYPE'] = record['TTY']
                        
                        results.append(result_row)
                        mapping_stats['successful_mappings'] += 1
                else:
                    # No valid records after filtering
                    result_row = {
                        'CUI': cui,
                        'TARGET_SYSTEM': system,
                        'TARGET_CODE': None,
                        'MAPPING_STATUS': 'SUPPRESSED'
                    }
                    
                    if include_metadata:
                        result_row['DESCRIPTION'] = None
                        result_row['TERM_TYPE'] = None
                    
                    results.append(result_row)
            else:
                # CUI not found in this system
                result_row = {
                    'CUI': cui,
                    'TARGET_SYSTEM': system,
                    'TARGET_CODE': None,
                    'MAPPING_STATUS': 'NOT_FOUND'
                }
                
                if include_metadata:
                    result_row['DESCRIPTION'] = None
                    result_row['TERM_TYPE'] = None
                
                results.append(result_row)
    
    # Create result DataFrame
    result_df = pd.DataFrame(results)
    
    # Log statistics
    success_rate = (mapping_stats['successful_mappings'] / mapping_stats['total_queries']) * 100
    logger.info(f"Mapping completed: {mapping_stats['successful_mappings']}/{mapping_stats['total_queries']} successful ({success_rate:.1f}%)")
    
    return result_df

def get_available_systems() -> List[str]:
    """Return list of available coding systems."""
    available = _get_available_systems()
    return sorted(list(available))

def clear_cache():
    """Clear all cached data to free memory."""
    global _cache
    _cache = {
        'data_loaded': False,
        'mrconso_df': None,
        'system_indices': {},
        'available_systems': set()
    }
    logger.info("Cache cleared")

# Example usage and testing
if __name__ == "__main__":
    # Example CUI codes for testing
    test_cuis = ['C0020538', 'C0004096', 'C0002962']  # Example CUIs
    test_systems = ['RXNORM', 'ICD10CM', 'LNC']
    
    try:
        # Basic mapping
        print("=== Basic Mapping ===")
        result = map_cui_to_codes(test_cuis, test_systems)
        print(result.head())
        print(f"\nTotal mappings: {len(result)}")
        print(f"Successful mappings: {len(result[result['MAPPING_STATUS'] == 'FOUND'])}")
        
        # Mapping with metadata
        print("\n=== Mapping with Metadata ===")
        result_with_meta = map_cui_to_codes(test_cuis, ['RXNORM'], include_metadata=True)
        print(result_with_meta.head())
        
        # Show available systems
        print(f"\n=== Available Systems (first 20) ===")
        available = get_available_systems()
        print(available[:20])
        
    except Exception as e:
        print(f"Error in example: {str(e)}")