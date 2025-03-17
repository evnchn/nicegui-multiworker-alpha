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

        # print "/nicegui page function is being ran at port 8080"
        print(f"Page function is being ran at port {os.environ.get('PORT', '8080')}")

        ui.label("Hello, world!") #
        random_string = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=10))
        ui.label(f"Random string: {random_string}")
        # get the port
        port = os.environ.get("PORT", "8080")
        ui.label(f"I am hosted at port {port}")

        print(f"Page function await ui.context.client.connected() {os.environ.get('PORT', '8080')}")
        await ui.context.client.connected()
        print(f"Page function past the await {os.environ.get('PORT', '8080')}")
        # make the string capital and display it
        ui.label(f"Capitalized: {random_string.upper()}")

        print(f"Page function await ui.run_javascript('1+1') {os.environ.get('PORT', '8080')}")
        # await ui.run_javascript("1+1") # This doesn't seem to work? 
        print(f"Page function past the await {os.environ.get('PORT', '8080')}")

    @ui.page("/perhaps_simplier")
    def perhaps_simplier():
        print(f"Page function is being ran at port {os.environ.get('PORT', '8080')}")
        ui.label("Hello, world!")
        random_string = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=10))
        ui.label(f"Random string: {random_string}")
        port = os.environ.get("PORT", "8080")
        ui.label(f"I am hosted at port {port}")
        
        text_element = ui.label("Here is the text element")
        ui.button("Change text", on_click=lambda: text_element.set_text(random_string.upper()))

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