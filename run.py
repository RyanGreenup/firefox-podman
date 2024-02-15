#!/usr/bin/env python
import os
import sys
import subprocess
from subprocess import PIPE
from subprocess import run as sh
import click

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
@click.option("--image_name", default="firefox", help="The Image to run")
@click.option(
    "--container_name", default=None, help="The name of the container to build"
)
@click.option("--engine", default="podman", help="The container engine to use")
@click.option(
    "--rm",
    default=True,
    help="Remove the container after running by appending --rm to podman/docker",
)
@click.option(
    "--profile",
    default=".mozilla/firefox/main_profile",
    help="The relative path from home to the profile directory",
)
def run(image_name: str, engine: str, container_name: str, rm: bool, profile: str):
    """Run the firefox image as a container"""
    # NOTE
    # UID is set in the Dockerfile so it needs to be built to inherit
    # Username is also set in the Dockerfile
    UNAME = "user"

#    if not is_wayland():

    cmd = [engine, "run"]
    opts = ["-t", "-i"]
    if rm:
        opts = ["--rm"]
    if engine == "podman":
        opts.append("--userns=keep-id")
        # TODO not sure about this (--user=1000:1000)
        # opts += ["--user", f"{os.getuid()}:{os.getgid()}"]
        # opts.append("--user=1000:1000")
        image_name = f"localhost/{image_name}"
    if container_name is not None:
        opts += ["--name", container_name]

    opts += ["-w", f"/home/{UNAME}"]
    # User Files
    opts += [
        "-v",
        f"{HOME}/.local/share/containerized_apps/firefox-arkenfox-alpine:/home/{UNAME}:Z",
    ]
    opts += ["-v", f"{HOME}/Downloads:/home/{UNAME}/Downloads:Z"]
    # SELinux
    opts += ["--security-opt", "label=type:container_runtime_t"]
    # Network
    opts += ["--net", "host"]
    # Video
    opts += ["-e", "XAUTHORITY"]
    opts += ["-e", "DISPLAY"]
    if (xauth_file := os.getenv("XAUTHORITY")) is not None:
        opts += ["-v", f"{xauth_file}:{xauth_file}"]
    opts += ["-v", "/tmp/.X11-unix:/tmp/.X11-unix"]
    if is_wayland():
        opts += ["-e", "MOZ_ENABLE_WAYLAND=1"]
    if os.path.exists(f"{HOME}/.Xauthority"):
        opts += ["-v", f"{HOME}/.Xauthority:/home/{UNAME}/.Xauthority"]
    else:
        if get_os == "Linux" and not is_wayland():
            print(f"Warning: {HOME}/.Xauthority file not found!", file=sys.stderr)
    # Sound with Pulse
    opts += ["-v", "/dev/dri:/dev/dri"]
    opts += ["-v",
             f"{HOME}/.config/pulse/cookie:/home/{UNAME}/.config/pulse/cookie"]
    opts += ["-v", "/etc/machine-id:/etc/machine-id"]
    if (UUID := os.getenv("UUID")) is not None:
        opts += ["-v", f"/run/user/{UUID}/pulse:/run/user/{UUID}/pulse"]
    opts += ["-v", "/var/lib/dbus:/var/lib/dbus"]
    opts += ["--device", "/dev/snd"]
    if (XDG_RUNTIME_DIR := os.getenv("XDG_RUNTIME_DIR")) is not None:
        opts += ["-e", f"PULSE_SERVER=unix:{XDG_RUNTIME_DIR}/pulse/native"]
        opts += ["-v", f"{XDG_RUNTIME_DIR}/pulse/native:{XDG_RUNTIME_DIR}/pulse/native"]

    cmd += opts
    cmd += [f"{image_name}"]
    cmd += ["/bin/sh"]
    # cmd += ["firefox", "--profile", f"/home/{UNAME}/{profile}", "--new-instance"]
    print(' '.join(cmd))
    sh(cmd)


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
