#!/usr/bin/env python3
import os
from flask import Flask, jsonify, send_from_directory
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

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cleaned_data_dir = os.path.join(base_dir, "cleaned_data")
    allowed_cleaned_files = {
        "zones_cleaned.csv",
        "zones_geo_cleaned.geojson",
    }

    @app.get("/cleaned_data/<path:filename>")
    def serve_cleaned_data(filename):
        if filename not in allowed_cleaned_files:
            return jsonify({"error": "File not allowed"}), 404
        return send_from_directory(cleaned_data_dir, filename, max_age=3600)

    @app.get("/health")
    def health():
        """Simple health probe."""
        return jsonify({"status": "ok"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    debug_mode = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=debug_mode)

