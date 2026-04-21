"""Run the training server: python -m football_ml.server"""

import uvicorn

from football_ml.server.app import app


def main():
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
