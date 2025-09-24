# 个人知识库处理逻辑
1. 写一个单独的fastapi服务监听RabbitMQ的Channel，监听要处理的文件。用户ID和文件ID。[main.py](main.py).
2. 下载七牛上的文件，并读取文件。
3. 使用[read_all_files.py](read_all_files.py)读取文件，PDF，PPT，PPTX，DOC，DOCX，TXT（可以自行更换其它方式）
4. 使用[embedding_utils.py](embedding_utils.py)生成embedding向量
5. MCP工具


# 只需读Channel，不需要写回。
person_db_question

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py

# 
FastAPI Web 服务（端口 9900） → 接收 HTTP 请求
RabbitMQ 消费者 → 从队列读取任务


# 消息队列文档

## 添加文件 updateOrSave

```json
{
    "message": {
        "id": 72, ##文件id
        "userId": 1101712, ##用户id
        "createdTime": "2025-08-12 13:34:20",
        "modifiedTime": null,
        "fileKey": null,
        "fileSize": 123456,
        "fileType": "image",
        "name": "张三5.png",
        "url": "https://www.bing.com/img/newLog1o.0f45b6bb.png", ##文件地址
        "folderId": 2
    },
    "type": "updateOrSave"
}
```


## 移动文件 moveFiles
```json
{
    "message": {
        "pageNum": 1,
        "pageSize": 10,
        "sort": null,
        "order": null,
        "notConvert": null,
        "userId": 1101712, ##用户id
        "fileType": null,
        "name": null,
        "folderId": 3, ##文件夹id
        "ids": [ ##需要移动的文件ids
            72
        ]
    },
    "type": "moveFiles"
}
```

## 删除文件 removeById
```json
{
    "message": {
        "pageNum": 1,
        "pageSize": 10,
        "sort": null,
        "order": null,
        "notConvert": null,
        "userId": 1101712, ##用户id
        "fileType": null,
        "name": null,
        "folderId": null,
        "ids": [ ##需要删除的文件ids
            72
        ]
    },
    "type": "removeById"
}
```

删除文件夹下所有文件 

```json
{
    "message": {
        "userId": 1101712, ##用户id
        "folderId": 3 ##文件夹id
    },
    "type": "removeByFolderId"
}
```




