from kubernetes import client, config

# Load Kubernetes configuration from default location
config.load_kube_config()

# Create Kubernetes API client
api = client.AppsV1Api()

# Define Persistent Volume Claim
pvc = client.V1PersistentVolumeClaim(
    metadata=client.V1ObjectMeta(
        name='my-pvc'
    ),
    spec=client.V1PersistentVolumeClaimSpec(
        access_modes=['ReadWriteOnce'],
        resources=client.V1ResourceRequirements(
            requests={'storage': '1Gi'}
        )
    )
)

# Create Persistent Volume Claim
api.create_namespaced_persistent_volume_claim(namespace='default', body=pvc)

# Define Pod template
container = client.V1Container(
    name='my-container',
    image='nginx',
    volume_mounts=[client.V1VolumeMount(
        name='my-volume',
        mount_path='/data'
    )]
)
template = client.V1PodTemplateSpec(
    metadata=client.V1ObjectMeta(
        labels={'app': 'my-app'}
    ),
    spec=client.V1PodSpec(
        containers=[container],
        volumes=[client.V1Volume(
            name='my-volume',
            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                claim_name='my-pvc'
            )
        )]
    )
)

# Define Deployment
deployment = client.V1Deployment(
    metadata=client.V1ObjectMeta(
        name='my-deployment'
    ),
    spec=client.V1DeploymentSpec(
        replicas=1,
        selector=client.V1LabelSelector(
            match_labels={'app': 'my-app'}
        ),
        template=template
    )
)

# Create Deployment
api.create_namespaced_deployment(namespace='default', body=deployment)

