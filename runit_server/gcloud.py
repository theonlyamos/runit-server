# Import the required modules
import os
import subprocess
import googleapiclient.discovery

# Set the project ID and the app name
project_id = "your-project-id"
app_name = "your-app-name"

# Create an App Engine service object
appengine = googleapiclient.discovery.build("appengine", "v1")

# Check if the app already exists
try:
    app = appengine.apps().get(appsId=project_id).execute()
    print(f"App {app_name} already exists on GCP.")
except googleapiclient.errors.HttpError:
    # Create the app if it does not exist
    print(f"Creating app {app_name} on GCP...")
    body = {"id": project_id, "locationId": "us-central"}
    operation = appengine.apps().create(body=body).execute()
    # Wait for the operation to finish
    while operation.get("done") is not True:
        operation = appengine.apps().operations().get(
            appsId=project_id, operationsId=operation["name"]
        ).execute()
    print(f"App {app_name} created on GCP.")

# Create a Dockerfile for the app
print("Creating a Dockerfile for the app...")
with open("Dockerfile", "w") as f:
    f.write(
        f"""FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9
COPY ./app /app
"""
    )

# Build the Docker image and push it to Google Container Registry
print("Building and pushing the Docker image...")
image_name = f"gcr.io/{project_id}/{app_name}"
subprocess.run(["gcloud", "auth", "configure-docker"])
subprocess.run(["docker", "build", "-t", image_name, "."])
subprocess.run(["docker", "push", image_name])

# Create an app.yaml file for the app configuration
print("Creating an app.yaml file for the app configuration...")
with open("app.yaml", "w") as f:
    f.write(
        f"""runtime: custom
env: flex
service: {app_name}
handlers:
- url: /.*
  script: auto
"""
    )

# Deploy the app using gcloud app deploy
print("Deploying the app using gcloud app deploy...")
subprocess.run(["gcloud", "app", "deploy", "--project", project_id, "--quiet"])

# Print the app URL
print(f"App {app_name} deployed on GCP. You can access it at https://{app_name}.uc.r.appspot.com")