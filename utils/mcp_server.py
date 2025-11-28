#!/usr/bin/env python3
"""
各种本地的操作的MCP，方便各种cli使用，例如cherry studio ,qwen, claude code ,gemini cli等
fastmcp>=0.2.0
cryptography>=41.0.0
"""

import os
import re
import shutil
import subprocess
import zipfile
import tarfile
import json
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
from fastmcp import FastMCP

# Initialize fastMCP server
mcp = FastMCP("file-system-mcp")

# Security: Define allowed base paths to prevent unauthorized access
# Use OS-specific defaults and os.pathsep (Windows=';', macOS/Linux=':')
def _get_default_allowed_paths() -> str:
    home = Path.home()
    desktop = home / "Desktop"
    paths = []

    if os.name == "nt":
        # Include system drive root (usually C:\) and D:\ if it exists, plus Desktop
        sys_drive = os.environ.get("SystemDrive", "C:") + "\\"
        paths.append(sys_drive)
        if Path("D:\\").exists():
            paths.append("D:\\")
        paths.append(str(desktop))
    else:
        # On macOS/Linux, allow Home and Desktop by default
        paths.append(str(home))
        paths.append(str(desktop))

    return os.pathsep.join(paths)

_default_paths = _get_default_allowed_paths()
ALLOWED_BASE_PATHS = [
    p for p in os.getenv("MCP_ALLOWED_PATHS", _default_paths).split(os.pathsep) if p
]


def is_path_allowed(path: str) -> bool:
    """Check if the given path is within allowed base paths."""
    abs_path = os.path.abspath(path)
    return any(abs_path.startswith(os.path.abspath(base)) for base in ALLOWED_BASE_PATHS)


def validate_path(path: str) -> str:
    """Validate and normalize path."""
    if not path:
        raise ValueError("Path cannot be empty")

    normalized = os.path.normpath(path)

    if not is_path_allowed(normalized):
        raise PermissionError(f"Access denied: {path} is outside allowed directories")

    return normalized


def format_file_info(path: str, stat_info) -> dict:
    """Format file information for response."""
    return {
        "path": path,
        "name": os.path.basename(path),
        "size": stat_info.st_size,
        "created": stat_info.st_ctime,
        "modified": stat_info.st_mtime,
        "is_directory": os.path.isdir(path),
        "is_file": os.path.isfile(path),
    }



# ============================================================================
# BASIC FILE OPERATIONS
# ============================================================================

@mcp.tool()
def read_file(
    path: str,
    encoding: str = "utf-8",
    start_line: Optional[int] = None,
    end_line: Optional[int] = None
) -> str:
    """
    Read file contents with optional line range.

    Args:
        path: File path to read
        encoding: Text encoding (default: utf-8)
        start_line: Starting line number (1-based, optional)
        end_line: Ending line number (inclusive, optional)

    Returns:
        File contents as string
    """
    path = validate_path(path)

    with open(path, "r", encoding=encoding) as f:
        if start_line is not None or end_line is not None:
            lines = f.readlines()
            start_idx = (start_line - 1) if start_line else 0
            end_idx = end_line if end_line else len(lines)
            content = "".join(lines[start_idx:end_idx])
        else:
            content = f.read()

    return content

@mcp.tool()
def list_files(directory: str, pattern: str = None) -> list[dict]:
    """
    List files in a directory with optional regex filtering.

    Args:
        directory: Directory to list
        pattern: Optional regex pattern to filter filenames

    Returns:
        List of file info dictionaries
    """
    directory = validate_path(directory)

    if not os.path.isdir(directory):
        raise NotADirectoryError(f"{directory} is not a directory")

    files = []
    regex = re.compile(pattern) if pattern else None

    for item in os.listdir(directory):
        if regex and not regex.search(item):
            continue

        full_path = os.path.join(directory, item)
        try:
            stat_info = os.stat(full_path)
            files.append(format_file_info(full_path, stat_info))
        except (OSError, PermissionError):
            continue

    return files

@mcp.tool()
def read_hex(
    path: str,
    offset: int = 0,
    length: Optional[int] = None
) -> str:
    """
    Read file as hexadecimal with optional byte range.

    Args:
        path: File path to read
        offset: Starting byte offset (default: 0)
        length: Number of bytes to read (default: all)

    Returns:
        Formatted hex dump
    """
    path = validate_path(path)

    with open(path, "rb") as f:
        f.seek(offset)
        data = f.read(length) if length else f.read()

    # Format as hex dump
    hex_output = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_str = " ".join(f"{b:02x}" for b in chunk)
        ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        hex_output.append(f"{offset + i:08x}  {hex_str:<48}  {ascii_str}")

    return "\n".join(hex_output)


@mcp.tool()
def write_file(file_path: str, content: str, encoding: str = "utf-8") -> str:
    """
    Write content to a file, creating directories if needed.

    Args:
        file_path: Path to file
        content: Content to write
        encoding: Text encoding (default: utf-8)

    Returns:
        Success message
    """
    file_path = validate_path(file_path)

    # Create parent directories if they don't exist
    parent_dir = os.path.dirname(file_path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    with open(file_path, "w", encoding=encoding) as f:
        f.write(content)

    return f"Successfully wrote to {file_path}"

@mcp.tool()
def edit_file_by_line(
    path: str,
    start_line: int,
    end_line: int,
    new_content: str,
    encoding: str = "utf-8"
) -> str:
    """
    Edit file content by line range. Can insert, replace, or delete lines.

    Args:
        path: File path to edit
        start_line: Starting line number (1-based)
        end_line: Ending line number (inclusive)
        new_content: New content (empty string to delete lines)
        encoding: Text encoding (default: utf-8)

    Returns:
        Success message
    """
    path = validate_path(path)

    with open(path, "r", encoding=encoding) as f:
        lines = f.readlines()

    # Validate line numbers
    if start_line < 1 or end_line < start_line or end_line > len(lines):
        raise ValueError(f"Invalid line range: {start_line}-{end_line} (file has {len(lines)} lines)")

    start_idx = start_line - 1
    end_idx = end_line

    if new_content:
        # Ensure new content ends with newline if it's not the last line
        if not new_content.endswith("\n") and end_idx < len(lines):
            new_content += "\n"
        lines[start_idx:end_idx] = [new_content]
    else:
        # Delete lines
        del lines[start_idx:end_idx]

    with open(path, "w", encoding=encoding) as f:
        f.writelines(lines)

    return f"Successfully edited lines {start_line}-{end_line} in {path}"


@mcp.tool()
def edit_file_by_regex(
    path: str,
    pattern: str,
    replacement: str,
    count: int = 0,
    encoding: str = "utf-8"
) -> str:
    """
    Edit file content using regular expression pattern matching.

    Args:
        path: File path to edit
        pattern: Regular expression pattern to search
        replacement: Replacement text (supports regex groups like \\1, \\2)
        count: Maximum number of replacements (0 = all)
        encoding: Text encoding (default: utf-8)

    Returns:
        Success message with number of replacements
    """
    path = validate_path(path)

    with open(path, "r", encoding=encoding) as f:
        content = f.read()

    # Perform regex replacement
    new_content, num_replaced = re.subn(pattern, replacement, content, count=count)

    with open(path, "w", encoding=encoding) as f:
        f.write(new_content)

    return f"Successfully replaced {num_replaced} occurrence(s) in {path}"


@mcp.tool()
def append_file(file_path: str, content: str, encoding: str = "utf-8") -> str:
    """
    Append content to a file.

    Args:
        file_path: Path to file
        content: Content to append
        encoding: Text encoding (default: utf-8)

    Returns:
        Success message
    """
    file_path = validate_path(file_path)

    # Create parent directories if they don't exist
    parent_dir = os.path.dirname(file_path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    with open(file_path, "a", encoding=encoding) as f:
        f.write(content)

    return f"Successfully appended to {file_path}"


# ============================================================================
# FILE MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
def delete_file(file_path: str) -> str:
    """
    Delete a file.

    Args:
        file_path: Path to file to delete

    Returns:
        Success message
    """
    file_path = validate_path(file_path)

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"{file_path} does not exist")

    os.remove(file_path)
    return f"Successfully deleted {file_path}"


@mcp.tool()
def create_directory(directory_path: str) -> str:
    """
    Create a directory (including parent directories if needed).

    Args:
        directory_path: Path to directory to create

    Returns:
        Success message
    """
    directory_path = validate_path(directory_path)
    os.makedirs(directory_path, exist_ok=True)
    return f"Successfully created directory {directory_path}"


@mcp.tool()
def delete_directory(directory_path: str, recursive: bool = False) -> str:
    """
    Delete a directory.

    Args:
        directory_path: Path to directory to delete
        recursive: If True, delete all contents recursively

    Returns:
        Success message
    """
    directory_path = validate_path(directory_path)

    if not os.path.isdir(directory_path):
        raise NotADirectoryError(f"{directory_path} is not a directory")

    if recursive:
        shutil.rmtree(directory_path)
    else:
        os.rmdir(directory_path)

    return f"Successfully deleted directory {directory_path}"


@mcp.tool()
def copy_file(source: str, destination: str) -> str:
    """
    Copy a file from source to destination.

    Args:
        source: Source file path
        destination: Destination file path

    Returns:
        Success message
    """
    source = validate_path(source)
    destination = validate_path(destination)

    if not os.path.isfile(source):
        raise FileNotFoundError(f"{source} does not exist")

    # Create destination directory if needed
    dest_dir = os.path.dirname(destination)
    if dest_dir and not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)

    shutil.copy2(source, destination)
    return f"Successfully copied {source} to {destination}"


@mcp.tool()
def move_file(source: str, destination: str) -> str:
    """
    Move/rename a file from source to destination.

    Args:
        source: Source file path
        destination: Destination file path

    Returns:
        Success message
    """
    source = validate_path(source)
    destination = validate_path(destination)

    if not os.path.exists(source):
        raise FileNotFoundError(f"{source} does not exist")

    dest_dir = os.path.dirname(destination)
    if dest_dir and not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)

    shutil.move(source, destination)
    return f"Successfully moved {source} to {destination}"


@mcp.tool()
def file_exists(path: str) -> bool:
    """
    Check if a file or directory exists.

    Args:
        path: Path to check

    Returns:
        True if exists, False otherwise
    """
    path = validate_path(path)
    return os.path.exists(path)


@mcp.tool()
def get_file_info(path: str) -> dict:
    """
    Get detailed information about a file or directory.

    Args:
        path: Path to file or directory

    Returns:
        File information dictionary
    """
    path = validate_path(path)

    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} does not exist")

    stat_info = os.stat(path)
    info = format_file_info(path, stat_info)

    if os.path.isfile(path):
        info["extension"] = os.path.splitext(path)[1]
    else:
        # Directory info
        try:
            contents = os.listdir(path)
            info["item_count"] = len(contents)
        except PermissionError:
            info["item_count"] = None

    return info


# ============================================================================
# SEARCH AND TEXT OPERATIONS
# ============================================================================

@mcp.tool()
def search_files(directory: str, query: str, case_sensitive: bool = False,
                 file_pattern: str = None) -> list[dict]:
    """
    Search for text within files in a directory.

    Args:
        directory: Directory to search
        query: Text to search for
        case_sensitive: Whether search is case sensitive
        file_pattern: Optional regex to filter files by name

    Returns:
        List of matches with file paths and line information
    """
    directory = validate_path(directory)

    if not os.path.isdir(directory):
        raise NotADirectoryError(f"{directory} is not a directory")

    matches = []
    file_regex = re.compile(file_pattern) if file_pattern else None
    flags = 0 if case_sensitive else re.IGNORECASE

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file_regex and not file_regex.search(file):
                continue

            file_path = os.path.join(root, file)

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if re.search(query, line, flags):
                            matches.append({
                                "file": file_path,
                                "line_number": line_num,
                                "line": line.strip()
                            })
            except (PermissionError, UnicodeDecodeError):
                continue

    return matches

@mcp.tool()
def search_content(
    directory: str,
    search_text: str,
    file_pattern: str = "*",
    recursive: bool = True,
    case_sensitive: bool = False,
    regex: bool = False
) -> str:
    """
    Search for text content within files in a directory.

    Args:
        directory: Directory to search in
        search_text: Text to search for
        file_pattern: File pattern to filter (e.g., '*.py')
        recursive: Search recursively (default: true)
        case_sensitive: Case sensitive search (default: false)
        regex: Use regular expression (default: false)

    Returns:
        List of matching lines with file paths and line numbers
    """
    directory = validate_path(directory)

    matches = []

    # Compile search pattern
    if regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        search_pattern = re.compile(search_text, flags)
    else:
        search_text_lower = search_text if case_sensitive else search_text.lower()

    # Search files
    search_paths = []
    if recursive:
        for root, dirs, files in os.walk(directory):
            for name in files:
                if Path(name).match(file_pattern):
                    search_paths.append(os.path.join(root, name))
    else:
        for item in os.listdir(directory):
            full_path = os.path.join(directory, item)
            if os.path.isfile(full_path) and Path(item).match(file_pattern):
                search_paths.append(full_path)

    for file_path in search_paths:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    found = False
                    if regex:
                        if search_pattern.search(line):
                            found = True
                    else:
                        line_to_search = line if case_sensitive else line.lower()
                        if search_text_lower in line_to_search:
                            found = True

                    if found:
                        matches.append(f"{file_path}:{line_num}: {line.rstrip()}")
        except Exception:
            continue

    result = f"Found {len(matches)} match(es):\n" + "\n".join(matches[:100])
    if len(matches) > 100:
        result += f"\n... and {len(matches) - 100} more"

    return result


@mcp.tool()
def replace_text_in_file(file_path: str, old_text: str, new_text: str,
                         backup: bool = True, encoding: str = "utf-8") -> str:
    """
    Replace text in a file with optional backup.

    Args:
        file_path: Path to file
        old_text: Text to replace
        new_text: Replacement text
        backup: Whether to create backup file
        encoding: File encoding

    Returns:
        Success message with replacement count
    """
    file_path = validate_path(file_path)

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"{file_path} does not exist")

    # Create backup if requested
    if backup:
        backup_path = file_path + ".bak"
        shutil.copy2(file_path, backup_path)

    with open(file_path, "r", encoding=encoding) as f:
        content = f.read()

    count = content.count(old_text)
    new_content = content.replace(old_text, new_text)

    with open(file_path, "w", encoding=encoding) as f:
        f.write(new_content)

    return f"Successfully replaced {count} occurrences in {file_path}"


# ============================================================================
# COMMAND EXECUTION TOOLS
# ============================================================================

# Default shell depends on OS
DEFAULT_SHELL = "powershell" if os.name == "nt" else "bash"

@mcp.tool()
def execute_command(
    command: str,
    shell: str = DEFAULT_SHELL,
    timeout: int = 600,
    working_directory: Optional[str] = None
) -> str:
    """
    Execute a PowerShell, CMD, or Bash command with optional timeout.

    Args:
        command: Command to execute
        shell: Shell to use: 'powershell', 'cmd', 'bash', or 'zsh' (default: OS-specific)
        timeout: Timeout in seconds (default: 600)
        working_directory: Optional working directory

    Returns:
        Command output including exit code, stdout, and stderr
    """
    if working_directory:
        working_directory = validate_path(working_directory)

    # Prepare command based on shell type
    shell = shell.lower()
    if shell in ("powershell", "cmd") and os.name != "nt":
        raise ValueError("'powershell' and 'cmd' shells are only available on Windows. Use 'bash' or 'zsh'.")

    if shell == "powershell":
        # Support both Windows PowerShell and PowerShell Core if installed
        ps_exe = shutil.which("powershell") or shutil.which("pwsh") or "powershell.exe"
        cmd = [ps_exe, "-Command", command]
    elif shell == "cmd":
        cmd = ["cmd.exe", "/c", command]
    elif shell == "bash":
        cmd = ["bash", "-lc", command]
    elif shell == "zsh":
        cmd = ["zsh", "-lc", command]
    else:
        raise ValueError(f"Unsupported shell type: {shell}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_directory,
        )

        output = f"Exit Code: {result.returncode}\n\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"

        return output

    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds"


@mcp.tool()
def run_program(
    program: str,
    arguments: list[str] = None,
    timeout: int = 30,
    working_directory: Optional[str] = None
) -> str:
    """
    Run an external program with arguments.

    Args:
        program: Program/executable to run
        arguments: List of arguments
        timeout: Timeout in seconds
        working_directory: Optional working directory

    Returns:
        Program output
    """
    program = validate_path(program)

    if working_directory:
        working_directory = validate_path(working_directory)

    cmd = [program]
    if arguments:
        cmd.extend(arguments)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_directory,
        )

        output = f"Exit Code: {result.returncode}\n\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"

        return output

    except subprocess.TimeoutExpired:
        return f"Program timed out after {timeout} seconds,you can try to increase the timeout."


# ============================================================================
# COMPRESSION TOOLS
# ============================================================================

@mcp.tool()
def compress_file(
    source: str,
    output: str,
    format: str = "zip"
) -> str:
    """
    Compress files or directories into a zip or tar.gz archive.

    Args:
        source: Source file or directory path
        output: Output archive path
        format: Archive format: 'zip' or 'tar.gz' (default: zip)

    Returns:
        Success message
    """
    source = validate_path(source)
    output = validate_path(output)

    if format == "zip":
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zipf:
            if os.path.isdir(source):
                for root, dirs, files in os.walk(source):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(source))
                        zipf.write(file_path, arcname)
            else:
                zipf.write(source, os.path.basename(source))

    elif format == "tar.gz":
        with tarfile.open(output, "w:gz") as tarf:
            tarf.add(source, arcname=os.path.basename(source))

    else:
        raise ValueError(f"Unsupported format: {format}")

    return f"Successfully compressed {source} to {output}"


@mcp.tool()
def decompress_file(
    archive: str,
    destination: str
) -> str:
    """
    Decompress a zip or tar.gz archive.

    Args:
        archive: Archive file path
        destination: Destination directory

    Returns:
        Success message
    """
    archive = validate_path(archive)
    destination = validate_path(destination)

    os.makedirs(destination, exist_ok=True)

    if archive.endswith(".zip"):
        with zipfile.ZipFile(archive, "r") as zipf:
            zipf.extractall(destination)

    elif archive.endswith((".tar.gz", ".tgz")):
        with tarfile.open(archive, "r:gz") as tarf:
            tarf.extractall(destination)

    elif archive.endswith(".tar"):
        with tarfile.open(archive, "r") as tarf:
            tarf.extractall(destination)

    else:
        raise ValueError(f"Unsupported archive format: {archive}")

    return f"Successfully decompressed {archive} to {destination}"


# ============================================================================
# ENCRYPTION TOOLS
# ============================================================================
@mcp.tool()
def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        Encryption key as string
    """
    key = Fernet.generate_key()
    return key.decode('utf-8')


@mcp.tool()
def encrypt_file(file_path: str, key: str, output_path: str = None) -> str:
    """
    Encrypt a file using Fernet symmetric encryption.

    Args:
        file_path: Path to file to encrypt
        key: Encryption key (base64)
        output_path: Optional output path (default: file_path + '.enc')

    Returns:
        Success message
    """
    file_path = validate_path(file_path)

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"{file_path} does not exist")

    fernet = Fernet(key.encode('utf-8'))

    if not output_path:
        output_path = file_path + '.enc'
    output_path = validate_path(output_path)

    with open(file_path, 'rb') as f:
        data = f.read()

    encrypted_data = fernet.encrypt(data)

    with open(output_path, 'wb') as f:
        f.write(encrypted_data)

    return f"Successfully encrypted {file_path} to {output_path}"


@mcp.tool()
def decrypt_file(encrypted_path: str, key: str, output_path: str = None) -> str:
    """
    Decrypt a file using Fernet symmetric encryption.

    Args:
        encrypted_path: Path to encrypted file
        key: Encryption key (base64)
        output_path: Optional output path (default: original filename)

    Returns:
        Success message
    """
    encrypted_path = validate_path(encrypted_path)

    if not os.path.isfile(encrypted_path):
        raise FileNotFoundError(f"{encrypted_path} does not exist")

    fernet = Fernet(key.encode('utf-8'))

    if not output_path:
        # Remove .enc extension if present
        if encrypted_path.endswith('.enc'):
            output_path = encrypted_path[:-4]
        else:
            output_path = encrypted_path + '.dec'
    output_path = validate_path(output_path)

    with open(encrypted_path, 'rb') as f:
        encrypted_data = f.read()

    decrypted_data = fernet.decrypt(encrypted_data)

    with open(output_path, 'wb') as f:
        f.write(decrypted_data)

    return f"Successfully decrypted {encrypted_path} to {output_path}"


@mcp.tool()
def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        Base64 encoded encryption key
    """
    key = Fernet.generate_key()
    return f"Generated encryption key:\n{key.decode()}"


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # mcp.run()
    # stream mode
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, path="/mcp")