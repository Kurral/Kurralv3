"""
CLI commands for Kurral configuration
"""

import os
import click
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

from kurral.core.config import (
    KurralConfig,
    save_config_file,
    get_config,
    CONFIG_FILE_LOCATIONS,
)

console = Console()


@click.group()
def config():
    """Manage Kurral configuration"""
    pass


@config.command()
@click.option("--global", "is_global", is_flag=True, help="Save to user config (~/.config/kurral/)")
@click.option("--local", "is_local", is_flag=True, help="Save to project config (./.kurral/)")
def init(is_global, is_local):
    """
    Initialize Kurral configuration
    
    Saves settings to config file so you don't need env vars every time.
    """
    console.print("\n[bold cyan]🔧 Kurral Configuration Setup[/bold cyan]\n")
    
    # Determine location
    if is_local:
        location = "project"
        console.print("📁 Saving to: [cyan]./.kurral/config.json[/cyan] (project-specific)\n")
    else:
        location = "user"
        console.print("📁 Saving to: [cyan]~/.config/kurral/config.json[/cyan] (user-wide)\n")
    
    # Storage backend
    console.print("[bold]Storage Configuration:[/bold]")
    console.print("  • [cyan]local[/cyan] - Save artifacts to local disk")
    console.print("  • [cyan]memory[/cyan] - Store artifacts in RAM (fast, no I/O)")
    console.print("  • [cyan]api[/cyan] - Upload to Kurral Cloud (requires API key)")
    console.print("  • [cyan]custom-bucket[/cyan] - Use your own R2/S3 bucket")
    console.print("  • [cyan]r2[/cyan] - Legacy: Kurral's shared R2 bucket\n")
    
    storage = Prompt.ask(
        "Storage backend",
        choices=["local", "memory", "api", "custom-bucket", "r2"],
        default="local"
    )
    
    config_dict = {"storage_backend": storage if storage != "custom-bucket" else "local"}
    
    # Kurral API configuration
    if storage == "api":
        console.print("\n[yellow]🔑 Kurral Cloud API[/yellow]")
        console.print("Upload artifacts to Kurral's managed cloud storage.\n")
        console.print("[dim]Get your API key at: https://app.kurral.io/settings/api-keys[/dim]\n")
        
        config_dict["kurral_api_key"] = Prompt.ask("Kurral API Key", password=True, default=os.getenv("KURRAL_API_KEY", ""))
        config_dict["kurral_api_url"] = Prompt.ask("Kurral API URL", default=os.getenv("KURRAL_API_URL", "https://api.kurral.io"))
    
    # Custom bucket configuration
    elif storage == "custom-bucket":
        console.print("\n[yellow]🪣 Custom Bucket Configuration[/yellow]")
        console.print("Store artifacts in your own R2/S3 bucket.\n")
        
        bucket_type = Prompt.ask("Bucket type", choices=["r2", "s3"], default="r2")
        
        config_dict["custom_bucket_enabled"] = True
        config_dict["custom_bucket_name"] = Prompt.ask("Bucket name", default=os.getenv("KURRAL_CUSTOM_BUCKET_NAME", ""))
        
        if bucket_type == "r2":
            console.print("\n[dim]Cloudflare R2 Configuration:[/dim]")
            config_dict["custom_bucket_account_id"] = Prompt.ask("Cloudflare Account ID", default=os.getenv("KURRAL_CUSTOM_BUCKET_ACCOUNT_ID", ""))
            config_dict["custom_bucket_region"] = "auto"
        else:
            console.print("\n[dim]AWS S3 Configuration:[/dim]")
            config_dict["custom_bucket_endpoint"] = Prompt.ask("S3 Endpoint (optional, leave blank for AWS)", default=os.getenv("KURRAL_CUSTOM_BUCKET_ENDPOINT", ""))
            config_dict["custom_bucket_region"] = Prompt.ask("S3 Region", default=os.getenv("KURRAL_CUSTOM_BUCKET_REGION", "us-east-1"))
        
        config_dict["custom_bucket_access_key_id"] = Prompt.ask("Access Key ID", default=os.getenv("KURRAL_CUSTOM_BUCKET_ACCESS_KEY_ID", ""))
        config_dict["custom_bucket_secret_access_key"] = Prompt.ask("Secret Access Key", password=True, default=os.getenv("KURRAL_CUSTOM_BUCKET_SECRET_ACCESS_KEY", ""))
    
    # Legacy R2 configuration
    elif storage == "r2":
        console.print("\n[yellow]📦 Legacy: Kurral R2 Storage[/yellow]")
        console.print("[dim]⚠️  This option is deprecated. Please use 'api' mode instead.[/dim]\n")
        console.print("Contact your Kurral admin for these credentials.\n")
        
        # Pre-fill with Kurral's bucket if available in env
        config_dict["r2_bucket"] = Prompt.ask("R2 Bucket name", default=os.getenv("KURRAL_R2_BUCKET", "kurral-artifacts"))
        config_dict["r2_account_id"] = Prompt.ask("R2 Account ID", default=os.getenv("KURRAL_R2_ACCOUNT_ID", ""))
        config_dict["r2_access_key_id"] = Prompt.ask("R2 Access Key ID", default=os.getenv("KURRAL_R2_ACCESS_KEY_ID", ""))
        config_dict["r2_secret_access_key"] = Prompt.ask("R2 Secret Access Key", password=True, default=os.getenv("KURRAL_R2_SECRET_ACCESS_KEY", ""))
    
    # LangSmith (optional)
    console.print("\n[yellow]🔍 LangSmith Integration (Optional)[/yellow]")
    if Confirm.ask("Enable LangSmith integration?", default=False):
        config_dict["langsmith_enabled"] = True
        config_dict["langsmith_api_key"] = Prompt.ask("LangSmith API Key", password=True)
        config_dict["langsmith_project"] = Prompt.ask("LangSmith Project", default="default")
    
    # Debug mode
    config_dict["debug"] = Confirm.ask("\nEnable debug mode?", default=False)
    
    # Save config
    try:
        config_obj = KurralConfig(**config_dict)
        config_path = save_config_file(config_obj, location=location)
        
        console.print(f"\n[green]✅ Configuration saved to: {config_path}[/green]")
        console.print("\n[dim]You can now use Kurral without setting environment variables![/dim]")
        
        # Show example usage
        console.print("\n[bold]Example usage:[/bold]")
        console.print("""
[cyan]from kurral.core.decorator import trace_llm

@trace_llm(semantic_bucket="support", tenant_id="acme")
def my_agent(query):
    return llm.invoke(query)
[/cyan]
""")
        if storage == "r2":
            console.print("[dim]✅ Artifacts will auto-upload to Kurral's R2 bucket after each trace.[/dim]\n")
        
    except Exception as e:
        console.print(f"[red]❌ Error saving configuration: {e}[/red]")


@config.command()
def show():
    """Show current configuration"""
    config = get_config()
    
    console.print("\n[bold cyan]📋 Current Kurral Configuration[/bold cyan]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")
    
    # Storage
    table.add_row("Storage Backend", config.storage_backend)
    if config.storage_backend == "local":
        table.add_row("Local Path", str(config.local_storage_path))
    elif config.storage_backend == "api":
        table.add_row("Kurral API URL", config.kurral_api_url)
        table.add_row("Kurral API Key", "***" if config.kurral_api_key else "[dim]Not set[/dim]")
        if config.tenant_id:
            table.add_row("Tenant ID", config.tenant_id)
    elif config.storage_backend == "r2":
        table.add_row("R2 Bucket", config.r2_bucket or "[dim]Not set[/dim]")
        table.add_row("R2 Account ID", config.r2_account_id or "[dim]Not set[/dim]")
        table.add_row("R2 Access Key", "***" if config.r2_access_key_id else "[dim]Not set[/dim]")
    
    # Custom bucket (can be used with any storage backend)
    if config.custom_bucket_enabled:
        table.add_row("─" * 20, "─" * 20)  # Separator
        table.add_row("Custom Bucket Enabled", "✅ Yes")
        table.add_row("Custom Bucket Name", config.custom_bucket_name or "[dim]Not set[/dim]")
        if config.custom_bucket_account_id:
            table.add_row("Custom Account ID", config.custom_bucket_account_id)
        if config.custom_bucket_endpoint:
            table.add_row("Custom Endpoint", config.custom_bucket_endpoint)
        table.add_row("Custom Region", config.custom_bucket_region)
        table.add_row("Custom Access Key", "***" if config.custom_bucket_access_key_id else "[dim]Not set[/dim]")
    
    # LangSmith
    table.add_row("LangSmith Enabled", "✅ Yes" if config.langsmith_enabled else "❌ No")
    if config.langsmith_enabled:
        table.add_row("LangSmith Project", config.langsmith_project or "[dim]Not set[/dim]")
    
    # Other
    table.add_row("Environment", config.environment)
    table.add_row("Debug Mode", "✅ Yes" if config.debug else "❌ No")
    
    console.print(table)
    
    # Show config file location
    console.print("\n[bold]Config file locations (in priority order):[/bold]")
    for i, path in enumerate(CONFIG_FILE_LOCATIONS, 1):
        exists = "✅" if path.exists() else "  "
        console.print(f"  {exists} {i}. {path}")
    console.print()


@config.command()
def path():
    """Show config file locations"""
    console.print("\n[bold cyan]📂 Kurral Config File Locations[/bold cyan]\n")
    console.print("Kurral checks these locations in order:\n")
    
    for i, path in enumerate(CONFIG_FILE_LOCATIONS, 1):
        exists = path.exists()
        status = "[green]✅ EXISTS[/green]" if exists else "[dim]❌ Not found[/dim]"
        console.print(f"{i}. {status}")
        console.print(f"   [cyan]{path}[/cyan]\n")
    
    console.print("[dim]Tip: Use 'kurral config init' to create a config file.[/dim]\n")


@config.command()
@click.option("--global", "is_global", is_flag=True, help="Reset user config")
@click.option("--local", "is_local", is_flag=True, help="Reset project config")
def reset(is_global, is_local):
    """Delete configuration file"""
    if is_local:
        config_path = Path.cwd() / ".kurral" / "config.json"
    else:
        config_path = Path.home() / ".config" / "kurral" / "config.json"
    
    if not config_path.exists():
        console.print(f"[yellow]⚠️  Config file not found: {config_path}[/yellow]")
        return
    
    if Confirm.ask(f"Delete {config_path}?", default=False):
        config_path.unlink()
        console.print(f"[green]✅ Deleted: {config_path}[/green]")
    else:
        console.print("[dim]Cancelled[/dim]")

