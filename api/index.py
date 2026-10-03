"""Vercel entry point: every request is rewritten here (see vercel.json) and handled by offgrid.wsgi."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "server"))

from offgrid.wsgi import app  # noqa: E402,F401
