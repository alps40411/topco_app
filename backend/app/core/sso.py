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
        print("[SSO_HEADERS] Getting empno...")
        print(f"[SSO_HEADERS] Available headers: {dict(self.headers)}")
        print(f"[SSO_HEADERS] Available cookies: {dict(self.cookies)}")

        # 從 Header 獲取
        empno = self.headers.get("wwwuser.empno")
        if empno:
            print(f"[SSO_HEADERS] Got empno from header: {empno}")
            logger.info(f"Got empno from header: {empno}")
            return empno.strip()

        # 從 Cookie 獲取 (如果 Header 沒有)
        empno = self.cookies.get("empno")
        if empno:
            print(f"[SSO_HEADERS] Got empno from cookie: {empno}")
            logger.info(f"Got empno from cookie: {empno}")
            return empno.strip()

        print("[SSO_HEADERS] No empno found in headers or cookies")
        return None

    def get_cocode(self) -> Optional[str]:
        """
        獲取公司代碼 (cocode)
        優先順序: Headers > Cookies > 默認值 'A'
        """
        print("[SSO_HEADERS] Getting cocode...")

        # 從 Header 獲取
        cocode = self.headers.get("wwwuser.cocode")
        if cocode:
            print(f"[SSO_HEADERS] Got cocode from header: {cocode}")
            logger.info(f"Got cocode from header: {cocode}")
            return cocode.strip()

        # 從 Cookie 獲取
        cocode = self.cookies.get("CoCode")
        if cocode:
            print(f"[SSO_HEADERS] Got cocode from cookie: {cocode}")
            logger.info(f"Got cocode from cookie: {cocode}")
            return cocode.strip()

        # 默認值
        print("[SSO_HEADERS] Using default cocode: A")
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
        print("[SSO_HEADERS] Validating SSO headers...")
        empno = self.get_empno()
        cocode = self.get_cocode()

        print(f"[SSO_HEADERS] Validation check: empno={empno}, cocode={cocode}")

        if not empno:
            print("[SSO_HEADERS] SSO validation failed: missing empno")
            logger.warning("SSO validation failed: missing empno")
            return False

        if not cocode:
            print("[SSO_HEADERS] SSO validation failed: missing cocode")
            logger.warning("SSO validation failed: missing cocode")
            return False

        print(f"[SSO_HEADERS] SSO validation passed: empno={empno}, cocode={cocode}")
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
        print("[MOCK_SSO] Getting empno (with mock fallback)...")
        # 優先使用真實 headers，如果沒有則使用 mock
        real_empno = super().get_empno()
        if real_empno:
            print(f"[MOCK_SSO] Using real empno: {real_empno}")
            return real_empno

        print(f"[MOCK_SSO] Using mock empno: {self.mock_empno}")
        logger.info(f"Using mock empno: {self.mock_empno}")
        return self.mock_empno

    def get_cocode(self) -> Optional[str]:
        print("[MOCK_SSO] Getting cocode (with mock fallback)...")
        # 優先使用真實 headers，如果沒有則使用 mock
        real_cocode = super().get_cocode()
        if real_cocode and real_cocode != "A":  # "A" 是默認值
            print(f"[MOCK_SSO] Using real cocode: {real_cocode}")
            return real_cocode

        print(f"[MOCK_SSO] Using mock cocode: {self.mock_cocode}")
        logger.info(f"Using mock cocode: {self.mock_cocode}")
        return self.mock_cocode

def get_sso_headers_with_mock(request: Request, enable_mock: bool = False) -> SSOHeaders:
    """
    獲取 SSO Headers，支援開發環境 Mock
    """
    print("[SSO_FACTORY] Creating SSO headers instance...")
    print(f"[SSO_FACTORY] enable_mock parameter: {enable_mock}")

    # 導入配置
    from app.core.config import settings
    print(f"[SSO_FACTORY] SSO_MOCK_ENABLED from settings: {getattr(settings, 'SSO_MOCK_ENABLED', 'NOT_SET')}")

    # 根據配置決定是否啟用 Mock
    should_use_mock = enable_mock or getattr(settings, 'SSO_MOCK_ENABLED', False)
    print(f"[SSO_FACTORY] should_use_mock: {should_use_mock}")

    if should_use_mock:
        print("[SSO_FACTORY] Using MockSSOHeaders")
        mock_empno = getattr(settings, 'SSO_MOCK_EMPNO', 'TEST001')
        mock_cocode = getattr(settings, 'SSO_MOCK_COCODE', 'A')
        print(f"[SSO_FACTORY] Mock settings: empno={mock_empno}, cocode={mock_cocode}")
        return MockSSOHeaders(
            request,
            mock_empno=mock_empno,
            mock_cocode=mock_cocode
        )
    else:
        print("[SSO_FACTORY] Using standard SSOHeaders")
        return SSOHeaders(request)