# Synapsis
A transaction automator with api integration for full control. (Sebuah automator pulsa dengan api untuk kendali penuh automator).
Currently all available plugins have stopped working, and thus the archival of this project.

## Compatibility
Compatible with Python 3.8 - 3.10
> Python 3.7 and lower is incompatible
> Python 3.11 is also incompatible

---

## Usage
### Configuration
Simply copy one of the sample config and then edit the configurations of the copied file accordingly to your needs. The app supports 2 types of configuration extensions, JSON and YAML. 

- [config.schematics.json](./config.schematics.json)
- [config.schematics.yaml](./config.schematics.yaml)

> if you ever felt the need to use another type of configuration, you can add the decoder and encoder to [from_file](./automators/data_structs.py#L77-L85) and [to_file](./automators/data_structs.py#L87-L94) respectively.

### Deployment
The entry point of the app is in [main.py](./main.py), to deploy it, simply do:
```bash
$ python3 main.py
```
The above command defaults to using `config.yaml` as its config file. However if you named it differently or used another type of config, then use the following (replace `<config_filename>` with your actual config filename, without the angle brackets):
```bash
$ python3 main.py -c <config_filename>
```


---

## Development
### Clone
Run these commands:
```bash
$ git clone git@github.com:Vin-Ren/Synapsis-Public.git
$ git submodule update --init
```

### Update
While to update run:
```bash
$ git pull
$ git submodule update --remote
```

### Testing
There exists a flag for the app's entry point that makes testing a bit practical called `dev-mode`.

To use this flag, you need to copy the example yaml config to `./config.test.yaml` and adjust accordingly to your environment. Sadly while the project is still being maintained, testing was only ever done with yaml config, and the file path is hardcoded. Hence why this flag requires **exactly that path with that type of configuration** to work.

The flag enables interactive interaction with the app from the console, however keep in mind that the main thread of the app is being run on a seperate thread, while the main thread of the process is used by the interactive console.
```bash
$ python3 main.py --dev-mode
```
