#!/usr/bin/env bash

# This script is the start command for the Render web service.
# It uses Uvicorn to run the FastAPI application.

# --host 0.0.0.0 makes the server accessible from the public internet,
# and --port $PORT tells Uvicorn to use the port assigned by Render.

uvicorn main:app --host 0.0.0.0 --port $PORT
