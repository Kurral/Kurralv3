"""
CLI commands for Kurral authentication and registration
"""

import os
import json
import click
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text

try:
    import httpx
except ImportError:
    httpx = None

from kurral.core.config import (
    KurralConfig,
    save_config_file,
    get_config,
)

console = Console()


@click.group()
def auth():
    """Authentication and user management"""
    pass


@auth.command()
@click.option("--email", help="Email address for registration")
@click.option("--password", help="Password (will prompt if not provided)", hide_input=True)
@click.option("--tenant-id", help="Tenant ID (organization identifier)")
@click.option("--api-url", default="https://api.kurral.io", help="Kurral API URL")
@click.option("--global", "is_global", is_flag=True, help="Save to user config (~/.config/kurral/)")
@click.option("--local", "is_local", is_flag=True, help="Save to project config (./.kurral/)")
def register(email, password, tenant_id, api_url, is_global, is_local):
    """
    Register a new Kurral account and configure CLI
    
    This command will:
    1. Register your account
    2. Login and get authentication token
    3. Generate an API key
    4. Save configuration automatically
    """
    if httpx is None:
        console.print("[red]❌ Error: httpx is required for registration[/red]")
        console.print("Install with: [cyan]pip install httpx[/cyan]")
        return
    
    console.print("\n[bold cyan]🚀 Kurral Registration[/bold cyan]\n")
    
    # Collect user inputs
    if not email:
        email = Prompt.ask("Email address")
    
    if not password:
        password = Prompt.ask("Password", password=True)
        password_confirm = Prompt.ask("Confirm password", password=True)
        
        if password != password_confirm:
            console.print("[red]❌ Passwords do not match[/red]")
            return
    
    if not tenant_id:
        tenant_id = Prompt.ask("Tenant ID (organization name)", default=email.split("@")[0])
    
    # Determine config location
    if is_local:
        location = "project"
        console.print(f"📁 Will save to: [cyan]./.kurral/config.json[/cyan] (project-specific)\n")
    else:
        location = "user"
        console.print(f"📁 Will save to: [cyan]~/.config/kurral/config.json[/cyan] (user-wide)\n")
    
    api_url = api_url.rstrip("/")
    
    try:
        with console.status("[bold yellow]Registering account...[/bold yellow]"):
            # Step 1: Register
            with httpx.Client(timeout=30.0) as client:
                register_response = client.post(
                    f"{api_url}/api/v1/auth/register",
                    json={
                        "email": email,
                        "password": password,
                        "tenant_id": tenant_id,
                    }
                )
                
                if register_response.status_code not in [200, 201]:
                    error_msg = "Registration failed"
                    try:
                        error_data = register_response.json()
                        error_msg = error_data.get("detail", error_msg)
                    except Exception:
                        error_msg = register_response.text or error_msg
                    
                    console.print(f"[red]❌ Registration failed: {error_msg}[/red]")
                    return
        
        console.print("[green]✅ Account registered successfully[/green]")
        
        with console.status("[bold yellow]Logging in...[/bold yellow]"):
            # Step 2: Login to get JWT
            with httpx.Client(timeout=30.0) as client:
                login_response = client.post(
                    f"{api_url}/api/v1/auth/login",
                    json={
                        "email": email,
                        "password": password,
                    }
                )
                
                if login_response.status_code != 200:
                    console.print("[red]❌ Login failed. Please try logging in manually.[/red]")
                    return
                
                login_data = login_response.json()
                jwt_token = login_data.get("access_token") or login_data.get("token")
                
                if not jwt_token:
                    console.print("[red]❌ No JWT token received from login[/red]")
                    return
        
        console.print("[green]✅ Login successful[/green]")
        
        with console.status("[bold yellow]Creating API key...[/bold yellow]"):
            # Step 3: Create API key using JWT
            with httpx.Client(timeout=30.0) as client:
                api_key_response = client.post(
                    f"{api_url}/api/v1/api-keys/",  # Note: trailing slash is required
                    headers={
                        "Authorization": f"Bearer {jwt_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "name": f"CLI Auto-generated ({tenant_id})",
                        "description": f"Auto-generated API key for tenant {tenant_id}",
                        "scopes": ["read:artifacts", "write:artifacts"],
                    }
                )
                
                if api_key_response.status_code not in [200, 201]:
                    error_msg = "API key creation failed"
                    try:
                        error_data = api_key_response.json()
                        error_msg = error_data.get("detail", error_msg)
                    except Exception:
                        error_msg = api_key_response.text or error_msg
                    
                    console.print(f"[red]❌ API key creation failed: {error_msg}[/red]")
                    console.print("[yellow]⚠️  You may need to create an API key manually[/yellow]")
                    return
                
                api_key_data = api_key_response.json()
                api_key = api_key_data.get("api_key") or api_key_data.get("key")
                
                if not api_key:
                    console.print("[red]❌ No API key received[/red]")
                    return
        
        console.print("[green]✅ API key created successfully[/green]")
        
        # Step 4: Save configuration
        with console.status("[bold yellow]Saving configuration...[/bold yellow]"):
            config_dict = {
                "storage_backend": "api",
                "kurral_api_key": api_key,
                "kurral_api_url": api_url,
                "tenant_id": tenant_id,
            }
            
            config_obj = KurralConfig(**config_dict)
            config_path = save_config_file(config_obj, location=location)
        
        console.print(f"\n[green]✅ Configuration saved to: {config_path}[/green]\n")
        
        # Success panel
        success_panel = Panel(
            Text.from_markup(
                f"[green]Registration Complete! 🎉[/green]\n\n"
                f"[cyan]Email:[/cyan] {email}\n"
                f"[cyan]Tenant ID:[/cyan] {tenant_id}\n"
                f"[cyan]API URL:[/cyan] {api_url}\n"
                f"[cyan]Storage:[/cyan] Kurral Cloud (API mode)\n\n"
                f"[dim]Your API key has been saved securely.[/dim]"
            ),
            title="✅ Success",
            border_style="green",
        )
        console.print(success_panel)
        
        # Show example usage
        console.print("\n[bold]Next steps:[/bold]\n")
        console.print("1. Create your first trace:")
        console.print("""
[cyan]from kurral import trace_llm
from openai import OpenAI

client = OpenAI()

@trace_llm(semantic_bucket="support", tenant_id="{tenant_id}")
def my_agent(query: str):
    return client.chat.completions.create(
        model="gpt-4",
        messages=[{{"role": "user", "content": query}}],
        seed=42
    ).choices[0].message.content

# Automatically uploads to Kurral Cloud
result = my_agent("Hello, world!")
[/cyan]""".format(tenant_id=tenant_id))
        
        console.print("2. View your artifacts:")
        console.print("   [cyan]kurral buckets list[/cyan]\n")
        
        console.print("3. Replay a trace:")
        console.print("   [cyan]kurral replay <artifact>.kurral[/cyan]\n")
        
    except httpx.HTTPError as e:
        console.print(f"\n[red]❌ Network error: {str(e)}[/red]")
        console.print("[yellow]Please check your internet connection and API URL[/yellow]")
        import traceback
        # console.print(f"\n[dim]{traceback.format_exc()}[/dim]")
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error: {str(e)}[/red]")
        import traceback
        # console.print(f"\n[dim]{traceback.format_exc()}[/dim]")


@auth.command()
@click.option("--email", help="Email address")
@click.option("--password", help="Password (will prompt if not provided)", hide_input=True)
@click.option("--api-url", default="https://api.kurral.io", help="Kurral API URL")
def login(email, password, api_url):
    """
    Login to existing Kurral account and get API key
    
    Use this if you already have an account but need to configure a new machine.
    """
    if httpx is None:
        console.print("[red]❌ Error: httpx is required for login[/red]")
        console.print("Install with: [cyan]pip install httpx[/cyan]")
        return
    
    console.print("\n[bold cyan]🔐 Kurral Login[/bold cyan]\n")
    
    if not email:
        email = Prompt.ask("Email address")
    
    if not password:
        password = Prompt.ask("Password", password=True)
    
    api_url = api_url.rstrip("/")
    
    try:
        with console.status("[bold yellow]Logging in...[/bold yellow]"):
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{api_url}/api/v1/auth/login",
                    json={
                        "email": email,
                        "password": password,
                    }
                )
                
                if response.status_code != 200:
                    error_msg = "Login failed"
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("detail", error_msg)
                    except Exception:
                        error_msg = response.text or error_msg
                    
                    console.print(f"[red]❌ {error_msg}[/red]")
                    return
                
                data = response.json()
                token = data.get("access_token") or data.get("token")
                
                if not token:
                    console.print("[red]❌ No token received[/red]")
                    return
        
        console.print("[green]✅ Login successful[/green]")
        console.print(f"\n[yellow]⚠️  Use 'kurral auth register' for automatic API key setup[/yellow]")
        console.print(f"[dim]JWT Token (for manual API key creation):[/dim]")
        console.print(f"[cyan]{token}[/cyan]\n")
        
    except httpx.HTTPError as e:
        console.print(f"[red]❌ Network error: {str(e)}[/red]")
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {str(e)}[/red]")


@auth.command()
def status():
    """Show current authentication status"""
    config = get_config()
    
    console.print("\n[bold cyan]🔐 Authentication Status[/bold cyan]\n")
    
    if config.storage_backend == "api":
        if config.kurral_api_key:
            console.print("[green]✅ Authenticated[/green]")
            console.print(f"[cyan]API URL:[/cyan] {config.kurral_api_url}")
            console.print(f"[cyan]API Key:[/cyan] {config.kurral_api_key[:20]}...")
            
            if config.tenant_id:
                console.print(f"[cyan]Tenant ID:[/cyan] {config.tenant_id}")
            
            console.print("\n[dim]Run 'kurral config show' for full configuration[/dim]\n")
        else:
            console.print("[yellow]⚠️  API mode enabled but no API key configured[/yellow]")
            console.print("\nRun: [cyan]kurral auth register[/cyan] or [cyan]kurral config init[/cyan]\n")
    else:
        console.print(f"[yellow]ℹ️  Using {config.storage_backend} storage (no API authentication needed)[/yellow]\n")

