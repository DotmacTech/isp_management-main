"""
OLT Output Parser Utilities

This module provides utilities for parsing command output from different OLT vendors,
converting raw text responses into structured data.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Union, Tuple

logger = logging.getLogger(__name__)

class BaseParser:
    """Base class for OLT output parsers."""
    
    @staticmethod
    def clean_output(output: str) -> str:
        """
        Clean raw command output by removing terminal control characters and noise.
        
        Args:
            output: Raw command output
            
        Returns:
            str: Cleaned output
        """
        # Remove ANSI escape sequences
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', output)
        
        # Remove non-printable characters
        cleaned = ''.join(c for c in cleaned if c.isprintable() or c in '\n\r\t')
        
        # Remove repetitive spaces
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        
        # Remove empty lines
        cleaned = '\n'.join(line for line in cleaned.splitlines() if line.strip())
        
        return cleaned
    
    @staticmethod
    def extract_table(output: str, headers: Optional[List[str]] = None, 
                    start_marker: Optional[str] = None, end_marker: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Extract tabular data from command output.
        
        Args:
            output: Command output
            headers: Optional list of column headers (if not provided, will try to detect from output)
            start_marker: Optional string marking the start of the table
            end_marker: Optional string marking the end of the table
            
        Returns:
            List[Dict]: List of dictionaries, each representing a row of the table
        """
        lines = output.splitlines()
        table_lines = []
        in_table = False if start_marker else True
        
        # Extract table lines using markers
        for line in lines:
            if not in_table and start_marker and start_marker in line:
                in_table = True
                continue
            elif in_table and end_marker and end_marker in line:
                break
                
            if in_table and line.strip():
                table_lines.append(line)
        
        if not table_lines:
            return []
            
        # Try to detect headers if not provided
        if not headers:
            # Use first line as header
            header_line = table_lines[0]
            headers = [h.strip() for h in re.split(r'\s{2,}', header_line)]
            table_lines = table_lines[1:]
        
        # Process each row
        result = []
        for line in table_lines:
            # Skip lines that don't look like data
            if not re.search(r'\s{2,}', line):
                continue
                
            # Split by multiple spaces
            values = [v.strip() for v in re.split(r'\s{2,}', line)]
            
            # Make sure we have the right number of values
            if len(values) != len(headers):
                # Try to adjust for missing or extra values
                if len(values) < len(headers):
                    values.extend([''] * (len(headers) - len(values)))
                else:
                    values = values[:len(headers)]
            
            # Create row dictionary
            row = dict(zip(headers, values))
            result.append(row)
            
        return result
    
    @staticmethod
    def extract_key_value_pairs(output: str, separator: str = ':') -> Dict[str, str]:
        """
        Extract key-value pairs from command output.
        
        Args:
            output: Command output
            separator: Character(s) separating keys from values
            
        Returns:
            Dict[str, str]: Dictionary of key-value pairs
        """
        result = {}
        lines = output.splitlines()
        
        for line in lines:
            if separator in line:
                parts = line.split(separator, 1)
                key = parts[0].strip()
                value = parts[1].strip()
                result[key] = value
                
        return result
    
    @staticmethod
    def extract_section(output: str, start_marker: str, end_marker: Optional[str] = None) -> str:
        """
        Extract a section of text from command output.
        
        Args:
            output: Command output
            start_marker: String marking the start of the section
            end_marker: Optional string marking the end of the section
            
        Returns:
            str: Extracted section
        """
        lines = output.splitlines()
        section_lines = []
        in_section = False
        
        for line in lines:
            if not in_section and start_marker in line:
                in_section = True
                continue
            elif in_section and end_marker and end_marker in line:
                break
                
            if in_section:
                section_lines.append(line)
                
        return '\n'.join(section_lines)
    
    @staticmethod
    def extract_multi_value(output: str, key: str, separator: str = ':') -> List[str]:
        """
        Extract multiple values for the same key from command output.
        
        Args:
            output: Command output
            key: Key to search for
            separator: Character(s) separating keys from values
            
        Returns:
            List[str]: List of values for the key
        """
        values = []
        pattern = re.compile(f"{re.escape(key)}{re.escape(separator)}\\s*(.+)")
        
        for line in output.splitlines():
            match = pattern.search(line)
            if match:
                values.append(match.group(1).strip())
                
        return values


class HuaweiParser(BaseParser):
    """Parser for Huawei OLT command output."""
    
    @staticmethod
    def parse_ont_list(output: str) -> List[Dict[str, Any]]:
        """
        Parse ONT list output from Huawei OLT.
        
        Args:
            output: Command output from 'display ont info' or similar
            
        Returns:
            List[Dict]: List of ONT information dictionaries
        """
        cleaned_output = HuaweiParser.clean_output(output)
        onts = []
        
        # Pattern to match ONT entries
        # Example format: "1    FHTT12345678    online    Home ONT"
        pattern = re.compile(r'(\d+)\s+(\w+)\s+(\w+)(?:\s+(.*))?')
        
        for line in cleaned_output.splitlines():
            match = pattern.match(line)
            if match:
                ont_id, sn, status, description = match.groups()
                ont = {
                    'id': ont_id,
                    'serial_number': sn,
                    'status': status,
                    'description': description or ''
                }
                onts.append(ont)
        
        return onts
    
    @staticmethod
    def parse_ont_status(output: str) -> Dict[str, Any]:
        """
        Parse ONT status output from Huawei OLT.
        
        Args:
            output: Command output from 'display ont state' or similar
            
        Returns:
            Dict: ONT status information
        """
        cleaned_output = HuaweiParser.clean_output(output)
        status = {}
        
        # Extract key-value pairs
        key_value_map = {
            'Run State': 'state',
            'Online Duration': 'uptime',
            'Distance(m)': 'distance',
            'Rx optical power(dBm)': 'rx_power',
            'Temperature(C)': 'temperature',
            'Voltage(V)': 'voltage',
            'Tx optical power(dBm)': 'tx_power'
        }
        
        for line in cleaned_output.splitlines():
            for key, mapped_key in key_value_map.items():
                if key in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        status[mapped_key] = parts[1].strip()
        
        return status
    
    @staticmethod
    def parse_signal_history(output: str) -> Dict[str, Any]:
        """
        Parse ONT signal history from Huawei OLT.
        
        Args:
            output: Command output from 'display ont optical-info' or similar
            
        Returns:
            Dict: Signal history data with timestamps and levels
        """
        cleaned_output = HuaweiParser.clean_output(output)
        
        # Extract the table
        table = HuaweiParser.extract_table(
            cleaned_output, 
            headers=['Time', 'Rx Power(dBm)', 'Tx Power(dBm)', 'Laser Bias Current(mA)'],
            start_marker='--------------------------------------------------',
            end_marker='--------------------------------------------------'
        )
        
        # Format into time series
        history = {
            'timestamps': [],
            'rx_levels': [],
            'tx_levels': [],
            'bias_current': []
        }
        
        for row in table:
            history['timestamps'].append(row.get('Time', ''))
            history['rx_levels'].append(row.get('Rx Power(dBm)', ''))
            history['tx_levels'].append(row.get('Tx Power(dBm)', ''))
            history['bias_current'].append(row.get('Laser Bias Current(mA)', ''))
        
        return history
    
    @staticmethod
    def parse_alerts(output: str) -> List[Dict[str, Any]]:
        """
        Parse ONT alerts from Huawei OLT.
        
        Args:
            output: Command output from 'display ont alarm' or similar
            
        Returns:
            List[Dict]: List of alert information dictionaries
        """
        cleaned_output = HuaweiParser.clean_output(output)
        alerts = []
        
        # Extract the alerts table
        table = HuaweiParser.extract_table(
            cleaned_output,
            headers=['Time', 'Type', 'Description', 'Severity'],
            start_marker='--------------------------------------------------',
            end_marker='--------------------------------------------------'
        )
        
        for row in table:
            alert = {
                'timestamp': row.get('Time', ''),
                'type': row.get('Type', ''),
                'description': row.get('Description', ''),
                'severity': row.get('Severity', '')
            }
            alerts.append(alert)
        
        return alerts


class ZTEParser(BaseParser):
    """Parser for ZTE OLT command output."""
    
    @staticmethod
    def parse_ont_list(output: str) -> List[Dict[str, Any]]:
        """
        Parse ONT list output from ZTE OLT.
        
        Args:
            output: Command output from 'show ont' or similar
            
        Returns:
            List[Dict]: List of ONT information dictionaries
        """
        cleaned_output = ZTEParser.clean_output(output)
        onts = []
        
        # Pattern to match ONT entries
        # Example format: "1    ZTEG12345678    online    Home ONT"
        pattern = re.compile(r'(\d+)\s+(\w+)\s+(\w+)(?:\s+(.*))?')
        
        for line in cleaned_output.splitlines():
            match = pattern.match(line)
            if match:
                ont_id, sn, status, description = match.groups()
                ont = {
                    'id': ont_id,
                    'serial_number': sn,
                    'status': status,
                    'description': description or ''
                }
                onts.append(ont)
        
        return onts
    
    @staticmethod
    def parse_ont_status(output: str) -> Dict[str, Any]:
        """
        Parse ONT status output from ZTE OLT.
        
        Args:
            output: Command output from 'show ont status' or similar
            
        Returns:
            Dict: ONT status information
        """
        cleaned_output = ZTEParser.clean_output(output)
        status = {}
        
        # Extract key-value pairs
        key_value_map = {
            'Run State': 'state',
            'Online Duration': 'uptime',
            'Distance': 'distance',
            'Rx Power': 'rx_power',
            'Temperature': 'temperature',
            'Voltage': 'voltage',
            'Tx Power': 'tx_power'
        }
        
        for line in cleaned_output.splitlines():
            for key, mapped_key in key_value_map.items():
                if key in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        status[mapped_key] = parts[1].strip()
        
        return status
    
    @staticmethod
    def parse_signal_history(output: str) -> Dict[str, Any]:
        """
        Parse ONT signal history from ZTE OLT.
        
        Args:
            output: Command output from 'show ont optical' or similar
            
        Returns:
            Dict: Signal history data with timestamps and levels
        """
        cleaned_output = ZTEParser.clean_output(output)
        
        # Extract the table
        table = ZTEParser.extract_table(
            cleaned_output, 
            headers=['Time', 'Rx Power', 'Tx Power', 'Current'],
            start_marker='--------------------------------------------------',
            end_marker='--------------------------------------------------'
        )
        
        # Format into time series
        history = {
            'timestamps': [],
            'rx_levels': [],
            'tx_levels': [],
            'bias_current': []
        }
        
        for row in table:
            history['timestamps'].append(row.get('Time', ''))
            history['rx_levels'].append(row.get('Rx Power', ''))
            history['tx_levels'].append(row.get('Tx Power', ''))
            history['bias_current'].append(row.get('Current', ''))
        
        return history
    
    @staticmethod
    def parse_alerts(output: str) -> List[Dict[str, Any]]:
        """
        Parse ONT alerts from ZTE OLT.
        
        Args:
            output: Command output from 'show ont alarms' or similar
            
        Returns:
            List[Dict]: List of alert information dictionaries
        """
        cleaned_output = ZTEParser.clean_output(output)
        alerts = []
        
        # Extract the alerts table
        table = ZTEParser.extract_table(
            cleaned_output,
            headers=['Time', 'Type', 'Description', 'Severity'],
            start_marker='--------------------------------------------------',
            end_marker='--------------------------------------------------'
        )
        
        for row in table:
            alert = {
                'timestamp': row.get('Time', ''),
                'type': row.get('Type', ''),
                'description': row.get('Description', ''),
                'severity': row.get('Severity', '')
            }
            alerts.append(alert)
        
        return alerts
