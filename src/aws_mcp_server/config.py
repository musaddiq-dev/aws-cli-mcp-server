"""Configuration settings for AWS MCP Server."""

import os
from dotenv import load_dotenv
from pathlib import Path
from typing import Literal


# Load environment variables from .env file
load_dotenv()


# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_PROFILE = os.getenv("AWS_PROFILE", "default")

# MCP Server Configuration
WORKING_DIRECTORY = os.getenv("AWS_MCP_WORKING_DIR", "/tmp/aws-mcp-work")
TRANSPORT: Literal["stdio", "http"] = os.getenv("AWS_MCP_TRANSPORT", "stdio")  # type: ignore
REQUIRE_CONFIRMATION = os.getenv("AWS_MCP_REQUIRE_CONFIRMATION", "true").lower() == "true"
LOG_LEVEL = os.getenv("AWS_MCP_LOG_LEVEL", "INFO")

# HTTP Transport Settings
HOST = os.getenv("AWS_MCP_HOST", "127.0.0.1")
PORT = int(os.getenv("AWS_MCP_PORT", "8080"))

# FastMCP Settings
FASTMCP_LOG_LEVEL = os.getenv("FASTMCP_LOG_LEVEL", "WARNING")

# Server Metadata
SERVER_NAME = "aws_mcp"
SERVER_VERSION = "0.1.0"


def validate_config():
    """Validate the configuration settings."""
    # Ensure working directory is absolute
    if not os.path.isabs(WORKING_DIRECTORY):
        raise ValueError(f"AWS_MCP_WORKING_DIR must be an absolute path: {WORKING_DIRECTORY}")

    # Create working directory if it doesn't exist
    Path(WORKING_DIRECTORY).mkdir(parents=True, exist_ok=True)

    # Validate transport
    if TRANSPORT not in ("stdio", "http"):
        raise ValueError(f"Invalid transport: {TRANSPORT}. Must be 'stdio' or 'http'")

    # Validate log level
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if LOG_LEVEL not in valid_levels:
        raise ValueError(f"Invalid log level: {LOG_LEVEL}. Must be one of {valid_levels}")

    return True
