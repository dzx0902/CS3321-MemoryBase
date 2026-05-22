from __future__ import annotations

import typer

from .commands.configure import configure
from .commands.health import health

app = typer.Typer(
    name="memorybase",
    help="MemoryBase agent runtime CLI.",
    no_args_is_help=True,
)

app.command("configure")(configure)
app.command("health")(health)
