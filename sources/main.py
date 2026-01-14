import uvicorn
from settings import config

if __name__ == '__main__':
    uvicorn.run("api.fastapi_app:app", host=config.api.host, port=config.api.port)