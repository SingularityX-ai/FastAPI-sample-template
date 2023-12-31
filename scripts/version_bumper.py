import argparse
from pathlib import Path
from typing import List, Optional
import re
import requests

RAW_VERSION_RE = re.compile(r'(?P<package>.*)\s*=\s*\"(?P<version>[\^\~\>\=\<\!]?[\d\.\-\w]+)\"')
EXPANDED_VER_RE = re.compile(
    r'(?P<package>.*)\s*=\s*\{(.*)version\s*=\s*\"(?P<version>[\^\~\>\=\<\!]?[\d\.\-\w]+)\"(.*)\}'
)

def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: The parsed command line arguments.

    Raises:
        None

    Examples:
        >>> args = parse_args()
        >>> print(args.file)
        Path('example.txt')
        >>> print(args.section)
        'tool.poetry.dependencies'
    """
    
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "file",
        type=Path,
    )
    
    parser.add_argument(
        "--section",
        "-s",
        type=str,
        default="tool.poetry.dependencies",
    )
    return parser.parse_args()

def get_dependencies(path: Path, section: str) -> List[str]:
    """
    Get the dependencies from a file.

    Args:
        path (Path): The path to the file.
        section (str): The section to look for in the file.

    Returns:
        List[str]: The list of dependencies.

    Raises:
        FileNotFoundError: If the file specified by `path` does not exist.
    """
    read_file = path.read_text()
    recording = False
    deps = []
    
    for index, line in enumerate(read_file.splitlines(keepends=False)):
        if line.startswith('[') and line.strip('[]') != section:
            recording = False
            continue
        if line == f"[{section}]":
            recording = True
            continue
        if line.startswith('python ='):
            continue
        if line.startswith('{%'):
            continue
        if recording:
            deps.append((index, line))
    return deps

def get_new_version(package_name: str) -> Optional[str]:
    """
    Get the latest version of a package from PyPI.

    Args:
        package_name (str): The name of the package.

    Returns:
        Optional[str]: The latest version of the package, or None if it cannot be found.
    """
    resp = requests.get(f'https://pypi.org/pypi/{package_name}/json')
    if not resp.ok:
        return None
    rjson = resp.json()
    return rjson['info']["version"]


def bump_version(dependency: str) -> str:
    """
    Bump the version of a dependency.

    Args:
        dependency (str): The dependency string.

    Returns:
        str: The updated dependency string, or None if the version cannot be bumped.

    Raises:
        None

    Examples:
        >>> bump_version("^requests==2.25.0")
        '^requests==2.26.0'
        >>> bump_version("numpy>=1.19.0")
        'numpy>=1.19.0'

    Note:
        This function checks if there is a new version available for the given dependency.
        If a new version is found, it updates the version in the dependency string and returns the updated string.
        If no new version is found or the version cannot be bumped, it returns None.
    """
    exp_match = EXPANDED_VER_RE.match(dependency)
    raw_match = None
    if exp_match:
        package = exp_match.group("package").strip()
        version = exp_match.group("version").lstrip("^=!~<>")
    else:
        raw_match = RAW_VERSION_RE.match(dependency)
    if raw_match:
        package = raw_match.group("package").strip()
        version = raw_match.group("version").lstrip("^=!~<>")
    if exp_match is None and raw_match is None:
        return "This is not defined"

    print(f"Checking {package}")
    new_version = get_new_version(package)
    if new_version is not None and version != new_version:
        print(f"Found new version: {new_version}")
        return dependency.replace(version, new_version)

    return None

def main():
    """
    The main function.
    """
    args = parse_args()
    deps = get_dependencies(args.file, args.section)
    lines = args.file.read_text().splitlines(keepends=False)
    for i, dep in deps:
        new_version = bump_version(dep)
        if new_version:
            lines[i] = new_version
    args.file.write_text("\n".join(lines))
    


if __name__ == "__main__":
    main()
