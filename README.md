# CairnShop Tests

CairnShop 的接口 / UI / 性能自动化测试项目。测试对象是
[CairnShop](https://github.com/Ethan-y-Free/CairnShop) 的本地或测试环境实例，
本项目不修改产品代码，按黑盒方式验证接口契约和关键业务链路。

## 目标

- 接口自动化：认证、商品、购物车、订单、幂等、RBAC、配置回滚、fail-closed、限流
- 性能测试：浏览 / 加购 / 下单链路的 TPS、p95、错误率
- UI 冒烟：登录 → 加购 → 下单
- CI：GitHub Actions 自动跑接口回归并归档 Allure 报告

## 技术栈

| 层 | 选型 |
|---|---|
| 测试框架 | pytest |
| HTTP 客户端 | requests |
| 响应校验 | pydantic |
| 报告 | Allure |
| 并行 | pytest-xdist |
| UI | Playwright |
| 性能 | Locust |
| 代码质量 | ruff |

## 目录结构

```
cairnshop-tests/
├── config/settings.py       # 环境配置：base_url、管理员账号、超时
├── api/
│   ├── client.py            # requests.Session + Allure 附件 + X-Forwarded-For
│   ├── endpoints.py         # 按业务域分组的接口方法
│   └── models.py            # pydantic 响应模型
├── data/factories.py        # 唯一邮箱/手机号/幂等键/测试商品工厂
├── conftest.py              # admin/customer/测试商品/清空购物车 fixture
├── tests/
│   ├── api/                 # 接口用例
│   └── ui/                  # Playwright UI 冒烟
├── perf/locustfile.py       # 性能场景
├── scripts/                 # 本地运行脚本
└── .github/workflows/       # CI
```

## 快速开始

前提：CairnShop 已启动（后端 `127.0.0.1:8080`，前端 `127.0.0.1:5173`），
并且执行过 `migrate` / `seed`（创建管理员和商品）。

在 CairnShop 仓库里启动整套环境：

```bash
cd ../cairnshop
bash scripts/dev-up.sh
```

安装测试依赖：

```bash
cd ../cairnshop-tests
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"          # 接口测试
pip install -e ".[dev,ui,perf]"  # 再加 UI / 性能
cp .env.example .env             # 按需改 base_url / 管理员密码
```

跑接口测试：

```bash
pytest tests/api -m api
```

没有 CairnKV 时，跳过订单/配置相关用例：

```bash
CAIRNSHOP_TEST_REQUIRE_CAIRNKV=0 pytest tests/api -m api
```

生成并查看 Allure 报告：

```bash
pytest tests/api -m api
allure serve reports/allure-results
```

跑 UI 冒烟（需要 Playwright 浏览器）：

```bash
python -m playwright install chromium
pytest tests/ui -m ui
pytest tests/ui -m ui --headed   # 本地调试时看浏览器
```

跑性能测试：

```bash
bash perf/run_perf.sh
# 可覆盖：USERS=50 DURATION=2m SPAWN_RATE=5 bash perf/run_perf.sh
```

`perf/run_perf.sh` 会用管理员账号创建一个高库存压测商品，跑 Locust 浏览/加购/下单
场景，然后用 `scripts/check_perf.py` 检查 p95 和错误率阈值（默认 p95 < 500ms、
错误率 < 1%）。结果在 `reports/perf/`。

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `CAIRNSHOP_TEST_BASE_URL` | `http://127.0.0.1:8080` | 后端地址 |
| `CAIRNSHOP_TEST_UI_URL` | `http://127.0.0.1:5173` | 前端地址 |
| `CAIRNSHOP_TEST_ADMIN_EMAIL` | `admin@cairnshop.local` | 管理员邮箱 |
| `CAIRNSHOP_TEST_ADMIN_PASSWORD` | `admin123456` | 管理员密码 |
| `CAIRNSHOP_TEST_TIMEOUT` | `5` | 单请求超时（秒） |
| `CAIRNSHOP_TEST_REQUIRE_CAIRNKV` | `1` | `0` 时跳过 `requires_cairnkv` 用例 |

## 测试隔离设计

- **独立虚拟 IP**：每个测试客户端带随机 `X-Forwarded-For`，避免登录 5 次/分钟、
  注册 60 次/分钟的限流互相影响；限流用例则固定 IP，专门验证第 6 次返回 429。
- **专用测试商品**：会话开始时通过运营接口创建一个 `QA-xxxx` 商品，库存固定，
  不依赖 seed 商品，也不受其他用例扣库存影响。
- **会话复用**：管理员登录一次、普通用户注册一次（注册响应直接带 session cookie），
  避免反复登录触发限流；购物车用例通过 `empty_cart` fixture 清空。
- **数据唯一性**：邮箱、手机号、SKU、幂等键都带随机后缀，可重复执行。

## 用例清单（当前）

| 模块 | 覆盖点 |
|---|---|
| 健康检查 | `/healthz`、`/metrics`、`/readyz`（需 CairnKV） |
| 认证 | 邮箱/手机号注册、重复邮箱、非法参数、邮箱/手机号登录、错误密码、登出、`/me` |
| 商品 | 分类列表、商品分页、详情、404、搜索、非法分页参数 |
| 购物车 | 加购、累加、改数量、数量置 0 删除、删除、非法数量、不存在商品、未登录 |
| 订单 | 下单、幂等重放、支付、取消回补库存、订单列表/详情、空购物车、缺幂等键、库存不足 |
| 配置 | 创建/更新、版本历史、回滚、审计、快照刷新、非法 key/value |
| fail-closed | 关闭结算返回 503，恢复后同一购物车可正常下单 |
| 并发 | 15 买家抢 10 件库存，恰好 10 成功、5 冲突、库存归零 |
| RBAC | 匿名 401、普通用户 403、管理员 200 |
| 限流 | 登录第 6 次返回 429 + `Retry-After` |
| UI 冒烟 | Playwright：登录 → 首页 → 商品详情 → 加购 → 结算 → 订单支付 |

当前规模：约 65 条接口用例 + 1 条 UI 冒烟 + 1 个 Locust 性能场景。

## 设计说明（面试可讲）

1. **为什么分层**：`client` 只关心 HTTP 与报告，`endpoints` 只关心 URL/参数，
   `models` 只关心响应契约，用例只关心业务断言。接口变更时只改一层。
2. **为什么用 pydantic**：接口返回字段缺失/类型变化会直接让用例失败，
   比 `response.json()["x"]` 更早暴露契约问题。
3. **为什么用 X-Forwarded-For**：后端按该头识别客户端 IP；测试既可以用它隔离限流，
   也可以用它构造“同一 IP 连续请求”的限流场景，不需要改产品代码。
4. **为什么造专用商品**：测试数据自管理，避免依赖 seed 数据和执行顺序。
5. **AI 辅助**：用 Claude Code 生成用例骨架、参数化数据和失败日志分析，
   断言与预期结果由人工复核，避免把 AI 的猜测当成事实。

## 后续计划

- [x] 订单：下单、幂等重放、支付、取消回补、订单列表/详情
- [x] 配置：创建/更新/历史/回滚/审计、fail-closed 503
- [x] 并发：15 买家抢 10 件库存的超卖验证
- [x] UI：Playwright 登录 → 加购 → 下单冒烟
- [x] 性能：Locust 浏览/加购/下单场景 + p95/错误率阈值
- [x] CI：GitHub Actions 启动 MySQL + CairnKV + CairnShop，跑接口/UI 回归并上传 Allure 原始结果

## CI 说明

`.github/workflows/tests.yml` 会在 GitHub Actions 里：

1. checkout 测试仓库、CairnShop、CairnKV；
2. 启动 MySQL service，编译 CairnKV 和 CairnShop；
3. 启动 3 节点 CairnKV、执行 migrate/seed/seed-config、启动后端和前端；
4. 跑接口回归 + UI 冒烟，上传 `reports/allure-results`。

性能测试不放进 CI（共享 runner 的噪声太大），用 `perf/run_perf.sh` 在固定 VM 上跑。
