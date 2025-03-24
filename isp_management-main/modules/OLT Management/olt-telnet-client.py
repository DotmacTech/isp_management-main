"""
Telnet Client Utility Module

This module provides a unified interface for Telnet connections to network devices,
with extended functionality for command execution and response handling.
"""

import time
import logging
import telnetlib
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class TelnetClient:
    """
    Enhanced Telnet client for network equipment connections.
    
    Provides reliable connections to network equipment with automatic
    reconnection, command timeout handling, and output parsing conveniences.
    """
    
    def __init__(self, host: str, username: str, password: str, port: int = 23,
                 timeout: int = 10, encoding: str = 'ascii'):
        """
        Initialize a new Telnet client.
        
        Args:
            host: Hostname or IP address of the device
            username: Telnet username
            password: Telnet password
            port: Telnet port (default: 23)
            timeout: Connection timeout in seconds (default: 10)
            encoding: Character encoding for I/O (default: 'ascii')
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.encoding = encoding
        
        self.client = None
        self.prompt = None
    
    def connect(self) -> bool:
        """
        Establish a Telnet connection to the device.
        
        Returns:
            bool: True if connection is successful, False otherwise.
        """
        try:
            logger.info(f"Connecting to {self.host}:{self.port} via Telnet")
            
            # Create new Telnet client
            self.client = telnetlib.Telnet(self.host, self.port, self.timeout)
            
            # Handle login sequence
            username_prompt = self.client.read_until(b'Username:', self.timeout)
            self.client.write(self.username.encode(self.encoding) + b'\n')
            
            password_prompt = self.client.read_until(b'Password:', self.timeout)
            self.client.write(self.password.encode(self.encoding) + b'\n')
            
            # Wait for prompt
            time.sleep(1)
            response = self.client.read_very_eager().decode(self.encoding, errors='ignore')
            
            # Try to detect the prompt from the last line
            lines = response.splitlines()
            if lines:
                self.prompt = lines[-1].strip()
                logger.debug(f"Detected prompt: {self.prompt}")
            
            logger.info(f"Successfully connected to {self.host}")
            return True
            
        except Exception as e:
            logger.error(f"Telnet connection to {self.host} failed: {str(e)}")
            self.disconnect()
            return False
    
    def disconnect(self) -> None:
        """Close the Telnet connection to the device."""
        try:
            if self.client:
                self.client.close()
                self.client = None
                
            logger.info(f"Disconnected from {self.host}")
        except Exception as e:
            logger.error(f"Error disconnecting from {self.host}: {str(e)}")
    
    def is_connected(self) -> bool:
        """
        Check if the Telnet connection is still active.
        
        Returns:
            bool: True if connected, False otherwise.
        """
        if not self.client:
            return False
        
        try:
            # Try to send a newline and see if we get any response
            self.client.write(b'\n')
            time.sleep(0.5)
            response = self.client.read_very_eager()
            return bool(response)
            
        except Exception as e:
            logger.error(f"Error checking Telnet connection to {self.host}: {str(e)}")
            return False
    
    def send_command(self, command: str, wait_time: float = 1.0, 
                    expect_string: Optional[bytes] = None, 
                    max_wait_time: int = 30) -> str:
        """
        Send a command to the device and return the output.
        
        Args:
            command: The command to send
            wait_time: Time to wait after sending command (default: 1.0 seconds)
            expect_string: Optional byte string to wait for in the response
            max_wait_time: Maximum time to wait for expect_string (default: 30 seconds)
            
        Returns:
            str: Command output
            
        Raises:
            ConnectionError: If the connection is lost
            TimeoutError: If expect_string isn't found within max_wait_time
        """
        if not self.is_connected():
            self.connect()
            if not self.is_connected():
                raise ConnectionError(f"Could not establish Telnet connection to {self.host}")
        
        try:
            # Clear buffer before sending command
            self.client.read_very_eager()
            
            # Send the command
            logger.debug(f"Sending command to {self.host}: {command}")
            self.client.write(command.encode(self.encoding) + b'\n')
            
            # If waiting for a specific string in response
            if expect_string:
                output = self.client.read_until(expect_string, max_wait_time)
                output = output.decode(self.encoding, errors='ignore')
            else:
                # Simple wait approach
                time.sleep(wait_time)
                output = self.client.read_very_eager().decode(self.encoding, errors='ignore')
            
            logger.debug(f"Received output from {self.host} for command '{command}'")
            return output
            
        except Exception as e:
            logger.error(f"Error sending command to {self.host}: {str(e)}")
            # Try to reconnect once if there's an error
            self.disconnect()
            if self.connect():
                return self.send_command(command, wait_time, expect_string, max_wait_time)
            raise
    
    def send_commands(self, commands: List[str], wait_time: float = 1.0) -> List[str]:
        """
        Send multiple commands to the device and return their outputs.
        
        Args:
            commands: List of commands to send
            wait_time: Time to wait after sending each command
            
        Returns:
            List[str]: List of command outputs
        """
        results = []
        for cmd in commands:
            results.append(self.send_command(cmd, wait_time))
        return results
    
    def send_config_commands(self, config_commands: List[str], 
                           config_mode_command: str = "config",
                           exit_config_mode_command: str = "exit",
                           wait_time: float = 1.0) -> List[str]:
        """
        Send configuration commands to the device.
        
        Args:
            config_commands: List of configuration commands
            config_mode_command: Command to enter config mode
            exit_config_mode_command: Command to exit config mode
            wait_time: Time to wait after sending each command
            
        Returns:
            List[str]: List of command outputs
        """
        results = []
        
        # Enter configuration mode
        if config_mode_command:
            self.send_command(config_mode_command, wait_time)
        
        # Send configuration commands
        for cmd in config_commands:
            results.append(self.send_command(cmd, wait_time))
        
        # Exit configuration mode
        if exit_config_mode_command:
            self.send_command(exit_config_mode_command, wait_time)
        
        return results