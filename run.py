#!/usr/bin/env python
import os
import sys
import subprocess
from subprocess import PIPE
from subprocess import run as sh
import click

UNAME = "user"
UHOME = "/home/user"
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
        if engine == "podman":
            sh([engine, "build", "--layers", "-t", name, "."])
        else:
            sh([engine, "build", "-t", name, "."])
    else:
        print("Please Run this script in the directory of the Dockerfile")


@cli.command()
@click.option(
    "--home_dir",
    default=f"{HOME}/.local/share/containerized_apps/firefox-arkenfox",
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
@click.option(
    "--home_dir",
    default=f"{HOME}/.local/share/containerized_apps/firefox-arkenfox",
    help=(
        "The path to a directory for the containers $HOME.\n"
        "This should contain a firefox profile, "
        "by default: `~/.mozilla/firefox/main_profile`. "
        "One can be created using `firefox --ProfileManager` which is "
        "bound to the `new` command by default"
    ),
)
def runn(
    image_name: str,
    engine: str,
    container_name: str,
    rm: bool,
    profile: str,
    home_dir: str,
):
    """Run the firefox image as a container"""
    cmd = [engine, "run"]
    opts = ["-i", "-t"]
    opts += ["--user", f"{str(os.getuid())}:{str(os.getgid())}"]
    if rm:
        opts += ["--rm"]
    if engine == "podman":
        opts.append("--userns=keep-id")
        image_name = f"localhost/{image_name}"
    if container_name is not None:
        opts += ["--name", container_name]

    opts += ["-w", f"/home/{UNAME}"]
    # User Files
    # TODO does the whole home need to be synced?
    # Only files are ~/.cache and ~/.mozilla
    # TODO this needs to be dynamic
    # TODO need profile name and need homedir name
    opts += ["-v", f"{home_dir}:{UHOME}:Z"]
    opts += ["-v", f"{HOME}/Downloads:/home/{UNAME}/Downloads:Z"]
    # SELinux
    opts += ["--security-opt", "label=type:container_runtime_t"]
    # Network
    opts += ["--net", "host"]
    # Video
    if is_wayland():
        opts += ["-e", "MOZ_ENABLE_WAYLAND=1"]
        opts += ["-e", "WAYLAND_DISPLAY"]
        opts += ["-e", "XDG_RUNTIME_DIR"]
        opts += vol_env("XDG_RUNTIME_DIR")  # [fn_1]
    else:
        opts += ["-e", "DISPLAY"]
        opts += ["-e", "XAUTHORITY"]
        opts += vol("/tmp/.X11-unix")
        opts += vol(f"/.Xauthority", from_home=True)
        opts += vol_env("XAUTHORITY")
    # Sound with Pulse
    opts += vol("/dev/dri:/dev/dri")
    opts += vol("/.config/pulse/cookie", from_home=True)
    opts += vol("/etc/machine-id")
    opts += vol_env("UUID")
    opts += vol("/var/lib/dbus")
    opts += dev("/dev/snd")
    if (XDG_RUNTIME_DIR := os.getenv("XDG_RUNTIME_DIR")) is not None:
        opts += ["-e", f"PULSE_SERVER=unix:{XDG_RUNTIME_DIR}/pulse/native"]
        opts += vol(f"{XDG_RUNTIME_DIR}/pulse/native")

    cmd += opts
    cmd += [f"{image_name}"]
    # cmd += ["/bin/sh"]
    cmd += ["firefox", "--profile", f"/home/{UNAME}/{profile}", "--new-instance"]
    print(" ".join(cmd))
    # cmd = ["podman", "run", "-it", "--rm", "localhost/firefox", "/bin/sh"]
    sh(cmd)


def dev(file: str) -> list[str]:
    if os.path.exists(file):
        return ["--device", f"{file}"]
    else:
        print(f"Warning, not found and Unable to attach: {file}")
        return []


def vol(dir: str, from_home: bool = False) -> list[str]:
    if os.path.exists(dir):
        if from_home:
            return ["-v", f"{HOME}/dir:{UHOME}/dir"]
        else:
            return ["-v", f"{dir}:{dir}"]
    else:
        print(f"Warning, not found and Unable to mount: {dir}")
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
    if os.getenv("XDG_RUNTIME_DIR") is not None:
        return os.getenv("XDG_SESSION_TYPE") == "wayland"
    else:
        return False


if __name__ == "__main__":
    cli()


# Footnotes ....................................................................

# [fn_1]:  XDG RUNTIME is only needed specifically by wayland there may be
#          reasons for or against mounting it otherwise
