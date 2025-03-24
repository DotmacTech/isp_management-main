"""
Output Parser Utility Module

This module provides utilities for parsing command outputs from OLT devices.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Pattern, Match
from ....olt.exceptions import ParseError

logger = logging.getLogger(__name__)


class OutputParser:
    """
    Parser for OLT command outputs.
    
    This class provides methods for parsing and extracting structured data
    from OLT command outputs.
    """
    
    @staticmethod
    def parse_key_value_output(output: str, delimiter: str = ":") -> Dict[str, str]:
        """
        Parse output with key-value pairs.
        
        Args:
            output: Command output to parse
            delimiter: Delimiter between key and value (default: ":")
            
        Returns:
            Dict[str, str]: Dictionary of key-value pairs
        """
        result = {}
        for line in output.splitlines():
            line = line.strip()
            if not line or delimiter not in line:
                continue
            
            # Split on the first occurrence of the delimiter
            parts = line.split(delimiter, 1)
            if len(parts) != 2:
                continue
            
            key = parts[0].strip()
            value = parts[1].strip()
            
            # Skip empty values
            if not value:
                continue
            
            result[key] = value
        
        return result
    
    @staticmethod
    def parse_table_output(output: str, headers: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """
        Parse tabular output into a list of dictionaries.
        
        Args:
            output: Command output to parse
            headers: Optional list of headers (if not provided, will try to detect)
            
        Returns:
            List[Dict[str, str]]: List of dictionaries, one for each row
        """
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if not lines:
            return []
        
        # Try to detect headers if not provided
        if not headers:
            # Look for a line with dashes or equals signs that might indicate a header separator
            separator_index = None
            for i, line in enumerate(lines):
                if re.match(r'^[-=]+(\s+[-=]+)*$', line):
                    separator_index = i
                    break
            
            if separator_index is not None and separator_index > 0:
                # Headers are in the line before the separator
                header_line = lines[separator_index - 1]
                # Try to split headers based on multiple spaces
                headers = [h.strip() for h in re.split(r'\s{2,}', header_line) if h.strip()]
                # Remove header and separator lines
                lines = lines[separator_index + 1:]
            else:
                # No clear header separator found, assume first line is headers
                header_line = lines[0]
                headers = [h.strip() for h in re.split(r'\s{2,}', header_line) if h.strip()]
                lines = lines[1:]
        
        # Process each data line
        result = []
        for line in lines:
            # Skip lines that don't look like data
            if not line or re.match(r'^[-=]+(\s+[-=]+)*$', line):
                continue
            
            # Try to split the line into columns based on multiple spaces
            values = [v.strip() for v in re.split(r'\s{2,}', line) if v.strip()]
            
            # If we have more or fewer values than headers, try to adjust
            if len(values) != len(headers):
                # If we have more values than headers, combine the excess
                if len(values) > len(headers):
                    values = values[:len(headers) - 1] + [' '.join(values[len(headers) - 1:])]
                # If we have fewer values than headers, pad with empty strings
                else:
                    values.extend([''] * (len(headers) - len(values)))
            
            # Create a dictionary for this row
            row = {headers[i]: values[i] for i in range(len(headers))}
            result.append(row)
        
        return result
    
    @staticmethod
    def parse_ont_status(output: str, vendor: str) -> Dict[str, Any]:
        """
        Parse ONT status output.
        
        Args:
            output: Command output to parse
            vendor: OLT vendor (e.g., 'huawei', 'zte')
            
        Returns:
            Dict[str, Any]: ONT status information
        """
        if vendor.lower() == 'huawei':
            return OutputParser._parse_huawei_ont_status(output)
        elif vendor.lower() == 'zte':
            return OutputParser._parse_zte_ont_status(output)
        else:
            raise ParseError(f"Unsupported vendor: {vendor}")
    
    @staticmethod
    def _parse_huawei_ont_status(output: str) -> Dict[str, Any]:
        """
        Parse Huawei ONT status output.
        
        Args:
            output: Command output to parse
            
        Returns:
            Dict[str, Any]: ONT status information
        """
        result = {}
        
        # Extract run state
        run_state_match = re.search(r'Run state\s*:\s*(\w+)', output)
        if run_state_match:
            result['status'] = run_state_match.group(1).lower()
        
        # Extract config state
        config_state_match = re.search(r'Config state\s*:\s*(\w+)', output)
        if config_state_match:
            result['config_state'] = config_state_match.group(1).lower()
        
        # Extract match state
        match_state_match = re.search(r'Match state\s*:\s*(\w+)', output)
        if match_state_match:
            result['match_state'] = match_state_match.group(1).lower()
        
        # Extract optical power
        rx_power_match = re.search(r'RX optical power\(dBm\)\s*:\s*([-\d.]+)', output)
        if rx_power_match:
            try:
                result['rx_power'] = float(rx_power_match.group(1))
            except ValueError:
                pass
        
        tx_power_match = re.search(r'TX optical power\(dBm\)\s*:\s*([-\d.]+)', output)
        if tx_power_match:
            try:
                result['tx_power'] = float(tx_power_match.group(1))
            except ValueError:
                pass
        
        # Extract distance
        distance_match = re.search(r'ONT distance\(m\)\s*:\s*(\d+)', output)
        if distance_match:
            try:
                result['distance'] = int(distance_match.group(1))
            except ValueError:
                pass
        
        # Extract last down cause
        last_down_cause_match = re.search(r'Last down cause\s*:\s*(.+)', output)
        if last_down_cause_match:
            result['last_down_cause'] = last_down_cause_match.group(1).strip()
        
        # Extract last up time
        last_up_time_match = re.search(r'Last up time\s*:\s*(.+)', output)
        if last_up_time_match:
            result['last_up_time'] = last_up_time_match.group(1).strip()
        
        return result
    
    @staticmethod
    def _parse_zte_ont_status(output: str) -> Dict[str, Any]:
        """
        Parse ZTE ONT status output.
        
        Args:
            output: Command output to parse
            
        Returns:
            Dict[str, Any]: ONT status information
        """
        result = {}
        
        # Extract admin state
        admin_state_match = re.search(r'Admin state\s*:\s*(\w+)', output)
        if admin_state_match:
            result['admin_status'] = admin_state_match.group(1).lower()
        
        # Extract OMCC state
        omcc_state_match = re.search(r'OMCC state\s*:\s*(\w+)', output)
        if omcc_state_match:
            result['omcc_state'] = omcc_state_match.group(1).lower()
        
        # Extract phase state
        phase_state_match = re.search(r'Phase state\s*:\s*(\w+)', output)
        if phase_state_match:
            result['status'] = phase_state_match.group(1).lower()
        
        # Extract optical power
        rx_power_match = re.search(r'Rx power\(dBm\)\s*:\s*([-\d.]+)', output)
        if rx_power_match:
            try:
                result['rx_power'] = float(rx_power_match.group(1))
            except ValueError:
                pass
        
        tx_power_match = re.search(r'Tx power\(dBm\)\s*:\s*([-\d.]+)', output)
        if tx_power_match:
            try:
                result['tx_power'] = float(tx_power_match.group(1))
            except ValueError:
                pass
        
        # Extract distance
        distance_match = re.search(r'Distance\(m\)\s*:\s*(\d+)', output)
        if distance_match:
            try:
                result['distance'] = int(distance_match.group(1))
            except ValueError:
                pass
        
        # Extract last down reason
        last_down_reason_match = re.search(r'Last down reason\s*:\s*(.+)', output)
        if last_down_reason_match:
            result['last_down_cause'] = last_down_reason_match.group(1).strip()
        
        return result
    
    @staticmethod
    def parse_ont_list(output: str, vendor: str) -> List[Dict[str, Any]]:
        """
        Parse ONT list output.
        
        Args:
            output: Command output to parse
            vendor: OLT vendor (e.g., 'huawei', 'zte')
            
        Returns:
            List[Dict[str, Any]]: List of ONT information dictionaries
        """
        if vendor.lower() == 'huawei':
            return OutputParser._parse_huawei_ont_list(output)
        elif vendor.lower() == 'zte':
            return OutputParser._parse_zte_ont_list(output)
        else:
            raise ParseError(f"Unsupported vendor: {vendor}")
    
    @staticmethod
    def _parse_huawei_ont_list(output: str) -> List[Dict[str, Any]]:
        """
        Parse Huawei ONT list output.
        
        Args:
            output: Command output to parse
            
        Returns:
            List[Dict[str, Any]]: List of ONT information dictionaries
        """
        result = []
        
        # Regular expression to match ONT entries
        # Example: "  1    FHTT12345678    online    1    "
        ont_pattern = re.compile(r'^\s*(\d+)\s+(\S+)\s+(\S+)\s+(\d+)\s*$')
        
        for line in output.splitlines():
            match = ont_pattern.match(line)
            if match:
                ont_id, serial_number, status, port_count = match.groups()
                
                ont = {
                    'ont_id': ont_id,
                    'serial_number': serial_number,
                    'status': status.lower(),
                    'port_count': int(port_count)
                }
                
                result.append(ont)
        
        return result
    
    @staticmethod
    def _parse_zte_ont_list(output: str) -> List[Dict[str, Any]]:
        """
        Parse ZTE ONT list output.
        
        Args:
            output: Command output to parse
            
        Returns:
            List[Dict[str, Any]]: List of ONT information dictionaries
        """
        result = []
        
        # Regular expression to match ONT entries
        # Example: "  1/1/1    1    ZTEG12345678    online"
        ont_pattern = re.compile(r'^\s*(\S+)\s+(\d+)\s+(\S+)\s+(\S+)\s*$')
        
        for line in output.splitlines():
            match = ont_pattern.match(line)
            if match:
                gpon_index, ont_id, serial_number, status = match.groups()
                
                ont = {
                    'gpon_index': gpon_index,
                    'ont_id': ont_id,
                    'serial_number': serial_number,
                    'status': status.lower()
                }
                
                result.append(ont)
        
        return result
    
    @staticmethod
    def extract_section(output: str, section_start: str, section_end: Optional[str] = None) -> str:
        """
        Extract a section from the output.
        
        Args:
            output: Command output to parse
            section_start: String that marks the start of the section
            section_end: Optional string that marks the end of the section
            
        Returns:
            str: Extracted section
        """
        lines = output.splitlines()
        start_index = -1
        end_index = len(lines)
        
        # Find the start of the section
        for i, line in enumerate(lines):
            if section_start in line:
                start_index = i + 1
                break
        
        # If start not found, return empty string
        if start_index == -1:
            return ""
        
        # Find the end of the section if specified
        if section_end:
            for i in range(start_index, len(lines)):
                if section_end in lines[i]:
                    end_index = i
                    break
        
        # Extract the section
        section_lines = lines[start_index:end_index]
        return "\n".join(section_lines).strip()
    
    @staticmethod
    def parse_system_info(output: str, vendor: str) -> Dict[str, Any]:
        """
        Parse system information output.
        
        Args:
            output: Command output to parse
            vendor: OLT vendor (e.g., 'huawei', 'zte')
            
        Returns:
            Dict[str, Any]: System information
        """
        if vendor.lower() == 'huawei':
            return OutputParser._parse_huawei_system_info(output)
        elif vendor.lower() == 'zte':
            return OutputParser._parse_zte_system_info(output)
        else:
            raise ParseError(f"Unsupported vendor: {vendor}")
    
    @staticmethod
    def _parse_huawei_system_info(output: str) -> Dict[str, Any]:
        """
        Parse Huawei system information output.
        
        Args:
            output: Command output to parse
            
        Returns:
            Dict[str, Any]: System information
        """
        result = {}
        
        # Extract product name
        product_match = re.search(r'Product name\s*:\s*(.+)', output)
        if product_match:
            result['model'] = product_match.group(1).strip()
        
        # Extract product version
        version_match = re.search(r'Product version\s*:\s*(.+)', output)
        if version_match:
            result['firmware_version'] = version_match.group(1).strip()
        
        # Extract patch version
        patch_match = re.search(r'Patch version\s*:\s*(.+)', output)
        if patch_match:
            result['patch_version'] = patch_match.group(1).strip()
        
        # Extract uptime
        uptime_match = re.search(r'Uptime is\s*(.+)', output)
        if uptime_match:
            result['uptime'] = uptime_match.group(1).strip()
        
        return result
    
    @staticmethod
    def _parse_zte_system_info(output: str) -> Dict[str, Any]:
        """
        Parse ZTE system information output.
        
        Args:
            output: Command output to parse
            
        Returns:
            Dict[str, Any]: System information
        """
        result = {}
        
        # Extract system information
        model_match = re.search(r'ZTE\s+(\S+)', output)
        if model_match:
            result['model'] = model_match.group(1).strip()
        
        # Extract version
        version_match = re.search(r'Version\s*:\s*(.+)', output)
        if version_match:
            result['firmware_version'] = version_match.group(1).strip()
        
        # Extract uptime
        uptime_match = re.search(r'The system has been running for\s*(.+)', output)
        if uptime_match:
            result['uptime'] = uptime_match.group(1).strip()
        
        return result
