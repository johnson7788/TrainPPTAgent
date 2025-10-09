# 如何制作模版
- Step1: 部署前端，完成后访问 http://127.0.0.1:5173/editor
- Step2: 点击左上角导入json,或者已有的PPT文件都可以（自己的公司的或者个人学习任何已有pptx文件)
![template_import.png](template_import.png)
- Step3: 点击幻灯片类型标注
![template_label.png](template_label.png)
- Step4: 开始标注
![template_label_detail.png](template_label_detail.png)
- Step5: 标注完成后点击左上角菜单，导出成JSON文件
![export_template_json.png](export_template_json.png)
- Step6: 拷贝JSON文件到template目录下，并修改文件名
- Step7: 修改前端代码frontend/src/store/slides.ts，添加一个你自定义的模版
```
    templates: [
      { name: '红色通用', id: 'template_1', cover: '/api/data/template_1.jpg' },
      { name: '蓝色通用', id: 'template_2', cover: '/api/data/template_2.jpg' },
      { name: '紫色通用', id: 'template_3', cover: '/api/data/template_3.jpg' },
      { name: '莫兰迪配色', id: 'template_4', cover: '/api/data/template_4.jpg' },
    ], // 模板
```