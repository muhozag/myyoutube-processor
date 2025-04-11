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
- **Framework**: Django with Django REST Framework
- **Database**: PostgreSQL (starting with SQLite included in Django by default. Then using psycopg2-binary initially for staging)
- **Asynchronous Processing**: Celery with Redis
- **AI Integration**: Mistral Small 3 for summarization and critique

### Development Environment
- **Python**: Version 3.9+ (Using 3.13 for dev)
- **Dependency Management**: Virtual environments with requirements.txt
- **Version Control**: Git with GitHub
- **Code Quality**: PEP 8 guidelines, Black formatting, flake8 linting
- **Testing**: pytest with 80%+ code coverage

### Deployment
- **Containerization**: Docker
- **Orchestration**: Kubernetes
- **CI/CD**: GitHub Actions
- **Hosting**: Railway

### Security
- Environment-based configuration
- HTTPS enforcement
- Secure API key management
- Input validation and sanitization
- Protection against common web vulnerabilities

## Development Setup

Detailed setup instructions coming soon.

## Deployment to Railway

This project is configured for automatic deployment to Railway through GitHub Actions.

### Setup for Automatic Deployment

1. Create a Railway account and project at [railway.app](https://railway.app/)
2. Install Railway CLI locally: `npm install -g @railway/cli`
3. Login to Railway: `railway login`
4. Link your project: `railway link`
5. Generate a Railway token: `railway login --browserless`
6. Add the following secrets to your GitHub repository:
   - `RAILWAY_TOKEN`: Your Railway API token
   - `DJANGO_SECRET_KEY`: A secure Django secret key

When you push to the main branch, the GitHub workflow will:
1. Run tests
2. Deploy the application to Railway if all tests pass

### Manual Deployment

To deploy manually:
```
railway up
```

### Environment Variables on Railway

Configure the following environment variables in your Railway project:
- `SECRET_KEY`: Your Django secret key
- `DEBUG`: Set to 'False' in production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DATABASE_URL`: Automatically provided by Railway PostgreSQL plugin
