import uvicorn
from app.main import app

if __name__ == "__main__":

    # The host="0.0.0.0" parameter allows the server to be accessible from any IP address,
    #   which is suitable for production deployment
    # The port=8000 specifies the port on which the server will run
    uvicorn.run(app, host="0.0.0.0", port=8000)
