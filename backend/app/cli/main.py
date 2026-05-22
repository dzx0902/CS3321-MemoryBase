from __future__ import annotations

import typer

from .commands.configure import configure
from .commands.context import context
from .commands.eval import app as eval_app
from .commands.health import health
from .commands.observe import observe
from .commands.recall import recall
from .commands.remember import remember
from .commands.sessions import app as sessions_app

app = typer.Typer(
    name="memorybase",
    help="MemoryBase agent runtime CLI.",
    no_args_is_help=True,
)

app.command("configure")(configure)
app.command("context")(context)
app.command("health")(health)
app.command("observe")(observe)
app.command("recall")(recall)
app.command("remember")(remember)
app.add_typer(eval_app, name="eval")
app.add_typer(sessions_app, name="sessions")
