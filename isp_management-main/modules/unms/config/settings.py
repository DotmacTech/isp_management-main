"""
Configuration settings for the UNMS module.
"""
import os
import logging
import configparser
from typing import Optional, Any, Dict, List, Union

logger = logging.getLogger('unms')


class UNMSConfig:
    """
    Configuration manager for UNMS API.
    
    This class handles loading and accessing configuration settings.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_file (Optional[str], optional): Path to a configuration file. Defaults to None.
        """
        self._config = configparser.ConfigParser()
        self._config_file = config_file
        
        # Load default configuration
        self._load_defaults()
        
        # Load configuration from file if provided
        if config_file:
            self._load_from_file(config_file)
        
        # Load configuration from environment variables
        self._load_from_env()
    
    def _load_defaults(self) -> None:
        """
        Load default configuration settings.
        """
        self._config['api'] = {
            'base_url': '',
            'api_version': 'v2.1',
            'ssl_verify': 'true',
            'ssl_cert': '',
            'timeout': '30',
            'proxies': '',
            'auto_reconnect': 'true',
            'max_retries': '3',
            'retry_backoff': '0.5',
        }
        
        self._config['auth'] = {
            'username': '',
            'password': '',
            'token': '',
            'token_refresh': 'true',
        }
        
        self._config['cache'] = {
            'enabled': 'false',
            'ttl': '300',
            'redis_url': '',
        }
        
        self._config['logging'] = {
            'level': 'INFO',
            'trace_requests': 'false',
        }
    
    def _load_from_file(self, config_file: str) -> None:
        """
        Load configuration from a file.
        
        Args:
            config_file (str): Path to a configuration file.
        """
        try:
            if os.path.isfile(config_file):
                self._config.read(config_file)
                logger.info(f"Loaded configuration from {config_file}")
            else:
                logger.warning(f"Configuration file {config_file} not found")
        except Exception as e:
            logger.error(f"Error loading configuration from {config_file}: {e}")
    
    def _load_from_env(self) -> None:
        """
        Load configuration from environment variables.
        
        Environment variables should be in the format UNMS_SECTION_OPTION=value,
        e.g., UNMS_API_BASE_URL=https://example.com
        """
        for key, value in os.environ.items():
            if key.startswith('UNMS_'):
                parts = key.split('_', 2)
                if len(parts) == 3:
                    _, section, option = parts
                    section = section.lower()
                    option = option.lower()
                    
                    if section not in self._config:
                        self._config[section] = {}
                    
                    self._config[section][option] = value
                    logger.debug(f"Set {section}.{option} from environment variable {key}")
    
    def get(self, section: str, option: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            section (str): Configuration section.
            option (str): Configuration option.
            default (Any, optional): Default value if option is not found. Defaults to None.
            
        Returns:
            Any: Configuration value.
        """
        try:
            value = self._config.get(section, option)
            
            # Convert value to appropriate type
            if value.lower() in ('true', 'yes', '1'):
                return True
            elif value.lower() in ('false', 'no', '0'):
                return False
            elif value.isdigit():
                return int(value)
            elif value.replace('.', '', 1).isdigit() and value.count('.') <= 1:
                return float(value)
            else:
                return value
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
    
    def set(self, section: str, option: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            section (str): Configuration section.
            option (str): Configuration option.
            value (Any): Configuration value.
        """
        if section not in self._config:
            self._config[section] = {}
        
        self._config[section][option] = str(value)
    
    def save(self, config_file: Optional[str] = None) -> bool:
        """
        Save configuration to a file.
        
        Args:
            config_file (Optional[str], optional): Path to a configuration file. 
                                                  Defaults to the file used in initialization.
                                                  
        Returns:
            bool: Whether save was successful.
        """
        file_path = config_file or self._config_file
        if not file_path:
            logger.error("No configuration file specified for saving")
            return False
        
        try:
            with open(file_path, 'w') as f:
                self._config.write(f)
            logger.info(f"Saved configuration to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration to {file_path}: {e}")
            return False


def get_config(config_file: Optional[str] = None) -> UNMSConfig:
    """
    Get a configuration manager.
    
    Args:
        config_file (Optional[str], optional): Path to a configuration file. Defaults to None.
        
    Returns:
        UNMSConfig: Configuration manager.
    """
    return UNMSConfig(config_file)
