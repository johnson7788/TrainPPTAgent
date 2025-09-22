#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TrainPPTAgent 生产环境一键启动脚本
支持前端构建、后端服务启动、进程管理和监控
"""

import os
import sys
import time
import signal
import subprocess
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import threading
import http.server
import socketserver
from dotenv import load_dotenv

class ProductionStarter:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backend_dir = self.project_root / 'backend'
        self.frontend_dir = self.project_root / 'frontend'
        self.dist_dir = self.frontend_dir / 'dist'
        self.logs_dir = self.project_root / 'logs'

        # 加载环境配置
        env_file = self.project_root / '.env'
        if env_file.exists():
            load_dotenv(env_file)

        self.services = {
            'main_api': {
                'port': int(os.environ.get('MAIN_API_PORT', '6800')),
                'dir': self.backend_dir / 'main_api',
                'script': 'main.py',
                'name': '主API服务'
            },
            'outline': {
                'port': int(os.environ.get('OUTLINE_API_PORT', '10001')),
                'dir': self.backend_dir / 'simpleOutline',
                'script': 'main_api.py',
                'name': '大纲生成服务'
            },
            'content': {
                'port': int(os.environ.get('CONTENT_API_PORT', '10011')),
                'dir': self.backend_dir / 'slide_agent',
                'script': 'main_api.py',
                'name': '内容生成服务'
            }
        }

        self.frontend_port = int(os.environ.get('FRONTEND_PORT', '5173'))
        self.host = os.environ.get('HOST', '0.0.0.0')
        self.processes: Dict[str, subprocess.Popen] = {}
        self.frontend_server = None

    def setup_logging(self):
        """设置日志系统"""
        self.logs_dir.mkdir(exist_ok=True)

        log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(self.logs_dir / 'production.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('ProductionStarter')

    def print_banner(self):
        """打印启动横幅"""
        banner = f"""
{'='*80}
🚀 TrainPPTAgent 生产环境启动器
{'='*80}
📅 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🏠 项目目录: {self.project_root}
🌐 服务地址: {self.host}
📝 日志目录: {self.logs_dir}
{'='*80}
        """
        print(banner)
        self.logger.info("启动生产环境部署")

    def check_environment(self):
        """检查环境依赖"""
        self.logger.info("检查环境依赖...")

        # 检查Python版本
        if sys.version_info < (3, 8):
            self.logger.error("需要Python 3.8或更高版本")
            sys.exit(1)

        # 检查Node.js
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            self.logger.info(f"Node.js版本: {result.stdout.strip()}")
        except FileNotFoundError:
            self.logger.error("未找到Node.js，请先安装Node.js")
            sys.exit(1)

        # 检查项目结构
        if not self.backend_dir.exists():
            self.logger.error(f"后端目录不存在: {self.backend_dir}")
            sys.exit(1)

        if not self.frontend_dir.exists():
            self.logger.error(f"前端目录不存在: {self.frontend_dir}")
            sys.exit(1)

        self.logger.info("✅ 环境检查通过")

    def install_dependencies(self):
        """安装依赖"""
        self.logger.info("安装项目依赖...")

        # 安装后端依赖
        requirements_file = self.backend_dir / 'requirements.txt'
        if requirements_file.exists():
            self.logger.info("安装Python依赖...")
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file),
                '-i', 'https://mirrors.aliyun.com/pypi/simple/'
            ], check=True)

        # 安装前端依赖
        package_json = self.frontend_dir / 'package.json'
        if package_json.exists():
            self.logger.info("安装前端依赖...")
            subprocess.run(['npm', 'install'], cwd=self.frontend_dir, check=True)

        self.logger.info("✅ 依赖安装完成")

    def build_frontend(self):
        """构建前端"""
        self.logger.info("构建前端项目...")

        try:
            # 清理旧的构建文件
            if self.dist_dir.exists():
                shutil.rmtree(self.dist_dir)

            # 执行构建
            result = subprocess.run(
                ['npm', 'run', 'build'],
                cwd=self.frontend_dir,
                capture_output=True,
                text=True,
                check=True
            )

            if not self.dist_dir.exists():
                raise Exception("构建完成但未找到dist目录")

            self.logger.info("✅ 前端构建完成")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"前端构建失败: {e}")
            self.logger.error(f"错误输出: {e.stderr}")
            sys.exit(1)

    def check_ports(self):
        """检查端口占用"""
        import socket

        all_ports = [service['port'] for service in self.services.values()]
        all_ports.append(self.frontend_port)

        occupied_ports = []
        for port in all_ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    if s.connect_ex(('localhost', port)) == 0:
                        occupied_ports.append(port)
            except Exception:
                pass

        if occupied_ports:
            self.logger.warning(f"发现端口占用: {occupied_ports}")
            response = input("是否清理这些端口? (y/N): ").strip().lower()
            if response == 'y':
                self.kill_processes_on_ports(occupied_ports)
            else:
                self.logger.error("端口被占用，无法启动服务")
                sys.exit(1)

    def kill_processes_on_ports(self, ports: List[int]):
        """清理占用端口的进程"""
        try:
            import psutil
            killed_count = 0

            for port in ports:
                for proc in psutil.process_iter(['pid', 'name', 'connections']):
                    try:
                        connections = proc.info['connections']
                        if connections:
                            for conn in connections:
                                if hasattr(conn, 'laddr') and conn.laddr.port == port:
                                    self.logger.info(f"终止进程 {proc.info['name']} (PID: {proc.info['pid']}) 占用端口 {port}")
                                    proc.terminate()
                                    proc.wait(timeout=5)
                                    killed_count += 1
                                    break
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                        continue

            self.logger.info(f"清理完成，终止了 {killed_count} 个进程")
            time.sleep(2)

        except ImportError:
            self.logger.warning("未安装psutil，跳过进程清理")

    def start_backend_service(self, service_name: str, config: Dict) -> Optional[subprocess.Popen]:
        """启动后端服务"""
        service_dir = config['dir']
        script = config['script']
        port = config['port']
        name = config['name']

        self.logger.info(f"启动{name} (端口: {port})")

        try:
            log_file = self.logs_dir / f"{service_name}.log"

            with open(log_file, 'w', encoding='utf-8') as log_f:
                process = subprocess.Popen(
                    [sys.executable, script],
                    cwd=service_dir,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    text=True
                )

                # 等待服务启动
                time.sleep(3)

                if process.poll() is None:
                    self.logger.info(f"✅ {name}启动成功 (PID: {process.pid})")
                    return process
                else:
                    self.logger.error(f"❌ {name}启动失败，查看日志: {log_file}")
                    return None

        except Exception as e:
            self.logger.error(f"启动{name}时出错: {e}")
            return None

    def start_frontend_server(self):
        """启动前端静态文件服务"""
        self.logger.info(f"启动前端服务 (端口: {self.frontend_port})")

        # 创建一个闭包来传递dist_dir
        dist_dir = self.dist_dir

        class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(dist_dir), **kwargs)

            def end_headers(self):
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                super().end_headers()

            def do_GET(self):
                # 处理SPA路由，将所有非文件请求重定向到index.html
                if self.path != '/' and not self.path.startswith('/assets/') and '.' not in self.path:
                    self.path = '/index.html'
                return super().do_GET()

        def run_server():
            try:
                # 设置工作目录到dist目录
                os.chdir(dist_dir)

                with socketserver.TCPServer((self.host, self.frontend_port), CustomHTTPRequestHandler) as httpd:
                    self.frontend_server = httpd
                    self.logger.info(f"✅ 前端服务启动成功")
                    httpd.serve_forever()
            except Exception as e:
                self.logger.error(f"前端服务启动失败: {e}")
            finally:
                # 恢复工作目录
                os.chdir(self.project_root)

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        time.sleep(2)

    def start_all_services(self):
        """启动所有服务"""
        self.logger.info("启动所有服务...")

        # 启动后端服务
        for service_name, config in self.services.items():
            process = self.start_backend_service(service_name, config)
            if process:
                self.processes[service_name] = process
            else:
                self.logger.error(f"服务 {config['name']} 启动失败，停止所有服务")
                self.stop_all_services()
                sys.exit(1)

        # 启动前端服务
        self.start_frontend_server()

        # 显示服务状态
        self.show_service_status()

    def show_service_status(self):
        """显示服务状态"""
        print("\\n" + "="*80)
        print("🎉 所有服务启动成功!")
        print("="*80)
        print("📋 服务状态:")

        for service_name, config in self.services.items():
            if service_name in self.processes:
                print(f"  ✅ {config['name']}: http://{self.host}:{config['port']}")

        print(f"  ✅ 前端界面: http://{self.host}:{self.frontend_port}")
        print(f"  📝 日志目录: {self.logs_dir}")

        print("\\n💡 使用说明:")
        print("  - 按 Ctrl+C 停止所有服务")
        print("  - 在浏览器中访问前端界面开始使用")
        print("  - 服务日志保存在 logs/ 目录中")
        print("="*80)

    def monitor_services(self):
        """监控服务状态"""
        try:
            while self.processes:
                for service_name, process in list(self.processes.items()):
                    if process.poll() is not None:
                        self.logger.warning(f"服务 {service_name} 已停止")
                        del self.processes[service_name]
                time.sleep(5)
        except KeyboardInterrupt:
            self.logger.info("收到停止信号，正在关闭所有服务...")
            self.stop_all_services()

    def stop_all_services(self):
        """停止所有服务"""
        self.logger.info("停止所有服务...")

        # 停止后端服务
        for service_name, process in self.processes.items():
            try:
                self.logger.info(f"停止服务: {service_name}")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.logger.warning(f"强制终止服务: {service_name}")
                process.kill()
            except Exception as e:
                self.logger.error(f"停止服务 {service_name} 时出错: {e}")

        # 停止前端服务
        if self.frontend_server:
            try:
                self.frontend_server.shutdown()
            except Exception as e:
                self.logger.error(f"停止前端服务时出错: {e}")

        self.processes.clear()
        self.logger.info("✅ 所有服务已停止")

    def run(self):
        """主运行函数"""
        self.setup_logging()
        self.print_banner()

        # 环境检查
        self.check_environment()

        # 安装依赖
        self.install_dependencies()

        # 构建前端
        self.build_frontend()

        # 检查端口
        self.check_ports()

        # 启动所有服务
        self.start_all_services()

        # 监控服务
        self.monitor_services()

def main():
    """主函数"""
    starter = ProductionStarter()

    # 注册信号处理器
    def signal_handler(signum, frame):
        print("\\n🛑 收到信号，正在停止服务...")
        starter.stop_all_services()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        starter.run()
    except KeyboardInterrupt:
        print("\\n🛑 用户中断")
        starter.stop_all_services()
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        starter.stop_all_services()
        sys.exit(1)

if __name__ == "__main__":
    main()