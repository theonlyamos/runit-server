from fastapi import FastAPI, Request, HTTPException
from kubernetes import client, config
from typing import Dict

app = FastAPI()

config.load_kube_config()  # Load configuration from kubeconfig file
api_instance = client.CoreV1Api()

# Function discovery (example: using a dictionary)
functions = {
    'test': {'service': 'test-service', 'port': 9000},
    'another-app': {'service': 'another-app-service', 'port': 9000},
}

# Function to create a Kubernetes Service
def create_service(service_name: str, function_name: str, port: int):
    service = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(name=service_name),
        spec=client.V1ServiceSpec(
            selector={"app": function_name},
            ports=[
                client.V1ServicePort(
                    protocol="TCP", port=port, target_port=port
                )
            ],
        ),
    )
    api_instance.create_namespaced_service(namespace="default", body=service)

# Create services for each function on startup
for function_name, data in functions.items():
    create_service(data['service'], function_name, data['port'])

@app.get("/{path:path}")
async def route_request(path: str, request: Request):
    subdomain = request.headers.get('host').split('.')[0]
    if subdomain in functions:
        # No need to redirect, Nginx will handle forwarding
        return "Request forwarded to serverless app"
    else:
        raise HTTPException(status_code=404, detail="Function not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

