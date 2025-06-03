"""
Configuration manager for CLINES: Clinical LLM‐based Information Extraction and Structuring Agent.

This module provides configuration loading, validation, and management
with support for multiple environments and override mechanisms.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """
    Configuration manager with support for YAML files, environment variables,
    and multiple configuration profiles.
    """
    
    def __init__(self, config_dir: str = "config", default_profile: str = "default"):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
            default_profile: Default configuration profile to load
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_dir = Path(config_dir)
        self.default_profile = default_profile
        self.config_cache = {}
        self._config = {}
        
    def load_config(self, profile: Optional[str] = None, config_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from file with profile and environment variable support.
        
        Args:
            profile: Configuration profile name (e.g., 'development', 'production')
            config_file: Specific config file path (overrides profile)
            
        Returns:
            Dictionary containing the loaded configuration
        """
        if config_file:
            config_path = Path(config_file)
        else:
            profile = profile or self.default_profile
            config_path = self.config_dir / f"{profile}.yaml"
            
        # Check cache first
        cache_key = str(config_path)
        if cache_key in self.config_cache:
            self.logger.debug(f"Using cached configuration for {cache_key}")
            return self.config_cache[cache_key].copy()
            
        try:
            # Load base configuration
            config = self._load_yaml_file(config_path)
            
            # Apply environment variable overrides
            config = self._apply_env_overrides(config)
            
            # Cache the configuration
            self.config_cache[cache_key] = config.copy()
            self._config = config
            
            self.logger.info(f"Configuration loaded from {config_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration from {config_path}: {e}")
            raise
            
    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML configuration file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            return config
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {file_path}: {e}")
            
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.
        
        Environment variables should follow the pattern:
        APP_SECTION_KEY=value (e.g., APP_MODEL_DEFAULT_NAME=gpt4)
        """
        prefix = "APP_"
        
        for env_key, env_value in os.environ.items():
            if not env_key.startswith(prefix):
                continue
                
            # Convert APP_MODEL_DEFAULT_NAME -> model.default_name
            config_path = env_key[len(prefix):].lower().split('_')
            
            # Navigate/create nested structure
            current = config
            for key in config_path[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
                
            # Set the final value with type conversion
            final_key = config_path[-1]
            current[final_key] = self._convert_env_value(env_value)
            
        return config
        
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        # Convert common string representations to appropriate types
        if value.lower() in ('true', 'yes', '1'):
            return True
        elif value.lower() in ('false', 'no', '0'):
            return False
        elif value.isdigit():
            return int(value)
        elif self._is_float(value):
            return float(value)
        else:
            return value
            
    def _is_float(self, value: str) -> bool:
        """Check if string represents a float."""
        try:
            float(value)
            return True
        except ValueError:
            return False
            
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., 'model.default_name')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        current = self._config
        
        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return default
            
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation
            value: Value to set
        """
        keys = key.split('.')
        current = self._config
        
        # Navigate to parent
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
            
        # Set final value
        current[keys[-1]] = value
        
    def update_from_args(self, args: Any) -> None:
        """
        Update configuration from argparse.Namespace or similar object.
        
        Args:
            args: Object with configuration attributes
        """
        if hasattr(args, '__dict__'):
            for key, value in args.__dict__.items():
                if value is not None:
                    # Convert underscore to dot notation for nested configs
                    config_key = key.replace('_', '.')
                    self.set(config_key, value)
                    
    def get_config(self) -> Dict[str, Any]:
        """Get the complete configuration dictionary."""
        return self._config.copy()
        
    def reload_config(self, profile: Optional[str] = None, config_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Reload configuration, clearing cache.
        
        Args:
            profile: Configuration profile name
            config_file: Specific config file path
            
        Returns:
            Reloaded configuration dictionary
        """
        # Clear cache
        self.config_cache.clear()
        return self.load_config(profile, config_file) 