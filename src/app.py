"""
Flask Application Factory
Creates and configures the Flask application with blueprints
"""
import os
import logging
from pathlib import Path
from flask import Flask, send_from_directory
from config import get_config


def create_app(config_name=None):
    """
    Application factory for creating Flask app instances
    
    Args:
        config_name: Configuration environment ('development', 'production', 'testing')
                    If None, uses FLASK_ENV environment variable
    
    Returns:
        Configured Flask application instance
    """
    # Set template folder relative to this file
    template_folder = Path(__file__).parent / 'templates'
    app = Flask(__name__, template_folder=str(template_folder))
    
    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Convert Path objects to strings for Flask config
    app.config['UPLOAD_FOLDER'] = str(config.UPLOAD_FOLDER)
    app.config['OUTPUT_FOLDER'] = str(config.OUTPUT_FOLDER)
    app.config['ALLOWED_EXTENSIONS'] = config.ALLOWED_EXTENSIONS
    
    # Configure logging
    configure_logging(app)
    
    # Register blueprints
    from routes import bp as main_bp
    app.register_blueprint(main_bp)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register additional routes (favicon, etc)
    register_static_routes(app)
    
    app.logger.info(f"Application initialized in {config_name or 'default'} mode")
    
    return app


def configure_logging(app):
    """Configure application logging"""
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set Flask app logger level
    app.logger.setLevel(log_level)


def register_error_handlers(app):
    """Register error handlers for common HTTP errors"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.warning(f"404 error: {error}")
        return "Page not found", 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"500 error: {error}", exc_info=True)
        return "Internal server error", 500
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        app.logger.warning(f"413 error: File too large")
        return "File too large. Maximum size is 16MB.", 413


def register_static_routes(app):
    """Register routes for static files like favicon"""
    
    @app.route('/favicon.ico')
    def favicon():
        """Serve favicon"""
        static_dir = Path(app.root_path) / 'static'
        if static_dir.exists():
            return send_from_directory(
                static_dir,
                'favicon.svg',
                mimetype='image/svg+xml'
            )
        return '', 204  # No content if favicon doesn't exist


# For backward compatibility with existing run.py and app imports
app = create_app()

if __name__ == '__main__':
    # For direct execution
    app.run(debug=True, host='0.0.0.0', port=5000)
