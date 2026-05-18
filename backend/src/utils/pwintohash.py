from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 密码加密（修复截断逻辑）
def get_password_hash(password: str) -> str:
    # 直接截断字节串到72字节，不转回字符串
    password_bytes = password.encode("utf-8")[:72]
    # 直接用字节串加密（passlib支持字节串输入）
    return pwd_context.hash(password_bytes)

# 密码校验（同步调整，支持字节串校验）
def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_bytes = plain_password.encode("utf-8")[:72]
    return pwd_context.verify(plain_bytes, hashed_password)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
