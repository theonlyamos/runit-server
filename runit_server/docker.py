import docker

# Create Docker client
client = docker.from_env()

# Build Docker image
image = client.images.build(
    path="/path/to/dockerfile",
    tag="my-image",
)

# Create Docker container
container = client.containers.run(
    image="my-image",
    name="my-container",
    detach=True,
    ports={"80/tcp": ("0.0.0.0", 80)},
)

# List Docker containers
containers = client.containers.list()
for c in containers:
    print(c.name)

# Stop Docker container
container.stop()

# Remove Docker container
container.remove()

# Remove Docker image
client.images.remove("my-image")

