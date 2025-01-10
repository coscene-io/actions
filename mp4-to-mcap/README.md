# MP4 to MCAP Converter

This project provides a Dockerized service to convert MP4 files into MCAP format. Follow the steps below to set up and run the converter.

## Prerequisites
- Docker installed on your local machine.
- Access to the coScene Docker registry at cr.coscene.cn.

## Setup Instructions

### 1. Log in to coScene Docker Registry and Push the Image

Ensure you have the necessary credentials to [access the coScene Docker registry](https://docs.coscene.cn/docs/use-case/automated-data-processing/#%E7%99%BB%E5%BD%95%E9%95%9C%E5%83%8F%E4%BB%93%E5%BA%93).


```
# Log in to the coScene Docker registry
docker login cr.coscene.cn
# When prompted, enter your username and password
```


### 2. Clone the Repository and Build the Docker Image
```
# Clone the repository
git clone https://github.com/coscene-io/mp4-to-mcap.git
cd mp4-to-mcap

# Build and push the Docker image
docker buildx build --platform linux/amd64 -t cr.coscene.cn/{your_project_name}/h264-encoder:latest .
```

### 3. Set Up a coScene Action with the Docker Image and Configure Trigger

To automate the conversion process, set up a coScene action using the pushed Docker image.

1) Create a New Action: In your coScene project, navigate to the Actions section and create a new action.

2) Configure the Action:

Docker Image: Specify `cr.coscene.cn/{your_project_name}/h264-encoder:latest` as the Docker image.

Environment Variables: Set the following variables as needed:
- __TOPIC__: Defaults to `/video/h264`.
- __INPUT_PATHS__:

  The default value is where the files from the records mounted to. You can change it to the folder's subfolder.

  Defaults to `/cos/files`
- __OUTPUT_DIR__: Defaults to `/cos/outputs`.

3) Set Up Trigger:

Define the event that will trigger this action, such as uploading a new MP4 file to a specific directory.


### 4. Upload an MP4 File to a new Record and Verify the Docker Invocation

1. Upload the File: Drag an MP4 file to the `records` page of the project.
2. Check the Action Invocation:
   
    Monitor the Actions dashboard in coScene to ensure the conversion action is triggered.

3. Verify the output in the specified output directory of the run.

## Notes

- Ensure that the input and output directories are correctly mounted and accessible within the Docker container.
- Adjust environment variables as necessary to fit your specific use case.

For more detailed information, refer to the coScene documentation. ￼

Feel free to customize this README to better fit your project’s specifics.
