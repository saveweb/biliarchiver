import os


def main():
    _tools = os.listdir(os.path.dirname(__file__))
    available_tools = []
    for tool in _tools:
        if tool.endswith('.py') and tool != '__init__.py' and tool != 'biliarchiver.py':
            available_tools.append(tool[:-3])
    
    print("biliarchiver 可用的命令行工具有: (-h 查看帮助)")
    print("\n".join(available_tools))

if __name__ == '__main__':
    main()