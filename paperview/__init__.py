from pathlib import Path

__version__ = "0.1.0"
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

repo_root = Path(__file__).parent.parent
