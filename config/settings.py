from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """测试环境配置。

    所有字段都可以通过 CAIRNSHOP_TEST_ 前缀的环境变量覆盖，
    也可以在项目根目录放一个 .env 文件。
    """

    model_config = SettingsConfigDict(
        env_prefix="CAIRNSHOP_TEST_",
        env_file=".env",
        extra="ignore",
    )

    base_url: str = "http://127.0.0.1:8080"
    ui_url: str = "http://127.0.0.1:5173"
    admin_email: str = "admin@cairnshop.local"
    admin_password: str = "admin123456"
    timeout: float = 5.0
    require_cairnkv: bool = True
