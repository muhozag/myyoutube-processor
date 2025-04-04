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
- **Database**: PostgreSQL
- **Asynchronous Processing**: Celery with Redis
- **AI Integration**: Mistral Small 3 for summarization and critique

### Development Environment
- **Python**: Version 3.9+
- **Dependency Management**: Virtual environments with requirements.txt
- **Version Control**: Git with GitHub
- **Code Quality**: PEP 8 guidelines, Black formatting, flake8 linting
- **Testing**: pytest with 80%+ code coverage

### Deployment
- **Containerization**: Docker
- **Orchestration**: Kubernetes
- **CI/CD**: GitHub Actions

### Security
- Environment-based configuration
- HTTPS enforcement
- Secure API key management
- Input validation and sanitization
- Protection against common web vulnerabilities

## Development Setup

Detailed setup instructions coming soon.
