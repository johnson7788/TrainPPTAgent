# 个人知识库处理逻辑
1. 使用MinerU处理pdf，其它文件使用markitdown处理。
2. 输出的Markdown格式进行Trunk，然后对Trunk进行进行向量化。
3. 使用[embedding_utils.py](embedding_utils.py)生成embedding向量

# 运行
python main.py

#FastAPI Web 服务（端口 9900） → 接收 HTTP 请求



