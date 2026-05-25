"""输入验证器"""

import re
from typing import Optional


# 股票代码格式：6位数字 + 可选的 .SH/.SZ/.BJ 后缀
STOCK_CODE_PATTERN: re.Pattern = re.compile(r'^\d{6}(\.(SH|SZ|BJ))?$')


def validate_stock_code(code: str) -> str:
    """
    验证股票代码格式

    支持纯6位数字或带市场后缀（.SH/.SZ/.BJ）的格式。
    若未指定后缀，则根据代码首位数字自动补充：
    - 6/9 开头 → .SH（上海）
    - 0/3/2 开头 → .SZ（深圳）
    - 4/8 开头 → .BJ（北京）

    Args:
        code: 股票代码

    Returns:
        str: 标准化后的代码（带后缀）

    Raises:
        ValueError: 格式无效时抛出
    """
    if not code:
        raise ValueError("股票代码不能为空")

    code = code.strip().upper()

    if not STOCK_CODE_PATTERN.match(code):
        raise ValueError(
            f"股票代码格式无效: {code}，应为6位数字（如600519或600519.SH）"
        )

    # 自动补充后缀
    if "." not in code:
        if code.startswith(("6", "9")):
            code = f"{code}.SH"
        elif code.startswith(("0", "3", "2")):
            code = f"{code}.SZ"
        elif code.startswith(("4", "8")):
            code = f"{code}.BJ"
        else:
            code = f"{code}.SZ"

    return code


def validate_quantity(quantity: int) -> int:
    """
    验证交易数量

    A股最小交易单位为1手（100股），数量必须为100的整数倍。

    Args:
        quantity: 交易数量

    Returns:
        int: 验证通过的交易数量

    Raises:
        ValueError: 数量无效时抛出
    """
    if quantity <= 0:
        raise ValueError("交易数量必须大于0")
    if quantity % 100 != 0:
        raise ValueError("交易数量必须是100的整数倍（A股最小交易单位为1手=100股）")
    return quantity


def validate_price(price: Optional[float]) -> Optional[float]:
    """
    验证价格

    价格必须大于0，结果保留2位小数。

    Args:
        price: 交易价格，为None时表示市价单

    Returns:
        Optional[float]: 验证通过的价格，保留2位小数；None表示市价

    Raises:
        ValueError: 价格无效时抛出
    """
    if price is None:
        return None
    if price <= 0:
        raise ValueError("价格必须大于0")
    return round(price, 2)
