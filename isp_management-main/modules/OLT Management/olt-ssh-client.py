"""
SSH Client Utility Module

This module provides a unified interface for SSH connections to network devices,
with extended functionality for command execution and response handling.
"""

import time
import logging
import paramiko
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class SSHClient:
    """
    Enhanced SSH client for network equipment connections.
    
    Provides reliable connections to network equipment with automatic
    reconnection, command timeout handling, and output parsing conveniences.
    """
    
    def __init__(self, host: str, username: str, password: str, port: int = 22,
                 timeout: int = 10, buffer_size: int = 65535):
        """
        Initialize a new SSH client.
        
        Args:
            host: Hostname or IP address of the device
            username: SSH username
            password: SSH password
            port: SSH port (default: 22)
            timeout: Connection timeout in seconds (default: 10)
            buffer_size: Maximum buffer size for responses (default: 65535)
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.buffer_size = buffer_size
        
        self.client = None
        self.shell = None
        self.prompt = None
    
    def connect(self) -> bool:
        """
        Establish an SSH connection to the device.
        
        Returns:
            bool: True if connection is successful, False otherwise.
        """
        try:
            logger.info(f"Connecting to {self.host}:{self.port} via SSH")
            
            # Create new SSH client if none exists
            if not self.client:
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to the device
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False
            )
            
            # Get an interactive shell
            self.shell = self.client.invoke_shell()
            self.shell.settimeout(self.timeout)
            
            # Wait for initial data and detect the prompt
            time.sleep(1)
            initial_output = self.shell.recv(self.buffer_size)
            if initial_output:
                # Try to detect the prompt from the last line
                lines = initial_output.decode('utf-8', errors='ignore').splitlines()
                if lines:
                    self.prompt = lines[-1].strip()
                    logger.debug(f"Detected prompt: {self.prompt}")
            
            logger.info(f"Successfully connected to {self.host}")
            return True
            
        except Exception as e:
            logger.error(f"SSH connection to {self.host} failed: {str(e)}")
            self.disconnect()
            return False
    
    def disconnect(self) -> None:
        """Close the SSH connection to the device."""
        try:
            if self.shell:
                self.shell.close()
                self.shell = None
            
            if self.client:
                self.client.close()
                self.client = None
                
            logger.info(f"Disconnected from {self.host}")
        except Exception as e:
            logger.error(f"Error disconnecting from {self.host}: {str(e)}")
    
    def is_connected(self) -> bool:
        """
        Check if the SSH connection is still active.
        
        Returns:
            bool: True if connected, False otherwise.
        """
        if not self.client or not self.shell:
            return False
        
        try:
            # Try a simple transport check
            transport = self.client.get_transport()
            if transport and transport.is_active():
                # Also verify we can actually communicate
                self.shell.send("\n")
                time.sleep(0.5)
                if self.shell.recv(100):
                    return True
            
            # If we reached here, connection isn't fully working
            logger.debug(f"SSH connection to {self.host} is inactive")
            return False
            
        except Exception as e:
            logger.error(f"Error checking SSH connection to {self.host}: {str(e)}")
            return False
    
    def send_command(self, command: str, wait_time: float = 1.0, 
                    expect_string: Optional[str] = None, 
                    max_wait_time: int = 30) -> str:
        """
        Send a command to the device and return the output.
        
        Args:
            command: The command to send
            wait_time: Time to wait after sending command (default: 1.0 seconds)
            expect_string: Optional string to wait for in the response
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
                raise ConnectionError(f"Could not establish SSH connection to {self.host}")
        
        try:
            # Clear buffer before sending command
            if self.shell.recv_ready():
                self.shell.recv(self.buffer_size)
            
            # Send the command
            logger.debug(f"Sending command to {self.host}: {command}")
            self.shell.send(command + "\n")
            
            # Wait for output
            output = ""
            start_time = time.time()
            
            # If waiting for a specific string in response
            if expect_string:
                while True:
                    # Check for timeout
                    if time.time() - start_time > max_wait_time:
                        raise TimeoutError(
                            f"Timeout waiting for '{expect_string}' in response from {self.host}"
                        )
                    
                    # Wait a bit for more data
                    time.sleep(0.5)
                    if self.shell.recv_ready():
                        chunk = self.shell.recv(self.buffer_size).decode('utf-8', errors='ignore')
                        output += chunk
                        
                        # Found the expected string, can return
                        if expect_string in output:
                            break
            else:
                # Simple wait approach
                time.sleep(wait_time)
                
                # Collect all available data
                while self.shell.recv_ready():
                    chunk = self.shell.recv(self.buffer_size).decode('utf-8', errors='ignore')
                    output += chunk
                    time.sleep(0.1)
            
            # Remove the command and leading lines from output
            lines = output.splitlines()
            if lines and command in lines[0]:
                lines = lines[1:]
            output = "\n".join(lines)
            
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
