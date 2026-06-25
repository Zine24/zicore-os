# Contributing to ZICORE

Thank you for your interest in contributing to ZICORE System.

## Development Setup

```bash
git clone https://github.com/Zine24/zicore-system.git
cd zicore-system
pip install -r requirements.txt
pip install pytest pytest-asyncio
```

### Run Tests

```bash
python -m pytest tests/ -v
```

### Start Development Servers

```bash
python start_all.py
```

- Web: `http://localhost:3000`
- API: `http://localhost:8080`

---

## Code Style

### Python

- Use `async/await` for async functions
- Use type hints where possible
- Follow PEP 8
- Add docstrings to public functions

```python
async def process(self, user_input: str, context: dict = None) -> dict:
    """Process user input through dual-engine pipeline."""
    pass
```

### Frontend (HTML/JS)

- Use `var` instead of `let`/`const`
- Use `addEventListener` instead of inline `onclick`
- No external frameworks (vanilla JS only)
- Keep file sizes manageable

```javascript
// Good
var btn = document.getElementById('myBtn');
btn.addEventListener('click', function() { ... });

// Bad
let btn = document.getElementById('myBtn');
btn.onclick = () => { ... };
```

---

## Project Structure

```
backend/          FastAPI API (port 8080)
frontend/         Static HTML/JS/CSS (port 3000)
agent/            AI agent core
zicore/           Core modules (knowledge, vision, telemetry)
zty/              Z-TY Factory (aircraft design)
native/           Rust/C++ modules
tests/            Test suite
data/             Config, knowledge, missions
```

---

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `python -m pytest tests/ -v`
5. Commit: `git commit -m "Add my feature"`
6. Push: `git push origin feature/my-feature`
7. Open a Pull Request

### PR Title Format

```
feat: Add new feature
fix: Fix bug in module
docs: Update documentation
refactor: Refactor code
test: Add tests
```

---

## Reporting Issues

Use the GitHub issue templates:

- **Bug Report** — Steps to reproduce, expected vs actual behavior
- **Feature Request** — Use case, proposed solution

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Contact

- GitHub: [Zine24](https://github.com/Zine24)
- Organization: ZineMotion Foundation
