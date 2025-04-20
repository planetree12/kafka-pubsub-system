"""
Configuration loading and validation for the consumer application.
"""
import json
import os
import logging
from typing import Dict, Any


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from JSON file.

    Args:
        config_path: Path to the configuration file. If None, uses the default path.

    Returns:
        dict: Configuration dictionary
    """
    if config_path is None:
        # Use default path relative to this file
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(base_dir, 'config', 'config.json')

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except (IOError, json.JSONDecodeError) as e:
        logging.error(f"Failed to load configuration from {config_path}: {str(e)}")
        raise
