"""Watch CLI command for personal-index continuous monitoring."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import click


@click.command("watch")
@click.argument("path")
@click.option("--interval", "-i", default=30, type=int, help="Check interval in seconds")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--recursive", "-r", is_flag=True, help="Watch directories recursively")
@click.pass_context
def watch(ctx, path, interval, data_dir, recursive):
    """Watch a directory for changes and re-index automatically.

    Monitors a directory for new or modified files and automatically
    runs the pipeline on changes.

    Examples:
        personal-index watch ./docs
        personal-index watch ./content --interval 60 --recursive
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)

    if not os.path.exists(path):
        click.echo(f"Error: Path '{path}' does not exist.", err=True)
        sys.exit(1)

    click.echo(f"Watching {path} for changes (interval: {interval}s)")
    click.echo("Press Ctrl+C to stop.\n")

    # Track file modification times
    file_times: dict[str, float] = {}

    def scan_files(target_path: str) -> dict[str, float]:
        """Scan directory and return file modification times."""
        times = {}
        if os.path.isfile(target_path):
            times[target_path] = os.path.getmtime(target_path)
        elif os.path.isdir(target_path):
            for root, dirs, files in os.walk(target_path):
                for f in files:
                    fp = os.path.join(root, f)
                    if fp.endswith(('.txt', '.md', '.html', '.htm', '.json', '.xml', '.rst')):
                        times[fp] = os.path.getmtime(fp)
        return times

    try:
        while True:
            current_times = scan_files(path)
            new_files = []
            modified_files = []

            for fp, mtime in current_times.items():
                if fp not in file_times:
                    new_files.append(fp)
                elif mtime > file_times[fp]:
                    modified_files.append(fp)

            if new_files or modified_files:
                click.echo(f"\n[{time.strftime('%H:%M:%S')}] Changes detected:")
                for f in new_files:
                    click.echo(f"  + {f}")
                for f in modified_files:
                    click.echo(f"  ~ {f}")

                # Run import for changed files
                changed = new_files + modified_files
                if changed:
                    click.echo(f"\nRe-indexing {len(changed)} file(s)...")
                    from personal_index.cli_pipeline_unified import run_pipeline
                    from click.testing import CliRunner
                    runner = CliRunner()
                    import_args = ["--data-dir", dd]
                    for f in changed:
                        import_args.extend(["--import-file", f])
                    result = runner.invoke(run_pipeline, import_args)
                    if result.exit_code != 0:
                        click.echo(f"  Warning: Pipeline had issues: {result.output}", err=True)
                    else:
                        click.echo("  Re-index complete.")

            file_times = current_times
            time.sleep(interval)

    except KeyboardInterrupt:
        click.echo("\nWatch stopped.")
