from __future__ import annotations

import glob
import logging
import os
from pathlib import Path
from typing import MutableMapping, MutableSequence

from ruamel.yaml import YAML

from swirlc.core.entity import (
    Location,
    Step,
    Port,
    DistributedWorkflow,
    Workflow,
    Processor,
    Data,
)
from swirlc.core.translator import AbstractTranslator

MANDATORY_FILES = ("replicas", "sites", "transformations", "workflow")

# fixme: data_type cannot be always "file"
DATA_TYPE = "file"


def _open_yml(path):
    with open(path) as fd:
        config = YAML(typ="safe").load(fd.read())
    if config["pegasus"] != "5.0.4":
        logging.warning(
            f"Pegasus version supported 5.0.4. "
            f"This Pegasus version ({config['pegasus']}) is not checked for this translator. Errors can occur"
        )
    return config


def _get_key(searched: str, dictionary: MutableMapping[str, str]):
    for key, value in dictionary.items():
        if value == searched:
            return key
    return None


class DAXTranslator(AbstractTranslator):
    def __init__(self, dax_directory: Path):
        if not os.path.isdir(dax_directory):
            raise NotADirectoryError("DAXTranslator needs a directory")
        glob_result = {}
        for path in glob.glob(os.path.join(dax_directory, "*")):
            path = Path(path)
            glob_result.setdefault(path.stem, path)

        if missing_files := (set(MANDATORY_FILES) - set(glob_result.keys())):
            raise Exception(
                f"Missing files in the directory {dax_directory}: {missing_files}"
            )
        self.replicas_path: Path = glob_result["replicas"]
        self.sites_path: Path = glob_result["sites"]
        self.transformations_path: Path = glob_result["transformations"]
        self.workflow_path: Path = glob_result["workflow"]

    def _translate(self) -> Workflow:
        # Dax-Pegasus notation:
        #    - PFN: Physical File Names
        #    - LFN: Logical File Names
        workflow = DistributedWorkflow()

        # dax_data_logical_name : swirl_data_name
        data_binding_dax_swirl: MutableMapping[str, str] = {}

        # dax_location_logical_name : swirl_location_name
        location_binding_dax_swirl: MutableMapping[str, str] = {}

        # dax_step_id : swirl_step_name
        step_binding_dax_swirl: MutableMapping[str, str] = {}

        # swirl_step_name : [ swirl_data_names ]
        swirl_input_steps: MutableMapping[str, MutableSequence[str]] = {}
        swirl_output_steps: MutableMapping[str, MutableSequence[str]] = {}

        # swirl_step_name : [ string | swirl_data_name ]
        swirl_step_args = {}

        # dax_step_name : dax_step_id
        dax_step_name_id: MutableMapping[str, MutableSequence[str]] = {}

        # swirl_step_name : [ collector_step_name ]
        binding_collector_step = {}

        # Visit workflow yaml
        workflow_config = _open_yml(self.workflow_path.as_posix())
        for replica in workflow_config["jobs"]:
            dax_step_name_id.setdefault(replica["name"], []).append(replica["id"])
            swirl_step_name = f"s{len(step_binding_dax_swirl)}"
            step_binding_dax_swirl[replica["id"]] = swirl_step_name

            for data in replica["uses"]:
                if data["lfn"] not in data_binding_dax_swirl.keys():
                    data_binding_dax_swirl[data["lfn"]] = (
                        f"d{len(data_binding_dax_swirl)}"
                    )

                swirl_data_name = data_binding_dax_swirl[data["lfn"]]
                if data["type"] == "input":
                    swirl_input_steps.setdefault(swirl_step_name, []).append(
                        swirl_data_name
                    )
                elif data["type"] == "output":
                    swirl_output_steps.setdefault(swirl_step_name, []).append(
                        swirl_data_name
                    )
                    if data["stageOut"]:
                        # Generate a unique id for the collector step based on the DAX id of the previous step
                        collect_id = "COLLECT-" + replica["id"]
                        dax_step_name_id.setdefault(
                            f"{replica['name']}-{swirl_data_name}-collector", []
                        ).append(collect_id)
                        swirl_collect_step_name = f"s{len(step_binding_dax_swirl)}"
                        step_binding_dax_swirl[collect_id] = swirl_collect_step_name
                        # Add option for the copy command
                        swirl_step_args[swirl_collect_step_name] = [
                            "-r",
                            swirl_data_name,
                        ]
                        # Add output port of previous step as input of the collector step
                        swirl_input_steps.setdefault(
                            swirl_collect_step_name, []
                        ).append(swirl_data_name)
                        # Bind the collector step in the same location of previous step
                        binding_collector_step.setdefault(swirl_step_name, set()).add(
                            swirl_collect_step_name
                        )
            swirl_step_args[swirl_step_name] = [arg for arg in replica["arguments"]]

        # Create the steps
        for dax_id, swirl_step_name in step_binding_dax_swirl.items():
            display_name = next(
                dax_name
                for dax_name, dax_ids in dax_step_name_id.items()
                if dax_id in dax_ids
            )
            step = Step(swirl_step_name, display_name)
            workflow.add_step(step)
            if dax_id.startswith("COLLECT-"):
                step.command = "cp"

        # Add step output ports
        swirl_data_ports = {}
        for step_name, data_names in swirl_output_steps.items():
            for data_name in data_names:
                swirl_data_ports[data_name] = Port(
                    f"p{len(swirl_data_ports)}",
                    f"p{len(swirl_data_ports)}",
                    {data_name},
                )
                workflow.add_output_port(
                    workflow.steps[step_name], swirl_data_ports[data_name]
                )
                if workflow.steps[step_name].processors is None:
                    workflow.steps[step_name].processors = {}
                workflow.steps[step_name].processors[
                    swirl_data_ports[data_name].name
                ] = Processor(
                    type=DATA_TYPE, glob=_get_key(data_name, data_binding_dax_swirl)
                )

        # Add step input ports
        for step_name, data_names in swirl_input_steps.items():
            for data_name in data_names:
                if data_name not in swirl_data_ports.keys():
                    swirl_data_ports[data_name] = Port(
                        f"p{len(swirl_data_ports)}",
                        f"p{len(swirl_data_ports)}",
                        {data_name},
                    )
                workflow.add_input_port(
                    workflow.steps[step_name], swirl_data_ports[data_name]
                )

        # Add step arguments
        for step in workflow.steps.values():
            step.arguments = [
                swirl_data_ports.get(arg, arg) for arg in swirl_step_args[step.name]
            ]

        # Get locations
        sites_config = _open_yml(self.sites_path.as_posix())
        for site in sites_config["sites"]:
            location_binding_dax_swirl[site["name"]] = (
                f"l{len(location_binding_dax_swirl)}"
            )
            location = Location(
                name=location_binding_dax_swirl[site["name"]],
                display_name=site["name"],
                data={},
                hostname=site.get("hostname", "127.0.0.1"),
                port=site.get("port", 35050),
                workdir=(
                    next(
                        directory["path"]
                        for directory in site["directories"]
                        if directory["type"] == "sharedScratch"
                    )
                    if any(
                        True
                        for directory in site["directories"]
                        if directory["type"] == "sharedScratch"
                    )
                    else None
                ),
                outdir=(
                    next(
                        directory["path"]
                        for directory in site["directories"]
                        if directory["type"] == "localStorage"
                    )
                    if any(
                        True
                        for directory in site["directories"]
                        if directory["type"] == "localStorage"
                    )
                    else None
                ),
                connection_type=site.get("connectionType", "ssh"),
            )
            workflow.add_location(location)

        # Initial dataset
        replicas_config = _open_yml(self.replicas_path.as_posix())

        # logical_data_name : [ (location_name, physical_data_name) ]
        data_locations = {}
        for replica in replicas_config["replicas"]:
            for physical_path in replica["pfns"]:
                data_locations.setdefault(replica["lfn"], []).append(
                    (physical_path["site"], physical_path["pfn"])
                )
                location_name = location_binding_dax_swirl[physical_path["site"]]
                data_name = data_binding_dax_swirl[replica["lfn"]]
                if location_name in workflow.locations.keys():
                    workflow.locations[location_name].data[data_name] = Data(
                        data_name, DATA_TYPE, physical_path["pfn"]
                    )

        # Binding steps and locations
        transformations_config = _open_yml(self.transformations_path.as_posix())
        for transformation in transformations_config["transformations"]:
            for binding in transformation["sites"]:
                location_name = location_binding_dax_swirl[binding["name"]]
                for dax_step_id in dax_step_name_id[transformation["name"]]:
                    step_name = step_binding_dax_swirl[dax_step_id]
                    workflow.steps[step_name].command = binding["pfn"]
                    workflow.map(
                        workflow.steps[step_name], workflow.locations[location_name]
                    )
                    # Map the collector step and add last argument for the copy command
                    for c in binding_collector_step.get(
                        workflow.steps[step_name].name, []
                    ):
                        workflow.map(
                            workflow.steps[c], workflow.locations[location_name]
                        )
                        workflow.steps[c].arguments.append(
                            workflow.locations[location_name].outdir
                        )
        return workflow
