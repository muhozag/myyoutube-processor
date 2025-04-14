# YouTube Transcript Processor

## Project Purpose

This application extracts and processes YouTube video transcripts to provide valuable insights and analysis. The system:

- Extracts transcripts from YouTube videos using video URLs or IDs
- Generates AI-powered summaries of video content
- Provides critical analysis of video content
- Stores processing results for future retrieval

This tool helps users quickly understand video content without watching entire videos, enabling efficient content consumption and analysis.
This project was inspired by the [5 AI Projects for People in a Hurry](https://shawhin.medium.com/5-ai-projects-for-people-in-a-hurry-1220f0b27037) tutorial. 

## Technology Stack

### Backend
- **Framework**: Django 5.2 with Django REST Framework 3.16
- **Database**: PostgreSQL with psycopg2-binary (SQLite for development)
- **Asynchronous Processing**: Celery 5.5 with Redis
- **API Integration**: YouTube Transcript API
- **AI Models**: 
  - Mistral AI API (cloud-based) via mistralai 1.6.0
  - Local LLM integration via Ollama 0.4.7
- **Static Files**: Whitenoise 6.9 for serving static files

### Frontend
- **Template Engine**: Django Templates
- **Styling**: Custom CSS with responsive design
- **Markdown Rendering**: django-markdown-deux 1.0.6

### Development Environment
- **Python**: Version 3.9+ (3.13 recommended)
- **Dependency Management**: pip with requirements.txt
- **Version Control**: Git with GitHub
- **Code Quality**: PEP 8 guidelines, Black formatting, flake8 linting
- **Testing**: pytest with coverage reporting

### Deployment & DevOps
- **Hosting**: Railway (primary) with support for other platforms
- **Containerization**: Docker
- **WSGI Server**: Gunicorn 23.0.0
- **CI/CD**: GitHub Actions
- **Environment Management**: python-dotenv 1.0.1
- **Logging**: python-json-logger 3.3.0

### Security
- Environment-based configuration
- CSRF protection
- Secure API key management
- Input validation and sanitization
- Protection against common web vulnerabilities

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Python 3.9+** (preferably Python 3.13)
- **pip** (Python package installer)
- **git** (version control)
- **A text editor or IDE** (VS Code recommended)

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
- **Mistral-small 22B**: At least 32GB RAM required (tested on macOS with 36GB RAM)

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

#### Option 2: Cloud AI with Mistral API

1. Create a Mistral AI account at [mistral.ai](https://mistral.ai/)
2. Generate an API key in your dashboard
3. Store the key in your `.env` file

#### Option 3: Self-hosted Mistral on Linode VPS

For improved performance and control over your AI processing, Mistral can be self-hosted on a Linode VPS:

1. **Create a Linode VPS**:
   - Sign up on [Linode.com](https://www.linode.com/)
   - Create a new Linode instance with at least 16GB RAM (32GB recommended for better performance)
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
     OLLAMA_LOCAL_MODEL=mistral
     # Or if you pulled the larger model:
     # OLLAMA_LOCAL_MODEL=mistral-small:22b
     ```

This setup provides a dedicated server for running Mistral AI models, offloading the computational burden from your local machine while maintaining full control over your AI processing.

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

## Troubleshooting

### Transcript API Issues

If you encounter issues with the YouTube Transcript API:

```bash
pip install --upgrade youtube-transcript-api
```

### AI Model Connection Issues

For Ollama connection issues:
1. Ensure Ollama is running: `ollama serve`
2. Check your `.env` configuration for correct `OLLAMA_HOST`

For Mistral API issues:
1. Verify your API key in the `.env` file
2. Check your internet connection

### Database Issues

If you encounter database issues:
1. Delete the `db.sqlite3` file
2. Run migrations again: `python manage.py migrate`
3. Create a new superuser: `python manage.py createsuperuser`

## Development Workflow

1. **Submit a Video**: Use the "Submit Video" form to add a YouTube URL
2. **Process the Video**: Click the "Process" button to extract the transcript
3. **View Results**: View the processed transcript and AI-generated summary
4. **Reprocess if needed**: You can reprocess videos if needed

## Project Structure Overview

- `src/`: Main source directory
  - `myyoutubeprocessor/`: Main Django project
    - `settings.py`: Project settings
    - `urls.py`: URL configurations
    - `utils/`: Utility functions
      - `ai/`: AI integration services
      - `youtube_utils.py`: YouTube API utilities
  - `videos/`: App for video processing
    - `models.py`: Data models
    - `views.py`: View functions
    - `tasks.py`: Processing tasks
  - `templates/`: HTML templates
  - `static/`: Static files (CSS, JS)
  - `manage.py`: Django management script

## Deployment

This project can be deployed using various cloud platforms with primary support for Railway.

### Railway Deployment

The project is configured to deploy seamlessly to Railway with:
- Automatic detection of Railway environment
- Configured CSRF trusted origins for Railway domains
- Support for PostgreSQL database via DATABASE_URL

### Linode VPS Deployment Architecture

This project uses a hybrid deployment architecture:

1. **Web Application**: Deployed on Railway for reliable web hosting
2. **AI Model Serving**: Self-hosted on a Linode VPS for performance and control
   - Separate VPS running Ollama with Mistral models
   - Communication between Railway and Linode via secure API calls
   - Benefits include cost optimization, performance control, and customization options

To set up this architecture:
1. Deploy the web application on Railway (see Railway Deployment section)
2. Set up the Mistral server on Linode (see Option 3 in AI Components Setup)
3. Connect them by configuring the `OLLAMA_HOST` environment variable on Railway to point to your Linode server

### Manual Deployment

For manual deployment options, refer to the documentation of your preferred hosting platform.

### Environment Variables for Production

Configure the following environment variables in your production environment:
- `SECRET_KEY`: Your Django secret key
- `DEBUG`: Set to 'False' in production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DATABASE_URL`: Your database connection string
- `MISTRAL_API_KEY`: If using Mistral AI cloud service
- `OLLAMA_HOST`: URL to your Linode VPS running Ollama (format: http://your-linode-ip:11434)
- `OLLAMA_LOCAL_MODEL`: The Mistral model you've pulled on your VPS
