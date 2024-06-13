# Docker

This directory is used to host the [Docker](https://www.docker.com) files to build the container images and the [Docker Compose](https://docs.docker.com/compose/) files .

> [!NOTE]  
> Containers and compose files have hardcoded inside some paths, make sure to update them accordingly when launching the code.


## Container

There is a single container described by the Dockerfile in `me_environment/`.
This container holds the entire environment (including submodules). 
The container mounts the directories of the repository as volumes to ease access to shared data and code.

## Compose

There are two compose files, one to set up the APIs based on the LLM CSTK code and the other to set up the APIs and the demo web application.
