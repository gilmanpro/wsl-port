"""WSL Config Validator - validates and fixes .wslconfig issues."""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any


def get_wslconfig_path() -> Path:
    """Get the path to .wslconfig file."""
    return Path(os.environ.get("USERPROFILE", "")) / ".wslconfig"


def validate_wslconfig() -> dict[str, Any]:
    """Validate .wslconfig and return issues found."""
    config_path = get_wslconfig_path()
    issues = []
    warnings = []
    
    # Check if file exists
    if not config_path.exists():
        return {
            "ok": False,
            "error": ".wslconfig not found",
            "path": str(config_path),
            "issues": [".wslconfig file does not exist"],
            "warnings": [],
        }
    
    # Read file with multiple encoding attempts
    content = None
    for encoding in ["utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1"]:
        try:
            content = config_path.read_text(encoding=encoding)
            # Remove BOM if present
            if content.startswith("\ufeff"):
                content = content[1:]
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    if content is None:
        return {
            "ok": False,
            "error": "Cannot read .wslconfig: encoding error",
            "path": str(config_path),
            "issues": ["Cannot read file: encoding error"],
            "warnings": [],
        }
    
    # Check for valid section headers
    if not re.search(r"^\[wsl2\]", content, re.MULTILINE):
        issues.append("Missing [wsl2] section header")
    
    # Check for bridged networking (can cause hangs)
    if re.search(r"networkingMode\s*=\s*bridged", content, re.IGNORECASE):
        issues.append("networkingMode=bridged can cause WSL to hang")
    
    # Check for invalid memory values
    memory_match = re.search(r"memory\s*=\s*(\d+)([GMK]B)?", content, re.IGNORECASE)
    if memory_match:
        value = int(memory_match.group(1))
        unit = (memory_match.group(2) or "MB").upper()
        if unit == "GB" and value < 1:
            issues.append("memory too low (< 1GB)")
        elif unit == "GB" and value > 64:
            warnings.append("memory very high (> 64GB)")
    
    # Check for invalid processor values
    cpu_match = re.search(r"processors\s*=\s*(\d+)", content, re.IGNORECASE)
    if cpu_match:
        value = int(cpu_match.group(1))
        if value < 1:
            issues.append("processors too low (< 1)")
        elif value > 32:
            warnings.append("processors very high (> 32)")
    
    # Check for common typos
    valid_options = {
        "memory", "processors", "swap", "localhostForwarding",
        "nestedVirtualization", "vmIdleTimeout", "networkingMode",
        "dhcp", "dns", "firewall", "autoProxy", "autoMemoryReclaim",
    }
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#") or not line or line.startswith("["):
            continue
        if "=" in line:
            key = line.split("=")[0].strip()
            if key and key not in valid_options:
                warnings.append(f"Unknown option: {key}")
    
    return {
        "ok": len(issues) == 0,
        "path": str(config_path),
        "content": content,
        "issues": issues,
        "warnings": warnings,
    }


def fix_wslconfig() -> dict[str, Any]:
    """Fix common .wslconfig issues."""
    config_path = get_wslconfig_path()
    
    # Backup current config
    backup_path = config_path.with_suffix(".backup")
    if config_path.exists():
        shutil.copy2(config_path, backup_path)
    
    # Get system info
    import psutil
    total_ram_gb = psutil.virtual_memory().total / (1024**3)
    cpu_count = psutil.cpu_count(logical=True) or 4
    
    # Calculate safe limits
    safe_ram = max(4, int(total_ram_gb - 4))  # Leave 4GB for Windows
    safe_cpu = max(1, cpu_count - 1)  # Leave 1 CPU for Windows
    
    # Create safe config (UTF-8 without BOM)
    safe_config = f"""[wsl2]
# Memory limit (leave 4GB for Windows)
memory={safe_ram}GB

# Processor limit (leave 1 for Windows)
processors={safe_cpu}

# Swap file size
swap=4GB

# Localhost forwarding (required for port forwarding)
localhostForwarding=true

# Nested virtualization (for Docker in WSL)
nestedVirtualization=true

# VM idle timeout (seconds, -1 = never timeout)
vmIdleTimeout=-1
"""
    
    # Write safe config (UTF-8 without BOM)
    config_path.write_text(safe_config, encoding="utf-8")
    
    return {
        "ok": True,
        "message": "Fixed .wslconfig with safe defaults",
        "path": str(config_path),
        "backup": str(backup_path),
        "config": safe_config,
    }


def create_safe_wslconfig() -> dict[str, Any]:
    """Create a safe .wslconfig from scratch."""
    config_path = get_wslconfig_path()
    
    # Backup if exists
    if config_path.exists():
        backup_path = config_path.with_suffix(".backup")
        shutil.copy2(config_path, backup_path)
    
    # Get system info
    import psutil
    total_ram_gb = psutil.virtual_memory().total / (1024**3)
    cpu_count = psutil.cpu_count(logical=True) or 4
    
    # Calculate safe limits
    safe_ram = max(4, int(total_ram_gb - 4))  # Leave 4GB for Windows
    safe_cpu = max(1, cpu_count - 1)  # Leave 1 CPU for Windows
    
    # Create safe config (UTF-8 without BOM)
    safe_config = f"""[wsl2]
# Memory limit (leave 4GB for Windows)
memory={safe_ram}GB

# Processor limit (leave 1 for Windows)
processors={safe_cpu}

# Swap file size
swap=4GB

# Localhost forwarding (required for port forwarding)
localhostForwarding=true

# Nested virtualization (for Docker in WSL)
nestedVirtualization=true

# VM idle timeout (seconds, -1 = never timeout)
vmIdleTimeout=-1
"""
    
    # Write safe config (UTF-8 without BOM)
    config_path.write_text(safe_config, encoding="utf-8")
    
    return {
        "ok": True,
        "message": "Created safe .wslconfig",
        "path": str(config_path),
        "config": safe_config,
    }


if __name__ == "__main__":
    import json
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "fix":
        result = fix_wslconfig()
    elif len(sys.argv) > 1 and sys.argv[1] == "create":
        result = create_safe_wslconfig()
    else:
        result = validate_wslconfig()
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
