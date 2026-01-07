"""
Command-line interface for TSM Item ID Scraper.

Provides commands for:
- Loading and analyzing TSM saved variables
- Scraping items from Wowhead
- Importing items to TSM groups
"""

import sys
from pathlib import Path
from typing import Optional

try:
    import click
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("Please install required packages: pip install click rich")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

from .lua_parser import TSMLuaParser
from .lua_writer import TSMLuaWriter
from .wowhead_scraper import WowheadScraper
from .categorizer import ItemCategorizer

console = Console()

# Default TSM path
DEFAULT_TSM_PATH = r"c:\Ascension Launcher\resources\client\WTF\Account\Xurkon\SavedVariables\TradeSkillMaster.lua"


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """TSM Item ID Scraper - Import items into TradeSkillMaster."""
    pass


@cli.command()
@click.option('--file', '-f', default=DEFAULT_TSM_PATH, 
              help='Path to TradeSkillMaster.lua')
def info(file: str):
    """Show information about TSM saved variables."""
    parser = TSMLuaParser(file)
    
    if not parser.load():
        console.print(f"[red]Error: Could not load file: {file}[/red]")
        return
    
    parser.parse_items()
    parser.parse_groups()
    
    console.print(f"\n[bold]TSM SavedVariables Info[/bold]")
    console.print(f"File: [cyan]{file}[/cyan]")
    console.print(f"Total items: [green]{len(parser.items)}[/green]")
    console.print(f"Total groups: [green]{len(parser.groups)}[/green]")
    
    # Show top groups by item count
    console.print(f"\n[bold]Top Groups by Item Count:[/bold]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Group", style="cyan")
    table.add_column("Items", justify="right", style="green")
    
    group_counts = {}
    for group in parser.groups:
        count = len(parser.get_items_by_group(group))
        if count > 0:
            group_counts[group] = count
    
    for group, count in sorted(group_counts.items(), key=lambda x: -x[1])[:15]:
        table.add_row(group, str(count))
    
    console.print(table)


@cli.command()
@click.option('--file', '-f', default=DEFAULT_TSM_PATH,
              help='Path to TradeSkillMaster.lua')
def groups(file: str):
    """List all TSM groups."""
    parser = TSMLuaParser(file)
    
    if not parser.load():
        console.print(f"[red]Error: Could not load file: {file}[/red]")
        return
    
    parser.parse_groups()
    
    console.print(f"\n[bold]TSM Groups ({len(parser.groups)} total):[/bold]\n")
    
    # Organize by top-level category
    by_category = {}
    for group in sorted(parser.groups):
        parts = group.split('`')
        category = parts[0]
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(group)
    
    for category in sorted(by_category.keys()):
        console.print(f"[bold cyan]{category}[/bold cyan]")
        for group in by_category[category][:10]:  # Show first 10 per category
            console.print(f"  {group}")
        if len(by_category[category]) > 10:
            console.print(f"  [dim]... and {len(by_category[category]) - 10} more[/dim]")
        console.print()


@cli.command()
@click.argument('category')
@click.option('--limit', '-l', default=20, help='Maximum items to fetch')
@click.option('--cache/--no-cache', default=True, help='Use cached results')
def scrape(category: str, limit: int, cache: bool):
    """
    Scrape items from Wowhead.
    
    CATEGORY examples: sword_1h, sword_2h, axe_1h, dagger, staff, bow, gun, etc.
    """
    scraper = WowheadScraper()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"Scraping {category}...", total=None)
        
        items = scraper.scrape_weapons(category, limit=limit)
        
        progress.update(task, completed=True)
    
    if not items:
        console.print(f"[yellow]No items found for category: {category}[/yellow]")
        return
    
    console.print(f"\n[bold]Found {len(items)} items:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Name", style="white")
    table.add_column("Type", style="dim")
    
    for item in items:
        table.add_row(str(item.id), item.name, item.item_subclass or item.item_class)
    
    console.print(table)


@cli.command('import')
@click.option('--file', '-f', default=DEFAULT_TSM_PATH,
              help='Path to TradeSkillMaster.lua')
@click.option('--group', '-g', required=True, 
              help='TSM group path (use backticks, e.g. Transmog`Swords`One Hand)')
@click.option('--items', '-i', required=True,
              help='Comma-separated item IDs or @file with one ID per line')
@click.option('--dry-run', is_flag=True, help='Preview changes without modifying file')
def import_items(file: str, group: str, items: str, dry_run: bool):
    """Import item IDs into a TSM group."""
    # Parse item IDs
    item_ids = []
    
    if items.startswith('@'):
        # Read from file
        item_file = Path(items[1:])
        if not item_file.exists():
            console.print(f"[red]Error: Item file not found: {item_file}[/red]")
            return
        with open(item_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and line.isdigit():
                    item_ids.append(int(line))
    else:
        # Comma-separated
        for item in items.split(','):
            item = item.strip()
            if item.isdigit():
                item_ids.append(int(item))
    
    if not item_ids:
        console.print("[red]Error: No valid item IDs provided[/red]")
        return
    
    console.print(f"\n[bold]Importing {len(item_ids)} items to: [cyan]{group}[/cyan][/bold]")
    
    if dry_run:
        console.print("[yellow]DRY RUN - No changes will be made[/yellow]\n")
    
    # Create item dict
    items_dict = {item_id: group for item_id in item_ids}
    
    # Import
    writer = TSMLuaWriter(file)
    result = writer.add_items(items_dict, dry_run=dry_run)
    
    console.print(f"[green]Added: {result['added']}[/green]")
    console.print(f"[yellow]Skipped (already exist): {result['skipped']}[/yellow]")
    
    if result['errors']:
        for error in result['errors']:
            console.print(f"[red]Error: {error}[/red]")
    
    if result['items_added'] and not dry_run:
        console.print(f"\n[dim]Items added:[/dim]")
        for item_id, grp in result['items_added'][:10]:
            console.print(f"  {item_id} -> {grp}")
        if len(result['items_added']) > 10:
            console.print(f"  ... and {len(result['items_added']) - 10} more")


@cli.command()
@click.argument('category')
@click.option('--file', '-f', default=DEFAULT_TSM_PATH,
              help='Path to TradeSkillMaster.lua')
@click.option('--limit', '-l', default=50, help='Maximum items to fetch and import')
@click.option('--dry-run', is_flag=True, help='Preview changes without modifying file')
def auto_import(category: str, file: str, limit: int, dry_run: bool):
    """
    Scrape and auto-categorize items into TSM.
    
    CATEGORY: weapon type like sword_1h, axe_2h, dagger, staff, bow, etc.
    """
    scraper = WowheadScraper()
    categorizer = ItemCategorizer()
    
    console.print(f"\n[bold]Auto-importing {category} items...[/bold]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"Scraping {category} from Wowhead...", total=None)
        items = scraper.scrape_weapons(category, limit=limit)
        progress.update(task, completed=True)
    
    if not items:
        console.print(f"[yellow]No items found for: {category}[/yellow]")
        return
    
    console.print(f"Found [green]{len(items)}[/green] items")
    
    # Categorize items
    categorized = {}
    for item in items:
        group = categorizer.categorize(
            item.item_class,
            item.item_subclass,
            item.slot,
            item.name
        )
        if group not in categorized:
            categorized[group] = []
        categorized[group].append(item.id)
    
    # Show categorization
    console.print(f"\n[bold]Categories:[/bold]")
    for group, ids in categorized.items():
        console.print(f"  [cyan]{group}[/cyan]: {len(ids)} items")
    
    if dry_run:
        console.print(f"\n[yellow]DRY RUN - No changes made[/yellow]")
        return
    
    # Import each category
    writer = TSMLuaWriter(file)
    total_added = 0
    total_skipped = 0
    
    for group, ids in categorized.items():
        items_dict = {item_id: group for item_id in ids}
        result = writer.add_items(items_dict, dry_run=False)
        total_added += result['added']
        total_skipped += result['skipped']
    
    console.print(f"\n[bold]Import Complete:[/bold]")
    console.print(f"  [green]Added: {total_added}[/green]")
    console.print(f"  [yellow]Skipped: {total_skipped}[/yellow]")


@cli.command()
@click.option('--file', '-f', default=DEFAULT_TSM_PATH,
              help='Path to TradeSkillMaster.lua')
@click.option('--items', '-i', required=True,
              help='Comma-separated item IDs to remove')
@click.option('--dry-run', is_flag=True, help='Preview changes without modifying file')
def remove(file: str, items: str, dry_run: bool):
    """Remove items from TSM groups."""
    item_ids = [int(i.strip()) for i in items.split(',') if i.strip().isdigit()]
    
    if not item_ids:
        console.print("[red]Error: No valid item IDs provided[/red]")
        return
    
    console.print(f"\n[bold]Removing {len(item_ids)} items...[/bold]")
    
    if dry_run:
        console.print("[yellow]DRY RUN - No changes will be made[/yellow]")
    
    writer = TSMLuaWriter(file)
    result = writer.remove_items(item_ids, dry_run=dry_run)
    
    console.print(f"[green]Removed: {result['removed']}[/green]")
    console.print(f"[yellow]Not found: {result['not_found']}[/yellow]")


@cli.command()
@click.argument('item_id', type=int)
def lookup(item_id: int):
    """Look up an item from Wowhead by ID."""
    scraper = WowheadScraper()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"Looking up item {item_id}...", total=None)
        item = scraper.get_item(item_id)
        progress.update(task, completed=True)
    
    if not item:
        console.print(f"[red]Item not found: {item_id}[/red]")
        return
    
    console.print(f"\n[bold]Item {item_id}:[/bold]")
    console.print(f"  Name: [cyan]{item.name}[/cyan]")
    console.print(f"  Class: {item.item_class}")
    console.print(f"  Subclass: {item.item_subclass}")
    console.print(f"  Slot: {item.slot}")
    console.print(f"  Quality: {item.quality}")
    
    # Show suggested category
    categorizer = ItemCategorizer()
    group = categorizer.categorize(item.item_class, item.item_subclass, item.slot, item.name)
    console.print(f"\n  Suggested TSM group: [green]{group}[/green]")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
