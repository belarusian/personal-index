"""CLI interface for personal-index."""

from __future__ import annotations

import json
import os
from pathlib import Path

import click

from personal_index.interest_store import InterestStore
from personal_index.models import Interest, InterestType


DEFAULT_DATA_DIR = os.path.expanduser("~/.personal-index")


def get_data_dir() -> str:
    """Get the data directory path."""
    return os.environ.get("PERSONAL_INDEX_DATA_DIR", DEFAULT_DATA_DIR)


def get_interest_store() -> InterestStore:
    """Get the default interest store."""
    return InterestStore(storage_path=os.path.join(get_data_dir(), "interests.json"))


@click.group()
@click.version_option(version="0.1.0", prog_name="personal-index")
def cli():
    """personal-index: A personal web search engine.

    Define your interests and the system scans, filters, and indexes the web for you.
    """
    pass


@cli.group()
def interests():
    """Manage your tracked interests."""
    pass


@interests.command()
@click.option("--name", "-n", required=True, help="Name for this interest")
@click.option(
    "--type",
    "-t",
    "interest_type",
    type=click.Choice(["keyword", "topic", "url_pattern"], case_sensitive=False),
    default="keyword",
    help="Type of interest",
)
@click.option("--value", "-v", required=True, help="Value (keyword, topic terms, or regex)")
@click.option(
    "--priority", "-p", type=int, default=5, help="Priority 1-10 (default: 5)"
)
def add(name, interest_type, value, priority):
    """Add a new interest to track."""
    store = get_interest_store()
    if store.get(name):
        click.echo(f"Error: Interest '{name}' already exists.", err=True)
        raise SystemExit(1)

    interest = Interest(
        name=name,
        interest_type=InterestType(interest_type),
        value=value,
        priority=max(1, min(10, priority)),
    )
    store.add(interest)
    click.echo(f"Added interest: {name} ({interest_type}) = {value}")


@interests.command()
@click.option("--name", "-n", required=True, help="Name of interest to remove")
def remove(name):
    """Remove an interest."""
    store = get_interest_store()
    if store.remove(name):
        click.echo(f"Removed interest: {name}")
    else:
        click.echo(f"Error: Interest '{name}' not found.", err=True)
        raise SystemExit(1)


@interests.command("list")
@click.option("--enabled-only", "-e", is_flag=True, help="Show only enabled interests")
def list_interests(enabled_only):
    """List all configured interests."""
    store = get_interest_store()
    interests_list = store.list_all(enabled_only=enabled_only)

    if not interests_list:
        click.echo("No interests configured.")
        return

    click.echo(f"{'Name':<20} {'Type':<12} {'Value':<30} {'Pri':<5} {'Enabled':<8}")
    click.echo("-" * 75)
    for interest in interests_list:
        click.echo(
            f"{interest.name:<20} "
            f"{interest.interest_type.value:<12} "
            f"{interest.value:<30} "
            f"{interest.priority:<5} "
            f"{'✓' if interest.enabled else '✗':<8}"
        )


@interests.command()
@click.option("--name", "-n", required=True, help="Name of interest to toggle")
def toggle(name):
    """Toggle an interest on/off."""
    store = get_interest_store()
    result = store.toggle(name)
    if result:
        status = "enabled" if result.enabled else "disabled"
        click.echo(f"Interest '{name}' is now {status}")
    else:
        click.echo(f"Error: Interest '{name}' not found.", err=True)
        raise SystemExit(1)


@interests.command()
@click.option("--name", "-n", required=True, help="Name of interest")
@click.option("--priority", "-p", type=int, required=True, help="New priority 1-10")
def priority(name, priority):
    """Update the priority of an interest."""
    store = get_interest_store()
    result = store.update_priority(name, priority)
    if result:
        click.echo(f"Updated priority for '{name}' to {result.priority}")
    else:
        click.echo(f"Error: Interest '{name}' not found.", err=True)
        raise SystemExit(1)
