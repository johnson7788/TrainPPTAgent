# PPT生成的后端的代码

# 安装
pip install -r requirements.txt

# 运行
## 模拟接口（快速测试)
mock_api #模拟返回，只需要运行pyhton mock_main.py 即可，方便测试

## 运行和前端通信的API
```
cd main_api/
python main.py
```

## 运行大纲生成
```
cd simpleOutline
python main_api.py
```

## 运行PPT生成
```mermaid
cd slide_agent
python main_api.py
```





