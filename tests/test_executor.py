"""Tests for AWS executor module."""

import pytest
from aws_mcp_server.aws.executor import (
    AwsExecutionError,
    execute_aws_command,
    is_destructive_command,
    suggest_commands,
)


class TestIsDestructiveCommand:
    """Tests for is_destructive_command function."""

    def test_delete_command_is_destructive(self):
        assert is_destructive_command("aws ec2 delete-instance") is True

    def test_terminate_command_is_destructive(self):
        assert is_destructive_command("aws ec2 terminate-instances") is True

    def test_remove_command_is_destructive(self):
        assert is_destructive_command("aws s3 rm s3://bucket/file") is True

    def test_describe_command_is_not_destructive(self):
        assert is_destructive_command("aws ec2 describe-instances") is False

    def test_list_command_is_not_destructive(self):
        assert is_destructive_command("aws s3 ls") is False

    def test_get_command_is_not_destructive(self):
        assert is_destructive_command("aws iam get-user") is False


class TestSuggestCommands:
    """Tests for suggest_commands function."""

    def test_suggest_ec2_commands(self):
        suggestions = suggest_commands("List EC2 instances")
        assert len(suggestions) > 0
        assert any("ec2" in s["command"].lower() for s in suggestions)

    def test_suggest_s3_commands(self):
        suggestions = suggest_commands("List S3 buckets")
        assert len(suggestions) > 0
        assert any("s3" in s["command"].lower() for s in suggestions)

    def test_suggest_returns_limited_results(self):
        suggestions = suggest_commands("AWS commands")
        assert len(suggestions) <= 10

    def test_suggestions_have_required_fields(self):
        suggestions = suggest_commands("List EC2")
        for suggestion in suggestions:
            assert "command" in suggestion
            assert "description" in suggestion
            assert "confidence" in suggestion


class TestExecuteAwsCommand:
    """Tests for execute_aws_command function."""

    def test_invalid_command_raises_error(self):
        with pytest.raises(AwsExecutionError):
            execute_aws_command("invalid-command")

    def test_command_must_start_with_aws(self):
        with pytest.raises(AwsExecutionError) as exc_info:
            execute_aws_command("ls -la")
        assert "must start with 'aws '" in str(exc_info.value)

    def test_aws_version_works(self):
        # This should work if AWS CLI is installed
        result = execute_aws_command("aws --version")
        assert result["success"] is True
