#!/usr/bin/env python
"""测试新的数据源集成"""

import sys
sys.path.insert(0, '.')

print('测试新的数据源集成...')
print()

# 测试腾讯增强版
from astock_agents.data.tencent_client_enhanced import TencentClientEnhanced

tencent = TencentClientEnhanced(enabled=True)
print('✅ 腾讯财经增强版客户端初始化成功')

# 测试批量获取行情
quotes = tencent.get_batch_quotes(['600519', '000001', '688017'])
print(f'✅ 获取到 {len(quotes)} 只股票行情')

if quotes:
    for code, data in list(quotes.items())[:1]:
        print(f'\n示例数据 ({code}):')
        print(f'  名称: {data["name"]}')
        print(f'  价格: {data["price"]}')
        print(f'  PE(TTM): {data["pe_ttm"]}')
        print(f'  PB: {data["pb"]}')
        print(f'  市值: {data["mcap_yi"]}亿')
        print(f'  换手率: {data["turnover_pct"]}%')

print()
print('=' * 50)
print()

# 测试东财客户端
from astock_agents.data.eastmoney_client import EastmoneyClient

eastmoney = EastmoneyClient(enabled=True)
print('✅ 东方财富客户端初始化成功')

# 测试获取研报
reports = eastmoney.get_reports('600519', max_pages=1)
print(f'✅ 获取到 {len(reports)} 篇研报')

if reports:
    print('\n最新研报:')
    r = reports[0]
    print(f'  日期: {r.get("publishDate", "")[:10]}')
    print(f'  机构: {r.get("orgSName", "")}')
    print(f'  标题: {r.get("title", "")[:50]}...')
    print(f'  评级: {r.get("emRatingName", "")}')

print()
print('✅ 所有数据源测试通过!')
