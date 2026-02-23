# Database Migrations

This directory contains Alembic database migrations for the Specter conversation management system.

## Overview

The migration system has been completely migrated from raw SQL queries to SQLAlchemy ORM with comprehensive input sanitization using bleach. All database operations now use proper ORM patterns with automatic sanitization of user inputs.

## Key Features

- **SQLAlchemy ORM**: Complete replacement of raw SQL with SQLAlchemy ORM queries
- **Input Sanitization**: All text inputs are sanitized using bleach before database storage
- **Migration Management**: Automatic schema versioning and migration support with Alembic
- **Security**: No raw SQL queries remain in the codebase, preventing SQL injection
- **Performance**: Optimized queries with proper indexing and relationship loading

## Files

- `alembic.ini`: Alembic configuration file
- `env.py`: Alembic environment configuration
- `script.py.mako`: Template for generating new migrations
- `migration_manager.py`: Python utilities for managing migrations
- `versions/001_initial_schema.py`: Initial database schema migration
- `README.md`: This documentation file

## Usage

### Running Migrations

The database will automatically run migrations when initialized:

```python
from specter.src.infrastructure.conversation_management.repositories.database import DatabaseManager

db = DatabaseManager()
db.initialize()  # Automatically runs pending migrations
```

### Manual Migration Management

You can also manage migrations manually:

```python
from specter.src.infrastructure.conversation_management.migrations.migration_manager import MigrationManager
from specter.src.infrastructure.conversation_management.repositories.database import DatabaseManager

db = DatabaseManager()
migration_manager = MigrationManager(db)

# Check if database is up to date
is_up_to_date = migration_manager.is_database_up_to_date()

# Run migrations
success = migration_manager.run_migrations()

# Get current revision
current_rev = migration_manager.get_current_revision()

# Get migration history
history = migration_manager.get_migration_history()
```

### Command Line Interface

You can run migrations from the command line:

```bash
# Run all pending migrations
python migration_manager.py

# Run migrations to specific revision
python migration_manager.py --target abc123

# Check migration status
python migration_manager.py --status

# Reset database (WARNING: destroys all data)
python migration_manager.py --reset

# Create new migration
python migration_manager.py --create "Add new feature"
```

## Database Schema

The migration system manages the following tables:

### Core Tables
- `conversations`: Main conversation records with metadata
- `messages`: Individual messages within conversations
- `tags`: Normalized tag definitions
- `conversation_tags`: Many-to-many relationship between conversations and tags
- `conversation_summaries`: AI-generated conversation summaries
- `conversations_fts`: Full-text search index
- `schema_version`: Schema version tracking

### Security Features

All database models include built-in input sanitization:

1. **Text Sanitization**: Plain text inputs are cleaned of dangerous characters
2. **HTML Sanitization**: HTML content is sanitized using bleach with allowed tags
3. **Length Validation**: Input length limits prevent buffer overflow attacks  
4. **Type Validation**: Strong typing prevents type confusion attacks
5. **SQL Injection Prevention**: ORM queries eliminate raw SQL injection risks

### Input Sanitization Details

The system uses bleach for sanitization with the following configuration:

**Allowed HTML Tags**: 
- Text formatting: `p`, `br`, `strong`, `em`, `u`
- Lists: `ol`, `ul`, `li`
- Code: `code`, `pre`, `blockquote`
- Links: `a` (with `href` and `title` attributes)
- Headings: `h1`, `h2`, `h3`, `h4`, `h5`, `h6`

**Sanitization Functions**:
- `sanitize_text()`: For plain text content (strips all HTML)
- `sanitize_html()`: For rich content (allows safe HTML subset)

## Creating New Migrations

When you modify the SQLAlchemy models, create a new migration:

1. Make your changes to the models in `database_models.py`
2. Create a new migration:
   ```bash
   python migration_manager.py --create "Description of your changes"
   ```
3. Review the generated migration file in `versions/`
4. Test the migration on a development database
5. Run the migration: `python migration_manager.py`

## Troubleshooting

### Migration Fails
If a migration fails, check:
1. Database file permissions
2. Schema conflicts
3. Data validation errors
4. SQLite version compatibility

### Performance Issues
For large databases:
1. Consider running migrations during maintenance windows
2. Monitor disk space during schema changes
3. Use batch operations for data migrations

### Rollback
To rollback to a previous migration:
```bash
python migration_manager.py --target <previous_revision_id>
```

## Migration Best Practices

1. **Always backup** your database before running migrations in production
2. **Test migrations** thoroughly in development environments
3. **Keep migrations small** and focused on single changes
4. **Document breaking changes** in migration descriptions
5. **Never edit existing migrations** that have been applied to production
6. **Use batch operations** for data migrations on large datasets

## Security Considerations

1. All user inputs are automatically sanitized before database storage
2. No raw SQL queries are used anywhere in the system
3. ORM relationships prevent many classes of injection attacks
4. Input length limits prevent buffer overflow attacks
5. Type validation prevents type confusion vulnerabilities

## Dependencies

- SQLAlchemy >= 2.0.0
- Alembic >= 1.12.0
- bleach >= 6.0.0

These dependencies are automatically installed via requirements.txt.