# Internal FastAPI Development Guidelines

## 1. Project Structure
All FastAPI projects must follow the modular structure:
- src/api/: Route handlers.
- src/core/: Configuration and security.
- src/models/: Database models.
- src/schemas/: Pydantic models for request/response.
- src/services/: Business logic.

## 2. Pydantic v2
- Always use Pydantic v2 features.
- Prefer Field for descriptions and validation.

## 3. Dependency Injection
- Use FastAPI's Depends for database sessions and authentication.

## 4. Documentation
- Ensure all endpoints have clear summary and description fields.
- Use tags to group related endpoints.