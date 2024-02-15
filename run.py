#!/usr/bin/env python
import os
import sys
import subprocess
from subprocess import PIPE
from subprocess import run as sh
import click

# TODO build command needs to take UID and GID

HOME = os.getenv("HOME")
assert (
    HOME is not None
), "Unable to detect Home Directory, this is needed to mount Volumes!"


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
    help="The path to a directory that will act as Home for the container. This directory should contain a firefox profile at ~/.mozilla/firefox/main_profile, if it does not use `firefox --ProfileManager` to create one, this is bound to the `new` command in this cli.",
)
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
def runn(image_name: str, engine: str, container_name: str, rm: bool, profile: str):
    """Run the firefox image as a container"""
    UNAME = "user"

    #    if not is_wayland():
    cmd = [engine, "run"]
    opts = ["-t", "-i"]
    opts += ["--user", "1000:1000"]
    if rm:
        opts += ["--rm"]
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
    if is_wayland():
        opts += ["-e", "MOZ_ENABLE_WAYLAND=1"]
        opts += ["-e", "WAYLAND_DISPLAY"]
    else:
        opts += ["-e", "DISPLAY"]
        opts += ["-e", "XAUTHORITY"]
        tmp_x11_unix = "/tmp/.X11-unix"
        if os.path.exists(tmp_x11_unix):
            opts += ["-v", f"{tmp_x11_unix}:{tmp_x11_unix}"]
        if (xauth_file := os.getenv("XAUTHORITY")) is not None:
            opts += ["-v", f"{xauth_file}:{xauth_file}"]
        if os.path.exists(f"{HOME}/.Xauthority"):
            opts += ["-v", f"{HOME}/.Xauthority:/home/{UNAME}/.Xauthority"]
        else:
            if get_os == "Linux" and not is_wayland():
                print(f"Warning: {HOME}/.Xauthority file not found!", file=sys.stderr)
    # Sound with Pulse
    opts += ["-v", "/dev/dri:/dev/dri"]
    opts += ["-v", f"{HOME}/.config/pulse/cookie:/home/{UNAME}/.config/pulse/cookie"]
    opts += ["-v", "/etc/machine-id:/etc/machine-id"]
    if (UUID := os.getenv("UUID")) is not None:
        opts += ["-v", f"/run/user/{UUID}/pulse:/run/user/{UUID}/pulse"]
    opts += ["-v", "/var/lib/dbus:/var/lib/dbus"]
    opts += ["--device", "/dev/snd"]
    if (XDG_RUNTIME_DIR := os.getenv("XDG_RUNTIME_DIR")) is not None:
        opts += ["-e", f"PULSE_SERVER=unix:{XDG_RUNTIME_DIR}/pulse/native"]
        opts += ["-v", f"{XDG_RUNTIME_DIR}/pulse/native:{XDG_RUNTIME_DIR}/pulse/native"]
        opts += ["-e", "XDG_RUNTIME_DIR"]
        opts += ["-v", f"{XDG_RUNTIME_DIR}:{XDG_RUNTIME_DIR}"]

    cmd += opts
    cmd += [f"{image_name}"]
    cmd += ["/bin/sh"]
    # cmd += ["firefox", "--profile", f"/home/{UNAME}/{profile}", "--new-instance"]
    print(" ".join(cmd))
    # cmd = ["podman", "run", "-it", "--rm", "localhost/firefox", "/bin/sh"]
    sh(cmd)


def vol(dir: str) -> list[str]:
    if os.path.exists(dir):
        return ["-v", f"{dir}:{dir}"]
    else:
        return []


def vol_env(env: str) -> list[str]:
    if (file := os.getenv(env)) is not None:
        return vol(file)
    else:
        return []


def get_os() -> str | None:
    try:
        uname_output = run(["uname"], check=True, stdout=PIPE).stdout.decode().strip()
    except FileNotFoundError:
        print("uname command not found in path", file=sys.stderr)
        return None
    except Exception:
        return None


def is_wayland() -> bool:
    """Tests if the system is currently running on wayland.
    Note that the use of wayland in Firefox depends on:

        1. The Environment Variable MOZ_ENABLE_WAYLAND=1
        2. XDG_RUNTIME_DIR being set and accessible
        3. The WAYLAND_DISPLAY env var
    """

    # Wayland requires the XDG_RUNIME_DIR to be mounted
    return False
    if os.getenv("XDG_RUNTIME_DIR") is not None:
        return os.getenv("XDG_SESSION_TYPE") == "wayland"
    else:
        return False


if __name__ == "__main__":
    cli()
