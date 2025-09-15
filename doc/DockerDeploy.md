# Docker部署说明，主要是容器服务之间如何调用
如果你的文件所有容器是共享网络，需要进行更改network_mode和设置共同网络，那么每个容器之间可以使用容器名进行访问。
[docker-compose.yml](..%2Fdocker-compose.yml)

# 如果你的容器是使用的宿主机的网络，那么你应该配置simpleOutline和slide_agent中的Dockerfile
启动时，分别加上CMD ["python", "main_api.py", "--host", "0.0.0.0", "--port", "10001", "--agent_url", "http://xxxx:10011"]的agent url改为宿主机的ip和端口
同时修改main_api/.env中的为宿主机的ip
OUTLINE_API=http://xxx:10001
CONTENT_API=http://xxxx:10011