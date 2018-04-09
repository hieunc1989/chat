############################################################
# Based on Ubuntu
############################################################

# Set the base image to Ubuntu
FROM ubuntu

# File Author / Maintainer
MAINTAINER hieunc

# Update the sources list
RUN apt-get update

# Install basic applications
RUN apt-get install -y tar git curl 

# Install Python and Basic Python Tools
RUN apt-get install -y python python-dev python-distribute python-pip

# Copy the application folder inside the container
ADD ./ /chat

# Get pip to download and install requirements:
RUN pip install -r /chat/requirements.txt

# Expose ports
EXPOSE 8888

# Set the default directory where CMD will execute
WORKDIR /chat

# Set the default command to execute    
# when creating a new container
# i.e. using CherryPy to serve the application
CMD python main.py
