# SWIRL: Scientific Workflow Intermediate Representation Language

SWIRL is a framework which allows the low-level compilation target for distributed workflow execution plans.

## Install

### PyPI

Install SWIRL via [PyPi](https://pypi.org/project/swirl/)

```bash
pip install swirl
```

### Docker

SWIRL Docker images are available on [Docker Hub](https://hub.docker.com/r/alphaunito/swirl).

Example of `translate` option. Similar `compile` option with appropriate parameters.
Next sections explain SWIRL options deeply.

```bash
mkdir -p SWIRL
docker run                          \
        --user $(id -u):$(id -g)    \
        --volume $(pwd):/data       \
        --workdir /data             \
        alphaunito/swirl:0.0.1      \
    swirl                           \
        COMMAND                     \
        [OPTION]                     
```

## Translate

SWIRL allows to translate from an existing workflow language to the SWIRL semantics.
Current supported workflow languages for the translation:
- DAX: this format is supported by [Pegasus](https://pegasus.isi.edu/) workflow management system.
  
  ```bash
  swirl translate --language dax [DAX DIRECTORY]
  ```
  The `DAX directory` must contain four files: `replica.yml`, `sites.yml`, `transformations.yml` and `workflow.yml`.

## Compile

SWIRL allows to create traces in different programming languages. These can be moved in distributed environments to execute the workflow.
Current supported programming languages for the traces compilation:
- Python: this programming language has the advantages that is interpreted. It is helpful for the portability because the locations needs only the default Python interpreter.
  
```bash
swirl compile [PATH TO FILE .swirl] [PATH TO METADATA FILE .yml]
```

## SWIRL Team

Iacopo Colonnelli <iacopo.colonnelli@unito.it> (Designer and maintainer)  
Doriana Medić <doriana.medic@unito.it> (Designer and maintainer)  
Alberto Mulone <alberto.mulone@unito.it> (Maintainer)
