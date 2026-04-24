#!/usr/bin/env python3
"""Shared utilities for OpenCode review helpers (Claude and Gemini)."""

import subprocess
import json
import os
from pathlib import Path


def git_output(args, cwd, timeout=None, env=None, remaining_seconds=None):
    """Run a git command and return output.
    
    Args:
        args: List of git command arguments (e.g., ["status", "--porcelain"])
        cwd: Working directory for the git command
        timeout: Timeout in seconds (positional for backward compatibility)
        env: Optional environment variables dict
        remaining_seconds: Alternative way to specify timeout (keyword arg)
        
    Returns:
        Command output as string (if text=True implied) or bytes
        
    Raises:
        RuntimeError: If git command not found or command fails
    """
    # Support both timeout as positional and remaining_seconds as keyword
    if remaining_seconds is not None:
        timeout = remaining_seconds
    if timeout is None:
        timeout = 30  # Default timeout
    # Determine if we should return text based on caller needs
    # Default to text=True for backward compatibility
    text = True
    
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=text,
            timeout=timeout,
            env=env
        )
        result.check_returncode()
        return result.stdout
    except FileNotFoundError:
        raise RuntimeError("git command not found")
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else e.stderr
        raise RuntimeError(f"git command failed: {err_msg}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("git command timed out")


def collect_untracked_files(cwd, remaining_seconds, seen, prompt_file):
    """Collect untracked files from git status with rename/copy detection.
    
    Args:
        cwd: Repository path (Path or string)
        remaining_seconds: Time budget remaining
        seen: Set of already-seen file paths to avoid duplicates
        prompt_file: Path to prompt file (for potential future use)
        
    Returns:
        List of tuples (file_path, file_content_bytes) for untracked files
        that are text files under 1MB.
    """
    # Use -z for safe filename parsing (handles special chars, spaces, unicode)
    try:
        status_out = git_output(["status", "--porcelain", "-z"], cwd, remaining_seconds)
    except RuntimeError:
        return []
    
    untracked_files = []
    
    # Handle both string and bytes output from git_output
    if isinstance(status_out, str):
        status_out = status_out.encode("utf-8", errors="replace")
    
    # -z output uses NUL separator, entries are "XY filename\0" or "XY orig\0filename\0" for renames
    entries = status_out.split(b'\x00')
    i = 0
    while i < len(entries):
        entry = entries[i]
        if len(entry) < 3:
            i += 1
            continue
        # Check status code (first 2 chars)
        status_code = entry[:2].decode('ascii', errors='replace')
        # Handle renamed/copied entries: consume 2 entries (orig + new)
        # Match on X column (R/C) to catch all variants: R , RM, RD, C , CM, CD
        if status_code and status_code[0] in ('R', 'C'):
            i += 2  # Skip both orig and new path
            continue
        # Only process untracked entries (??)
        if status_code == "??":
            # Filename starts at position 3 (after "XY " with space separator)
            filename_bytes = entry[3:]
            if filename_bytes:
                try:
                    filename = filename_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    # Fall back to latin-1 which can decode any byte
                    filename = filename_bytes.decode("latin-1")
                
                if filename not in seen:
                    file_path = Path(cwd) / filename
                    if file_path.is_file():
                        try:
                            # Skip files that are too large (>1MB)
                            file_size = file_path.stat().st_size
                            if file_size > 1024 * 1024:
                                continue
                            
                            with open(file_path, "rb") as f:
                                content = f.read()
                            
                            # Skip binary files (contain NUL bytes in first 1KB)
                            if b'\x00' in content[:1024]:
                                continue
                            
                            untracked_files.append((filename, content))
                        except Exception:
                            # Skip files we can't read
                            pass
        i += 1
    
    return untracked_files


def synthesize_diff_for_new_file(path, content):
    """Generate a synthetic git diff for a new untracked file.
    
    Args:
        path: File path (relative to repo root)
        content: File content as bytes
        
    Returns:
        Synthetic diff as bytes with correct git index format.
        Format: index 0000000..e69de29 (e69de29 is the empty blob hash)
    """
    diff_lines = []
    diff_lines.append(f"\ndiff --git a/{path} b/{path}")
    diff_lines.append(f"new file mode 100644")
    diff_lines.append(f"index 0000000..e69de29")
    diff_lines.append(f"--- /dev/null")
    diff_lines.append(f"+++ b/{path}")
    
    # Add content as a single "added" hunk
    # Check if file ends with newline
    ends_with_newline = content.endswith(b"\n")
    lines = content.split(b"\n")
    # Remove trailing empty element only if file ends with newline
    if ends_with_newline and lines and lines[-1] == b"":
        lines = lines[:-1]
    
    diff_lines.append(f"@@ -0,0 +1,{len(lines)} @@")
    
    for line in lines:
        diff_lines.append("+" + line.decode("utf-8", errors="replace"))
    
    # Add "No newline at end of file" marker if needed
    if not ends_with_newline:
        diff_lines.append("\\ No newline at end of file")
    
    diff_lines.append("")  # Trailing empty line
    
    return "\n".join(diff_lines).encode("utf-8")


def classify_failure(stderr, returncode, timeout_occurred, budget_exhausted=False):
    """Classify the type of failure from stderr and return code.
    
    Args:
        stderr: Stderr output string
        returncode: Process return code
        timeout_occurred: Boolean indicating if timeout was detected
        budget_exhausted: Boolean indicating if time budget was too small
        
    Returns:
        Failure reason string: "auth", "rate_limited", "missing_cli", 
        "budget_exhausted", "timeout", "command_failed", or "model_unavailable"
    """
    stderr_lower = stderr.lower()
    
    # Check for budget exhaustion first (distinct from timeout during execution)
    if budget_exhausted:
        return "budget_exhausted"
    
    # Authentication errors
    if "not authenticated" in stderr_lower:
        return "auth"
    if "authentication failed" in stderr_lower:
        return "auth"
    if "invalid api key" in stderr_lower:
        return "auth"
    if "401" in stderr:
        return "auth"
    if "please run gemini login first" in stderr_lower:
        return "auth"
    
    # Model availability
    if "model is unavailable for this account" in stderr_lower:
        return "model_unavailable"
    
    # Rate limiting
    if "rate limit" in stderr_lower:
        return "rate_limited"
    if "quota exceeded" in stderr_lower:
        return "rate_limited"
    if "rate limit hit" in stderr_lower:
        return "rate_limited"
    
    # Missing CLI
    if "command not found" in stderr_lower:
        return "missing_cli"
    if returncode == 127:
        return "missing_cli"
    
    # Timeouts
    if timeout_occurred or returncode == 124 or "timeout" in stderr_lower:
        return "timeout"
    
    # Generic failure
    return "command_failed"


def write_summary(summary_path, **kwargs):
    """Write a JSON summary file.
    
    Args:
        summary_path: Path to write summary JSON file
        **kwargs: Key-value pairs to include in the summary
        
    Returns:
        None
    """
    summary_path = Path(summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(kwargs, f, indent=2)
