from fastapi import FastAPI, Request
import os
from multiprocessing import Process
import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware

fapp = FastAPI()
import asyncio
import random

from nicegui import ui, app

class AddPortMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-PORT"] = os.environ.get("PORT", "8080")
        return response
    
fapp.add_middleware(AddPortMiddleware)

def init(fastapi_app: FastAPI) -> None:
    @ui.page("/nicegui")
    async def index():
        ui.label("Hello, world!") #
        random_string = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=10))
        ui.label(f"Random string: {random_string}")
        # get the port
        port = os.environ.get("PORT", "8080")
        ui.label(f"I am hosted at port {port}")

        await ui.context.client.connected()
        # make the string capital and display it
        ui.label(f"Capitalized: {random_string.upper()}")
        await ui.run_javascript("1+1")

    ui.run_with(
        fastapi_app,
        storage_secret='hmm',
    )
    # app.config.socket_io_js_transports = ['polling', 'websocket']

@fapp.get("/")
async def read_root():
    # sleep for a random and short duration
    duration = random.random()
    print(f"Sleeping for {duration} seconds")
    await asyncio.sleep(duration)
    port = os.environ.get("PORT", "8080")
    return {"message": f"I am hosted at port {port}"}

init(fapp)

def run_server(port):
    os.environ["PORT"] = str(port)
    uvicorn.run(fapp, host="0.0.0.0", port=port)

if __name__ == "__main__":
    ports = [8080, 8081, 8082, 8083]
    processes = []

    for port in ports:
        process = Process(target=run_server, args=(port,))
        processes.append(process)
        process.start()

    for process in processes:
        process.join()