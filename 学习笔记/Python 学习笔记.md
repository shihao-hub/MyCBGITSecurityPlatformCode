











### 2024-09-09

【摘要】



【正文】

1、typing 使用

```python
import typing as t

T = t.TypeVar("T")

class OutputParamters(t.Generic[T]):
    def __init__(self, value: [T] = None):
        self._value = value
```

