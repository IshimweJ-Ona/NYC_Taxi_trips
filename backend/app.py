#!/usr/bin/env python3
import os
from flask import Flask, jsonify
from flask_cors import CORS
from flasgger import Swagger
from api import api  # Import the API blueprint

def create_app():
    """Create and configure the Flask app."""
    app = Flask(__name__)
    # Allow browser-based frontends (served from file:// or other ports) to call this API.
    CORS(app)

    # Initialize Swagger
    Swagger(app)

    # Register the API blueprint
    app.register_blueprint(api)

    @app.get("/health")
    def health():
        """Simple health probe."""
        return jsonify({"status": "ok"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    debug_mode = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=debug_mode)

