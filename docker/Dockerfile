FROM ollama/ollama:latest

# Set working directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the application code
COPY . /app/

# Install Python dependencies
RUN pip3 install -r requirements.txt

# Expose the Ollama port and Django application port
EXPOSE 11434 8000

# Create a startup script that pulls model on first use
RUN echo '#!/bin/bash\n\
ollama serve & \
OLLAMA_PID=$! \n\
sleep 5 && \
# Pull a smaller quantized model\n\
ollama pull mistral:7b-instruct-q4_0 && \
cd src && \
python3 manage.py runserver 0.0.0.0:8000\
' > /app/start.sh && chmod +x /app/start.sh

# Set the entry point
CMD ["/app/start.sh"]