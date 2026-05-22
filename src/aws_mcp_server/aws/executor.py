"""AWS CLI command execution module."""

import json
import shlex
import subprocess
from botocore.exceptions import NoCredentialsError
from loguru import logger
from typing import Any


class AwsExecutionError(Exception):
    """Error executing AWS CLI command."""

    def __init__(self, message: str, stderr: str = "", returncode: int = 1):
        self.message = message
        self.stderr = stderr
        self.returncode = returncode
        super().__init__(self.message)


def execute_aws_command(
    command: str,
    working_dir: str | None = None,
    timeout: int = 300,
) -> dict[str, Any]:
    """Execute an AWS CLI command and return the result.

    Args:
        command: The AWS CLI command to execute (must start with 'aws')
        working_dir: Optional working directory for the command
        timeout: Command timeout in seconds

    Returns:
        Dictionary containing:
            - success: bool indicating if command succeeded
            - output: Parsed JSON output or raw stdout
            - error: Error message if command failed
            - returncode: Command return code

    Raises:
        AwsExecutionError: If command execution fails
    """
    # Validate command
    command = command.strip()
    if not command.startswith("aws "):
        raise AwsExecutionError(
            f"Command must start with 'aws ': {command}",
        )

    # Prepare the command.
    # Use shell=False for security and shlex for quoted JSON/paths/arguments.
    try:
        cmd_parts = shlex.split(command)
    except ValueError as e:
        raise AwsExecutionError(f"Invalid command syntax: {e}") from e

    logger.debug(f"Executing AWS command: {command}")

    try:
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            cwd=working_dir,
            timeout=timeout,
        )

        if result.returncode == 0:
            # Try to parse as JSON
            output = result.stdout.strip()
            if output:
                try:
                    parsed_output = json.loads(output)
                except json.JSONDecodeError:
                    # Not JSON, return as string
                    parsed_output = output
            else:
                parsed_output = {"message": "Command executed successfully (no output)"}

            return {
                "success": True,
                "output": parsed_output,
                "error": None,
                "returncode": result.returncode,
            }
        else:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            logger.error(f"AWS command failed: {error_msg}")
            return {
                "success": False,
                "output": None,
                "error": error_msg,
                "returncode": result.returncode,
            }

    except subprocess.TimeoutExpired:
        logger.error(f"AWS command timed out after {timeout}s")
        raise AwsExecutionError(f"Command timed out after {timeout} seconds")
    except FileNotFoundError:
        logger.error("AWS CLI not found")
        raise AwsExecutionError(
            "AWS CLI not found. Please ensure 'aws' is installed and in PATH",
        )
    except NoCredentialsError as e:
        logger.error(f"AWS credentials error: {e}")
        raise AwsExecutionError(
            "AWS credentials not found. Please configure credentials using 'aws configure' "
            "or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables",
        )
    except Exception as e:
        logger.error(f"Unexpected error executing AWS command: {e}")
        raise AwsExecutionError(f"Unexpected error: {str(e)}")


def is_destructive_command(command: str) -> bool:
    """Check if an AWS command is potentially destructive.

    Args:
        command: The AWS CLI command to check

    Returns:
        True if the command appears to be destructive (delete, remove, terminate, etc.)
    """
    command_lower = command.lower()

    # Destructive keywords
    destructive_keywords = [
        "delete",
        "remove",
        "rm",
        "terminate",
        "destroy",
        "detach",
        "revoke",
        "disable",
        "stop",
        "deactivate",
        "cancel",
        "abandon",
        "fail",
        "reject",
    ]

    # Check for destructive operations
    for keyword in destructive_keywords:
        if keyword in command_lower:
            return True

    return False


def suggest_commands(query: str) -> list[dict[str, Any]]:
    """Suggest AWS CLI commands based on a natural language query.

    This is a simple implementation that returns common command patterns.
    For production, this could integrate with an LLM or use a more sophisticated approach.

    Args:
        query: Natural language description of what the user wants to do

    Returns:
        List of suggested commands with descriptions
    """
    query_lower = query.lower()
    suggestions = []

    # Common AWS service patterns
    patterns = {
        "ec2": {
            "list instances": "aws ec2 describe-instances",
            "start instance": "aws ec2 start-instances --instance-ids <instance-id>",
            "stop instance": "aws ec2 stop-instances --instance-ids <instance-id>",
            "create instance": "aws ec2 run-instances --image-id <ami-id> --instance-type <type>",
        },
        "s3": {
            "list buckets": "aws s3 ls",
            "list objects": "aws s3 ls s3://<bucket-name>",
            "upload file": "aws s3 cp <local-file> s3://<bucket-name>/<key>",
            "download file": "aws s3 cp s3://<bucket-name>/<key> <local-file>",
        },
        "lambda": {
            "list functions": "aws lambda list-functions",
            "invoke function": "aws lambda invoke --function-name <name> --payload '<json>' output.json",
            "get function": "aws lambda get-function --function-name <name>",
        },
        "iam": {
            "list users": "aws iam list-users",
            "list roles": "aws iam list-roles",
            "get user": "aws iam get-user --user-name <username>",
        },
        "cloudwatch": {
            "list metrics": "aws cloudwatch list-metrics",
            "get logs": "aws logs describe-log-groups",
        },
        "rds": {
            "list databases": "aws rds describe-db-instances",
            "list clusters": "aws rds describe-db-clusters",
        },
    }

    # Match query against patterns
    for service, commands in patterns.items():
        if service in query_lower:
            for description, cmd in commands.items():
                if any(word in query_lower for word in description.split()):
                    suggestions.append({
                        "command": cmd,
                        "description": f"{service.upper()}: {description}",
                        "confidence": 0.8,
                    })

    # If no specific matches, provide general suggestions
    if not suggestions:
        suggestions = [
            {
                "command": "aws ec2 describe-instances",
                "description": "List all EC2 instances",
                "confidence": 0.5,
            },
            {
                "command": "aws s3 ls",
                "description": "List all S3 buckets",
                "confidence": 0.5,
            },
            {
                "command": "aws lambda list-functions",
                "description": "List all Lambda functions",
                "confidence": 0.5,
            },
        ]

    return suggestions[:10]  # Return max 10 suggestions
