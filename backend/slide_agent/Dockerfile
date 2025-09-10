# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

# Copy the rest of the application's code into the container at /app
COPY . .

# Expose port 10011 to the outside world
EXPOSE 10011

# Command to run the application
CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "10011"]
