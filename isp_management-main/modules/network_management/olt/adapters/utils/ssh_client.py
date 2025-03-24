"""
SSH Client Utility Module

This module provides an SSH client for connecting to OLT devices.
"""

import logging
import time
import socket
import paramiko
from typing import Optional, List, Tuple, Dict, Any

from ....olt.exceptions import OLTConnectionError, OLTCommandError

logger = logging.getLogger(__name__)


class SSHClient:
    """
    SSH client for connecting to OLT devices.
    
    This class provides methods for establishing SSH connections to OLT devices
    and executing commands on them.
    """
    
    def __init__(self, host: str, username: str, password: str, port: int = 22,
                 timeout: int = 30, command_timeout: int = 60):
        """
        Initialize the SSH client.
        
        Args:
            host: Hostname or IP address of the OLT device
            username: SSH username
            password: SSH password
            port: SSH port (default: 22)
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
        self.shell = None
        self._connected = False
        self.prompt = None
    
    def connect(self) -> bool:
        """
        Establish an SSH connection to the OLT device.
        
        Returns:
            bool: True if connection is successful, False otherwise
            
        Raises:
            OLTConnectionError: If connection fails
        """
        if self._connected:
            return True
        
        try:
            # Create a new SSH client
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to the device
            logger.info(f"Connecting to {self.host}:{self.port} via SSH")
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False
            )
            
            # Open a shell channel
            self.shell = self.client.invoke_shell()
            self.shell.settimeout(self.command_timeout)
            
            # Wait for the initial prompt
            output = self._read_until_prompt()
            
            # Try to detect the prompt
            lines = output.splitlines()
            if lines:
                self.prompt = lines[-1].strip()
                logger.debug(f"Detected prompt: {self.prompt}")
            
            self._connected = True
            logger.info(f"Successfully connected to {self.host}")
            return True
            
        except (paramiko.SSHException, socket.error, socket.timeout) as e:
            if self.client:
                self.client.close()
            self.client = None
            self.shell = None
            self._connected = False
            error_msg = f"Failed to connect to {self.host}:{self.port}: {str(e)}"
            logger.error(error_msg)
            raise OLTConnectionError(error_msg)
    
    def disconnect(self) -> None:
        """
        Close the SSH connection.
        """
        if self.shell:
            self.shell.close()
        
        if self.client:
            self.client.close()
        
        self.shell = None
        self.client = None
        self._connected = False
        logger.info(f"Disconnected from {self.host}")
    
    def is_connected(self) -> bool:
        """
        Check if the SSH connection is active.
        
        Returns:
            bool: True if connected, False otherwise
        """
        if not self._connected or not self.client or not self.shell:
            return False
        
        try:
            # Send a simple command to check if the connection is still active
            self.shell.send("\n")
            time.sleep(0.5)
            if self.shell.recv_ready():
                self.shell.recv(1024)
                return True
            return False
        except (paramiko.SSHException, socket.error, socket.timeout):
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
            if self.shell.recv_ready():
                self.shell.recv(1024)
            
            # Send the command
            logger.debug(f"Executing command: {command}")
            self.shell.send(command + "\n")
            
            # Read the output
            output = self._read_until_prompt(timeout)
            
            # Remove the command from the output
            lines = output.splitlines()
            if lines and command in lines[0]:
                output = "\n".join(lines[1:])
            
            return output.strip()
            
        except (paramiko.SSHException, socket.error, socket.timeout) as e:
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
    
    def _read_until_prompt(self, timeout: Optional[int] = None) -> str:
        """
        Read shell output until a prompt is detected.
        
        Args:
            timeout: Optional timeout in seconds (overrides default)
            
        Returns:
            str: Shell output
            
        Raises:
            OLTCommandError: If reading times out
        """
        if timeout is None:
            timeout = self.command_timeout
        
        buffer = ""
        start_time = time.time()
        
        while True:
            # Check for timeout
            if time.time() - start_time > timeout:
                raise OLTCommandError(f"Timeout waiting for prompt after {timeout} seconds")
            
            # Check if there's data to read
            if not self.shell.recv_ready():
                time.sleep(0.1)
                continue
            
            # Read data
            chunk = self.shell.recv(1024).decode("utf-8", errors="ignore")
            buffer += chunk
            
            # Check for common prompt characters
            if buffer.endswith(">") or buffer.endswith("#") or buffer.endswith("$"):
                return buffer
            
            # Check if we've detected a prompt previously
            if self.prompt and buffer.endswith(self.prompt):
                return buffer
