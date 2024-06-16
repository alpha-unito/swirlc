from swirl.core.entity import Location, Step, Port, DistributedWorkflow, Workflow
from swirl.core.translator import AbstractTranslator


def test_example1():
    class Example1Translator(AbstractTranslator):
        def __init__(
            self, inputs: str, outputs: str, locations_mapping: str, data_locations: str
        ):
            self.inputs: str = inputs
            self.outputs: str = outputs
            self.locations_mapping: str = locations_mapping
            self.data_locations: str = data_locations

        def _translate(self) -> Workflow:
            workflow = DistributedWorkflow()

            step_names = set()
            inputs = {}
            for dependency in self.inputs.split(","):
                data, step_name = dependency.split(" -> ")
                step_names.add(step_name)
                inputs.setdefault(step_name, set()).add(data)

            outputs = {}
            data_port = {}
            port_counter = 0
            for output in self.outputs.split(","):
                step_name, data = output.split(" -> ")
                step_names.add(step_name)
                data_port[data] = Port(f"p{port_counter}", [data])
                port_counter += 1
                outputs.setdefault(step_name, []).append(data_port[data])

            for step_name in step_names:
                workflow.add_step(Step(step_name))
            for step_name, ports in outputs.items():
                for port in ports:
                    workflow.add_output_port(workflow.steps[step_name], port)
            for step_name, data in inputs.items():
                for d in data:
                    workflow.add_input_port(workflow.steps[step_name], data_port[d])

            location_names = set()
            mapping = {}
            for location in self.locations_mapping.split(","):
                step_name, location_name = location.split(": ")
                location_names.add(location_name)
                mapping.setdefault(step_name, set()).add(location_name)

            data_locations = {}
            for data_location in self.data_locations.split(","):
                location_name, data_name = data_location.split(": ")
                data_locations.setdefault(location_name, set()).add(data_name)

            for location_name in location_names:
                workflow.add_location(
                    Location(
                        location_name,
                        {
                            data_name: None
                            for data_name in data_locations.get(location_name, [])
                        },
                    )
                )

            for step_name, location_names in mapping.items():
                for location_name in location_names:
                    workflow.map(
                        workflow.steps[step_name], workflow.locations[location_name]
                    )

            return workflow

    # steps produce data
    step_out_names = "s1 -> d1,s1 -> d2"

    # steps take in input data
    step_in_names = "d1 -> s2,d2 -> s3"
    locations_mapping = "s1: ld,s2: l1,s3: l2,s3: l3"
    dataset = "ld: d"
    translator = Example1Translator(
        step_in_names, step_out_names, locations_mapping, dataset
    )
    translator.translate()
