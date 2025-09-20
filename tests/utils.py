from pathlib import Path
from typing import Final

from dotenv import dotenv_values

from crawler import Crawler

RootDir: Final[Path] = Path(__file__).parent.parent.resolve()

EnvVars: Final[dict[str, str]] = dotenv_values(RootDir / ".env")
