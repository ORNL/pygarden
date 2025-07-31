"""Command line arguments for helping with docker."""

import os
import subprocess

import click


@click.group()
def docker():
    """Docker related commands."""
    pass


@docker.command(name="remove-volumes", help="Remove all docker volumes with a specific prefix.")
@click.argument("prefix", required=False)
def remove_volumes(prefix):
    """Remove all docker volumes with a specific prefix.

    :param prefix: Prefix to filter volumes by.
    """
    if not prefix:
        prefix = os.path.basename(os.getcwd())
    command = f"docker volume ls -q --filter name={prefix} | xargs -r docker volume rm"
    subprocess.run(command, shell=True)


@docker.command(
    name="docker-execute-and-mount",
    help="Execute a command in a docker container with a /tmp as the pwd.",
)
@click.option("--image", "-i", default="python:3.11-latest", help="Docker image to use.")
@click.option("--volume-target", "-t", default=None, help="Target directory to mount.")
@click.option("--volume-mount", "-m", default="/tmp", help="Mount directory inside the container.")
@click.option("--exec", "-e", "exec_cmd", default="bash", help="Command to execute.")
def docker_execute_and_mount(image, volume_target, volume_mount, exec_cmd):
    """Execute a command in a docker container with a /tmp as the pwd.

    :param image: Docker image to use.
    :param volume_target: Target directory to mount.
    :param volume_mount: Mount directory inside the container.
    :param exec_cmd: Command to execute.
    """
    if not volume_target:
        volume_target = os.getcwd()
    command = f"docker run -it -v {volume_target}:{volume_mount} -w {volume_mount} {image} {exec_cmd}"
    subprocess.run(command, shell=True)
