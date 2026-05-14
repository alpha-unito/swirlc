

location 0 runs a step (execute) that returns a value.
location 0 has 2 more steps on a choice (+) based on the value returned by the first step.
location 0 has 2 send operations, one for each step on the choice, going to location 1 and location 2 respectively.
location 1 and location 2 each have a receive operation that waits for the message from location 0.
location 1 and location 2 each have a step (execute) that runs after receiving the message from location 0.


python tmp_main.py compile --outdir build examples/choice/source.swirl examples/choice/config.yml