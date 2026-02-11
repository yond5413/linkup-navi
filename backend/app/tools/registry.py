from typing import Dict, Callable, Any


_registry: Dict[str, Dict[str, Any]] = {}


def tool(name: str = None, description: str = None):
    def decorator(func: Callable):
        _registry[func.__name__] = {
            "func": func,
            "name": name or func.__name__,
            "description": description or func.__doc__ or "",
        }
        return func

    return decorator


class ToolRegistry:
    @staticmethod
    def get_tool(name: str):
        return _registry.get(name)

    @staticmethod
    def list_tools():
        return _registry

    @staticmethod
    def get_tool_names():
        return list(_registry.keys())
