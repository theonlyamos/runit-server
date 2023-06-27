from kubernetes import client, config

# Load Kubernetes configuration from default location
config.load_kube_config()

# Create Kubernetes API client
api = client.AppsV1Api()

# Define deployment object
deployment = client.V1Deployment()
deployment.metadata = client.V1ObjectMeta(name="my-deployment")
deployment.spec = client.V1DeploymentSpec(
    replicas=1,
    selector=client.V1LabelSelector(
        match_labels={"app": "my-app"}
    ),
    template=client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(
            labels={"app": "my-app"}
        ),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    name="my-container",
                    image="nginx:latest",
                    ports=[client.V1ContainerPort(container_port=80)]
                )
            ]
        )
    )
)

# Create deployment
api.create_namespaced_deployment(
    namespace="default",
    body=deployment
)

# List deployments
deployments = api.list_namespaced_deployment(namespace="default")
for d in deployments.items:
    print(d.metadata.name)

# Delete deployment
api.delete_namespaced_deployment(
    name="my-deployment",
    namespace="default",
    body=client.V1DeleteOptions()
)

