from __future__ import annotations

import typer

from ..core.config import get_settings
from .commands.configure import configure
from .commands.context import context
from .commands.eval import app as eval_app
from .commands.extract import extract
from .commands.health import health
from .commands.observe import observe
from .commands.recall import recall
from .commands.remember import remember
from .commands.search import search
from .commands.sessions import app as sessions_app

app = typer.Typer(
    name="memorybase",
    help="MemoryBase agent runtime CLI.",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"memorybase {get_settings().app_version}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show MemoryBase CLI version and exit.",
    ),
) -> None:
    _ = version


app.command("configure", short_help="Configure CLI defaults")(configure)
app.command("context", short_help="Render agent context")(context)
app.command("extract", short_help="Extract candidate memories from chunks")(extract)
app.command("health", short_help="Check API, workspace, and agent health")(health)
app.command("observe", short_help="Write conversation messages")(observe)
app.command("recall", short_help="Recall governed memories")(recall)
app.command("remember", short_help="Write a memory")(remember)
app.command("search", short_help="Search memories and sources")(search)
app.add_typer(eval_app, name="eval")
app.add_typer(sessions_app, name="sessions")
