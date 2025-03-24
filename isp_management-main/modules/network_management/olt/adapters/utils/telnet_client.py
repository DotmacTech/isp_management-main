"""
Telnet Client Utility Module

This module provides a Telnet client for connecting to OLT devices.
"""

import logging
import time
import socket
import telnetlib
from typing import Optional, List, Tuple, Dict, Any

from ....olt.exceptions import OLTConnectionError, OLTCommandError

logger = logging.getLogger(__name__)


class TelnetClient:
    """
    Telnet client for connecting to OLT devices.
    
    This class provides methods for establishing Telnet connections to OLT devices
    and executing commands on them.
    """
    
    def __init__(self, host: str, username: str, password: str, port: int = 23,
                 timeout: int = 30, command_timeout: int = 60):
        """
        Initialize the Telnet client.
        
        Args:
            host: Hostname or IP address of the OLT device
            username: Telnet username
            password: Telnet password
            port: Telnet port (default: 23)
            timeout: Connection timeout in seconds (default: 30)
            command_timeout: Command execution timeout in seconds (default: 60)
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.command_timeout = command_timeout
        self.client = None
        self._connected = False
        self.prompt = None
        
        # Common prompt patterns
        self.prompt_patterns = [b">", b"#", b"$", b":", b"]"]
        
        # Authentication prompts
        self.username_prompt = b"[Uu]sername:|[Ll]ogin:"
        self.password_prompt = b"[Pp]assword:"
    
    def connect(self) -> bool:
        """
        Establish a Telnet connection to the OLT device.
        
        Returns:
            bool: True if connection is successful, False otherwise
            
        Raises:
            OLTConnectionError: If connection fails
        """
        if self._connected:
            return True
        
        try:
            # Create a new Telnet client
            logger.info(f"Connecting to {self.host}:{self.port} via Telnet")
            self.client = telnetlib.Telnet(self.host, self.port, self.timeout)
            
            # Handle login
            index, match, text = self.client.expect([self.username_prompt, self.password_prompt], self.timeout)
            
            if index == 0:  # Username prompt
                self.client.write(self.username.encode('ascii') + b"\n")
                self.client.expect([self.password_prompt], self.timeout)
                self.client.write(self.password.encode('ascii') + b"\n")
            elif index == 1:  # Password prompt
                self.client.write(self.password.encode('ascii') + b"\n")
            else:
                raise OLTConnectionError(f"Unexpected login prompt: {text.decode('ascii', errors='ignore')}")
            
            # Wait for the initial prompt
            index, match, text = self.client.expect(self.prompt_patterns, self.timeout)
            
            if index >= 0:
                # Try to detect the prompt
                lines = text.decode('ascii', errors='ignore').splitlines()
                if lines:
                    self.prompt = lines[-1].strip()
                    logger.debug(f"Detected prompt: {self.prompt}")
                    # Add the detected prompt to the prompt patterns
                    if self.prompt:
                        self.prompt_patterns.append(self.prompt.encode('ascii'))
                
                self._connected = True
                logger.info(f"Successfully connected to {self.host}")
                return True
            else:
                raise OLTConnectionError(f"Failed to detect prompt after login")
            
        except (socket.error, socket.timeout, EOFError) as e:
            if self.client:
                self.client.close()
            self.client = None
            self._connected = False
            error_msg = f"Failed to connect to {self.host}:{self.port}: {str(e)}"
            logger.error(error_msg)
            raise OLTConnectionError(error_msg)
    
    def disconnect(self) -> None:
        """
        Close the Telnet connection.
        """
        if self.client:
            self.client.close()
        
        self.client = None
        self._connected = False
        logger.info(f"Disconnected from {self.host}")
    
    def is_connected(self) -> bool:
        """
        Check if the Telnet connection is active.
        
        Returns:
            bool: True if connected, False otherwise
        """
        if not self._connected or not self.client:
            return False
        
        try:
            # Send a simple command to check if the connection is still active
            self.client.write(b"\n")
            self.client.read_until(b"\n", 1)
            return True
        except (socket.error, socket.timeout, EOFError):
            self._connected = False
            return False
    
    def execute_command(self, command: str, timeout: Optional[int] = None) -> str:
        """
        Execute a command on the OLT device.
        
        Args:
            command: The command to execute
            timeout: Optional timeout in seconds (overrides default)
            
        Returns:
            str: Command output
            
        Raises:
            OLTConnectionError: If not connected
            OLTCommandError: If command execution fails
        """
        if not self._connected:
            raise OLTConnectionError("Not connected to OLT device")
        
        if timeout is None:
            timeout = self.command_timeout
        
        try:
            # Clear any pending output
            self.client.read_very_eager()
            
            # Send the command
            logger.debug(f"Executing command: {command}")
            self.client.write(command.encode('ascii') + b"\n")
            
            # Read the output until a prompt is detected
            index, match, output = self.client.expect(self.prompt_patterns, timeout)
            
            if index < 0:
                raise OLTCommandError(f"Timeout waiting for prompt after command: {command}")
            
            # Decode the output
            output_str = output.decode('ascii', errors='ignore')
            
            # Remove the command from the output
            lines = output_str.splitlines()
            if lines and command in lines[0]:
                output_str = "\n".join(lines[1:])
            
            return output_str.strip()
            
        except (socket.error, socket.timeout, EOFError) as e:
            error_msg = f"Error executing command '{command}': {str(e)}"
            logger.error(error_msg)
            raise OLTCommandError(error_msg)
    
    def execute_commands(self, commands: List[str], timeout: Optional[int] = None) -> str:
        """
        Execute multiple commands on the OLT device.
        
        Args:
            commands: List of commands to execute
            timeout: Optional timeout in seconds (overrides default)
            
        Returns:
            str: Combined command output
            
        Raises:
            OLTConnectionError: If not connected
            OLTCommandError: If command execution fails
        """
        if not self._connected:
            raise OLTConnectionError("Not connected to OLT device")
        
        outputs = []
        for command in commands:
            output = self.execute_command(command, timeout)
            outputs.append(output)
        
        return "\n".join(outputs)
