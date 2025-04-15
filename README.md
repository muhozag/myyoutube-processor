# YouTube Transcript Processor

## Project Purpose

This application is intended to extract and process YouTube video transcripts to provide valuable insights and analysis. I attempted to make the system:

- Extract transcripts from YouTube videos using video URLs or IDs
- Generate AI-powered summaries of video content
- Provide critical analysis of video content
- Store processing results for future retrieval

This tool helps users quickly understand video content without watching entire videos, enabling efficient content consumption and analysis.
This project was inspired by the [5 AI Projects for People in a Hurry](https://shawhin.medium.com/5-ai-projects-for-people-in-a-hurry-1220f0b27037). 

## Key Features (I have in mind--some are incomplete and others like Async have a workaround instead)

- **Transcript Extraction**: Automatically extract and clean transcripts from YouTube videos
- **AI-Powered Summaries**: Generate concise, informative summaries of video content using Mistral AI models
- **Flexible AI Integration**: Multiple AI backend options (local Ollama, Mistral API, or self-hosted VPS)
- **Multi-Environment Support**: Works in local development, Railway deployment, or custom server setups
- **Asynchronous Processing**: Background video processing with Celery and Redis
- **User-Friendly Interface**: Clean, responsive UI for submitting and viewing processed videos
- **Advanced IPv6/IPv4 Support**: Automatic handling of different network configurations
- **Admin Dashboard**: Comprehensive administration interface for content management

## Technology Stack

### Backend
- **Framework**: Django 5.2 with Django REST Framework 3.16
- **Database**: PostgreSQL with psycopg2-binary (SQLite for development)
- **Asynchronous Processing**: Celery 5.5 with Redis
- **API Integration**: YouTube Transcript API
- **AI Models**: 
  - Mistral AI API (cloud-based) via mistralai 1.6.0
  - Local LLM integration via Ollama 0.4.7; also used for smaller VPS deployment.
- **Static Files**: Whitenoise 6.9 for serving static files

### Frontend
- **Template Engine**: Django Templates
- **Styling**: Custom CSS with responsive design
- **Markdown Rendering**: django-markdown-deux 1.0.6

### Development Environment
- **Python**: Version 3.9+ (3.13 recommended)
- **Dependency Management**: pip with requirements.txt
- **Version Control**: Git with GitHub
- **Code Quality**: PEP 8 guidelines, Black formatting, flake8 linting (try but not always
abide by)
- **Testing**: pytest with coverage reporting

### Deployment & DevOps
- **Hosting**: Railway (primary) with support for other platforms
- **Containerization**: Docker
- **WSGI Server**: Gunicorn 23.0.0
- **CI/CD**: GitHub Actions
- **Environment Management**: python-dotenv 1.0.1
- **Logging**: python-json-logger 3.3.0

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Python 3.9+** (preferably Python 3.13)
- **git** (for version control)
- **A text editor or IDE** (I used VS Code )

## System Requirements

### For Railway Deployment

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU       | 2 cores | 4+ cores    |
| RAM       | 4GB     | 8GB+        |
| Disk      | 1GB     | 5GB+        |
| OS        | Ubuntu 20.04+ | Ubuntu 22.04+ |

### For Local AI Model Usage

When running Mistral AI models locally with Ollama:
- **Mistral 7B**: At least 8GB RAM recommended
- **Mistral-small 22B**: At least 32GB RAM required (tested on macOS with 36GB RAM).
This is probably the only deployment I am confident I can stabilize. Remote deployment
was trickier with database issues and stuff like that. 

## Quick Start Guide

1. **Clone and install**:
   ```bash
   git clone <your-repository-url>
   cd myyoutube-processor
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Set up environment**:
   - Create a `.env` file with necessary settings (see Development Setup section)
   - Configure your preferred AI backend (Ollama local, Mistral API, or VPS)

3. **Initialize the application**:
   ```bash
   cd src
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```

4. **Start using the app**:
   - Access http://127.0.0.1:8000/ in your browser
   - Submit YouTube videos for processing
   - View generated transcripts and AI summaries

## Development Setup

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd myyoutube-processor
```

### 2. Python Environment Setup

Create and activate a virtual environment:

```bash
# Using venv (built into Python)
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### Core Dependencies:

| Package | Version | Purpose |
|---------|---------|---------|
| Django | 5.2 | Web framework |
| djangorestframework | 3.16.0 | REST API support |
| python-dotenv | 1.0.1 | Environment variables management |
| gunicorn | 23.0.0 | WSGI HTTP Server |
| celery | 5.5.0 | Asynchronous task queue |
| youtube-transcript-api | 1.0.3 | Fetch YouTube transcripts |
| python-json-logger | 3.3.0 | JSON formatted logging |
| ollama | 0.4.7 | Local LLM integration |
| django-markdown-deux | 1.0.6 | Markdown rendering |
| psycopg2-binary | 2.9.10 | PostgreSQL adapter |
| dj-database-url | 2.3.0 | Database URL configuration |
| whitenoise | 6.9.0 | Static files serving |
| mistralai | 1.6.0 | Mistral AI API client |

### 4. AI Components Setup

This application uses AI for transcript processing. You have three options:

#### Option 1: Local AI with Ollama

1. Install Ollama:
   - **macOS**: Download from [ollama.com/download](https://ollama.com/download)
   - **Linux**: `curl -fsSL https://ollama.com/install.sh | sh`
   - **Windows**: Use WSL2 with the Linux instructions

2. Pull the required models:
   ```bash
   ollama pull mistral
   # Or for better performance (if your system can handle it)
   ollama pull mistral-small:22b
   ```

3. Verify installation:
   ```bash
   ollama list
   ```

4. Start Ollama server:
   ```bash
   ollama serve
   ```

5. Verify Ollama connection:
   ```bash
   curl http://localhost:11434/api/tags
   ```

#### Option 2: Cloud AI with Mistral API

1. Create a Mistral AI account at [mistral.ai](https://mistral.ai/)
2. Generate an API key in your dashboard
3. Store the key in your `.env` file as `MISTRAL_API_KEY=your_api_key_here`
4. No need to run Ollama locally - the application will automatically use the cloud API

#### Option 3: Self-hosted Mistral on Linode VPS

For improved performance and control over your AI processing, Mistral can be self-hosted on a Linode VPS:

1. **Create a Linode VPS**:
   - Sign up on [Linode.com](https://www.linode.com/)
   - Create a new Linode instance with at least 16GB RAM (32GB recommended for better performance--I didn't have cash for this so I used a smaller instance that can handle
   Mistral 7b only)
   - Select Ubuntu 22.04 LTS as the operating system
   - Set up SSH access

2. **Install Dependencies**:
   ```bash
   ssh root@your-linode-ip
   apt update && apt upgrade -y
   apt install -y git curl wget
   ```

3. **Install Docker**:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   ```

4. **Set Up Ollama on the VPS**:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

5. **Pull the Mistral Model**:
   ```bash
   ollama pull mistral
   # Or for better performance (if your VPS has enough RAM):
   # ollama pull mistral-small:22b
   ```

6. **Configure Ollama to Accept Remote Connections**:
   - Create or edit the Ollama service file:
     ```bash
     nano /etc/systemd/system/ollama.service
     ```
   - Add the following content:
     ```
     [Unit]
     Description=Ollama Service
     After=network.target

     [Service]
     ExecStart=/usr/local/bin/ollama serve -l 0.0.0.0:11434
     Restart=always
     User=root
     Environment="OLLAMA_HOST=0.0.0.0:11434"

     [Install]
     WantedBy=multi-user.target
     ```
   - Reload systemd and restart Ollama:
     ```bash
     systemctl daemon-reload
     systemctl restart ollama
     systemctl enable ollama
     ```

7. **Set Up Firewall**:
   ```bash
   apt install -y ufw
   ufw allow 22/tcp
   ufw allow 11434/tcp
   ufw enable
   ```

8. **Configure Application to Use Remote Ollama**:
   - Update your local `.env` file:
     ```
     OLLAMA_HOST=http://your-linode-ip:11434
     USE_VPS_MODEL=true
     OLLAMA_VPS_MODEL=mistral
     # Or if you pulled the larger model:
     # OLLAMA_VPS_MODEL=mistral-small:22b
     ```

9. **Test the VPS Connection**:
   ```bash
   curl http://your-linode-ip:11434/api/tags
   ```

### 5. Environment Configuration

Create a `.env` file in the project root:

```bash
touch .env
```

Add the following environment variables:

```
# Django settings
SECRET_KEY=your_django_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3

# AI configuration options
# Option 1: Mistral API (cloud)
MISTRAL_API_KEY=your_mistral_api_key

# Option 2: Ollama (local)
OLLAMA_HOST=http://localhost:11434
OLLAMA_LOCAL_MODEL=mistral
# Or for better performance model:
# OLLAMA_LOCAL_MODEL=mistral-small:22b

# Option 3: VPS-hosted Ollama
# OLLAMA_HOST=http://your-linode-ip:11434
# USE_VPS_MODEL=true
# OLLAMA_VPS_MODEL=mistral
# Or: OLLAMA_VPS_MODEL=mistral-small:22b

# Railway-specific settings (optional)
# OLLAMA_HOST_IPV6=http://[::1]:11434
```

Generate a Django secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 6. Database Setup

#### Development Database (SQLite)

SQLite is configured by default for development. No additional setup is required.

#### Production Database (PostgreSQL)

For production environments:

1. Install PostgreSQL server
2. Create a database and user
3. Update your `.env` file with:
   ```
   DATABASE_URL=postgres://username:password@localhost:5432/dbname
   ```

## Application Setup and Usage

### Step 1: Set Up the Database

Run migrations to create the database schema:

```bash
cd src
python manage.py migrate
```

### Step 2: Create a Superuser

Create an admin user for accessing the Django admin interface:

```bash
python manage.py createsuperuser
```

Follow the prompts to create your admin account.

### Step 3: Run the Development Server

Start the Django development server:

```bash
python manage.py runserver
```

The application should now be running at http://127.0.0.1:8000/

### Step 4: Access the Application

1. Open your web browser and navigate to http://127.0.0.1:8000/
2. Log in using the superuser credentials you created earlier.
3. You should now see the YouTube Processor interface where you can:
   - Submit YouTube videos for processing
   - View processed videos
   - See transcripts and AI-generated summaries

### Step 5: Admin Interface

Access the admin interface at http://127.0.0.1:8000/admin/

The admin dashboard provides:
- Video management
- Transcript viewing
- User management
- Processing status monitoring

## Potential Future Features If Time Allows
As time allows (which I cannot guarantee), I  keep playing with this. And with resources, I think I can make it
more useful

### What I think I Can Add

- **Advanced Model Configuration**: Extended parameters for fine-tuning AI model behavior and outputs
- **Multi-language Support**: Transcript handling and summarization for non-English videos is not great right now. This can be an opportunity.
- **Topic Detection**: Automatic identification of main topics and themes in videos. This is okay but can be improved.
- **Extended Analytics Dashboard**: Detailed metrics about processed videos including word counts and processing times
- **Enhanced User Authentication**: Role-based access control with different permission levels
- **Batch Processing**: Process multiple videos at once with a unified summary
- **Comparison Mode**: Side-by-side comparison of different videos on similar topics
- **Content Moderation**: Detection and filtering of inappropriate content in transcripts
- **Mobile-Optimized Interface**: Enhanced responsiveness for mobile users

### Technical Enhancements (I am Learning as I Go)

- **Automated Model Selection**: Smart selection of AI models based on transcript complexity and length
- **Caching System**: Improved performance through strategic caching of API responses
- **Rate Limiting Protection**: Advanced handling of API rate limits with smart backoff strategies
- **Hybrid Processing Mode**: Combined local and cloud AI processing for optimal performance/cost balance
- **Enhanced IPv6/IPv4 Compatibility**: Further network stack improvements for diverse deployment environments
- **Custom Model Integration**: Support for additional AI models beyond Mistral
- **API Documentation**: OpenAPI/Swagger documentation for programmatic access


## Support and Community

For support and community discussions:

- **GitHub Issues**: Submit bug reports and feature requests
- **Documentation**: Refer to this README and inline code documentation
- **Contributing**: Pull requests are welcome

## License

This project is open-source software licensed under the MIT license.

## Acknowledgments

- Special thanks to the Mistral AI and Ollama teams for their outstanding open-source AI models
- Thanks to the Django community for the robust web framework
- Inspiration from [5 AI Projects for People in a Hurry](https://shawhin.medium.com/5-ai-projects-for-people-in-a-hurry-1220f0b27037). He does great work and I wouldn't have gone in this rabbit hole without seeing his work. 
