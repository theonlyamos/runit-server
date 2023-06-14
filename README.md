# runit-server-Server ![Python](https://img.shields.io/badge/builthwith-python-brightgreen) 
The runit-server Command Line Interface (CLI) Tools can be used to test, manage, and deploy your runit-server project from the command line.
- Create new runit-server project
- Run a local web server for your runit-server project
- publish code and assets to your runit-server-server domain
- Interact with data in your runit-server-server database


## Supported Languages
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![JavaScript](https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E) ![PHP](https://img.shields.io/badge/php-%23777BB4.svg?style=for-the-badge&logo=php&logoColor=white)

## Installation
### Python Package
You can install the runit-server package using pip (Python package manager). Note that you will need to install [Python](https://python.org).
To download and install the Runit-Server package run the following command:
```shell
pip install runit-server
```
This will provide you with the globally accessible ```runit-server``` command.

### Install from source
```shell
git clone https://github.com/theonlyamos/runit-server.git
cd runit-server
pip install .
```

## Usage
Run the below command to print out usage message.
```shell
runit-server --help
```
![runit-server Cli](https://awesomescreenshot.s3.amazonaws.com/image/3778408/34500895-ad63d3ceaef8002f59fc5fd499797ca5.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAJSCJQ2NM3XLFPVKA%2F20221117%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20221117T180652Z&X-Amz-Expires=28800&X-Amz-SignedHeaders=host&X-Amz-Signature=afd652759d272e68a62fb9959ce4e86647af5d6269991c012c9e753bf22ef534)

### Setup Server
Run ```runit-server setup --help``` for help message.
***Follow the prompts to complete the setup after running the below command.***
```shell
runit-server setup
```
### Run Server
Run the command below to start the webserver
```shell
runit-server
```
## License
![License](https://img.shields.io/badge/LICENSE-MIT-brightgreen/?style=flat-square)

**Free Software, Hell Yeah!**

