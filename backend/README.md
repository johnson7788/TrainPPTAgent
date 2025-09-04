# PPT生成的后端的代码

# 安装
pip install -r requirements.txt

# 运行
## 模拟接口（快速测试)
mock_api #模拟返回，只需要运行pyhton mock_main.py 即可，方便测试

## 更详细的启动说明
[启动说明.md](%E5%90%AF%E5%8A%A8%E8%AF%B4%E6%98%8E.md)

## 运行和前端通信的API
```
cd main_api/
python main.py
# 测试
python test_main.py
```

## 运行大纲生成
```
cd simpleOutline
python main_api.py
# 测试
python a2a_client.py
```

## 运行PPT生成
```mermaid
cd slide_agent
python main_api.py
# 测试
python a2a_client.py
```





