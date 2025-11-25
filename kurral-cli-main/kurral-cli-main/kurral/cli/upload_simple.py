"""
Upload/download commands for R2 (standalone, no decorator imports)
"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@click.command()
@click.argument("artifact", type=click.Path(exists=True))
@click.option("--bucket", envvar="KURRAL_R2_BUCKET", required=True, help="R2 bucket name")
@click.option("--account-id", envvar="KURRAL_R2_ACCOUNT_ID", required=True, help="Cloudflare account ID")
@click.option("--access-key", envvar="KURRAL_R2_ACCESS_KEY_ID", required=True, help="R2 access key ID")
@click.option("--secret-key", envvar="KURRAL_R2_SECRET_ACCESS_KEY", required=True, help="R2 secret access key")
@click.option("--prefix", default="", help="Optional key prefix")
def upload(artifact, bucket, account_id, access_key, secret_key, prefix):
    """Upload a .kurral artifact to Cloudflare R2"""
    try:
        from kurral.models.kurral import KurralArtifact
        from kurral.storage.r2 import R2Storage
    except ImportError as e:
        console.print(f"[red]❌ Missing dependency: {e}[/red]")
        console.print("[yellow]Install boto3: pip install boto3[/yellow]")
        sys.exit(1)

    try:
        console.print(f"\n[cyan]Loading artifact: {artifact}[/cyan]")
        artifact_obj = KurralArtifact.load(artifact)
        console.print(f"[dim]Artifact ID: {artifact_obj.kurral_id}[/dim]")
        console.print(f"[dim]Tenant: {artifact_obj.tenant_id}[/dim]\n")

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Uploading to R2...", total=None)
            storage = R2Storage(bucket=bucket, account_id=account_id, r2_access_key_id=access_key, r2_secret_access_key=secret_key, prefix=prefix)
            uri = storage.save(artifact_obj)
            progress.update(task, description="Upload complete!", completed=True)

        console.print(f"\n[green]✅ Uploaded: {uri}[/green]")
    except Exception as e:
        console.print(f"\n[red]❌ Upload failed: {e}[/red]")
        sys.exit(1)


@click.command()
@click.argument("uri")
@click.option("--bucket", envvar="KURRAL_R2_BUCKET", help="R2 bucket name")
@click.option("--account-id", envvar="KURRAL_R2_ACCOUNT_ID", required=True, help="Cloudflare account ID")
@click.option("--access-key", envvar="KURRAL_R2_ACCESS_KEY_ID", required=True, help="R2 access key ID")
@click.option("--secret-key", envvar="KURRAL_R2_SECRET_ACCESS_KEY", required=True, help="R2 secret access key")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def download(uri, bucket, account_id, access_key, secret_key, output):
    """Download a .kurral artifact from Cloudflare R2"""
    try:
        from kurral.models.kurral import KurralArtifact
        from kurral.storage.r2 import R2Storage
    except ImportError as e:
        console.print(f"[red]❌ Missing dependency: {e}[/red]")
        console.print("[yellow]Install boto3: pip install boto3[/yellow]")
        sys.exit(1)

    try:
        console.print(f"\n[cyan]Downloading: {uri}[/cyan]")
        if not bucket and uri.startswith("r2://"):
            bucket = uri[5:].split("/")[0]

        storage = R2Storage(bucket=bucket, account_id=account_id, r2_access_key_id=access_key, r2_secret_access_key=secret_key)

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Downloading artifact...", total=None)
            artifact = storage.load_by_uri(uri)
            progress.update(task, description="Download complete!", completed=True)

        if not output:
            output = f"{artifact.kurral_id}.kurral"
        artifact.save(output)

        console.print(f"\n[green]✅ Saved to: {output}[/green]")
        console.print(f"[dim]Artifact ID: {artifact.kurral_id}[/dim]")
    except Exception as e:
        console.print(f"\n[red]❌ Download failed: {e}[/red]")
        sys.exit(1)


@click.command()
@click.option("--bucket", envvar="KURRAL_R2_BUCKET", required=True, help="R2 bucket name")
@click.option("--account-id", envvar="KURRAL_R2_ACCOUNT_ID", required=True, help="Cloudflare account ID")
@click.option("--access-key", envvar="KURRAL_R2_ACCESS_KEY_ID", required=True, help="R2 access key ID")
@click.option("--secret-key", envvar="KURRAL_R2_SECRET_ACCESS_KEY", required=True, help="R2 secret access key")
@click.option("--tenant", help="Filter by tenant ID")
@click.option("--limit", default=100, type=int, help="Max results")
def list_r2(bucket, account_id, access_key, secret_key, tenant, limit):
    """List .kurral artifacts in Cloudflare R2"""
    try:
        from kurral.storage.r2 import R2Storage
    except ImportError as e:
        console.print(f"[red]❌ Missing dependency: {e}[/red]")
        console.print("[yellow]Install boto3: pip install boto3[/yellow]")
        sys.exit(1)

    try:
        storage = R2Storage(bucket=bucket, account_id=account_id, r2_access_key_id=access_key, r2_secret_access_key=secret_key)
        console.print(f"\n[cyan]Listing artifacts in: {bucket}[/cyan]\n")

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Fetching list...", total=None)
            uris = storage.list_artifacts(tenant_id=tenant, limit=limit)
            progress.update(task, description=f"Found {len(uris)} artifacts", completed=True)

        if not uris:
            console.print("[yellow]No artifacts found[/yellow]")
            return

        console.print(f"\n[green]Found {len(uris)} artifact(s):[/green]\n")
        for uri in uris:
            console.print(f"  • {uri}")
    except Exception as e:
        console.print(f"\n[red]❌ List failed: {e}[/red]")
        sys.exit(1)

