"""Interests CLI command group for personal-index."""

from __future__ import annotations

import os
import sys

import click

from personal_index.interests import InterestStore
from personal_index.models import Interest, InterestType, MatchMode


@click.group("interests")
@click.pass_context
def interests(ctx):
    """Manage your content interests.

    Interests define what topics and keywords you care about.
    The pipeline uses interests to score and prioritize content.

    Examples:
        personal-index interests add python -k python -k django
        personal-index interests list
        personal-index interests remove python
    """


@interests.command("add")
@click.option("-n", "--name", required=True, help="Interest name")
@click.option("-k", "--keyword", "keywords", multiple=True, help="Keywords to match")
@click.option("-t", "--topic", "topics", multiple=True, help="Topics to match")
@click.option("-p", "--priority", default=5, type=int, help="Priority (1-10)")
@click.option("--type", "interest_type", default="keyword",
              type=click.Choice(["keyword", "topic", "url_pattern"]),
              help="Interest type")
@click.option("--match-mode", default="any",
              type=click.Choice(["any", "all", "regex"]),
              help="How keywords should match")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_add(ctx, name, keywords, topics, priority, interest_type, match_mode, data_dir):
    """Add a new interest."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)

    store = InterestStore(store_path=os.path.join(dd, "interests.json"))

    # Check if interest already exists
    existing = store.list_all()
    if any(i.name == name for i in existing):
        click.echo(f"Interest '{name}' already exists. Use 'remove' first to replace.", err=True)
        sys.exit(1)

    interest = Interest(
        name=name,
        interest_type=InterestType(interest_type),
        keywords=list(keywords),
        topics=list(topics),
        priority=max(1, min(10, priority)),
        match_mode=MatchMode(match_mode),
    )

    store.add(interest)
    click.echo(f"Added interest '{name}'")
    if keywords:
        click.echo(f"  Keywords: {', '.join(keywords)}")
    if topics:
        click.echo(f"  Topics: {', '.join(topics)}")
    click.echo(f"  Priority: {priority}")


@interests.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_list(ctx, data_dir):
    """List all configured interests."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = InterestStore(store_path=os.path.join(dd, "interests.json"))

    interests = store.list_all()
    if not interests:
        click.echo("No interests configured.")
        click.echo("Add one: personal-index interests add my-interest -k keyword1 -k keyword2")
        return

    click.echo(f"Interests ({len(interests)}):")
    click.echo("-" * 50)
    for interest in interests:
        status = "✓" if interest.enabled else "✗"
        click.echo(f"\n  {status} {interest.name} (priority: {interest.priority})")
        if interest.keywords:
            click.echo(f"    Keywords: {', '.join(interest.keywords)}")
        if interest.topics:
            click.echo(f"    Topics: {', '.join(interest.topics)}")
        if interest.url_patterns:
            click.echo(f"    URL patterns: {', '.join(interest.url_patterns)}")


@interests.command("remove")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_remove(ctx, name, data_dir):
    """Remove an interest by name."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = InterestStore(store_path=os.path.join(dd, "interests.json"))

    if store.remove(name):
        click.echo(f"Removed interest '{name}'")
    else:
        click.echo(f"Interest '{name}' not found.", err=True)
        sys.exit(1)


@interests.command("enable")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_enable(ctx, name, data_dir):
    """Enable a disabled interest."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = InterestStore(store_path=os.path.join(dd, "interests.json"))

    interest = store.get(name)
    if interest:
        interest.enabled = True
        store.add(interest)
        click.echo(f"Enabled interest '{name}'")
    else:
        click.echo(f"Interest '{name}' not found.", err=True)
        sys.exit(1)


@interests.command("disable")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_disable(ctx, name, data_dir):
    """Disable an interest without removing it."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = InterestStore(store_path=os.path.join(dd, "interests.json"))

    interest = store.get(name)
    if interest:
        interest.enabled = False
        store.add(interest)
        click.echo(f"Disabled interest '{name}'")
    else:
        click.echo(f"Interest '{name}' not found.", err=True)
        sys.exit(1)
