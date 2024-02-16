#!/usr/bin/env python
import os
import sys
import tempfile
from subprocess import PIPE
from subprocess import run as sh
import click

os.chdir(os.path.dirname(os.path.realpath(__file__)))

UNAME = "user"
UHOME = "/home/user"
HOME = os.getenv("HOME")
assert (
    HOME is not None
), "Unable to detect Home Directory, this is needed to mount Volumes!"


@click.group()
def cli():
    """Run a firefox container and optionally build it from a Dockerfile."""
    # We just need to define the group, for subcommands
    pass


@cli.command()
@click.option("--name", default="firefox", help="The name for the built firefox image")
@click.option(
    "--engine", default="podman", help="The container engine to use", show_default=True
)
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
    help=(
        "The path to a directory for the containers $HOME.\n"
        "This should contain a firefox profile, "
        "by default: `~/.mozilla/firefox/main_profile`. "
        "One can be created using `firefox --ProfileManager` which is "
        "bound to the `new` command by default"
    ),
    show_default=True,
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
def run_wrapper(new: bool, shell: bool, home_dir: str):
    """Run the firefox image as a container using the ./run.sh"""
    if new:
        sh(["./run.sh", "new"])
    elif shell:
        sh(["./run.sh", "sh"])
    else:
        sh(["./run.sh", home_dir])


@cli.command()
@click.option(
    "--image_name",
    default="localhost/firefox",
    help="The Image to run",
    show_default=True,
)
@click.option(
    "--container_name",
    default=None,
    help="The name of the container to build",
    show_default=True,
)
@click.option(
    "--engine", default="podman", help="The container engine to use", show_default=True
)
@click.option(
    "--rm",
    default=True,
    help="Remove the container after running by appending --rm to podman/docker",
)
@click.option(
    "-p",
    "--profile",
    default="./data/profiles/arkenfox",
    help="The relative path from home to the profile directory",
    show_default=True,
)
@click.option(
    "--shell",
    is_flag=True,
    default=False,
    help="Start a shell instead of Firefox",
)
@click.option(
    "-d", "--detach",
    is_flag=True,
    default=False,
    help="Detach from the container, using `./run.py &` doesn't work",
)
def run(
    image_name: str,
    engine: str,
    container_name: str,
    rm: bool,
    profile: str,
    shell: bool,
    detach: bool
):
    """Run the firefox image as a container"""
    cmd = [engine, "run"]
    opts = ["-i", "-t"]
    UID = str(os.getuid())
    GID = str(os.getgid())
    opts += ["--user", f"{UID}:{GID}"]
    if rm:
        opts += ["--rm"]
    if engine == "podman":
        opts.append("--userns=keep-id")
    if container_name is not None:
        opts += ["--name", container_name]
    opts += ["-d"] if detach else []

    # Network
    opts += ["--net", "host"]
    # User Files
    # TODO I've set UID as 1111 for this home while building
    #      Then I mount temp home over so it it's writeable by mapped user
    #      I can't know user UID at build time so this is easy fix
    opts += ["-w", f"{UHOME}"]
    opts += ["-v", f"{tempfile.mkdtemp()}:{UHOME}"]
    opts += ["-v", f"{profile}:{UHOME}/.mozilla/firefox/main_profile"]
    opts += vol("Downloads", from_home=True)
    # SELinux
    opts += ["--security-opt", "label=type:container_runtime_t"]
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
        opts += vol("/.Xauthority", from_home=True)
        opts += vol_env("XAUTHORITY")
    # Sound with Pulse
    opts += vol("/dev/dri")
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
    if shell:
        cmd += ["/bin/sh"]
        sh(cmd)
    cmd += [
        "firefox",
        "--profile",
        f"/home/{UNAME}/.mozilla/firefox/main_profile",
        "--new-instance",
    ]
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
    def map(a: str, b: str):
        if os.path.exists(a):
            return ["-v", f"{a}:{b}"]
        else:
            print(f"Warning, not found and Unable to mount: {a}")
            return []

    if from_home:
        return map(f"{HOME}/{dir}", f"{UHOME}/{dir}")
    else:
        return map(dir, dir)


def vol_env(env: str) -> list[str]:
    if (file := os.getenv(env)) is not None:
        return vol(file)
    else:
        return []


def get_os() -> str | None:
    try:
        run_wrapper(["uname"], check=True, stdout=PIPE).stdout.decode().strip()
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


@cli.command()
def install():
    target = f"{HOME}/.local/bin/firefox-podman"
    # Create a symlink
    if os.path.exists(target):
        print(f"A file already exists at {target}")
        print("Please remove it and try again")
    else:
        file = os.path.abspath(os.path.realpath(__file__))
        target = os.path.abspath(os.path.realpath(target))
        os.symlink(file, target)
        print(f"Installed firefox to {target}")


@cli.command()
def uninstall():
    target = f"{HOME}/.local/bin/firefox-podman"
    # Create a symlink
    if not os.path.exists(target):
        print(f"No symlink found to remove, looking for:\n{target}")
    else:
        os.remove(target)
        print(f"Removed {target}")


if __name__ == "__main__":
    cli()


# Footnotes ...................................................................

# [fn_1]:  XDG RUNTIME is only needed specifically by wayland there may be
#          reasons for or against mounting it otherwise
# Create temp dir

