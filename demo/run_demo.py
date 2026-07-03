import asyncio
import json
import logging
from pathlib import Path

# This is a terminal demo meant to be screenshot-clean — the pipeline's own
# graceful-degradation warnings (e.g. missing API keys) are informative in
# production logs but just noise here; the demo table already surfaces the
# same information to the viewer. Must run before importing the pipeline —
# some of its modules log a warning at import time.
logging.disable(logging.WARNING)

from rich.console import Console  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.table import Table  # noqa: E402

from pipeline.guard import guard  # noqa: E402
from pipeline.models import LLMResponse  # noqa: E402
from scoring.models import Verdict  # noqa: E402

console = Console()

PROMPTS_PATH = Path(__file__).parent / "hard_prompts.json"

_VERDICT_STYLE = {
    Verdict.FATAL_FLAW: "bold red",
    Verdict.FLAGGED: "yellow",
    Verdict.VERIFIED: "green",
    Verdict.UNCERTAIN: "dim",
}


def _build_table(entities) -> Table:
    table = Table(show_header=True, header_style="bold")
    table.add_column("Entity")
    table.add_column("Verdict")
    table.add_column("Detail")

    if not entities:
        table.add_row(
            "—",
            "N/A",
            "No entities extracted — ANTHROPIC_API_KEY / VOYGR_API_KEY not configured",
        )
        return table

    for entity_verdict in entities:
        style = _VERDICT_STYLE[entity_verdict.verdict]
        detail = entity_verdict.fatal_flaw_reason or f"confidence {entity_verdict.confidence:.2f}"
        table.add_row(
            entity_verdict.entity.name,
            f"[{style}]{entity_verdict.verdict.value.upper().replace('_', ' ')}[/{style}]",
            detail,
        )
    return table


async def run_demo() -> None:
    prompts = json.loads(PROMPTS_PATH.read_text())

    console.rule("[bold]GuardLayer Demo — VOYGR's hardest published prompts[/bold]")

    fatal_flaw_prompts = 0
    verified_clean_prompts = 0

    for i, prompt in enumerate(prompts, start=1):
        console.print()
        console.print(f"[bold cyan][{i}/{len(prompts)}][/bold cyan] {prompt['label']}")
        console.print(f"[dim]Source: {prompt['source']}[/dim]")
        console.print()
        console.print("  LLM response (simulated):")
        console.print(Panel(prompt["text"], expand=False, padding=(0, 1)))

        response = await guard(LLMResponse(text=prompt["text"], source_llm=prompt["source_llm"]))

        console.print()
        console.print("  GuardLayer verdict:")
        console.print(_build_table(response.entities))

        console.print()
        if response.fatal_flaw_count > 0:
            fatal_flaw_prompts += 1
            console.print(
                "  [bold red]✗ GuardLayer would have blocked this response "
                "from reaching the user.[/bold red]"
            )
        else:
            verified_clean_prompts += 1
            console.print(
                "  [bold green]✓ GuardLayer verified this response is safe "
                "to show the user.[/bold green]"
            )

        console.rule()

    console.print()
    console.print(
        f"[bold]Summary:[/bold] {fatal_flaw_prompts}/{len(prompts)} fatal flaws caught · "
        f"{verified_clean_prompts}/{len(prompts)} verified clean"
    )


def main() -> None:
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
