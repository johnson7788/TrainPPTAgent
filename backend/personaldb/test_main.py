
import os
import unittest
import time
import httpx
import asyncio
import json
from unittest.mock import patch, MagicMock, ANY
import pytest
from httpx import AsyncClient

class KnowledgeBaseTestCase(unittest.TestCase):
    """
    测试 FastAPI 接口
    """
    host = 'http://127.0.0.1'
    port = 9900
    env_host = os.environ.get('host')
    if env_host:
        host = env_host
    env_port = os.environ.get('port')
    if env_port:
        port = env_port
    base_url = f"{host}:{port}"

    def test_personal_db_search(self):
        """
        搜索知识库
        {'ids': [['987_20', '987_23', '987_24']], 'embeddings': None, 'documents': [['马斯克在第二季度财报电话会议中强调了这一点：“我们必须确保车辆完全在我们的控制下运行，这需要逐步推进。我们对安全保持极致审慎，但可以肯定的是，明年用户将能够自由增删其车辆在特斯拉车队中的使用权，尽管具体时间尚不确定。”', '特斯拉Robotaxi平台即将开放公众使用，预计明年全面普及', '特斯拉Robotaxi平台即将开放公众使用，预计明年全面普及']], 'uris': None, 'included': ['metadatas', 'documents', 'distances'], 'data': None, 'metadatas': [[{'folder_id': 543, 'file_id': 987, 'file_type': 'txt', 'user_id': 123456, 'url': ''}, {'user_id': 123456, 'folder_id': 543, 'file_id': 987, 'file_type': 'txt', 'url': ''}, {'url': '', 'file_id': 987, 'user_id': 123456, 'folder_id': 543, 'file_type': 'txt'}]], 'distances': [[1.2422254085540771, 1.2446644306182861, 1.2446644306182861]]}
        """
        url = f"{self.base_url}/search"
        # 正确的请求数据格式
        # data = {
        #     "userId": 123456,
        #     "query": "汽车",
        #     "keyword": "",
        #     "topk": 3
        # }
        data = {
            "userId": 23456,
            "query": "疾病",
            "keyword": "",
            "topk": 3
        }
        start_time = time.time()
        headers = {'content-type': 'application/json'}

        try:
            # 发送POST请求
            response = httpx.post(url, json=data, headers=headers, timeout=20.0)
            
            # 检查HTTP状态码
            response.raise_for_status()
            
            self.assertEqual(response.status_code, 200)
            
            # 解析返回的JSON数据
            result = response.json()
            
            # 验证返回结果的关键字段
            self.assertIn("documents", result)
            self.assertIn("ids", result)
            self.assertIn("distances", result)
            self.assertIn("metadatas", result)
            
            print("Response status:", response.status_code)
            print("Response body:", result)

        except httpx.RequestError as exc:
            self.fail(f"An error occurred while requesting {exc.request.url!r}: {exc}")
        except httpx.HTTPStatusError as exc:
            self.fail(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc.response.text}")

        print(f"ctest_personal_db_search测试花费时间: {time.time() - start_time}秒")
        print(f"调用的 server 是: {self.host}")

    def test_upload_file_and_vectorize(self):
        """
        测试上传文件并向量化
        """
        url = f"{self.base_url}/upload/"
        file_content = """特斯拉CEO埃隆·马斯克近日通过teslarati透露，特斯拉旗下的Robotaxi平台即将迎来重大进展，该平台将正式向公众开放服务，并计划在明年实现全面普及。

早在6月22日，特斯拉就在德克萨斯州奥斯汀启动了Robotaxi的小范围用户测试。随后，特斯拉不断扩大服务范围和用户规模，地理围栏的覆盖范围也在持续扩展。仅仅一个半月后，加州湾区也加入了测试行列。不过，值得注意的是，两地运营版本存在一些差异，奥斯汀的版本并未在驾驶座配备安全监控员，而加州湾区则配备了安全监控员。

随着测试的不断深入，越来越多的特斯拉用户开始期待收到平台使用权限的邀请邮件。马斯克在社交媒体上的一则消息让等待中的用户看到了曙光，他表示：“下个月，Robotaxi将开放公众使用权限。”这无疑为期待已久的用户们打了一剂强心针。

安全始终是特斯拉最为重视的方面，在Robotaxi平台的推广上也不例外。尽管特斯拉对平台能力和全自动驾驶套件充满信心，但一旦发生事故，自动驾驶的研发进程可能会受到严重挫折。因此，特斯拉在发放新用户邀请上表现得极为谨慎，以确保车辆完全在可控范围内运行。

马斯克在第二季度财报电话会议中强调了这一点：“我们必须确保车辆完全在我们的控制下运行，这需要逐步推进。我们对安全保持极致审慎，但可以肯定的是，明年用户将能够自由增删其车辆在特斯拉车队中的使用权，尽管具体时间尚不确定。”


特斯拉Robotaxi平台即将开放公众使用，预计明年全面普及
特斯拉Robotaxi平台即将开放公众使用，预计明年全面普及
尽管下个月Robotaxi平台将在奥斯汀和湾区全面开放服务，但特斯拉仍然重申，Robotaxi的全面普及将在明年实现。随着测试的不断深入和各方面的逐步完善，奥斯汀和湾区的地理围栏将持续扩展，以覆盖更多的区域和用户。

对于特斯拉来说，Robotaxi平台的开放不仅意味着技术的进一步成熟和普及，更是对未来出行方式的一次重要探索。随着越来越多的用户加入测试行列，特斯拉将不断收集数据、优化算法，为未来的全面普及奠定坚实的基础。"""
        file_name = "tesla.txt"

        data = {
            "userId": 123456,
            "fileId": 987,
            "folderId": 543,
            "fileType": "txt"
        }
        files = {"file": (file_name, file_content, "text/plain")}

        try:
            # 注意: 这个测试需要FastAPI服务正在运行，并且设置了ALI_API_KEY环境变量
            start_time = time.time()
            response = httpx.post(url, data=data, files=files, timeout=40.0)

            print(f"test_upload_file_and_vectorize 请求花费时间: {time.time() - start_time}秒")

            response.raise_for_status()

            self.assertEqual(response.status_code, 200)
            result = response.json()
            self.assertEqual(result['id'], 987)
            self.assertEqual(result['userId'], 123456)
            self.assertIn('embedding_result', result)

            print("Response status:", response.status_code)
            print("Response body:", result)

        except httpx.RequestError as exc:
            self.fail(f"An error occurred while requesting {exc.request.url!r}: {exc}")
        except httpx.HTTPStatusError as exc:
            self.fail(
                f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc.response.text}")