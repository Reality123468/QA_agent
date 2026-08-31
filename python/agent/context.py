"""
请求级上下文变量 — 通过 contextvars 在线程/协程间安全传递安全级别等请求信息。

使用方式:
  - agent_routes.py 请求入口: current_security_level.set("机密")
  - tools.py 工具内部:    seclevel = current_security_level.get()
"""

import contextvars

current_security_level: contextvars.ContextVar[str] = contextvars.ContextVar(
    "security_level", default="内部"
)
