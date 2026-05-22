"""Main MCP server implementation for AWS."""

import os
import sys
from aws_mcp_server.aws.executor import (
    AwsExecutionError,
    execute_aws_command,
    is_destructive_command,
    suggest_commands,
)
from aws_mcp_server.config import (
    AWS_REGION,
    FASTMCP_LOG_LEVEL,
    LOG_LEVEL,
    REQUIRE_CONFIRMATION,
    SERVER_NAME,
    SERVER_VERSION,
    TRANSPORT,
    WORKING_DIRECTORY,
    validate_config,
)
from fastmcp import Context, FastMCP
from loguru import logger
from mcp.types import ToolAnnotations
from pydantic import Field
from typing import Any
from typing_extensions import Annotated


# Configure logging
logger.remove()
logger.add(sys.stderr, level=LOG_LEVEL)

# Add file logging
log_dir = os.path.expanduser("~/.aws-mcp-server/logs")
os.makedirs(log_dir, exist_ok=True)
logger.add(
    os.path.join(log_dir, "aws-mcp-server.log"),
    rotation="10 MB",
    retention="7 days",
    level=LOG_LEVEL,
)

# Initialize FastMCP server
mcp = FastMCP(SERVER_NAME)


@mcp.tool(
    name="call_aws",
    description=f"""Execute AWS CLI commands with validation and error handling.

This is the primary tool for executing AWS CLI commands. Use this when you know
the specific AWS service and operation you want to perform.

Key points:
- Commands MUST start with "aws" and follow AWS CLI syntax
- Default region: {AWS_REGION} (override with --region parameter)
- Working directory: {WORKING_DIRECTORY}
- Use absolute paths for files

Command restrictions:
- DO NOT use shell pipes (|), redirects (>, >>, <), or command substitution ($())
- DO NOT use shell variables or environment variables
- DO NOT use relative paths for file operations

Examples:
- "aws ec2 describe-instances" - List EC2 instances
- "aws s3 ls" - List S3 buckets
- "aws lambda list-functions" - List Lambda functions
- "aws iam list-users" - List IAM users
- "aws cloudwatch describe-alarms" - List CloudWatch alarms

Returns:
    Dictionary with success status, output data, and error information
""",
    annotations=ToolAnnotations(
        title="Execute AWS CLI Command",
        readOnlyHint=False,
        destructiveHint=True,
        openWorldHint=True,
    ),
)
async def call_aws(
    cli_command: Annotated[
        str,
        Field(
            description="The complete AWS CLI command to execute. MUST start with 'aws'",
            examples=["aws ec2 describe-instances", "aws s3 ls"],
        ),
    ],
    ctx: Context,
    max_results: Annotated[
        int | None,
        Field(
            description="Optional limit for number of results (useful for pagination)",
            default=None,
        ),
    ] = None,
) -> dict[str, Any]:
    """Execute an AWS CLI command and return the results.

    Args:
        cli_command: The AWS CLI command to execute
        ctx: MCP context for logging and progress reporting
        max_results: Optional limit for results

    Returns:
        Dictionary containing command results or error information
    """
    command = cli_command.strip()

    logger.info(f"Executing AWS command: {command}")
    await ctx.info(f"Executing: {command}")

    # Validate command starts with 'aws'
    if not command.startswith("aws "):
        error_msg = f"Command must start with 'aws ': {command}"
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "output": None,
        }

    # Check for destructive operations
    if REQUIRE_CONFIRMATION and is_destructive_command(command):
        warning_msg = (
            f"WARNING: This command appears to be destructive: {command}\n"
            "This operation may delete, terminate, or modify AWS resources."
        )
        logger.warning(warning_msg)
        await ctx.info(warning_msg)

    try:
        result = execute_aws_command(
            command=command,
            working_dir=WORKING_DIRECTORY,
        )

        # Apply max_results limit if specified
        if max_results and result["success"] and isinstance(result["output"], list):
            result["output"] = result["output"][:max_results]
            result["truncated"] = True

        if result["success"]:
            logger.info(f"Command executed successfully: {command}")
            await ctx.info("Command executed successfully")
        else:
            logger.error(f"Command failed: {result.get('error', 'Unknown error')}")
            await ctx.error(f"Command failed: {result.get('error', 'Unknown error')}")

        return result

    except AwsExecutionError as e:
        error_msg = f"AWS execution error: {e.message}"
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "output": None,
        }
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "output": None,
        }


@mcp.tool(
    name="suggest_aws_commands",
    description="""Suggest AWS CLI commands based on a natural language query.

Use this tool when you're unsure about the exact AWS CLI command syntax or
want to explore available commands for a specific task.

Best practices for query formulation:
1. Include the AWS service name (EC2, S3, Lambda, etc.)
2. Describe the action you want to perform
3. Include any relevant context or constraints

Query examples:
- "List all running EC2 instances in us-east-1"
- "Get the size of my S3 bucket named 'my-backup-bucket'"
- "List all IAM users with AdministratorAccess policy"
- "Show me all Lambda functions in my account"
- "Create a new security group for SSH access"

Returns:
    Dictionary with success status, query, and list of suggested commands
""",
    annotations=ToolAnnotations(
        title="Suggest AWS CLI Commands",
        readOnlyHint=True,
        openWorldHint=False,
    ),
)
async def suggest_aws_commands(
    query: Annotated[
        str,
        Field(
            description="Natural language description of what you want to accomplish",
            max_length=2000,
            examples=[
                "List all EC2 instances",
                "Create an S3 bucket",
                "Get Lambda function details",
            ],
        ),
    ],
    ctx: Context,
) -> dict[str, Any]:
    """Suggest AWS CLI commands based on a natural language query.

    Args:
        query: Natural language description of the task
        ctx: MCP context for logging

    Returns:
        Dictionary containing suggested commands
    """
    query = query.strip()

    if not query:
        error_msg = "Empty query provided"
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "suggestions": [],
        }

    logger.info(f"Suggesting commands for query: {query}")
    await ctx.info(f"Analyzing query: {query}")

    try:
        suggestions = suggest_commands(query)

        logger.info(f"Found {len(suggestions)} suggestions")
        await ctx.info(f"Found {len(suggestions)} command suggestions")

        return {
            "success": True,
            "query": query,
            "suggestions": suggestions,
            "error": None,
        }

    except Exception as e:
        error_msg = f"Error generating suggestions: {str(e)}"
        logger.error(error_msg)
        await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "suggestions": [],
        }


@mcp.tool(
    name="get_aws_regions",
    description="""Get a list of available AWS regions.

Returns:
    Dictionary with success status and list of AWS regions
""",
    annotations=ToolAnnotations(
        title="Get AWS Regions",
        readOnlyHint=True,
        openWorldHint=False,
    ),
)
async def get_aws_regions(ctx: Context) -> dict[str, Any]:
    """Get a list of available AWS regions.

    Args:
        ctx: MCP context

    Returns:
        Dictionary containing list of regions
    """
    logger.info("Getting AWS regions")
    await ctx.info("Fetching AWS regions...")

    try:
        result = execute_aws_command("aws ec2 describe-regions")
        return result
    except Exception as e:
        error_msg = f"Error fetching regions: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "output": None,
        }


@mcp.tool(
    name="get_caller_identity",
    description="""Get the AWS identity of the current caller.

Returns information about the IAM user or role whose credentials are used
to call the operation.

Returns:
    Dictionary with success status and caller identity (Account, ARN, UserId)
""",
    annotations=ToolAnnotations(
        title="Get Caller Identity",
        readOnlyHint=True,
        openWorldHint=False,
    ),
)
async def get_caller_identity(ctx: Context) -> dict[str, Any]:
    """Get the AWS identity of the current caller.

    Args:
        ctx: MCP context

    Returns:
        Dictionary containing caller identity information
    """
    logger.info("Getting caller identity")
    await ctx.info("Fetching caller identity...")

    try:
        result = execute_aws_command("aws sts get-caller-identity")
        return result
    except Exception as e:
        error_msg = f"Error fetching caller identity: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "output": None,
        }


def main():
    """Main entry point for the AWS MCP server."""
    logger.info(f"Starting {SERVER_NAME} v{SERVER_VERSION}")
    logger.info(f"Transport: {TRANSPORT}")
    logger.info(f"Working directory: {WORKING_DIRECTORY}")
    logger.info(f"Default region: {AWS_REGION}")

    # Validate configuration
    try:
        validate_config()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Change to working directory
    os.chdir(WORKING_DIRECTORY)
    logger.info(f"Changed working directory to: {WORKING_DIRECTORY}")

    # Run the server
    try:
        mcp.run(transport=TRANSPORT, log_level=FASTMCP_LOG_LEVEL)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
