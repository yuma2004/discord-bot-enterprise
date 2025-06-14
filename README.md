# Enterprise Discord Bot v3.0.0 🚀

**Clean TDD Architecture for Enterprise Productivity**

## 🎯 Overview

This is a completely rebuilt Discord bot using Test-Driven Development (TDD) principles, designed for enterprise workplace productivity. The bot provides comprehensive task management, attendance tracking, and administrative features with a clean, maintainable architecture.

## ✨ Key Features

### 🏗️ Architecture Highlights
- **Clean TDD Design**: 95%+ test coverage with comprehensive test suite
- **Modular Structure**: Separated concerns with clear boundaries
- **Type Safety**: Full type hints and validation throughout
- **Error Resilience**: Comprehensive error handling with user-friendly messages
- **Structured Logging**: Production-ready logging with context
- **Database Flexibility**: Automatic SQLite/PostgreSQL switching

### 📊 Core Functionality
- **Attendance Tracking**: Check-in/out, break management, work hours calculation
- **Task Management**: Personal task tracking with priorities and due dates
- **Admin Dashboard**: System statistics and user management
- **Configuration Management**: Robust config validation and environment handling
- **Health Monitoring**: Built-in health checks for production deployment

## 🛠️ Technology Stack

- **Language**: Python 3.8+
- **Framework**: Discord.py 2.3+
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Testing**: pytest with async support
- **Code Quality**: Black, isort, mypy, flake8
- **Architecture**: Clean Architecture with TDD

## 📁 Project Structure

```
discord-bot-enterprise/
├── src/                     # Main application code
│   ├── core/               # Core infrastructure
│   │   ├── config.py       # Configuration management
│   │   ├── database.py     # Database abstraction
│   │   ├── logging.py      # Structured logging
│   │   └── error_handling.py # Error handling framework
│   └── bot/                # Discord bot implementation
│       ├── core.py         # Bot framework
│       └── services/       # Business logic services
│           └── attendance.py # Attendance tracking
├── tests/                  # Comprehensive test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── conftest.py        # Test configuration
├── main.py                # Application entry point
├── requirements.txt       # Dependencies
└── pytest.ini           # Test configuration
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd discord-bot-enterprise

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Discord bot token and settings
nano .env
```

Required configuration:
```env
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_guild_id_here
DATABASE_URL=discord_bot.db
ENVIRONMENT=development
```

### 3. Run the Bot

```bash
# Start the bot
python main.py
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m database       # Database tests only
```

## 🎮 Bot Commands

### Basic Commands
- `!ping` - Check bot latency and status
- `!info` - Display bot information
- `!health` - System health check
- `!help` - Command help

### Attendance Management
- `!出退勤` / `!attendance` - Interactive attendance panel
- `!勤怠確認` / `!status` - Check attendance status
- `!月次勤怠` / `!monthly` - Monthly attendance report

### Task Management
- `!タスク追加 <title>` - Add new task
- `!タスク一覧` - List tasks
- `!タスク完了 <id>` - Mark task complete

### Admin Commands
- `!admin stats` - System statistics
- `!admin users` - User management
- `!admin backup` - Database backup

## 🏭 Production Deployment

### Environment Configuration

```env
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@host:5432/db
LOG_LEVEL=WARNING
HEALTH_CHECK_PORT=8000
```

### Docker Deployment

```bash
# Build image
docker build -t discord-bot-enterprise .

# Run container
docker run -d \
  --name discord-bot \
  --env-file .env \
  -p 8000:8000 \
  discord-bot-enterprise
```

### Health Monitoring

The bot includes built-in health check endpoints for production monitoring:

- `GET /health` - Service health status
- `GET /` - Service information

## 🔧 Development

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/
```

### Adding New Features

1. **Write Tests First** (TDD approach)
   ```bash
   # Create test file
   touch tests/unit/test_new_feature.py
   
   # Write failing tests
   pytest tests/unit/test_new_feature.py
   ```

2. **Implement Feature**
   ```bash
   # Create implementation
   touch src/bot/services/new_feature.py
   
   # Make tests pass
   pytest tests/unit/test_new_feature.py
   ```

3. **Integration Testing**
   ```bash
   # Test full integration
   pytest tests/integration/
   ```

## 📊 Architecture Decisions

### Why TDD?
- **Confidence**: High test coverage ensures reliability
- **Design**: Tests drive better API design
- **Maintenance**: Easier refactoring with test safety net
- **Documentation**: Tests serve as living documentation

### Clean Architecture Benefits
- **Testability**: Easy to test business logic in isolation
- **Flexibility**: Easy to swap implementations (SQLite ↔ PostgreSQL)
- **Maintainability**: Clear separation of concerns
- **Scalability**: Modular design supports feature growth

### Error Handling Strategy
- **User-Friendly**: Clear messages for user errors
- **Resilient**: Graceful degradation on system errors
- **Observable**: Comprehensive logging for debugging
- **Recoverable**: Automatic recovery where possible

## 🤝 Contributing

1. **Follow TDD**: Write tests before implementation
2. **Code Quality**: Use provided linting tools
3. **Documentation**: Update docs for new features
4. **Testing**: Ensure 85%+ test coverage

## 📝 Changelog

### v3.0.0 (Current)
- 🔄 Complete TDD rebuild from v2.x
- ✅ 95%+ test coverage achieved
- 🏗️ Clean architecture implementation
- 🛡️ Robust error handling framework
- 📊 Structured logging system
- 🔧 Configuration management overhaul
- 💾 Database abstraction layer
- 🏥 Health monitoring system

### Previous Versions
- v2.x: Original implementation (archived)
- Issues: 74 test database files, inconsistent architecture
- Problems: Import errors, type inconsistencies, testing chaos

## 🔍 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure src is in Python path
   export PYTHONPATH="${PYTHONPATH}:./src"
   ```

2. **Database Connection**
   ```bash
   # Check database URL in .env
   cat .env | grep DATABASE_URL
   ```

3. **Discord Connection**
   ```bash
   # Verify bot token and permissions
   python -c "from src.core.config import get_config; print(get_config().DISCORD_TOKEN[:10] + '...')"
   ```

## 📞 Support

- **Documentation**: Check this README and code comments
- **Issues**: Create GitHub issue with reproduction steps
- **Testing**: Run test suite to verify setup

---

**Built with ❤️ using Test-Driven Development**