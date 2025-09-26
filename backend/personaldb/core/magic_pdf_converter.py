"""
Magic-PDF转换器 - 本地高质量PDF转Markdown转换
基于 mineru 库实现
"""

import copy
import json
import logging
import os
import tempfile
import shutil
from typing import Tuple, Optional, Dict, Any, List
from pathlib import Path

from loguru import logger as loguru_logger

logger = logging.getLogger(__name__)


class MagicPDFConverter:
    """
    Magic-PDF转换器，使用mineru库进行本地PDF转Markdown转换

    mineru是一个强大的本地PDF处理库，提供：
    - 高质量的PDF解析
    - OCR文字识别
    - 布局分析
    - 表格和图片提取
    - 公式识别
    - 多种后端支持（pipeline, vlm等）
    - 本地处理，无需网络
    """

    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化Magic-PDF转换器

        Args:
            output_dir: 输出目录，如果为None则使用临时目录
        """
        self.output_dir = output_dir or tempfile.mkdtemp(prefix="magic_pdf_")
        self._is_available = None

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"Mineru转换器初始化，输出目录: {self.output_dir}")
    
    def is_available(self) -> bool:
        """检查mineru是否可用"""
        if self._is_available is None:
            try:
                from mineru.cli.common import convert_pdf_bytes_to_bytes_by_pypdfium2, prepare_env, read_fn
                from mineru.data.data_reader_writer import FileBasedDataWriter
                from mineru.utils.enum_class import MakeMode
                from mineru.backend.pipeline.pipeline_analyze import doc_analyze as pipeline_doc_analyze
                from mineru.backend.pipeline.pipeline_middle_json_mkcontent import union_make as pipeline_union_make
                from mineru.backend.pipeline.model_json_to_middle_json import result_to_middle_json as pipeline_result_to_middle_json

                self._is_available = True
                logger.info("Mineru库检查成功")
            except ImportError as e:
                self._is_available = False
                logger.warning(f"Mineru库未安装: {e}")

        return self._is_available
    
    def convert_pdf_file(self, file_path: str,
                        lang: str = "ch",
                        backend: str = "pipeline",
                        method: str = "auto",
                        formula_enable: bool = True,
                        table_enable: bool = True) -> Tuple[str, str]:
        """
        转换PDF文件为Markdown

        Args:
            file_path: PDF文件路径
            lang: 语言选项，默认'ch'，可选值包括['ch', 'ch_server', 'ch_lite', 'en', 'korean', 'japan', 'chinese_cht', 'ta', 'te', 'ka']
            backend: 解析后端，默认'pipeline'，可选值包括['pipeline', 'vlm-transformers', 'vlm-sglang-engine', 'vlm-sglang-client']
            method: 解析方法，默认'auto'，可选值包括['auto', 'txt', 'ocr']
            formula_enable: 是否启用公式解析
            table_enable: 是否启用表格解析

        Returns:
            (转换后的Markdown内容, 编码)

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 转换失败
            ImportError: mineru库未安装
        """
        if not self.is_available():
            raise ImportError(
                "mineru库未安装。请安装: pip install mineru 或参考官方文档"
            )

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if not path.suffix.lower() == '.pdf':
            raise ValueError(f"不支持的文件格式: {path.suffix}")

        logger.info(f"开始使用Mineru转换文件: {file_path}")

        try:
            # 导入必要的模块
            from mineru.cli.common import convert_pdf_bytes_to_bytes_by_pypdfium2, prepare_env, read_fn
            from mineru.data.data_reader_writer import FileBasedDataWriter
            from mineru.utils.enum_class import MakeMode
            from mineru.backend.pipeline.pipeline_analyze import doc_analyze as pipeline_doc_analyze
            from mineru.backend.pipeline.pipeline_middle_json_mkcontent import union_make as pipeline_union_make
            from mineru.backend.pipeline.model_json_to_middle_json import result_to_middle_json as pipeline_result_to_middle_json

            # 准备文件名和目录
            pdf_file_name = str(path.absolute())
            name_without_suff = path.stem

            # 读取PDF文件
            pdf_bytes = read_fn(path)

            # 准备输出目录
            local_image_dir, local_md_dir = prepare_env(self.output_dir, name_without_suff, method)
            image_dir = os.path.basename(local_image_dir)

            # 创建数据写入器
            image_writer = FileBasedDataWriter(local_image_dir)
            md_writer = FileBasedDataWriter(local_md_dir)

            # 使用pipeline后端进行处理
            if backend == "pipeline":
                # 转换PDF字节
                new_pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(pdf_bytes, 0, None)

                # 进行文档分析
                infer_results, all_image_lists, all_pdf_docs, lang_list, ocr_enabled_list = pipeline_doc_analyze(
                    [new_pdf_bytes], [lang],
                    parse_method=method,
                    formula_enable=formula_enable,
                    table_enable=table_enable
                )

                # 处理结果
                model_list = infer_results[0]
                model_json = copy.deepcopy(model_list)
                images_list = all_image_lists[0]
                pdf_doc = all_pdf_docs[0]
                _lang = lang_list[0]
                _ocr_enable = ocr_enabled_list[0]

                # 转换为中间JSON格式
                middle_json = pipeline_result_to_middle_json(
                    model_list, images_list, pdf_doc, image_writer,
                    _lang, _ocr_enable, formula_enable
                )

                pdf_info = middle_json["pdf_info"]

                # 生成调试文件（可选）
                try:
                    from mineru.utils.draw_bbox import draw_layout_bbox, draw_span_bbox

                    # 绘制布局边界框
                    draw_layout_bbox(pdf_info, new_pdf_bytes, local_md_dir, f"{name_without_suff}_layout.pdf")

                    # 绘制span边界框
                    draw_span_bbox(pdf_info, new_pdf_bytes, local_md_dir, f"{name_without_suff}_span.pdf")

                    logger.debug(f"调试文件已生成: {local_md_dir}")
                except Exception as e:
                    logger.warning(f"生成调试文件失败: {e}")

                # 保存原始PDF
                try:
                    md_writer.write(f"{name_without_suff}_origin.pdf", new_pdf_bytes)
                except Exception as e:
                    logger.warning(f"保存原始PDF失败: {e}")

                # 生成Markdown内容
                md_content = pipeline_union_make(pdf_info, MakeMode.MM_MD, image_dir)

                # 保存Markdown文件
                md_writer.write_string(f"{name_without_suff}.md", md_content)

                # 保存内容列表（JSON格式）
                try:
                    content_list = pipeline_union_make(pdf_info, MakeMode.CONTENT_LIST, image_dir)
                    md_writer.write_string(
                        f"{name_without_suff}_content_list.json",
                        json.dumps(content_list, ensure_ascii=False, indent=4)
                    )

                    # 保存中间JSON
                    md_writer.write_string(
                        f"{name_without_suff}_middle.json",
                        json.dumps(middle_json, ensure_ascii=False, indent=4)
                    )

                    # 保存模型输出JSON
                    md_writer.write_string(
                        f"{name_without_suff}_model.json",
                        json.dumps(model_json, ensure_ascii=False, indent=4)
                    )

                    logger.debug(f"额外文件已保存: content_list.json, middle.json, model.json")
                except Exception as e:
                    logger.warning(f"保存额外文件失败: {e}")

            else:
                raise ValueError(f"不支持的后端: {backend}")

            if not md_content or not md_content.strip():
                raise ValueError("Mineru转换结果为空")

            logger.info(f"Mineru转换成功，内容长度: {len(md_content)} 字符")
            return md_content, "utf-8"

        except Exception as e:
            logger.error(f"Mineru转换失败: {e}")
            raise ValueError(f"Mineru转换失败: {e}")

    def get_conversion_info(self, file_path: str) -> Dict[str, Any]:
        """
        获取转换信息（不执行实际转换）

        Args:
            file_path: PDF文件路径

        Returns:
            转换信息字典
        """
        if not self.is_available():
            return {"available": False, "error": "mineru库未安装"}

        path = Path(file_path)
        if not path.exists():
            return {"available": False, "error": f"文件不存在: {file_path}"}

        try:
            from mineru.cli.common import read_fn

            # 读取PDF文件
            pdf_bytes = read_fn(path)

            return {
                "available": True,
                "file_path": str(path.absolute()),
                "file_size": path.stat().st_size,
                "pdf_type": "auto",  # mineru会自动检测
                "recommended_ocr": True,  # 默认推荐OCR
                "output_dir": self.output_dir,
                "supported_backends": ["pipeline", "vlm-transformers", "vlm-sglang-engine", "vlm-sglang-client"],
                "supported_methods": ["auto", "txt", "ocr"],
                "supported_languages": ["ch", "ch_server", "ch_lite", "en", "korean", "japan", "chinese_cht", "ta", "te", "ka"]
            }

        except Exception as e:
            return {"available": False, "error": str(e)}

    def parse_documents(self,
                       path_list: List[Path],
                       lang: str = "ch",
                       backend: str = "pipeline",
                       method: str = "auto",
                       server_url: Optional[str] = None,
                       start_page_id: int = 0,
                       end_page_id: Optional[int] = None) -> List[Tuple[str, str]]:
        """
        批量解析多个文档

        Args:
            path_list: 文档路径列表，可以是PDF或图片文件
            lang: 语言选项，默认'ch'
            backend: 解析后端
            method: 解析方法
            server_url: 当backend为sglang-client时需要指定服务器URL
            start_page_id: 开始页面ID，默认0
            end_page_id: 结束页面ID，默认None（解析到文档末尾）

        Returns:
            (Markdown内容, 编码) 的列表
        """
        if not self.is_available():
            raise ImportError("mineru库未安装")

        results = []
        for path in path_list:
            try:
                md_content, encoding = self.convert_pdf_file(
                    str(path), lang=lang, backend=backend, method=method
                )
                results.append((md_content, encoding))
                logger.info(f"成功处理文档: {path}")
            except Exception as e:
                logger.error(f"处理文档失败 {path}: {e}")
                results.append(("", "utf-8"))  # 失败时返回空内容

        return results

    def cleanup(self):
        """清理临时文件"""
        if self.output_dir and os.path.exists(self.output_dir):
            try:
                # 只清理临时目录
                if "magic_pdf_" in self.output_dir:
                    shutil.rmtree(self.output_dir)
                    logger.info(f"已清理临时目录: {self.output_dir}")
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")

    def get_output_files(self, file_path: str, method: str = "auto") -> Dict[str, str]:
        """
        获取输出文件路径

        Args:
            file_path: 原始PDF文件路径
            method: 解析方法，用于确定输出目录结构

        Returns:
            输出文件路径字典
        """
        name_without_suff = Path(file_path).stem

        # 根据method确定输出目录结构
        if method in ["auto", "txt", "ocr"]:
            method_dir = os.path.join(self.output_dir, name_without_suff, method)
        else:
            method_dir = os.path.join(self.output_dir, name_without_suff)

        return {
            "markdown": os.path.join(method_dir, f"{name_without_suff}.md"),
            "content_list": os.path.join(method_dir, f"{name_without_suff}_content_list.json"),
            "middle_json": os.path.join(method_dir, f"{name_without_suff}_middle.json"),
            "model_json": os.path.join(method_dir, f"{name_without_suff}_model.json"),
            "origin_pdf": os.path.join(method_dir, f"{name_without_suff}_origin.pdf"),
            "layout_pdf": os.path.join(method_dir, f"{name_without_suff}_layout.pdf"),
            "span_pdf": os.path.join(method_dir, f"{name_without_suff}_span.pdf"),
            "images_dir": os.path.join(method_dir, "images")
        }
    
    def __del__(self):
        """析构函数，自动清理临时文件"""
        self.cleanup()


def parse_doc(path_list: List[Path],
              output_dir: str,
              lang: str = "ch",
              backend: str = "pipeline",
              method: str = "auto",
              server_url: Optional[str] = None,
              start_page_id: int = 0,
              end_page_id: Optional[int] = None) -> None:
    """
    便利函数：解析文档列表，兼容参考代码的API

    Args:
        path_list: 文档路径列表，可以是PDF或图片文件
        output_dir: 输出目录
        lang: 语言选项，默认'ch'，可选值包括['ch', 'ch_server', 'ch_lite', 'en', 'korean', 'japan', 'chinese_cht', 'ta', 'te', 'ka']
        backend: 解析后端，可选值：
            pipeline: 更通用
            vlm-transformers: 更通用
            vlm-sglang-engine: 更快（引擎）
            vlm-sglang-client: 更快（客户端）
        method: 解析方法，可选值：
            auto: 根据文件类型自动确定方法
            txt: 使用文本提取方法
            ocr: 对基于图像的PDF使用OCR方法
        server_url: 当backend为sglang-client时需要指定服务器URL，例如：http://127.0.0.1:30000
        start_page_id: 开始页面ID，默认0
        end_page_id: 结束页面ID，默认None（解析到文档末尾）
    """
    try:
        # 创建转换器实例
        converter = MagicPDFConverter(output_dir=output_dir)

        # 检查可用性
        if not converter.is_available():
            raise ImportError("mineru库未安装。请安装: pip install mineru")

        # 处理每个文件
        for path in path_list:
            try:
                file_name = str(Path(path).stem)
                logger.info(f"开始处理文件: {path}")

                # 转换文件
                md_content, encoding = converter.convert_pdf_file(
                    str(path),
                    lang=lang,
                    backend=backend,
                    method=method
                )

                logger.info(f"成功处理文件: {path}, 输出目录: {output_dir}")

            except Exception as e:
                logger.error(f"处理文件失败 {path}: {e}")

    except Exception as e:
        logger.error(f"批量处理失败: {e}")
        raise
