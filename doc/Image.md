# 图片的两种类型
背景图片，项目图片
背景图片： 装饰作用
项目图片： 配合显示有意义的内容。

# 背景图片
1. 目前通过模版中的显示，backend/main_api/template
2. 还可以通过搜索进行动态替换，参考backend/mock_api/mock_main.py和backend/slide_agent/slide_agent/sub_agents/ppt_writer/tools.py
3. 如果想要文生图，也可以改tools.py, 例如接google的 Nano Banana。

# 项目图片
1. 来自检索的内容，例如网络搜索（通过tools实现）或者文献上传时的图片（通过MinerU解析后，然后搜索后自动添加）
2. 显示的方式，参考backend/mock_api/mock_main.py