# Import the required modules
import os
import subprocess
import boto3

# Set the AWS region and the app name
region = "us-east-1"
app_name = "your-app-name"

# Create a Lambda service object
lambda_client = boto3.client("lambda", region_name=region)

# Check if the app already exists
try:
    function = lambda_client.get_function(FunctionName=app_name)
    print(f"App {app_name} already exists on AWS.")
except lambda_client.exceptions.ResourceNotFoundException:
    # Create the app if it does not exist
    print(f"Creating app {app_name} on AWS...")
    # Create a zip file containing the app code and the requirements.txt file
    print("Creating a zip file for the app...")
    subprocess.run(["pip", "install", "-r", "requirements.txt", "-t", "package"])
    os.chdir("package")
    subprocess.run(["zip", "-r", "../app.zip", "."])
    os.chdir("..")
    subprocess.run(["zip", "-g", "app.zip", "app/_init_.py"])
    # Create a Lambda function using the zip file
    print("Creating a Lambda function for the app...")
    with open("app.zip", "rb") as f:
        zip_file = f.read()
    response = lambda_client.create_function(
        FunctionName=app_name,
        Runtime="python3.9",
        Role="arn:aws:iam::your-account-id:role/your-role-name",
        Handler="app.handler",
        Code={"ZipFile": zip_file},
        Timeout=30,
        MemorySize=512,
    )
    function_arn = response["FunctionArn"]
    print(f"Lambda function {app_name} created on AWS.")

# Create an API Gateway service object
apigateway = boto3.client("apigateway", region_name=region)

# Check if the API already exists
try:
    api = apigateway.get_rest_api(restApiId=app_name)
    print(f"API {app_name} already exists on AWS.")
except apigateway.exceptions.NotFoundException:
    # Create the API if it does not exist
    print(f"Creating API {app_name} on AWS...")
    # Create a REST API
    print("Creating a REST API for the app...")
    response = apigateway.create_rest_api(name=app_name, apiKeySource="HEADER")
    api_id = response["id"]
    # Get the root resource ID
    response = apigateway.get_resources(restApiId=api_id)
    root_id = response["items"][0]["id"]
    # Create a proxy resource
    print("Creating a proxy resource for the app...")
    response = apigateway.create_resource(
        restApiId=api_id, parentId=root_id, pathPart="{proxy+}"
    )
    resource_id = response["id"]
    # Create a ANY method for the proxy resource
    print("Creating a ANY method for the proxy resource...")
    response = apigateway.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod="ANY",
        authorizationType="NONE",
        requestParameters={"method.request.path.proxy": True},
    )
    # Create an integration for the ANY method
    print("Creating an integration for the ANY method...")
    response = apigateway.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod="ANY",
        type="AWS_PROXY",
        integrationHttpMethod="POST",
        uri=f"arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{function_arn}/invocations",
    )
    # Create a deployment for the API
    print("Creating a deployment for the API...")
    response = apigateway.create_deployment(restApiId=api_id, stageName="prod")
    # Add permission for the API to invoke the Lambda function
    print("Adding permission for the API to invoke the Lambda function...")
    response = lambda_client.add_permission(
        FunctionName=app_name,
        StatementId=f"{app_name}-apigateway-permission",
        Action="lambda:InvokeFunction",
        Principal="apigateway.amazonaws.com",
        SourceArn=f"arn:aws:execute-api:{region}:your-account-id:{api_id}///*",
    )
    print(f"API {app_name} created on AWS.")

# Print the app URL
print(f"App {app_name} deployed on AWS. You can access it at https://{api_id}.execute-api.{region}.amazonaws.com/prod")