# SwanLab 0.10.2+qzfix.1

基于上游 `v0.10.2` Git 标签的启智子路径代理修复版。标签内的 package.json
仍是开发版本占位值；本发行包显式标记为 `0.10.2+qzfix.1`。

## 安装

将 dist/swanlab-0.10.2+qzfix.1-py3-none-any.whl 上传至训练服务器，然后在训练环境执行：

```bash
python -m pip install --upgrade './swanlab-0.10.2+qzfix.1-py3-none-any.whl'
python -m pip show swanlab
```

不要使用 --no-deps，除非环境已经具有所需依赖。wheel 是纯 Python 包，可用于 Linux。

## 登录

在训练服务器设置完整服务入口，不要在地址末尾附加 /api：

```bash
export SWANLAB_WEB_HOST='https://nat2-notebook-inspire.sii.edu.cn/你的完整路径/proxy/8000'
export SWANLAB_API_HOST="$SWANLAB_WEB_HOST"
curl --max-time 15 -i "${SWANLAB_API_HOST%/}/api/"
swanlab login --host "$SWANLAB_API_HOST" --relogin
```

输入自托管 SwanLab 的 API Key。设置页提示和后续请求会保留完整路径前缀。
显式 --host、SWANLAB_API_HOST 和已保存的 .netrc 凭据均支持路径前缀。
仅 SWANLAB_WEB_HOST 仍只控制网页入口；请同时设置 SWANLAB_API_HOST 或传入 --host。
登录保存后，新进程可从凭据文件读取完整入口；旧版 SDK 截断过的凭据需要重新登录。

## 最小实验

```python
import swanlab

swanlab.init(project="qizhi-smoke", experiment_name="prefix-fix")
for step in range(5):
    swanlab.log({"loss": 1 / (step + 1)}, step=step)
swanlab.finish()
```

## 修复范围和限制

- 保留服务基础 URL 的路径与编码，去掉末尾斜杠、query 和 fragment。
- 保留原有根目录 /api 地址兼容性；部署前缀应填写服务根入口。
- CLI 不再向已经负责追加 /api 的客户端重复传入 /api。
- .netrc 保存/重载不会丢失路径；不同前缀的服务不会混用已有凭据。
- 自托管存储的同域 /swanlab-public/ 和 /swanlab-private/ 上传 URL 会补上代理前缀，
  已有前缀不会重复追加；签名 query 不会被重新编码；外部 S3 地址保持原样。
- 该修改不绕过启智平台认证。如果 curl 返回平台登录页、302 或 401，
  仍需提供平台支持的非浏览器认证方式或使用 SSH 转发。
- 未登录真实启智代理进行端到端验证；测试使用隔离的模拟 HTTP 响应，不使用真实 API Key。

## 验证和重建

337 项配置、凭据、登录、客户端、上传和传输相关测试通过。

```bash
python -m pytest tests/unit/sdk/internal/pkg/nrc tests/unit/sdk/internal/settings \
  tests/unit/sdk/cmd/login tests/unit/sdk/internal/pkg/client \
  tests/unit/sdk/internal/core_python/api/test_upload.py \
  tests/unit/sdk/internal/core_python/transport -q
python -m build --no-isolation
```
