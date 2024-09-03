# LLM Support for Real-Time Technical Assistance

Codebase for the demo paper [LLM Support for Real-Time Technical Assistance](https://link.springer.com/chapter/10.1007/978-3-031-70371-3_26).
The demo web application allows to explore the use of LLM as support tool for technical assistance.

Demonstration video is available at thi [link](https://bit.ly/4aAVFLV)
For further details about the paper see [this section](#reference).

## Repository structure

This repository is organised into four main directories:

```
|- experiments/
  |- ...
|- notebooks/
  |- ...
|- docker/
  |- ...
|- resources/
  |- configs/
    |- ...
  |- data/
    |- ...
  |- models/
    |- ...
|- services/
  |- generator
    |- ...
  |- retrieval
    |- ...
  |- web_app
    |- ...  
|- submodules/
  |- llm_cstk/
    |- ...
|- src/
  |- script/
    |- ...
  |- web_app/
    |- ...
  |- me_project
    |- ...
```

For further details, refer to the `README.md` within each directory.

## Setup

There are two ways to set up the environment: either via the main Docker container of the project (suggested) or via manual installation.
After setting up the environment you are expected to do the following:

1. [Download pre-trained models](#pre-trained-models-download);
2. [Pre-process data](#data-pre-processing);
3. [Populate the DB](#database-population) (optional, this passage is necessary to run the demo);
4. [Register users](#register-users) (optional, this passage is necessary to run the evaluation);
5. [Train custom (L)LMs](#train-custom--l--lms) (optional, depending whether you want to work with chatbots fine-tuned on your data).

> [!NOTE]  
> The order of execution of the scripts for the setup (and training) is important and should be followed.

Before doing anything, it's recommended to:
- Install NVIDIA drivers (the instructions are to install drivers version 535 for CUDA 11.8 on Ubuntu 22.04 adapted from [this script](https://gist.github.com/MihailCosmin/affa6b1b71b43787e9228c25fe15aeba?permalink_comment_id=4715433), make sure to do all the changes for the desired version)
  ```bash
  ### To verify your gpu is cuda enable check (optional)
  lspci | grep -i nvidia
  
  ### If you have previous installation remove it first (optional)
  sudo apt-get purge nvidia*
  sudo apt remove nvidia-*
  sudo rm /etc/apt/sources.list.d/cuda*
  sudo apt-get autoremove && sudo apt-get autoclean
  sudo rm -rf /usr/local/cuda*
  
  # System update
  sudo apt-get update
  sudo apt-get upgrade
  
  # Install other important packages 
  sudo apt-get install g++ freeglut3-dev build-essential libx11-dev libxmu-dev libxi-dev libglu1-mesa libglu1-mesa-dev
  
  # Install all Ubuntu drivers including Nvidia drivers with dependencies
  sudo ubuntu-drivers autoinstall
  
  # Reboot
  sudo reboot now
  
  # verify that the following command works
  nvidia-smi
  ```
- Install git and clone repository (it may require to use an authentication token from GitHub)
```bash
sudo apt install git-all
```
Clone the repository and initialise its submodules
```bash
git clone https://<authentication token>@github.com/vincenzo-scotti/me_project.git
git config credential.helper store
git submodule init; git submodule update
```
- Install and configure Docker ([installation guide](https://docs.docker.com/engine/install/ubuntu/))
  ```bash
  # Add Docker's official GPG key:
  sudo apt-get update
  sudo apt-get install ca-certificates curl gnupg
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  
  # Add the repository to Apt sources:
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt-get update
  
  sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  
  sudo service docker start
  ```
  Additionally, make sure to add the current use to the Docker group ([post installation guide](https://docs.docker.com/engine/install/linux-postinstall/))
  ```bash
  sudo groupadd docker
  sudo usermod -aG docker $USER
  newgrp docker
  ```
- Nvidia Docker ([installation guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html))
  ```bash
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list \
  && \
    sudo apt-get update
  sudo apt-get install -y nvidia-container-toolkit
  
  sudo nvidia-ctk runtime configure --runtime=docker
  sudo systemctl restart docker
  
  sudo nvidia-ctk runtime configure --runtime=containerd
  sudo systemctl restart containerd
  
  sudo nvidia-ctk runtime configure --runtime=crio
  sudo systemctl restart crio
  ```
  
> [!NOTE]  
> These instructions where written for Ubuntu, make sure to make the appropriate changes depending on your system version.

### Container

Build the image with the ME project environment.

```bash
DOCKER_BUILDKIT=1 docker build . -f ./docker/me_environment/Dockerfile -t me_environment
```

Start the container and connect it to be sure everything is working correctly.

```bash
docker \
  run \
  -v /home/scotti/Projects/me_project/resources:/app/me_project/resources \
  -v /home/scotti/Projects/me_project/experiments:/app/me_project/experiments \
  -v /home/scotti/Projects/me_project/notebooks:/app/me_project/notebooks \
  -v /home/scotti/Projects/me_project/services:/app/me_project/services \
  -v /home/scotti/Projects/me_project/src:/app/me_project/src \
  -v /home/scotti/Projects/me_project/submodules:/app/me_project/submodules \
  --gpus all \
  --network="host" \
  --name me_environment \
  -it me_environment \
  /bin/bash
```

Optionally, you can also build an image with the LLM CSTK environment.

```bash
docker build ./submodules/llm_cstk -f ./docker/cstk/Dockerfile -t cstk
```

### Manual

To install all the required packages within an anaconda environment, run the following commands:

```bash
# Create anaconda environment 
conda create -n me_project python=3.10 cudatoolkit=11.8
# Activate anaconda environment
conda activate me_project
# Install submodule(s) required packages
pip install -r submodules/llm_cstk/requirements.txt
# Install packages
pip install -r requirements.txt
# Download modules
python -m spacy download it_core_news_sm
```

> [!NOTE]  
> Skip the `cudatoolkit` option if you don't want to use the GPU.

> [!NOTE]  
> Skip the submodules initialisation and submodules' packages installation if you are planning on using the containers for the external web services

> [!WARNING]  
> The code in this repository uses the [`llm_cstk` toolkit](https://github.com/vincenzo-scotti/llm_cstk/tree/main); be sure to read the instructions to use the attached code.

To add the source code directory(ies) to the Python path, you can add this line to the file `~/.bashrc`

```bash
export PYTHONPATH=$PYTHONPATH:/path/to/me_project/submodules/llm_cstk/src
export PYTHONPATH=$PYTHONPATH:/path/to/me_project/src
export PYTHONPATH=$PYTHONPATH:/path/to/me_project/src/web_app
```

## Scripts

The repository contains many script to automate data preparation, model training, etc.
All scripts expect to have the `./src` directory included in the Python path.
Scripts can be run either from the Docker environment (suggested) or manually. 

When running from the docker environment, make sure to have a container with the environment running detached 

```bash
docker \
  run \
  -v /home/scotti/Projects/me_project/resources:/app/me_project/resources \
  -v /home/scotti/Projects/me_project/experiments:/app/me_project/experiments \
  -v /home/scotti/Projects/me_project/notebooks:/app/me_project/notebooks \
  -v /home/scotti/Projects/me_project/services:/app/me_project/services \
  -v /home/scotti/Projects/me_project/src:/app/me_project/src \
  -v /home/scotti/Projects/me_project/submodules:/app/me_project/submodules \
  --gpus all \
  --network="host" \
  --name me_environment \
  -dit me_environment \
  /bin/bash
```

### Pre-trained models download

There is a script to download and save pre-trained models.
It is useful to get easy access to the foundational LLM and the (L)LMs to fine-tune, without requiring to download these models each time.

> [!NOTE]  
> This passage is necessary to set up the APIs

#### Container

To execute the script from Docker, run:

```bash
docker exec -it me_environment python3 ./src/script/download_pre_trained_llm.py --config_file_path ./resources/configs/download_pre_trained_llm.yml
```

To execute the script in background, run:

```bash
docker exec -dit me_environment python3 ./src/script/download_pre_trained_llm.py --config_file_path ./resources/configs/download_pre_trained_llm.yml
```

#### Manual

To execute the script, given a configuration file with the models to download (e.g., `./resources/configs/`), run:

```bash
python ./src/script/download_pre_trained_llm.py --config_file_path ./resources/configs/download_pre_trained_llm.yml
```

To execute the script in background, run:

```bash
python ./src/script/download_pre_trained_llm.py --config_file_path ./resources/configs/download_pre_trained_llm.yml > download_pre_trained_llm_"$(date '+%Y_%m_%d_%H_%M_%S')".out &
```

for further details, run: 

```bash
python ./src/script/download_pre_trained_llm.py --help
```

### Data pre-processing

There is a script to run data pre-processing on the three corpora:
- `NatCS`
- `Teacher-Student Chatroom Corpus V2`
- `TWEETSUMM`

The script takes care of creating different pre-processed version of each of the selected corpora for:
- Dialogue Language Model fine-tuning (it creates train/validation/test splits)
- Information retrieval (it creates document collections and indices for the entire documents and the chunked documents)

> [!NOTE]  
> This passage is necessary to set up the APIs

#### Container

To execute the script from Docker, run:

```bash
docker exec -it me_environment python3 ./src/script/pre_process_corpora.py --config_file_path ./resources/configs/pre_process_corpora.yml
```

To execute the script in background, run:

```bash
docker exec -dit me_environment python3 ./src/script/pre_process_corpora.py --config_file_path ./resources/configs/pre_process_corpora.yml
```

#### Manual

To execute the script, given a configuration file with the corpora to pre-process (e.g., `./resources/configs/`), run:

```bash
python ./src/script/pre_process_corpora.py --config_file_path ./resources/configs/pre_process_corpora.yml
```

To execute the script in background, run:

```bash
nohup python ./src/script/pre_process_corpora.py --config_file_path ./resources/configs/pre_process_corpora.yml > pre_process_corpora_"$(date '+%Y_%m_%d_%H_%M_%S')".out &
```

for further details, run: 

```bash
python ./src/script/pre_process_corpora.py --help
```

### Database population

There is a script to run database population using the three corpora:
- `NatCS`
- `Teacher-Student Chatroom Corpus V2`
- `TWEETSUMM`

The script is used to prepare the databases to be used in the demo web application.

If the script does not work at the first attempt, refer to this StackOverflow question: [link](https://stackoverflow.com/questions/34548768/no-such-table-exception).
Look at the answer from `adam` on October 13th 2019 at 9:20.
Change the commands to use the container if doing the migrations from there.

#### Container

To execute the script from Docker, run:

```bash
docker exec -it me_environment python3 ./src/script/populate_db.py --config_file_path ./resources/configs/populate_db.yml
```

To execute the script in background, run:

```bash
docker exec -dit me_environment python3 ./src/script/populate_db.py --config_file_path ./resources/configs/populate_db.yml
```

#### Manual

To execute the script, given a configuration file with the corpora to use to populate the database (e.g., `./resources/configs/`), run:

```bash
python ./src/script/populate_db.py --config_file_path ./resources/configs/populate_db.yml
```

To execute the script in background, run:

```bash
nohup python ./src/script/populate_db.py --config_file_path ./resources/configs/populate_db.yml > pre_process_corpora_"$(date '+%Y_%m_%d_%H_%M_%S')".out &
```

for further details, run: 

```bash
python ./src/script/populate_db.py --help
```

### Register users

User registration is managed manually from the Django iPython shell.

To register a user, start an iPython shell from Django.
You can do it either from the container:

```bash
docker exec -it me_environment python3 ./src/web_app/manage.py shell
```

or manually:

```bash
python3 ./src/web_app/manage.py shell
```

Then, execute the following command:

```python
from django.contrib.auth.models import User
user = User.objects.create_user(
    'username',
    email='emailaddress',
    password='password',
    first_name='name',
    last_name='surname'
)
user.save()
```

### Train custom (L)LMs

There is a script to fine-tune (L)LMs.

#### Container

To execute the script from Docker, run:

```bash
docker exec -it me_environment python3 ./submodules/llm_cstk/src/script/train_dialogue_lm.py --config_file_path ./resources/configs/train_dialogue_lm/X/configs.yml
```

To execute the script in background, run:

```bash
docker exec -dit me_environment python3 ./submodules/llm_cstk/src/script/train_dialogue_lm.py --config_file_path ./resources/configs/train_dialogue_lm/X/configs.yml
```

#### Manual

To execute the script, given a configuration file with the model to train and the data set(s) to use

```bash
python ./submodules/llm_cstk/src/script/train_dialogue_lm.py --config_file_path ./resources/configs/train_dialogue_lm/X/configs.yml
```

To execute the script in background, run:

```bash
nohup python ./submodules/llm_cstk/src/script/train_dialogue_lm.py --config_file_path ./resources/configs/train_dialogue_lm/X/configs.yml > populate_db_"$(date '+%Y_%m_%d_%H_%M_%S')".out &
```

for further details, run: 

```bash
python ./submodules/llm_cstk/src/script/train_dialogue_lm.py --help
```

### Evaluation data preparation

There is a script to prepare evaluation data using the three corpora:
- `NatCS`
- `Teacher-Student Chatroom Corpus V2`
- `TWEETSUMM`

The script is used to collect feedback from logged users in the demo web application.

#### Container

To execute the script from Docker, run:

```bash
docker exec -it me_environment python3 ./src/script/prepare_evaluation_data.py --config_file_path ./resources/configs/prepare_evaluation_data.yml
```

To execute the script in background, run:

```bash
docker exec -dit me_environment python3 ./src/script/prepare_evaluation_data.py --config_file_path ./resources/configs/prepare_evaluation_data.yml
```

#### Manual

To execute the script, given a configuration file with the corpora to use to populate the database (e.g., `./resources/configs/`), run:

```bash
python ./src/script/prepare_evaluation_data.py --config_file_path ./resources/configs/prepare_evaluation_data.yml
```

To execute the script in background, run:

```bash
nohup python ./src/script/prepare_evaluation_data.py --config_file_path ./resources/configs/prepare_evaluation_data.yml > prepare_evaluation_data_"$(date '+%Y_%m_%d_%H_%M_%S')".out &
```

for further details, run: 

```bash
python ./src/script/prepare_evaluation_data.py --help
```

## Web services and APIs

The core of this repository is to make available a set o services based on the [`llm_cstk` toolkit](https://github.com/vincenzo-scotti/llm_cstk/tree/main) using custom data and models, to show the possible usages of the toolkit.
These services are available via REST APIs.
All services have been encapsulated into [Docker](https://www.docker.com) containers.

### Start

There are docker configuration files to set automatically the web services and APIs in the `./docker/` directory.
For further details on the services and the configurations, refer to the [`llm_cstk` toolkit](https://github.com/vincenzo-scotti/llm_cstk/tree/main) webpage.

To start the web services and setup all the services, there is a [Docker Compose](https://docs.docker.com/compose/) file in the `./docker/` directory.
To start all the web services, run:

```bash
docker-compose -f ./docker/me_api/compose.yml up -d
```

To re-build the services (for example after modifying the code), run:

```bash
DOCKER_BUILDKIT=1  docker-compose -f ./docker/me_api/compose.yml up -d --build
```

> [!NOTE]  
> If the demo web application is running using the Docker Compose, the APIs are already running and do not need to be started.

### Stop

To stop all the web services, run:

```bash
docker-compose -f ./docker/me_api/compose.yml stop
```

## Web application

There is a web-application serving as demo to show examples of usage of the web services as well as to show the capabilities of the developed models.
The demo web application requires all web services to be up and running, refer to the [previous section](#web-application)

To connect to a remote server and start there the application, connect via ssh to your remote machine using a tunnel:

```
ssh <user>@<address> -p <port> -L 18000:127.0.0.1:8000 
```

Skip this last instruction if you are planning on running the service on your local machine.

### Start

There two ways to start the demo web application, from a docker container or manually from the source code (if the APIs are already running) or via the Docker Compose.
Once started, connect to http://127.0.0.1:8000 or http://127.0.0.1:18000 on your local machine, depending, respectively, whether the application is running on the local machine or a remote machine.

> [!WARNING]  
> Use the Docker Compose only if the APIs are not already running, else use either the container approach or the manual approach.

#### Container

To use the containerised version of the application, it is necessary to build the image of the container.
Refer to the `README.md` file in the `./docker/` directory for further instructions.


To start the demo web application from the docker container, run

```bash
docker exec -it me_environment python3 ./src/web_app/manage.py runserver
```

To start the demo web application in background, run:

```bash
docker exec -dit me_environment python3 ./src/web_app/manage.py runserver
```

#### Manual

To start the demo web application, run:

```bash
python ./src/web_app/manage.py runserver
```

To start the demo web application in background, run:

```bash
nohup python ./src/web_app/manage.py runserver > ./services/web_app/web_app_session_"$(date '+%Y_%m_%d_%H_%M_%S')".out &
```

#### Compose

To start the demo web application and all the web services, run:

```bash
docker-compose -f ./docker/me_demo/compose.yml up -d
```

To re-build the demo web application and all the web services (for example after modifying the code), run:

```bash
DOCKER_BUILDKIT=1 docker-compose -f ./docker/me_demo/compose.yml up -d --build
```

### Stop

Depending on the setup, either container or manually, 

#### Container

To stop the demo web application from the docker container in foreground, hit `[CTRL+C]`

To stop the demo web application running in background, stop the container running

```bash
docker stop me_environment
```

#### Manual

To stop the demo web application running in foreground, hit `[CTRL+C]`

To stop the demo web application running in background, run

```bash
kill <web_app_pid>
```

after retrieving the PID of the service.

## Reference

If you are willing to use our code, please consider citing our work through the following BibTeX entry (note, the entry is temporary):

<!-- TODO update with correct BibTeX entry -->

```bibtex

@inproceedings{scotti-carman-2024-llm,
    address = {Cham},
	author = {Scotti, Vincenzo and Carman, Mark James},
	booktitle = {Machine Learning and Knowledge Discovery in Databases. Research Track and Demo Track},
	editor = {Bifet, Albert and Daniu{\v{s}}is, Povilas and Davis, Jesse and Krilavi{\v{c}}ius, Tomas and Kull, Meelis and Ntoutsi, Eirini and Puolam{\"a}ki, Kai and {\v{Z}}liobait{\.{e}}, Indr{\.{e}}},
	isbn = {978-3-031-70371-3},
	pages = {388--393},
	publisher = {Springer Nature Switzerland},
	title = {LLM Support for Real-Time Technical Assistance},
    doi = {10.1007/978-3-031-70371-3\_26},
	url = {https://doi.org/10.1007/978-3-031-70371-3\_26},
	year = {2024}
}

```

## Acknowledgements

- Vincenzo Scotti: ([vincenzo.scotti@polimi.it](mailto:vincenzo.scotti@polimi.it))
- Mark James Carman: ([mark.carman@polimi.it](mailto:mark.carman@.polimi.it))
