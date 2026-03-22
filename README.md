# ai_commit

A CLI tool that generates a commit message from Git diffs using AI, asks for confirmation, and then runs `git commit`.

## Overview

- Displays the generated commit message in the console
- Asks for final confirmation with `OK / Edit / Cancel`
- In `Edit`, resolves and launches an editor using Git-compatible priority
- Passes through commit options to `git commit`
- Includes unstaged changes in AI input diff only when `-a/--all` is specified

## Requirements

- Windows
- Python virtual environment (`venv`)
- Git command available in PATH
- Configuration file at `.secret/api.json`

### Example `.secret/api.json`

```json
{
  "api_url": "https://api.x.ai/v1",
  "model": "grok-4-latest",
  "api_key": "YOUR_API_KEY"
}
```

Required keys are `api_url`, `model`, and `api_key`.

## How To Run

### Recommended: via batch file

```bat
ai_commit.bat [issue_reference] [git_commit_options...]
```

`ai_commit.bat` does the following:

- Runs with `venv\Scripts\python.exe`
- Checks that `ai_commit.py` exists
- Forwards all arguments to `ai_commit.py`

### Direct execution

```bat
python ai_commit.py [issue_reference] [git_commit_options...]
```

## CLI Arguments

### Positional argument

- `issue_reference` (optional)
  - Format: `#42` or `otherproject#4242`
  - Appended to the end of the commit subject line
  - Not passed as an argument to `git commit`

### Option arguments

- Tokens starting with `-` or `--` are passed through to `git commit`
- `-h` and `--help` are reserved for this tool's own help output

### Special rule for `-a` / `--all`

- With `-a` or `--all`: AI input diff is `staged + unstaged`
- Without `-a/--all`: AI input diff is `staged only`

## Interactive Flow

1. Print the generated commit message body in the console
2. Prompt: `Choose action [OK/Edit/Cancel] (default: OK):`
3. Branch by input

- `OK` (`ok`, `o`, or empty Enter)
  - Commit immediately with the generated message
- `Edit` (`edit`, `e`)
  - Write message to a temporary file and open an editor
  - Block until the editor process exits
  - If edited message is empty, cancel commit
  - Otherwise, commit with the edited message
- `Cancel` (`cancel`, `c`)
  - Exit without committing

## Editor Resolution Order (`Edit`)

Resolved with the following priority:

1. `GIT_EDITOR` environment variable
2. `git config core.editor`
3. `VISUAL` environment variable
4. `EDITOR` environment variable

If no editor can be resolved, the tool prints an error and exits.

## Commit Message Normalization

- Removes Markdown code fences
- Normalizes output to Conventional Commits style
- Converts `type(scope): subject` to `type: subject`
- Moves scope to body as `Scope: <scope>`
- Appends `issue_reference` to the subject line when provided

## Help

```bat
ai_commit.bat --help
```

## Main Exit Conditions and Errors

- Current directory is not a Git repository
  - `Current directory is not a Git repository.`
- Git command is not found
  - `git command not found. Please install Git.`
- Configuration file is missing
  - `Configuration file not found: .secret/api.json`
- No diff is available for message generation
  - `No changes detected in git diff.`
- Invalid issue reference format
  - `Issue reference must be like '#42' or 'otherproject#4242'`
- Unsupported non-option argument was provided
  - `Non-option arguments are not supported: ...`

## Examples

```bat
ai_commit.bat
ai_commit.bat #123
ai_commit.bat #123 --no-verify
ai_commit.bat --all
ai_commit.bat #42 -a --no-verify
```
