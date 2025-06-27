"""
Command line arguments for helping with docker.

This module provides Click-based command line interfaces for common Docker
operations, including volume management and container execution with mounts.

The module provides:
- Docker volume removal with prefix filtering
- Container execution with volume mounting
- Interactive container management
- Docker command automation

Examples
--------
Remove Docker volumes with a prefix::

    $ pygarden docker remove-volumes myapp

Execute a command in a Docker container::

    $ pygarden docker docker-execute-and-mount --image python:3.11

Remove volumes and run container::

    $ pygarden docker remove-volumes myapp
    $ pygarden docker docker-execute-and-mount --image myapp:latest

Notes
-----
This module requires Docker to be installed and running on the system.
Commands are executed using subprocess with shell=True.
"""
import os
import subprocess

import click


@click.group()
def docker():
    """
    Docker related commands.

    This command group provides utilities for Docker operations including
    volume management and container execution with various mounting options.

    Examples
    --------
    Remove volumes::

        $ pygarden docker remove-volumes myapp

    Execute in container::

        $ pygarden docker docker-execute-and-mount --image python:3.11

    Clean up and run::

        $ pygarden docker remove-volumes oldapp
        $ pygarden docker docker-execute-and-mount --image newapp:latest

    Notes
    -----
    This command group provides utilities for common Docker operations
    including volume cleanup and container execution with volume mounting.
    """
    pass


@docker.command(name="remove-volumes", help="Remove all docker volumes with a specific prefix.")
@click.argument("prefix", required=False)
def remove_volumes(prefix):
    """
    Remove all docker volumes with a specific prefix.

    This command removes all Docker volumes that match the specified prefix.
    If no prefix is provided, it uses the current directory name as the prefix.

    :param prefix: Prefix to match volumes for removal. If None, uses current directory name
    :type prefix: str or None

    Examples
    --------
    Remove volumes with 'myapp' prefix::

        $ pygarden docker remove-volumes myapp

    Remove volumes with current directory name as prefix::

        $ pygarden docker remove-volumes

    Remove volumes with specific prefix::

        $ pygarden docker remove-volumes test_
        $ pygarden docker remove-volumes dev_

    Notes
    -----
    - Uses 'docker volume ls -q --filter name={prefix}' to find volumes
    - Uses 'docker volume rm' to remove the found volumes
    - The command is executed using shell=True for subprocess
    - If no volumes match the prefix, no error is raised
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
    """
    Execute a command in a docker container with a mounted volume.

    This command runs a Docker container with the specified image and mounts
    a target directory to a specified location inside the container. It then
    executes the specified command in the container.

    :param image: Docker image to use
    :type image: str
    :param volume_target: Target directory to mount. If None, uses current directory
    :type volume_target: str or None
    :param volume_mount: Mount directory inside the container
    :type volume_mount: str
    :param exec_cmd: Command to execute in the container
    :type exec_cmd: str

    Examples
    --------
    Execute bash in a Python container::

        $ pygarden docker docker-execute-and-mount

    Execute a specific command::

        $ pygarden docker docker-execute-and-mount --exec "python script.py"

    Use a different image::

        $ pygarden docker docker-execute-and-mount --image ubuntu:latest

    Mount a specific directory::

        $ pygarden docker docker-execute-and-mount --volume-target /path/to/data

    Use short options::

        $ pygarden docker docker-execute-and-mount -i python:3.9 -e "pip install requests"

    Run with custom mount point::

        $ pygarden docker docker-execute-and-mount --volume-mount /workspace

    Execute Python script with data mount::

        $ pygarden docker docker-execute-and-mount \
        ...     --image python:3.11 \
        ...     --volume-target ./data \
        ...     --volume-mount /data \
        ...     --exec "python /data/process.py"

    Notes
    -----
    - The container runs in interactive mode (-it)
    - The target directory is mounted to the specified mount point
    - The working directory in the container is set to the mount point
    - The command is executed using shell=True for subprocess
    - If volume_target is not specified, uses current working directory
    """
    if not volume_target:
        volume_target = os.getcwd()
    command = f"docker run -it -v {volume_target}:{volume_mount} -w {volume_mount} {image} {exec_cmd}"
    subprocess.run(command, shell=True)
