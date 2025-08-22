import os
import unittest
import time
import httpx
import asyncio
import json
import pytest
from httpx import AsyncClient

class PPTBaseTestCase(unittest.TestCase):
    """
    Test FastAPI interface
    """
    host = 'http://127.0.0.1'
    port = 6800
    env_host = os.environ.get('host')
    if env_host:
        host = env_host
    env_port = os.environ.get('port')
    if env_port:
        port = env_port
    base_url = f"{host}:{port}"

    def test_generate_outline_stream(self):
        """
        Test generating an outline with streaming
        """
        url = f"{self.base_url}/tools/aippt_outline"
        data = {
            "content": "2025 tech trends",
            "language": "en",
            "model": "gpt-4",
            "stream": True
        }
        start_time = time.time()
        headers = {'content-type': 'application/json'}
        with httpx.stream("POST", url, json=data, headers=headers, timeout=None) as response:
            self.assertEqual(response.status_code, 200, "aippt_outline stream endpoint should return 200")
            response_text = ""
            for chunk in response.iter_text():
                response_text += chunk
            self.assertIn("2025科技前沿动态", response_text)
        print(f"outline: {response_text}")
        print(f"Outline stream test took: {time.time() - start_time}s")
        print(f"Server called: {self.host}")

    async def test_generate_outline_no_stream(self):
        """
        Test generating an outline without streaming
        """
        url = f"{self.base_url}/tools/aippt_outline"
        data = {
            "content": "2025 tech trends",
            "language": "en",
            "model": "gpt-4",
            "stream": False
        }
        start_time = time.time()
        headers = {'content-type': 'application/json'}
        response_data = []
        async with AsyncClient() as client:
            async with client.stream("POST", url, json=data, headers=headers, timeout=None) as response:
                assert response.status_code == 200, "aippt content endpoint should return 200"
                async for line in response.aiter_lines():
                    if line:
                        try:
                            json_object = json.loads(line)
                            print(f"PPT content chunk: {json_object}")
                            assert "type" in json_object
                            assert "data" in json_object
                            response_data.append(json_object)
                        except json.JSONDecodeError:
                            pytest.fail(f"Failed to decode JSON line: {line}")
        print(f"content: {response_data}")
        print(f"Outline no-stream test took: {time.time() - start_time}s")
        print(f"Server called: {self.host}")

if __name__ == "__main__":
    unittest.main()