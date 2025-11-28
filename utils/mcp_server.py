#!/usr/bin/env python3
"""
各种本地的操作的MCP，方便各种cli使用，例如cherry studio ,qwen, claude code ,gemini cli等
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
# Default: D drive + C drive Desktop
_default_paths = f"D:\\;{os.path.join(os.path.expanduser('~'), 'Desktop')}"
ALLOWED_BASE_PATHS = os.getenv("MCP_ALLOWED_PATHS", _default_paths).split(";")


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


def format_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


# ============================================================================
# FILE READING TOOLS
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


# ============================================================================
# FILE WRITING/EDITING TOOLS
# ============================================================================

@mcp.tool()
def write_file(
    path: str,
    content: str,
    encoding: str = "utf-8"
) -> str:
    """
    Write content to a file (creates new or overwrites existing).

    Args:
        path: File path to write
        content: Content to write
        encoding: Text encoding (default: utf-8)

    Returns:
        Success message
    """
    path = validate_path(path)

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding=encoding) as f:
        f.write(content)

    return f"Successfully wrote to {path}"


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
def append_file(
    path: str,
    content: str,
    newline: bool = True,
    encoding: str = "utf-8"
) -> str:
    """
    Append content to the end of a file.

    Args:
        path: File path to append to
        content: Content to append
        newline: Add newline before content (default: true)
        encoding: Text encoding (default: utf-8)

    Returns:
        Success message
    """
    path = validate_path(path)

    with open(path, "a", encoding=encoding) as f:
        if newline and os.path.exists(path) and os.path.getsize(path) > 0:
            f.write("\n")
        f.write(content)

    return f"Successfully appended to {path}"


# ============================================================================
# FILE MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
def delete_file(
    path: str,
    recursive: bool = False
) -> str:
    """
    Delete a file or directory.

    Args:
        path: File or directory path to delete
        recursive: Delete directories recursively (default: false)

    Returns:
        Success message
    """
    path = validate_path(path)

    if os.path.isdir(path):
        if recursive:
            shutil.rmtree(path)
        else:
            os.rmdir(path)
    else:
        os.remove(path)

    return f"Successfully deleted {path}"


@mcp.tool()
def copy_file(
    source: str,
    destination: str,
    overwrite: bool = False
) -> str:
    """
    Copy a file or directory to a new location.

    Args:
        source: Source path
        destination: Destination path
        overwrite: Overwrite if exists (default: false)

    Returns:
        Success message
    """
    source = validate_path(source)
    destination = validate_path(destination)

    if os.path.exists(destination) and not overwrite:
        raise FileExistsError(f"Destination {destination} already exists")

    if os.path.isdir(source):
        if os.path.exists(destination):
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
    else:
        os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
        shutil.copy2(source, destination)

    return f"Successfully copied {source} to {destination}"


@mcp.tool()
def move_file(
    source: str,
    destination: str,
    overwrite: bool = False
) -> str:
    """
    Move or rename a file or directory.

    Args:
        source: Source path
        destination: Destination path
        overwrite: Overwrite if exists (default: false)

    Returns:
        Success message
    """
    source = validate_path(source)
    destination = validate_path(destination)

    if os.path.exists(destination) and not overwrite:
        raise FileExistsError(f"Destination {destination} already exists")

    if os.path.exists(destination):
        if os.path.isdir(destination):
            shutil.rmtree(destination)
        else:
            os.remove(destination)

    shutil.move(source, destination)

    return f"Successfully moved {source} to {destination}"


@mcp.tool()
def create_directory(path: str) -> str:
    """
    Create a new directory (with parent directories if needed).

    Args:
        path: Directory path to create

    Returns:
        Success message
    """
    path = validate_path(path)
    os.makedirs(path, exist_ok=True)
    return f"Successfully created directory {path}"


# ============================================================================
# SEARCH TOOLS
# ============================================================================

@mcp.tool()
def search_files(
    directory: str,
    pattern: str,
    recursive: bool = True
) -> str:
    """
    Search for files by name pattern (supports wildcards).

    Args:
        directory: Directory to search in
        pattern: File name pattern (e.g., '*.txt', 'test*.py')
        recursive: Search recursively (default: true)

    Returns:
        List of matching file paths
    """
    directory = validate_path(directory)

    matches = []
    if recursive:
        for root, dirs, files in os.walk(directory):
            for name in files + dirs:
                full_path = os.path.join(root, name)
                if Path(full_path).match(pattern):
                    matches.append(full_path)
    else:
        for item in os.listdir(directory):
            full_path = os.path.join(directory, item)
            if Path(full_path).match(pattern):
                matches.append(full_path)

    result = f"Found {len(matches)} match(es):\n" + "\n".join(matches)
    return result


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


# ============================================================================
# FILE INFORMATION TOOLS
# ============================================================================

@mcp.tool()
def get_file_info(path: str) -> str:
    """
    Get detailed information about a file or directory.

    Args:
        path: File or directory path

    Returns:
        JSON formatted file information
    """
    path = validate_path(path)
    stat_info = os.stat(path)

    info = {
        "path": path,
        "type": "directory" if os.path.isdir(path) else "file",
        "size": stat_info.st_size,
        "size_human": format_size(stat_info.st_size),
        "created": stat_info.st_ctime,
        "modified": stat_info.st_mtime,
        "accessed": stat_info.st_atime,
        "permissions": oct(stat_info.st_mode)[-3:],
    }

    if os.path.isfile(path):
        info["extension"] = os.path.splitext(path)[1]

    return json.dumps(info, indent=2)


@mcp.tool()
def list_directory(
    path: str,
    show_hidden: bool = False
) -> str:
    """
    List contents of a directory with detailed information.

    Args:
        path: Directory path to list
        show_hidden: Show hidden files (default: false)

    Returns:
        Formatted directory listing
    """
    path = validate_path(path)

    items = []
    for item in os.listdir(path):
        if not show_hidden and item.startswith("."):
            continue

        full_path = os.path.join(path, item)
        stat_info = os.stat(full_path)

        items.append({
            "name": item,
            "type": "dir" if os.path.isdir(full_path) else "file",
            "size": stat_info.st_size if os.path.isfile(full_path) else 0,
            "size_human": format_size(stat_info.st_size) if os.path.isfile(full_path) else "-",
            "modified": stat_info.st_mtime,
        })

    # Sort: directories first, then by name
    items.sort(key=lambda x: (x["type"] != "dir", x["name"]))

    result = f"Contents of {path} ({len(items)} items):\n\n"
    for item in items:
        type_indicator = "[DIR]" if item["type"] == "dir" else "[FILE]"
        result += f"{type_indicator:6} {item['size_human']:>10} {item['name']}\n"

    return result


# ============================================================================
# COMMAND EXECUTION TOOLS
# ============================================================================

@mcp.tool()
def execute_command(
    command: str,
    shell: str = "powershell",
    timeout: int = 600,
    working_directory: Optional[str] = None
) -> str:
    """
    Execute a PowerShell, CMD, or Bash command with optional timeout.

    Args:
        command: Command to execute
        shell: Shell to use: 'powershell', 'cmd', or 'bash' (default: powershell)
        timeout: Timeout in seconds (default: 30)
        working_directory: Working directory (default: current)

    Returns:
        Command output including exit code, stdout, and stderr
    """
    if working_directory:
        working_directory = validate_path(working_directory)

    # Prepare command based on shell type
    if shell == "powershell":
        cmd = ["powershell.exe", "-Command", command]
    elif shell == "cmd":
        cmd = ["cmd.exe", "/c", command]
    elif shell == "bash":
        cmd = ["bash", "-c", command]
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
    Run a program with arguments and optional timeout.

    Args:
        program: Program path or name
        arguments: Program arguments (default: [])
        timeout: Timeout in seconds (default: 30)
        working_directory: Working directory (default: current)

    Returns:
        Program output including exit code, stdout, and stderr
    """
    if arguments is None:
        arguments = []

    if working_directory:
        working_directory = validate_path(working_directory)

    cmd = [program] + arguments

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
def encrypt_file(
    source: str,
    output: str,
    key: Optional[str] = None
) -> str:
    """
    Encrypt a file using Fernet symmetric encryption.

    Args:
        source: Source file path
        output: Output encrypted file path
        key: Encryption key (base64, optional - will generate if not provided)

    Returns:
        Success message with encryption key if generated
    """
    source = validate_path(source)
    output = validate_path(output)

    # Generate key if not provided
    if not key:
        key_bytes = Fernet.generate_key()
        key_str = key_bytes.decode()
    else:
        key_str = key
        key_bytes = key.encode()

    fernet = Fernet(key_bytes)

    with open(source, "rb") as f:
        data = f.read()

    encrypted = fernet.encrypt(data)

    with open(output, "wb") as f:
        f.write(encrypted)

    result = f"Successfully encrypted {source} to {output}\n"
    if not key:
        result += f"\nEncryption Key (SAVE THIS): {key_str}"

    return result


@mcp.tool()
def decrypt_file(
    source: str,
    output: str,
    key: str
) -> str:
    """
    Decrypt a file encrypted with Fernet.

    Args:
        source: Encrypted file path
        output: Output decrypted file path
        key: Decryption key (base64)

    Returns:
        Success message
    """
    source = validate_path(source)
    output = validate_path(output)
    key_bytes = key.encode()

    fernet = Fernet(key_bytes)

    with open(source, "rb") as f:
        encrypted_data = f.read()

    decrypted = fernet.decrypt(encrypted_data)

    with open(output, "wb") as f:
        f.write(decrypted)

    return f"Successfully decrypted {source} to {output}"


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