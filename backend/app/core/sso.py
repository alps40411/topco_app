# backend/app/core/sso.py

from fastapi import Request, HTTPException, status
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class SSOHeaders:
    """SSO Headers 管理類別"""

    def __init__(self, request: Request):
        self.request = request
        self.headers = request.headers
        self.cookies = request.cookies

    def get_empno(self) -> Optional[str]:
        """
        獲取員工編號 (empno)
        優先順序: Headers > Cookies
        """
        # 從 Header 獲取
        empno = self.headers.get("wwwuser.empno")
        if empno:
            logger.info(f"Got empno from header: {empno}")
            return empno.strip()

        # 從 Cookie 獲取 (如果 Header 沒有)
        empno = self.cookies.get("empno")
        if empno:
            logger.info(f"Got empno from cookie: {empno}")
            return empno.strip()

        return None

    def get_cocode(self) -> Optional[str]:
        """
        獲取公司代碼 (cocode)
        優先順序: Headers > Cookies > 默認值 'A'
        """
        # 從 Header 獲取
        cocode = self.headers.get("wwwuser.cocode")
        if cocode:
            logger.info(f"Got cocode from header: {cocode}")
            return cocode.strip()

        # 從 Cookie 獲取
        cocode = self.cookies.get("CoCode")
        if cocode:
            logger.info(f"Got cocode from cookie: {cocode}")
            return cocode.strip()

        # 默認值
        logger.info("Using default cocode: A")
        return "A"

    def get_language(self) -> str:
        """
        獲取語言設置
        優先順序: Cookies > Accept-Language Header > 默認 zh_TW
        """
        # 從 Cookie 獲取
        language = self.cookies.get("Language")
        if language:
            return language.strip()

        # 從 Accept-Language Header 獲取
        accept_language = self.headers.get("Accept-Language", "")
        if accept_language:
            user_lang = accept_language.split(',')[0].lower()
            language_mapping = {
                "zh-cn": "zh_CN",
                "zh": "zh_CN",
                "ja": "ja_JP",
                "ja-jp": "ja_JP",
                "en-us": "en_US",
                "en-gb": "en_US",
                "en": "en_US"
            }

            mapped_lang = language_mapping.get(user_lang)
            if mapped_lang:
                return mapped_lang

        # 默認值
        return "zh_TW"

    def is_sso_enabled(self) -> bool:
        """
        檢查是否啟用 SSO (有 empno 就認為是 SSO 環境)
        """
        return self.get_empno() is not None

    def validate_sso_headers(self) -> bool:
        """
        驗證 SSO Headers 的完整性
        """
        empno = self.get_empno()
        cocode = self.get_cocode()

        if not empno:
            logger.warning("SSO validation failed: missing empno")
            return False

        if not cocode:
            logger.warning("SSO validation failed: missing cocode")
            return False

        logger.info(f"SSO validation passed: empno={empno}, cocode={cocode}")
        return True

def get_sso_headers(request: Request) -> SSOHeaders:
    """
    獲取 SSO Headers 工廠函數
    """
    return SSOHeaders(request)

def require_sso_headers(request: Request) -> SSOHeaders:
    """
    要求有效的 SSO Headers，否則拋出異常
    """
    sso_headers = get_sso_headers(request)

    if not sso_headers.validate_sso_headers():
        logger.error("SSO headers validation failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid SSO headers - missing empno or cocode",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return sso_headers

# 開發環境的 Mock SSO Headers (用於測試)
class MockSSOHeaders(SSOHeaders):
    """開發環境用的 Mock SSO Headers"""

    def __init__(self, request: Request, mock_empno: str = "TEST001", mock_cocode: str = "A"):
        super().__init__(request)
        self.mock_empno = mock_empno
        self.mock_cocode = mock_cocode

    def get_empno(self) -> Optional[str]:
        # 優先使用真實 headers，如果沒有則使用 mock
        real_empno = super().get_empno()
        if real_empno:
            return real_empno

        logger.info(f"Using mock empno: {self.mock_empno}")
        return self.mock_empno

    def get_cocode(self) -> Optional[str]:
        # 優先使用真實 headers，如果沒有則使用 mock
        real_cocode = super().get_cocode()
        if real_cocode and real_cocode != "A":  # "A" 是默認值
            return real_cocode

        logger.info(f"Using mock cocode: {self.mock_cocode}")
        return self.mock_cocode

def get_sso_headers_with_mock(request: Request, enable_mock: bool = False) -> SSOHeaders:
    """
    獲取 SSO Headers，支援開發環境 Mock
    """
    # 導入配置
    from app.core.config import settings

    # 根據配置決定是否啟用 Mock
    should_use_mock = enable_mock or settings.SSO_MOCK_ENABLED

    if should_use_mock:
        return MockSSOHeaders(
            request,
            mock_empno=settings.SSO_MOCK_EMPNO,
            mock_cocode=settings.SSO_MOCK_COCODE
        )
    else:
        return SSOHeaders(request)