import asyncio
import aiohttp
from collections import Counter
import matplotlib.pyplot as plt

# Function to send a request
async def fetch(session, url):
    async with session.get(url) as response:
        return response.headers

# Main function to send requests in parallel
async def main():
    url = 'http://127.0.0.1:8000/'
    responses = []

    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for _ in range(100)]
        responses = await asyncio.gather(*tasks)

    return responses

# Function to plot the responses
def plot_responses(responses):
    print(responses)
    ports = [int(resp['X-PORT']) for resp in responses]
    port_counts = Counter(ports)

    labels = port_counts.keys()
    sizes = port_counts.values()

    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
    plt.title('Port Distribution of Responses')
    plt.axis('equal')
    plt.show()

# Entry point
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    responses = loop.run_until_complete(main())
    plot_responses(responses)