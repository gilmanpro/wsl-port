# Contributing to wsl-port

Thank you for your interest in contributing to wsl-port! This document provides guidelines and information for contributors.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/wsl-port.git
   cd wsl-port
   ```
3. **Create a branch** for your feature or fix:
   ```bash
   git checkout -b feature/my-feature
   ```

## Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # Linux/macOS
   ```

2. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Run tests:
   ```bash
   python -m pytest tests -q
   ```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Keep functions focused and small
- Write docstrings for public functions

## Testing

- All new features must include tests
- Run the full test suite before submitting:
  ```bash
  python -m pytest tests -q
  ```

## Submitting Changes

1. **Commit** your changes with a clear message:
   ```bash
   git commit -m "Add feature: description of what you did"
   ```

2. **Push** to your fork:
   ```bash
   git push origin feature/my-feature
   ```

3. **Create a Pull Request** on GitHub with:
   - A clear description of the changes
   - Reference to any related issues
   - Screenshots if UI changes are involved

## Reporting Issues

- Use the GitHub Issues page
- Include steps to reproduce the issue
- Include your OS and Python version
- Include error messages if applicable

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
