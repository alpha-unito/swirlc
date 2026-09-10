# 1000Genomes Workflow - CWL Implementation

This repository contains a [Common Workflow Language](https://www.commonwl.org/) (CWL) implementation of the [1000Genomes Workflow](https://github.com/pegasus-isi/1000genome-workflow), initially implemented for the [Pegasus](https://pegasus.isi.edu/) workflow management system.

Note that all the metadata reported in the `*.cwl` files, particularly the `s:author` and `s:license` fields, concern only the CWL descriptions themselves, not the related script, whose [License](https://github.com/pegasus-isi/1000genome-workflow/blob/ee083a8a55436d437e3cf9f542f12d491b739c21/LICENSE) is reported on the original repository. If you want to give credit to the original 1000Genomes Workflow, please cite the following article:

> Rafael Ferreira da Silva, Rosa Filgueira, Ewa Deelman, Erola Pairo-Castineira, Ian M. Overton, Malcolm P. Atkinson, Using simple PID-inspired controllers for online resilient resource management of distributed scientific workflows, *Future Generation Computer Systems*, 95, 615-628, 2019,
ISSN 0167-739X, https://doi.org/10.1016/j.future.2019.01.015.

## Usage

Running this workflow requires a [CWL runner](https://www.commonwl.org/implementations/). For example, the CWL reference implementation, called [cwltool](https://github.com/common-workflow-language/cwltool), can be installed as follows:

```bash
python3 -m venv venv
source venv/bin/activate
pip install cwlref-runner
```

Two workflow steps require a `Python>=3.6` interpreter and the packages listed in the `requirements.txt` file. Such packages can be installed as follows:

```bash
pip install -r requirements.txt
```

Workflow input data are stored online on the [1000Genomes workflow repository](https://github.com/pegasus-isi/1000genome-workflow) and the [1000Genomes FTP server](https://ftp.1000genomes.ebi.ac.uk). The `download_data.sh` script creates the data directory structure and downloads all the required data in the proper locations.

Once all software and data dependencies are installed, the workflow can be launched using the following command:

```bash
cwl-runner main.cwl config.yml
```
