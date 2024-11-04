# Use an official Python runtime as a parent image
FROM python:3.11

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install MySQL server
RUN apt-get update && \
    apt-get install -y default-mysql-server && \
    apt-get clean

# Copy the application code
COPY . .

# Create a script to start MySQL and your application
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Expose the port for MySQL
EXPOSE 3306

# Expose the port for your application (if using FastAPI, the default is 8000)
EXPOSE 8000

# Start MySQL and the application
CMD ["/start.sh"]
