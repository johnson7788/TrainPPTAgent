#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TrainPPTAgent dev环境一键启动脚本，生产环境需要使用npm run build或者docker
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
import glob
import itertools

# -----------------------------
#多文件 tail -f 的实现
# -----------------------------
class MultiLogTailer:
    """
    在同一控制台跟随打印 logs/*.log 的新增内容，行为类似 `tail -f`.
    - 自动发现新文件
    - 每行带文件名前缀
    - 可优雅停止
    """
    COLORS = [
        "\033[95m", "\033[94m", "\033[96m", "\033[92m",
        "\033[93m", "\033[91m", "\033[90m"
    ]
    RESET = "\033[0m"

    def __init__(self, logs_dir: Path, pattern: str = "*.log", poll_interval: float = 1.0, color: bool = True):
        self.logs_dir = Path(logs_dir)
        self.pattern = pattern
        self.poll_interval = poll_interval
        self.stop_event = threading.Event()
        self.threads: Dict[Path, threading.Thread] = {}
        self.opened: Dict[Path, 'io.TextIOWrapper'] = {}
        self._color = color and sys.stdout.isatty()
        self._color_map: Dict[Path, str] = {}

    def _color_for(self, path: Path) -> str:
        if not self._color:
            return ""
        if path not in self._color_map:
            idx = len(self._color_map) % len(self.COLORS)
            self._color_map[path] = self.COLORS[idx]
        return self._color_map[path]

    def _prefix(self, path: Path) -> str:
        color = self._color_for(path)
        name = path.name
        return f"{color}[{name}]{self.RESET if color else ''} "

    def _tail_file(self, path: Path):
        try:
            f = open(path, "r", encoding="utf-8", errors="ignore")
            self.opened[path] = f
            # 定位到文件末尾，仅读取新增
            f.seek(0, os.SEEK_END)
            while not self.stop_event.is_set():
                line = f.readline()
                if line:
                    # 去掉末尾多余换行后打印
                    if line.endswith("\n"):
                        line = line[:-1]
                    print(self._prefix(path) + line, flush=True)
                else:
                    # 文件可能被轮转/截断，尝试刷新并等待
                    if not path.exists():
                        # 若被轮转导致路径不存在，稍等后退出当前线程，等待主 watcher 重新发现新文件
                        break
                    time.sleep(0.1)
        except Exception as e:
            print(f"[LogTailer] 打开/读取日志失败: {path} -> {e}", flush=True)
        finally:
            try:
                f = self.opened.pop(path, None)
                if f:
                    f.close()
            except Exception:
                pass
            # 线程退出时从线程表删除
            self.threads.pop(path, None)

    def _spawn_tail_thread(self, path: Path):
        if path in self.threads:
            return
        t = threading.Thread(target=self._tail_file, args=(path,), daemon=True)
        self.threads[path] = t
        t.start()

    def _watcher(self):
        # 主 watcher：定期扫描新文件
        while not self.stop_event.is_set():
            try:
                self.logs_dir.mkdir(exist_ok=True)
                matches = [Path(p) for p in glob.glob(str(self.logs_dir / self.pattern))]
                # 启动新出现的文件
                for p in matches:
                    if p.is_file() and p not in self.threads:
                        self._spawn_tail_thread(p)
                # 清理已消失的文件对应线程（线程在文件消失时会自行退出）
                for p in list(self.threads.keys()):
                    if not p.exists():
                        # 线程会在读取时自行退出，这里不强杀
                        pass
            except Exception as e:
                print(f"[LogTailer] 目录扫描失败: {e}", flush=True)
            finally:
                time.sleep(self.poll_interval)

    def start(self):
        # 先对当前存在的文件起 tail
        initial = [Path(p) for p in glob.glob(str(self.logs_dir / self.pattern))]
        for p in sorted(initial):
            if p.is_file():
                self._spawn_tail_thread(p)
        # 再起 watcher
        self.watcher_thread = threading.Thread(target=self._watcher, daemon=True)
        self.watcher_thread.start()

    def stop(self):
        self.stop_event.set()
        # 等待 watcher 退出
        try:
            if hasattr(self, 'watcher_thread'):
                self.watcher_thread.join(timeout=2)
        except Exception:
            pass
        # 关闭所有文件
        for f in list(self.opened.values()):
            try:
                f.close()
            except Exception:
                pass
        self.opened.clear()
        # 等待子线程退出
        for t in list(self.threads.values()):
            try:
                t.join(timeout=2)
            except Exception:
                pass
        self.threads.clear()


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
        else:
            print("WARNING: 未找到环境配置文件，请检查项目根目录下是否存在.env文件，如果没有，从env_template.txt考呗一份")
            sys.exit(1)

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
            },
            'personal_db': {
                'port': int(os.environ.get('PERSONALDB_PORT', '9100')),
                'dir': self.backend_dir / 'personaldb',
                'script': 'main.py',
                'name': '知识库'
            }
        }

        self.frontend_port = int(os.environ.get('FRONTEND_PORT', '5173'))
        self.host = os.environ.get('HOST', '127.0.0.1')
        self.processes: Dict[str, subprocess.Popen] = {}
        self.frontend_server = None
        self.log_tailer: Optional[MultiLogTailer] = None

    def setup_logging(self):
        """设置日志系统"""
        self.logs_dir.mkdir(exist_ok=True)

        log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(self.logs_dir / 'production.log', encoding='utf-8'),
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
                sys._base_executable or sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file),
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
            self.logger.warning(f"发现端口占用: {occupied_ports}，清理占用端口")
            self.kill_processes_on_ports(occupied_ports)

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
            # 关键更改：追加模式 + 行缓冲，便于 tailer 及时读到
            log_f = open(log_file, 'a', encoding='utf-8', buffering=1)

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
        """启动前端静态文件服务（开发：vite dev）"""
        self.logger.info(f"启动前端服务 (端口: {self.frontend_port})")
        try:
            log_file = self.logs_dir / f"frontend.log"
            # 关键更改：追加模式 + 行缓冲
            log_f = open(log_file, 'a', encoding='utf-8', buffering=1)

            process = subprocess.Popen(
                ['npm', 'run', 'dev'],
                cwd=self.frontend_dir,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                text=True
            )

            # 等待服务启动
            time.sleep(3)

            if process.poll() is None:
                self.logger.info(f"✅ 前端启动成功 (PID: {process.pid})")
                return process
            else:
                self.logger.error(f"❌ 前端启动失败，查看日志: {log_file}")
                return None

        except Exception as e:
            self.logger.error(f"启动前端时出错: {e}")
            return None

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
        process = self.start_frontend_server()
        if process:
            self.processes['frontend'] = process

        # 显示服务状态
        self.show_service_status()

        # 关键新增：启动多文件日志 tailer
        self.start_log_tailer()

    def start_log_tailer(self):
        """启动日志汇总输出（类似 tail -f logs/*.log）"""
        try:
            self.log_tailer = MultiLogTailer(self.logs_dir, pattern="*.log", poll_interval=1.0, color=True)
            print("\n" + "=" * 80)
            print("🖨️ 实时日志（相当于：tail -f logs/*.log）")
            print("   - 每行以 [文件名] 为前缀")
            print("   - 新创建的日志文件会自动开始跟随")
            print("=" * 80 + "\n")
            self.log_tailer.start()
        except Exception as e:
            print(f"[LogTailer] 启动失败：{e}")

    def show_service_status(self):
        """显示服务状态"""
        print("\n" + "="*80)
        print("🎉 所有服务启动成功!")
        print("="*80)
        print("📋 服务状态:")

        for service_name, config in self.services.items():
            if service_name in self.processes:
                print(f"  ✅ {config['name']}: http://{self.host}:{config['port']}")

        print(f"  ✅ 前端界面: http://{self.host}:{self.frontend_port}")
        print(f"  📝 日志目录: {self.logs_dir}")

        print("\n💡 使用说明:")
        print("  - 按 Ctrl+C 停止所有服务，请耐心等待5秒，等待Agent启动完成")
        print("  - 在浏览器中访问前端界面开始使用")
        print("  - 服务日志保存在 logs/ 目录中，且已在当前控制台实时展示（tail -f 效果）")
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

        # 停止日志 tailer
        if self.log_tailer:
            try:
                self.log_tailer.stop()
            except Exception as e:
                print(f"[LogTailer] 停止失败：{e}")

        # 停止后端/前端服务
        for service_name, process in list(self.processes.items()):
            try:
                self.logger.info(f"停止服务: {service_name}")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.logger.warning(f"强制终止服务: {service_name}")
                process.kill()
            except Exception as e:
                self.logger.error(f"停止服务 {service_name} 时出错: {e}")

        # 停止内置前端服务器（如果有）
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

        # 构建前端（如生产需要）
        # self.build_frontend()

        # 检查端口
        self.check_ports()

        # 启动所有服务 + 日志 tailer
        self.start_all_services()

        # 监控服务
        self.monitor_services()

def main():
    """主函数"""
    starter = ProductionStarter()

    # 注册信号处理器
    def signal_handler(signum, frame):
        print("\n🛑 收到信号，正在停止服务...")
        starter.stop_all_services()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        starter.run()
    except KeyboardInterrupt:
        print("\n🛑 用户中断")
        starter.stop_all_services()
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        starter.stop_all_services()
        sys.exit(1)

if __name__ == "__main__":
    main()
