# Import the required modules
import os
import subprocess
from azure.identity import DefaultAzureCredential
import azure.mgmt.resource
import azure.mgmt.web
import azure.core

# Set the subscription ID and the app name
subscription_id = "your-subscription-id"
app_name = "your-app-name"

# Create a Resource Management service object
resource_client = azure.mgmt.resource.ResourceManagementClient(
    credential=DefaultAzureCredential(),
    subscription_id=subscription_id,
)

# Check if the resource group already exists
try:
    resource_group = resource_client.resource_groups.get(app_name)
    print(f"Resource group {app_name} already exists on Azure.")
except azure.core.exceptions.ResourceNotFoundError:
    # Create the resource group if it does not exist
    print(f"Creating resource group {app_name} on Azure...")
    location = "westus"
    resource_group = resource_client.resource_groups.create_or_update(
        app_name, {"location": location}
    )
    print(f"Resource group {app_name} created on Azure.")

# Create a Web Apps Management service object
web_client = azure.mgmt.web.WebSiteManagementClient(
    credential=DefaultAzureCredential(),
    subscription_id=subscription_id,
)

# Check if the app service plan already exists
try:
    app_service_plan = web_client.app_service_plans.get(app_name, app_name)
    print(f"App service plan {app_name} already exists on Azure.")
except azure.core.exceptions.ResourceNotFoundError:
    # Create the app service plan if it does not exist
    print(f"Creating app service plan {app_name} on Azure...")
    sku = "B1"
    app_service_plan = web_client.app_service_plans.create_or_update(
        app_name, app_name, {"location": location, "sku": {"name": sku}}
    )
    print(f"App service plan {app_name}