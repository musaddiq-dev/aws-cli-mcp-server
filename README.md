<!-- mcp-name: io.github.musaddiq-dev/aws-cli-mcp-server -->
# AWS MCP Server

A Python Model Context Protocol (MCP) server that lets MCP-compatible clients inspect and operate AWS through the AWS CLI. It supports command execution with validation, command suggestions, AWS region lookup, and caller identity checks.

## Features

- Execute AWS CLI commands without shell expansion, preserving quoted arguments with shell-style parsing
- Suggest common AWS CLI commands from natural language requests
- Return available AWS regions
- Return the current caller identity
- Support stdio transport for local MCP clients
- Validate configuration and write logs to stderr plus a local log file

## Safety Model

This server can execute AWS CLI commands using the credentials available to the process. It blocks shell operators by using `subprocess.run(..., shell=False)` and flags destructive-looking commands, but it cannot replace IAM least privilege or human review. Use scoped AWS profiles or roles, prefer non-production accounts for testing, and keep destructive commands on manual approval in your MCP client.

## Requirements

- Python 3.12+
- [AWS CLI v2 installed](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and available on `PATH`
- [AWS CLI authentication configured](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html) and [configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) through an AWS profile, IAM Identity Center/SSO, environment variables, an IAM role, or another AWS-supported credential provider
- MCP-compatible client such as Claude Desktop, Cursor, VS Code, or another MCP host

## Installation

When published to PyPI, install or run the server like a standard Python MCP package:

```bash
uvx mdev-aws-mcp-server
```

For local development from source:

```bash
git clone https://github.com/musaddiq-dev/aws-cli-mcp-server.git
cd aws-cli-mcp-server
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

Before running this server, install the AWS CLI using the official [AWS CLI install guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), then configure credentials using the official [AWS CLI sign-in guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html) and [AWS CLI configuration guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html). AWS recommends short-term credentials where possible; avoid long-term IAM user keys unless your use case requires them.

Copy the example environment file and adjust values as needed.

```bash
cp .env.example .env
```

| Variable | Description | Default |
| --- | --- | --- |
| `AWS_REGION` | Default AWS region | `us-east-1` |
| `AWS_PROFILE` | AWS credentials profile | `default` |
| `AWS_MCP_WORKING_DIR` | Working directory for file operations | `/tmp/aws-mcp-work` |
| `AWS_MCP_REQUIRE_CONFIRMATION` | Emit warnings for destructive-looking operations | `true` |
| `AWS_MCP_LOG_LEVEL` | Application log level | `INFO` |

## Running

```bash
mdev-aws-mcp-server
```

From a local checkout before PyPI publication, run:

```bash
python -m aws_mcp_server.server
```

## MCP Client Configuration

For published installs, prefer `uvx`. MCP servers using stdio must write protocol messages only to stdout; this server writes logs to stderr and a local file under `~/.aws-mcp-server/logs`.

### Claude Desktop / Cursor / Windsurf / Cline

Most MCP clients accept this `mcpServers` JSON shape:

```json
{
  "mcpServers": {
    "aws": {
      "command": "uvx",
      "args": ["mdev-aws-mcp-server"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

For local development from this repository, use the installed console script path instead:

```json
{
  "mcpServers": {
    "aws": {
      "command": "/absolute/path/to/aws-cli-mcp-server/.venv/bin/mdev-aws-mcp-server",
      "args": [],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

### Claude Code CLI

```bash
claude mcp add aws --env AWS_PROFILE=default --env AWS_REGION=us-east-1 -- uvx mdev-aws-mcp-server
```

### VS Code MCP

VS Code uses the same command/args/env model in its MCP configuration:

```json
{
  "servers": {
    "aws": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mdev-aws-mcp-server"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

## Tools

| Tool | Purpose | Safety |
| --- | --- | --- |
| `call_aws` | Execute an AWS CLI command | Can modify AWS resources |
| `suggest_aws_commands` | Suggest common AWS CLI commands | Read-only |
| `get_aws_regions` | List AWS regions | Read-only |
| `get_caller_identity` | Return current AWS identity | Read-only |

## Development

```bash
pip install -e .
pip install -e '.[dev]'
pytest
ruff check .
ruff format .
pyright
```

## Smoke Check

```bash
python -m py_compile src/aws_mcp_server/server.py src/aws_mcp_server/config.py src/aws_mcp_server/aws/executor.py
python -m pytest
```

Manual AWS check, if credentials are configured:

```bash
aws sts get-caller-identity
```

## Distribution

This server is published through the standard Python MCP distribution path:

- PyPI package: [`mdev-aws-mcp-server`](https://pypi.org/project/mdev-aws-mcp-server/)
- MCP Registry name: `io.github.musaddiq-dev/aws-cli-mcp-server`
- Runtime hint: `uvx`
- Transport: `stdio`

The `mcp-name` marker at the top of this README is required for MCP Registry ownership verification. Users should prefer `uvx mdev-aws-mcp-server` in local MCP client configurations.

## Security Notes

- Do not commit `.env`, AWS credentials, profiles, access keys, or account-specific outputs.
- Use least-privilege IAM permissions for the profile or role running this server.
- Keep `call_aws` on explicit manual approval in your MCP client.
- Do not expose this server over a network without adding authentication, TLS, and network controls.
- Review generated command suggestions before executing them.

## License

MIT
