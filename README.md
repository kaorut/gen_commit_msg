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
- Python 3.x (virtual environment recommended, but system Python works as fallback)
- Git command available in PATH
- Configuration file at `.secret/api.json`

### Example `.secret/api.json`

```json
{
  "openai": {
    "api_url": "https://api.x.ai/v1",
    "model": "grok-4-latest",
    "api_key": "YOUR_OPENAI_API_KEY"
  },
  "github": [
    {
      "name": "kaorut/ai_commit",
      "api_key": "YOUR_GITHUB_TOKEN_FOR_AI_COMMIT"
    },
    {
      "name": "tetengo/hasune.rs",
      "api_key": "YOUR_GITHUB_TOKEN_FOR_HASUNE"
    },
    {
      "name": "kaorut/*",
      "api_key": "YOUR_GITHUB_TOKEN_FOR_KAORUT_RESOURCES"
    },
    {
      "name": "*",
      "api_key": "YOUR_DEFAULT_GITHUB_TOKEN_OPTIONAL"
    }
  ]
}
```

Required keys are `openai.api_url`, `openai.model`, and `openai.api_key`.
Optional key:

- `github[]`: resource-specific GitHub tokens used to call GitHub Issues API for issue-context RAG.
- `github[].name`: resource selector. Supported forms are `owner/repo`, `owner/*`, `owner`, `repo`, and `*`.
- `github[].api_key`: token for the matched resource.
- `diff_unified_lines`: unified context lines for `git diff` (default: `100`)
- `normalization_mode`: commit message normalization mode: `strict` (default) or `loose`

## How To Run

### Recommended: via batch file

```bat
ai_commit.bat [issue_reference] [revision_spec] [git_commit_options...]
```

`ai_commit.bat` does the following:

- Attempts to run with `venv\Scripts\python.exe` if available
- Falls back to system Python (`python.exe` in PATH) if venv is not found
- Checks that `ai_commit.py` exists
- Forwards all arguments to `ai_commit.py`

### Direct execution

```bat
python ai_commit.py [issue_reference] [revision_spec] [git_commit_options...]
```

## CLI Arguments

### Positional arguments

- `issue_reference` (optional)
  - Format: `#42`, `repo#4242`, or `owner/repo#4242`
  - Appended to the end of the commit subject line
  - Not passed as an argument to `git commit`
  - If omitted, and the latest commit subject contains issue references, all of them are reused automatically

- `revision_spec` (optional)
  - Specifies the git revision(s) for the diff (follows git diff syntax)
  - Formats:
    - `REV1..REV2` — 2-dot form: diff from REV1 to REV2
    - `REV1...REV2` — 3-dot form: diff from merge-base(REV1, REV2) to REV2
    - `REV` — single commit: diff of `REV` (same as `REV^..REV`)
    - (omitted) — staged changes only (default behavior)
  - `revision_spec` が指定されていても、unstaged changes は `-a/--all` 指定時のみ AI 入力に含まれます
  - Examples: `HEAD^..HEAD`, `main..feature`, `v1.0...v1.1`

### Option arguments

- Tokens starting with `-` or `--` are passed through to `git commit`
- `-h` and `--help` are reserved for this tool's own help output

### Special rule for `-a` / `--all`

- With `-a` or `--all`: AI input diff is `staged + unstaged`
- Without `-a/--all`: AI input diff is `staged only`

### Special rule for `--amend`

- If `--amend` is present and no `revision_spec` is explicitly provided:
  - `revision_spec` is automatically set to `HEAD^..HEAD`
  - This shows the diff of the current commit (HEAD) for amending
- If both `--amend` and an explicit `revision_spec` are provided:
  - The explicit `revision_spec` takes precedence
  - `--amend` is still passed through to `git commit`

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
- In `strict` mode, normalizes output to Conventional Commits style
- In `strict` mode, converts `type(scope): subject` to `type: subject`
- In `strict` mode, moves scope to body as `Scope: <scope>`
- In `loose` mode, keeps AI output mostly as-is (after code-fence removal)
- Appends `issue_reference` to the subject line when provided
- If `issue_reference` is omitted, reuses all issue references found in the latest commit subject when available
- When the diff supports it, the body may include both a short summary of what changed and an inferred reason for the change
- If the reason cannot be inferred with reasonable confidence from the diff, the tool prefers omission over speculation

## GitHub Issue RAG

When the commit message includes issue references (explicitly passed or inherited from the latest commit subject), the tool attempts to fetch issue details from GitHub and appends them to the AI user prompt as supplemental context.

- `#123` resolves against the current repository's `origin` remote
- `repo#123` resolves against the same owner as `origin`, with `repo` overridden
- `owner/repo#123` resolves directly to that repository
- The GitHub token is selected in this order: exact `owner/repo`, then `owner/*`, then `owner` or `repo`, then `*`
- If multiple entries match with the same priority, the first declared entry in `github[]` is used

If all API calls for resolved issue references fail, the tool prints a warning to stderr,
then skips issue context and continues commit generation.

## Improving Why Inference

`git diff` alone is often enough to infer low-level intent such as fixing validation, preventing a crash, reducing duplication, or improving readability.

It is usually not enough to infer higher-level product or business intent. If you want the generated message to explain "why" more reliably, the most useful extra inputs are:

- issue or ticket reference with a short title
- problem statement or bug symptom
- user-visible impact
- expected behavior before and after the change
- design note or implementation constraint
- related error message, log snippet, or failing test name

Examples of useful context:

- `#123 Fix crash when revision_spec is empty`
- `Bug: amend flow used the wrong diff range for HEAD`
- `Why: align single-revision behavior with git show semantics`

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
  - `Issue reference must be like '#42', 'repo#4242', or 'owner/repo#4242'`
- Unsupported non-option argument was provided
  - `Non-option arguments are not supported: ...`

## Examples

```bat
ai_commit.bat
ai_commit.bat #123
ai_commit.bat HEAD^
ai_commit.bat main..feature
ai_commit.bat #123 HEAD^..HEAD
ai_commit.bat #123 --no-verify
ai_commit.bat v1.0..v1.1 -a --no-verify
ai_commit.bat --amend
ai_commit.bat #42 --amend
ai_commit.bat --all
ai_commit.bat #42 -a --no-verify
```
