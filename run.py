#!/usr/bin/env python
import os
import sys
import subprocess
from subprocess import PIPE
from subprocess import run as sh
import click

# TODO build command needs to take UID and GID

HOME = os.getenv("HOME")
assert HOME is not None, "Unable to detect Home Directory, this is needed to mount Volumes!"


@click.group()
def cli():
    """Run a firefox container and optionally build it from a Dockerfile."""
    pass  # We just need to define the group, so we don’t call other commands directly


@cli.command()
@click.option("--name", default="firefox", help="The name for the built firefox image")
@click.option("--engine", default="podman", help="The container engine to use")
def build(name: str, engine: str):
    """Build a Firefox Image from the Dockerfile."""
    # Check if the Dockerfile exists in the current directory
    if os.path.exists("./Dockerfile"):
        sh([engine, "build", "--layers", "-t", name, "."])
    else:
        print("Please Run this script in the directory of the Dockerfile")


@cli.command()
@click.option(
    "--home_dir",
    default="f{HOME}/.local/share/containerized_apps/firefox-arkenfox",
    help="The path to a directory that will act as Home for the container. This directory should contain a firefox profile at ~/.mozilla/firefox/main_profile, if it does not use `firefox --ProfileManager` to create one, this is bound to the `new` command in this cli.",)
@click.option(
    "--shell",
    is_flag=True,
    default=False,
    help="Start the Firefox Profile Manager to create a new profile, The new profile should be called main_profile if it is to be auto-started",
)
@click.option(
    "--new",
    is_flag=True,
    default=False,
    help="Start the Firefox Profile Manager to create a new profile, The new profile should be called main_profile if it is to be auto-started",
)
def run(new: bool, shell: bool, home_dir: str):
    """Run the firefox image as a container"""
    if new:
        sh(["./run.sh", "new"])
    elif shell:
        sh(["./run.sh", "sh"])
    else:
        sh(["./run.sh", home_dir])


# @click.option("--engine", default="podman", help="The container engine to use")
# def run(image_name: str, engine: str, container_name: str, rm: bool, home_dir: str, new: bool, shell: bool):

def get_os() -> str | None:
    try:
        uname_output = run(["uname"], check=True,
                           stdout=PIPE).stdout.decode().strip()
    except FileNotFoundError:
        print("uname command not found in path", file=sys.stderr)
        return None
    except Exception:
        return None


def is_wayland() -> bool:
    return os.getenv("XDG_SESSION_TYPE") == "wayland"


if __name__ == "__main__":
    cli()
