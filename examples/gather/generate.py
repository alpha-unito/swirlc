n_locations = input("Number of locations: [10]")
if n_locations == "":
    n_locations = 10
n_locations = int(n_locations)

message_size = input("Message size (e.g., [10KB], 5MB, 1GB): ")
if message_size == "":
    message_size = "10KB"
    
message_size = message_size.upper()
size_translation = {
    "KB": 10**3,
    "MB": 10**6,
    "GB": 10**9,
}

message_size_bytes = int(message_size[:-2]) * size_translation[message_size[-2:]]

current_path = __file__.rsplit("/", 1)[0] + "/"

config_file = open(f"{current_path}config.yml", "w")
source_file = open(f"{current_path}source.swirl", "w")

locations = [f"location{i}" for i in range(n_locations)]

# config.yml ==================
config_file.write("version: v1.0\n\n")
config_file.write("locations:")

for i in range(n_locations):
    config_file.write(f"""
  {locations[i]}:
    hostname: 127.0.0.1
    port: {8080 + i}
    workdir: /workdir""")

config_file.write(f"""\n
dependencies:
  d1:
    type: file
    value: /data/message.txt
    """) 


# source.swirl ==================
for i in range(1, n_locations):
    send = f"send(d1->p{i},{locations[i]},{locations[0]})"
    source_file.write(f"""
<{locations[i]}, {{(p{i}, d1)}}, {send}> |""")


receives = [f"recv(p{i},{locations[i]},{locations[0]})" for i in range(1, n_locations)]

source_file.write(f"""
<{locations[0]}, {{}},
  (
    {" |\n    ".join(receives)}
  )
>
""")

# Generate message.txt ==================
message_file = open(f"{current_path}message.txt", "w")

# write random text to message.txt
import random
import string
message_file.write(''.join(random.choices(string.ascii_letters + string.digits, k=message_size_bytes)))
message_file.close()