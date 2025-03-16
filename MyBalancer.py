import asyncio
import os
from typing import Union
import uvicorn
from bareasgi import Application, HttpRequest, HttpResponse, WebSocketRequest, text_writer
import httpx
from httpx_ws import aconnect_ws
import random

# Define the backends and their ports
backends = [8080, 8081, 8082, 8083]
request_counts = {port: 0 for port in backends}
failed_requests = {port: 0 for port in backends}
lock = asyncio.Lock()

websocket_affinity = {} # key: id in the cookie, value: port

# Create a single instance of httpx.AsyncClient
client = httpx.AsyncClient()
client2 = httpx.AsyncClient()

def session_from_cookie(cookie: str) -> str:
    if cookie:
        cookie_entries = cookie.split(';')
        for entry in cookie_entries:
            if entry.startswith('session='):
                session = entry.partition('=')[-1]
                session = session.partition('.')[0]
                session = session.strip()
                return session
    return None

def path_from_request(request: Union[HttpRequest, WebSocketRequest]) -> str:
    return request.scope['path']

def query_string_from_request(request: Union[HttpRequest, WebSocketRequest]) -> str:
    return request.scope['query_string'].decode()

def headers_from_request(request: Union[HttpRequest, WebSocketRequest]) -> dict:
    return {k.decode(): v.decode() for k, v in request.scope['headers']}

async def http_request_callback(request: HttpRequest) -> HttpResponse:
    # reading the request
    path = path_from_request(request)
    query_string = query_string_from_request(request)
    method = request.scope['method']
    headers = headers_from_request(request)
    body = b""
    async for chunk in request.body:
        body += chunk

    print("headers: ", headers)
    cookie = headers.get('cookie', None)
    session = session_from_cookie(cookie)
    print("session: ", session)

    print("failed_requests: ", failed_requests)
    print("request_counts: ", request_counts)

    # Sort backends by least failed requests, and then by least requests
    sorted_backends = sorted(
        backends,
        key=lambda port: (failed_requests[port], request_counts[port], random.random())
    )
    
    for backend_port in sorted_backends:
        try:
            websocket_affinity[session] = backend_port # NOTE: Remove this line to see affinity break
            print(f"Trying backend: {backend_port}")

            # Update request count in a thread-safe manner
            async with lock:
                request_counts[backend_port] += 1

            backend_url = f"http://localhost:{backend_port}{path}?{query_string}"
            print(f"Forwarding request to backend: {backend_url}")

            # Forward the request to the selected backend
            response = await client.request(
                method,
                backend_url,
                headers=headers,
                data=body
            )

            print("Received response from backend")

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                print(f"Backend {backend_port} failed")
                async with lock:
                    failed_requests[backend_port] += 10
                continue

            # drop content-length header
            response.headers.pop('content-length', None)
            # drop content-encoding header
            response.headers.pop('content-encoding', None)

            return HttpResponse(
                response.status_code,
                [(k.encode(), v.encode()) for k, v in response.headers.items()],
                text_writer(response.text)
            )
        except Exception as ex:
            print(f"Error contacting backend {backend_port}: {ex}")
            async with lock:
                failed_requests[backend_port] += 10
        finally:
            # Ensure the request count is decremented
            async with lock:
                request_counts[backend_port] -= 1
            # decrement failed_requests by 1 for all backends
            async with lock:
                for port in backends:
                    failed_requests[port] -= 1
                    failed_requests[port] = max(0, failed_requests[port])

    # If all backends fail, return a 502 Bad Gateway response
    return HttpResponse(
        502,
        [],
        text_writer("All backends are unavailable.")
    )

async def websocket_callback(request: WebSocketRequest) -> None:
    # reading the request
    path = path_from_request(request)
    query_string = query_string_from_request(request)
    headers = headers_from_request(request)

    web_socket = request.web_socket
    cookie = headers.get('cookie', None)
    session = session_from_cookie(cookie)

    if session:
        backend_port = websocket_affinity.get(session)
        if not backend_port: # this generally ends in disaster, though...
            sorted_backends = sorted(backends, key=lambda port: (failed_requests[port], request_counts[port]))
            backend_port = sorted_backends[0]
            websocket_affinity[session] = backend_port
    else:
        sorted_backends = sorted(backends, key=lambda port: (failed_requests[port], request_counts[port]))
        backend_port = sorted_backends[0]

    backend_url = f"ws://localhost:{backend_port}{path}?{query_string}"

    print(f"Forwarding websocket connection to backend: {backend_url}")

    headers_with_just_cookie = {'cookie': headers['cookie']}

    print("Headers used for websocket: ", headers_with_just_cookie)  

    await web_socket.accept()

    print("Websocket accepted")

    async with aconnect_ws(backend_url, client2, headers=headers_with_just_cookie) as ws:
        try:
            while True:
                print("...", end="", flush=True)
                async def receive_from_web_socket(web_socket):
                    data = await web_socket.receive()
                    return ('web_socket', data)

                async def receive_from_ws(ws):
                    data = await ws.receive()
                    return ('ws', data.data)

                task1 = asyncio.create_task(receive_from_web_socket(web_socket))
                task2 = asyncio.create_task(receive_from_ws(ws))
                
                done, pending = await asyncio.wait(
                    {task1, task2},
                    return_when=asyncio.FIRST_COMPLETED
                )

                for task in pending:
                    task.cancel()

                for task in done:
                    source, result = task.result()
                    if result is None:
                        return
                    if source == 'web_socket':
                        print("Srv <-- Cli", result)
                        await ws.send_text(result)
                    elif source == 'ws':
                        print("Srv --> Cli", result)
                        await web_socket.send(result)

        except Exception as error:
            print(error)

        await web_socket.close()

if __name__ == "__main__":
    app = Application()
    app.ws_router.add(
        '/_nicegui_ws/{full_path:path}',
        websocket_callback
    )
    app.http_router.add(
        {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'},
        '/{full_path:path}',
        http_request_callback
    )

    uvicorn.run(app, port=8000)