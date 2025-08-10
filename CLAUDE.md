# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a horse racing prediction AI system (競馬予想AIシステム) that uses machine learning to predict race outcomes based on JRA-VAN DataLab data. The project is built with Python, FastAPI, and utilizes Docker for containerization.

## Architecture

### Core Components
- **FastAPI Backend**: REST API for serving predictions and managing data (`src/api/`)
- **Data Pipeline**: CSV import and processing system for JRA-VAN data (`src/data/`)
- **ML Module**: Machine learning models using LightGBM and XGBoost (`src/ml/`)
- **Feature Engineering**: Extract and transform race, horse, and performance features (`src/features/`)
- **Task Queue**: Celery for async processing with Redis as broker (`src/tasks/`)
- **Dashboard**: Streamlit for visualization (`streamlit/`)
- **Experiment Tracking**: MLflow for model versioning and metrics

### Database Structure
- **MySQL**: Primary database for structured race data
- **Redis**: Cache and message broker for Celery
- **Alembic**: Database migration management

## Development Commands

### Environment Setup
```bash
make setup          # Initial project setup
make build          # Build Docker images
make up             # Start all containers
make down           # Stop all containers
```

### Data Operations
```bash
make csv-import     # Import CSV files from volumes/csv_import/
make db-migrate     # Run database migrations (alembic upgrade head)
make db-rollback    # Rollback migrations (alembic downgrade -1)
```

### Model Training & Prediction
```bash
make train          # Train ML models
make predict        # Run predictions
```

### Development Tools
```bash
make test           # Run tests with pytest
make test-cov       # Run tests with coverage report
make lint           # Run flake8 and mypy
make format         # Format code with black and isort
```

### Interactive Development
```bash
make shell          # Access app container bash
make db-shell       # Access MySQL shell
make jupyter        # Start Jupyter Lab (http://localhost:8888)
make streamlit      # Start Streamlit dashboard (http://localhost:8501)
make mlflow         # Start MLflow UI (http://localhost:5000)
```

### Container Management
```bash
make logs           # View all container logs
make logs-app       # View app container logs
make logs-db        # View database logs
make ps             # Show container status
```

## Testing Strategy

### Test Execution
- Run all tests: `docker compose exec app pytest tests/ -v`
- Run specific test file: `docker compose exec app pytest tests/unit/test_models.py -v`
- Run with coverage: `docker compose exec app pytest tests/ -v --cov=src --cov-report=html`
- Coverage report location: `htmlcov/index.html`

### Test Structure
- `tests/unit/`: Unit tests for individual components
- `tests/integration/`: Integration tests for API and database
- `tests/fixtures/`: Shared test fixtures and mock data

## Code Quality Tools

### Linting & Formatting
- **Black**: Code formatting (line length: 88)
- **isort**: Import sorting (profile: black)
- **flake8**: Style guide enforcement
- **mypy**: Static type checking

Configuration in `pyproject.toml` and `mypy.ini`

## Data Flow

1. **Import**: CSV files → `volumes/csv_import/` → Data importers parse and validate
2. **Storage**: Validated data → MySQL database via SQLAlchemy models
3. **Processing**: Feature extraction → Time series processing → Data aggregation
4. **Training**: Processed features → ML models (LightGBM/XGBoost) → Model artifacts
5. **Prediction**: New race data → Feature pipeline → Trained model → Predictions

## Key Directories

- `src/data/importers/`: CSV parsers for race, horse, odds, results
- `src/data/models/`: SQLAlchemy ORM models
- `src/data/processors/`: Data cleaning and aggregation
- `src/features/extractors/`: Feature engineering modules
- `src/ml/models/`: ML model implementations
- `src/ml/trainers/`: Training pipelines
- `src/ml/predictors/`: Prediction services

## Environment Variables

Key environment variables (set in `.env`):
- `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_NAME`: MySQL credentials
- `DATABASE_PORT`: MySQL port (default: 3306)
- `REDIS_URL`: Redis connection string
- `API_PORT`: FastAPI port (default: 8000)
- `JUPYTER_TOKEN`: Jupyter Lab access token
- `MLFLOW_PORT`: MLflow UI port (default: 5000)

## Database Migrations

Using Alembic for schema management:
```bash
# Create new migration
docker compose exec app alembic revision --autogenerate -m "migration message"

# Apply migrations
docker compose exec app alembic upgrade head

# Rollback last migration
docker compose exec app alembic downgrade -1
```

## CI/CD Pipeline

GitHub Actions workflows:
- **ci.yml**: Main CI pipeline with tests and linting
- **pr-check.yml**: Pull request validation
- **test.yml**: Test execution on push/PR
- **claude.yml**: Claude Code integration

## Important Notes

- CSV import directory: `volumes/csv_import/` - Place JRA-VAN CSV files here
- Model outputs: `outputs/models/` - Trained model artifacts
- Predictions: `outputs/predictions/` - Prediction results
- Logs: `logs/` - Application logs
- MLflow artifacts: `volumes/mlflow/` - Experiment tracking data