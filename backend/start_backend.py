#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TrainPPTAgent 后端服务启动脚本
支持一键启动所有后端服务，包括端口清理和环境检查
"""

import os
import sys
import time
import signal
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import dotenv_values

class BackendStarter:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.logs_dir = self.base_dir / 'logs'
        self.services = {
            'main_api': {
                'port': 6800,
                'dir': self.base_dir / 'main_api',
                'script': 'main.py',
                'env_file': '.env',
                'env_template': 'env_template'
            },
            'simpleOutline': {
                'port': 10001,
                'dir': self.base_dir / 'simpleOutline',
                'script': 'main_api.py',
                'env_file': '.env',
                'env_template': 'env_template'
            },
            'slide_agent': {
                'port': 10011,
                'dir': self.base_dir / 'slide_agent',
                'script': 'main_api.py',
                'env_file': '.env',
                'env_template': 'env_template'
            },
            'personal_db': {
                'port': 10011,
                'dir': self.base_dir / 'personaldb',
                'script': 'main.py',
                'env_file': '.env',
                'env_template': 'env_template'
            }
        }
        self.processes: Dict[str, subprocess.Popen] = {}
        self.log_files: Dict[str, Path] = {}
        
    def setup_logs_directory(self):
        """设置日志目录"""
        print("📁 设置日志目录...")
        
        # 创建logs目录
        if not self.logs_dir.exists():
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ 创建日志目录: {self.logs_dir}")
        else:
            print(f"✅ 日志目录已存在: {self.logs_dir}")
            
        # 为每个服务创建日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for service_name in self.services.keys():
            log_file = self.logs_dir / f"{service_name}_{timestamp}.log"
            self.log_files[service_name] = log_file
            print(f"📝 日志文件: {service_name} -> {log_file}")
            
    def print_banner(self):
        """打印启动横幅"""
        print("=" * 60)
        print("🚀 TrainPPTAgent 后端服务启动器")
        print("=" * 60)
        print()
        
    def check_python_version(self):
        """检查Python版本"""
        if sys.version_info < (3, 8):
            print("❌ 错误: 需要Python 3.8或更高版本")
            sys.exit(1)
        print(f"✅ Python版本: {sys.version}")
        
    def check_dependencies(self):
        """检查依赖包"""
        print("📦 检查依赖包...")
        requirements_file = self.base_dir / 'requirements.txt'
        if not requirements_file.exists():
            print("❌ 错误: requirements.txt 文件不存在")
            sys.exit(1)
            
        try:
            # 检查pip是否可用
            subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                         check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print("❌ 错误: pip不可用")
            sys.exit(1)
            
        print("✅ 依赖检查完成")
        
    def install_dependencies(self):
        """安装依赖包"""
        print("📦 安装依赖包...")
        requirements_file = self.base_dir / 'requirements.txt'

        # 定义可用的镜像源
        mirrors = {
            '0': {
                'name': '官方PyPI源',
                'url': None,
                'description': '官方源，全球通用但可能较慢'
            },
            '1': {
                'name': '清华大学镜像源',
                'url': 'https://pypi.tuna.tsinghua.edu.cn/simple/',
                'description': '清华大学开源软件镜像站，国内访问速度快'
            },
            '2': {
                'name': '阿里云镜像源',
                'url': 'https://mirrors.aliyun.com/pypi/simple/',
                'description': '阿里云提供的PyPI镜像，稳定可靠'
            },
            '3': {
                'name': '中科大镜像源',
                'url': 'https://pypi.mirrors.ustc.edu.cn/simple/',
                'description': '中科大开源软件镜像，教育网用户推荐'
            },
            '4': {
                'name': '豆瓣镜像源',
                'url': 'https://pypi.douban.com/simple/',
                'description': '豆瓣提供的PyPI镜像，老牌稳定'
            },
            '5': {
                'name': '华为云镜像源',
                'url': 'https://mirrors.huaweicloud.com/repository/pypi/simple/',
                'description': '华为云镜像，企业级稳定性'
            },
            '6': {
                'name': '腾讯云镜像源',
                'url': 'https://mirrors.cloud.tencent.com/pypi/simple/',
                'description': '腾讯云镜像，国内访问优化'
            }
        }

        print("🚀 请选择PyPI镜像源:")
        print("   - 在国内使用镜像源可以显著提升下载速度")
        print("   - 建议根据网络环境选择合适的镜像源")
        print()
        
        for key, mirror in mirrors.items():
            print(f"   {key}. {mirror['name']}")
            print(f"      {mirror['description']}")
            if mirror['url']:
                print(f"      地址: {mirror['url']}")
            print()
        
        while True:
            choice = input("请选择镜像源 (0-6, 默认0): ").strip()
            if not choice:
                choice = '0'  # 默认选择清华大学镜像源
            
            if choice in mirrors:
                selected_mirror = mirrors[choice]
                break
            else:
                print("❌ 无效选择，请输入 0-6 之间的数字")
        
        pip_cmd = [sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)]
        
        if selected_mirror['url']:
            pip_cmd.extend(['-i', selected_mirror['url']])
            print(f"✅ 使用 {selected_mirror['name']}")
        else:
            print(f"✅ 使用 {selected_mirror['name']}")
        
        try:
            result = subprocess.run(pip_cmd, capture_output=False, text=True)
            
            if result.returncode == 0:
                print("✅ 依赖安装成功")
            else:
                print("⚠️  依赖安装可能有问题，请检查输出:")
                print(result.stderr)
        except Exception as e:
            print(f"❌ 依赖安装失败: {e}")
            sys.exit(1)
            
    def check_ports(self) -> List[int]:
        """检查端口占用情况"""
        occupied_ports = []
        for service_name, config in self.services.items():
            port = config['port']
            try:
                # 检查端口是否被占用
                import socket
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    if s.connect_ex(('localhost', port)) == 0:
                        occupied_ports.append(port)
            except Exception:
                pass
        return occupied_ports
        
    def kill_processes_on_ports(self, ports: List[int]):
        """杀死占用指定端口的进程"""
        if not ports:
            return
            
        print(f"🔍 发现端口占用: {ports}")
        response = input("是否清理这些端口? (y/N): ").strip().lower()
        
        if response != 'y':
            print("❌ 用户取消操作")
            sys.exit(1)
            
        killed_count = 0
        for port in ports:
            try:
                import psutil
                # 查找占用端口的进程
                for proc in psutil.process_iter(['pid', 'name', 'connections']):
                    try:
                        connections = proc.info['connections']
                        if connections:
                            for conn in connections:
                                if conn.laddr.port == port:
                                    print(f"🔄 终止进程 {proc.info['name']} (PID: {proc.info['pid']}) 占用端口 {port}")
                                    proc.terminate()
                                    proc.wait(timeout=5)
                                    killed_count += 1
                                    break
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                        continue
            except Exception as e:
                print(f"⚠️  清理端口 {port} 时出错: {e}")
                
        print(f"✅ 清理完成，终止了 {killed_count} 个进程")
        time.sleep(2)  # 等待端口释放
        
    def setup_env_files(self):
        """设置环境文件"""
        print("⚙️  设置环境文件...")
        
        for service_name, config in self.services.items():
            service_dir = config['dir']
            env_file = service_dir / config['env_file']
            env_template = service_dir / config['env_template']
            
            if not service_dir.exists():
                print(f"❌ 错误: 服务目录不存在 {service_dir}")
                sys.exit(1)
                
            if not env_template.exists():
                print(f"⚠️  警告: 环境模板文件不存在 {env_template}")
                continue
                
            if not env_file.exists():
                print(f"📝 复制环境文件: {service_name}")
                shutil.copy2(env_template, env_file)
            else:
                print(f"✅ 环境文件已存在: {service_name}")
                
    def start_service(self, service_name: str, config: Dict) -> Optional[subprocess.Popen]:
        """启动单个服务"""
        service_dir = config['dir']
        script = config['script']
        port = config['port']
        log_file = self.log_files[service_name]
        
        print(f"🚀 启动服务: {service_name} (端口: {port})")
        print(f"📝 日志文件: {log_file}")
        
        try:
            # 切换到服务目录
            os.chdir(service_dir)
            
            # 打开日志文件
            with open(log_file, 'w', encoding='utf-8') as log_f:
                # 写入启动信息
                log_f.write(f"=== {service_name} 服务启动日志 ===\n")
                log_f.write(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                log_f.write(f"工作目录: {service_dir}\n")
                log_f.write(f"脚本文件: {script}\n")
                log_f.write(f"端口: {port}\n")
                log_f.write("=" * 50 + "\n\n")
                log_f.flush()
                
                # 读取 .env 并合入当前环境
                env = os.environ.copy()
                env_file_path = service_dir / config['env_file']
                if env_file_path.exists():
                    env.update(dotenv_values(str(env_file_path)))
                
                process = subprocess.Popen(
                    [sys.executable, script],
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env=env  
                )
                
                # 等待一段时间检查进程是否正常启动
                time.sleep(3)
                
                if process.poll() is None:
                    print(f"✅ {service_name} 启动成功 (PID: {process.pid})")
                    return process
                else:
                    print(f"❌ {service_name} 启动失败，请查看日志文件: {log_file}")
                    return None
                    
        except Exception as e:
            print(f"❌ 启动 {service_name} 时出错: {e}")
            return None
        finally:
            # 切换回原目录
            os.chdir(self.base_dir)
            
    def start_all_services(self):
        """启动所有服务"""
        print("🚀 启动所有后端服务...")
        print()
        
        # 启动所有服务
        for service_name, config in self.services.items():
            process = self.start_service(service_name, config)
            if process:
                self.processes[service_name] = process
            else:
                print(f"❌ 服务 {service_name} 启动失败，停止所有服务")
                self.stop_all_services()
                sys.exit(1)
                
        print()
        print("=" * 60)
        print("🎉 所有后端服务启动成功!")
        print("=" * 60)
        print("📋 服务状态:")
        for service_name, config in self.services.items():
            if service_name in self.processes:
                print(f"  ✅ {service_name}: http://127.0.0.1:{config['port']}")
                print(f"     📝 日志: {self.log_files[service_name]}")
        print()
        print("💡 提示:")
        print("  - 按 Ctrl+C 停止所有服务")
        print("  - 前端服务请访问: http://127.0.0.1:5173")
        print("  - 服务日志保存在 backend/logs/ 目录中")
        print("=" * 60)
        
        # 等待所有进程
        try:
            while self.processes:
                for service_name, process in list(self.processes.items()):
                    if process.poll() is not None:
                        print(f"⚠️  服务 {service_name} 已停止")
                        del self.processes[service_name]
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 收到停止信号，正在关闭所有服务...")
            self.stop_all_services()
            
    def stop_all_services(self):
        """停止所有服务"""
        print("🛑 停止所有服务...")
        
        for service_name, process in self.processes.items():
            try:
                print(f"🔄 停止服务: {service_name}")
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ {service_name} 已停止")
            except subprocess.TimeoutExpired:
                print(f"⚠️  {service_name} 强制终止")
                process.kill()
            except Exception as e:
                print(f"❌ 停止 {service_name} 时出错: {e}")
                
        self.processes.clear()
        print("✅ 所有服务已停止")
        
    def run(self):
        """主运行函数"""
        self.print_banner()
        
        # 设置日志目录
        self.setup_logs_directory()
        
        # 检查Python版本
        self.check_python_version()
        
        # 检查依赖
        self.check_dependencies()
        
        # 安装依赖
        self.install_dependencies()
        
        # 检查端口占用
        occupied_ports = self.check_ports()
        if occupied_ports:
            self.kill_processes_on_ports(occupied_ports)
            
        # 设置环境文件
        self.setup_env_files()
        
        # 启动所有服务
        self.start_all_services()

def main():
    """主函数"""
    starter = BackendStarter()
    
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
