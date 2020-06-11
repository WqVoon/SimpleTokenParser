*仅支持py3*

使用方法

```python
from Tokens import TokenProcessor as TP

with open(<文件名>) as f:
    tp = TP(f)

for token_type, token_id in tp:
    print(tp[token_type][token_id])

```

或

```python
from Tokens import TokenProcessor as TP

src = """
#include <included_file>

int main(void)
{
    puts("Hello World");    
    return 0;
}
"""

tp = TP(src)

for token_type, token_id in tp:
    print(tp[token_type][token_id])

```

