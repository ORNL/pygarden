# common[cli] README.md

The `common[cli]` extra provides a system-wide method for managing command-line interfaces (CLIs) such as abstractions
to commonly used operations such as creating a Python module with `common py mkpymodule` or creating a CSV file with
a 100MB file size and 10 CSV columns with `common gen csv -s 100MB -c 10`. Additionally, the `common[cli]` extra provides
methods for interacting with `docker` and `docker-compose` commands, as well as a method for creating a new Python project
like removing all docker volumes with a prefix via `common docker remove-volumes myprojectprefix`. Additionally, you can
easily execute into a container with `common docker execute-and-mount` which will mount the pwd directory.