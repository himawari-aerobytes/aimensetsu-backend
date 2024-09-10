import json  # 追加
import os
from unittest.mock import MagicMock, Mock, patch

import jwt
from django.contrib.auth import get_user_model
from django.db import DatabaseError, IntegrityError
from django.http import JsonResponse
from django.test import RequestFactory, TestCase
from dotenv import load_dotenv

from rag_sample_app.utils import get_cognito_public_keys, jwt_required, load_environment

User = get_user_model()

SAMPLE_TOKEN = "eyJraWQiOiIxMjM0ZXhhbXBsZT0iLCJhbGciOiJSUzI1NiIsImt0eSI6IlJTQSIsImUiOiJBUUFCIiwibiI6IjEyMzQ1Njc4OTAiLCJ1c2UiOiJzaWcifQ.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMn0.qpldgWTqr6dA_vZCZcmnJgV7JPanhBzEloQA9CQuyLMLfi9u1T0y8Kr6uK4j-WiDHvqtzo5zoFBuwqO-o1adnAnTKmqKj2RHU3bXqXKtawLkMC-E_cwGrr_XBQQSMnfw8OX2C8tFr5nxr1Bi8KD2G4T4_9pqv6fz3STDTPeMOSZ-kx-p2lJYJVexxPfSg1j69Yc5Jd6nT7eJakzu09CTwcBdlKMGMgfKjzuUPWWc9gnO21PQgYPTP8UAohM_mvNyejYRlrluJBrG01faOj_WMpLR2rv9tg0s-HdjoR3FGlmMnJnssu3v5YF1wnPS2HPNaAZuu_12NDR5BjH_ulOiXA"  # gitleaks:allow
JWKS_MOCK_RESPONSE = {
    "keys": [
        {
            "kid": "test_kid_1",
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "n": "test_n_value",
            "e": "AQAB",
        },
        {
            "kid": "test_kid_2",
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "n": "another_n_value",
            "e": "AQAB",
        },
    ]
}


class JWTRequiredDecoratorTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("rag_sample_app.utils.get_cognito_public_keys")
    def test_missing_authorization_header(self, mock_get_cognito_public_keys):
        request = self.factory.get("/api/some-endpoint/")
        response = jwt_required(lambda r: JsonResponse({"success": "True"}))(request)
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data, {"error": "Authorization header missing"})

    @patch("rag_sample_app.utils.get_cognito_public_keys")
    def test_invalid_authorization_header_format(self, mock_get_cognito_public_keys):
        request = self.factory.get(
            "/api/some-endpoint/", HTTP_AUTHORIZATION="InvalidTokenFormat"
        )
        response = jwt_required(lambda r: JsonResponse({"success": "True"}))(request)
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(
            response_data, {"error": "Invalid Authorization header format"}
        )

    @patch("rag_sample_app.utils.get_cognito_public_keys")
    def test_invalid_token_type(self, mock_get_cognito_public_keys):
        request = self.factory.get(
            "/api/some-endpoint/", HTTP_AUTHORIZATION="Basic " + SAMPLE_TOKEN
        )
        response = jwt_required(lambda r: JsonResponse({"success": "True"}))(request)
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data, {"error": "Invalid token type"})

    @patch("rag_sample_app.utils.jwt.decode")
    @patch("rag_sample_app.utils.get_cognito_public_keys")
    def test_expired_token(self, mock_get_cognito_public_keys, mock_jwt_decode):
        mock_jwt_decode.side_effect = jwt.ExpiredSignatureError()
        request = self.factory.get(
            "/api/some-endpoint/", HTTP_AUTHORIZATION="Bearer " + SAMPLE_TOKEN
        )
        response = jwt_required(lambda r: JsonResponse({"success": "True"}))(request)
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data, {"error": "Token has expired"})

    @patch("rag_sample_app.utils.jwt.decode")
    @patch("rag_sample_app.utils.get_cognito_public_keys")
    def test_invalid_token(self, mock_get_cognito_public_keys, mock_jwt_decode):
        mock_jwt_decode.side_effect = jwt.InvalidTokenError("Invalid token")
        invalid_token = "eyJraWQiOiIxMjM0ZXhhbXBsZT0iLCJhbGciOiJSUzI1NiIsImt0eSI6IlJTQSIsImUiOiJBUUFCIiwibiI6IjEyMzQ1Njc4OTAiLCJ1c2UiOiJzaWcifQ.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMn0.qpldgWTqr6dA_vZCZcmnJgV7JPanhBzEloQA9CQuyLMLfi9u1T0y8Kr6uK4j-WiDHvqtzo5zoFBuwqO-o1adnAnTKmqKj2RHU3bXqXKtawLkMC-E_cwGrr_XBQQSMnfw8OX2C8tFr5nxr1Bi8KD2G4T4_9pqv6fz3STDTPeMOSZ-kx-p2lJYJVexxPfSg1j69Yc5Jd6nT7eJakzu09CTwcBdlKMGMgfKjzuUPWWc9gnO21PQgYPTP8UAohM_mvNyejYRlrluJBrG01faOj_WMpLR2rv9tg0s-HdjoR3FGlmMnJnssu3v5YF1wnPS2HPNaAZuu_12NDR5BjH_ulOiXA"  # gitleaks:allow
        request = self.factory.get(
            "/api/some-endpoint/", HTTP_AUTHORIZATION="Bearer " + invalid_token
        )
        response = jwt_required(lambda r: JsonResponse({"success": "True"}))(request)
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(
            response_data, {"error": "Invalid token", "details": "Invalid token"}
        )

    @patch("rag_sample_app.utils.get_cognito_public_keys")
    @patch("rag_sample_app.utils.jwt.decode")
    def test_valid_token_creates_user(
        self, mock_jwt_decode, mock_get_cognito_public_keys
    ):
        # モックのCognitoのパブリックキーとJWTデコードの戻り値を設定
        mock_jwt_decode.return_value = {
            "cognito:username": "testuser",
            "email": "testuser@example.com",
        }
        mock_get_cognito_public_keys.return_value = {"1234example=": "test"}

        request = self.factory.get(
            "/api/some-endpoint/", HTTP_AUTHORIZATION="Bearer " + SAMPLE_TOKEN
        )

        # 初期ユーザーデータの存在確認
        self.assertEqual(User.objects.filter(username="testuser").count(), 0)

        # デコレータ適用後のレスポンス
        response = jwt_required(lambda r: JsonResponse({"success": "True"}))(request)

        # モックが正しく呼ばれたか確認
        mock_jwt_decode.assert_called_once()

        # ユーザーが作成されていることの確認
        self.assertEqual(User.objects.filter(username="testuser").count(), 1)

        # レスポンスの確認
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data, {"success": "True"})

    @patch("rag_sample_app.utils.get_cognito_public_keys")
    @patch("rag_sample_app.utils.jwt.decode")
    def test_valid_token_existing_user(
        self, mock_jwt_decode, mock_get_cognito_public_keys
    ):
        # モックのCognitoのパブリックキーとJWTデコードの戻り値を設定
        mock_jwt_decode.return_value = {
            "cognito:username": "existinguser",
            "email": "existinguser@example.com",
        }
        mock_get_cognito_public_keys.return_value = {"1234example=": "test"}

        # 既存ユーザーを作成
        user = User.objects.create(
            username="existinguser", email="existinguser@example.com"
        )

        request = self.factory.get(
            "/api/some-endpoint/", HTTP_AUTHORIZATION="Bearer " + SAMPLE_TOKEN
        )

        # デコレータ適用後のレスポンス
        response = jwt_required(lambda r: JsonResponse({"success": "True"}))(request)

        # ユーザーが再作成されていないことを確認
        self.assertEqual(User.objects.filter(username="existinguser").count(), 1)

        # レスポンスの確認
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data, {"success": "True"})

    @patch("rag_sample_app.utils.get_cognito_public_keys")
    @patch("rag_sample_app.utils.jwt.decode")
    def test_public_key_not_found(self, mock_jwt_decode, mock_get_cognito_public_keys):
        # モックのCognitoのパブリックキーとJWTデコードの戻り値を設定
        mock_jwt_decode.return_value = {
            "cognito:username": "testuser",
            "email": "testuser@example.com",
        }

        # JWTと異なるキーを返す。
        mock_get_cognito_public_keys.return_value = {"invalid_key": "test"}

        request = self.factory.get(
            "/api/some-endpoint/", HTTP_AUTHORIZATION="Bearer " + SAMPLE_TOKEN
        )

        # 初期ユーザーデータの存在確認
        self.assertEqual(User.objects.filter(username="testuser").count(), 0)

        # デコレータ適用後のレスポンス
        response = jwt_required(lambda r: JsonResponse({"success": "True"}))(request)

        # モックが呼ばれていないことを確認
        mock_jwt_decode.assert_not_called()

        # ユーザーが作成されていないことを確認
        self.assertEqual(User.objects.filter(username="testuser").count(), 0)

        # レスポンスの確認
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data, {"error": "Public key not found"})

    @patch("rag_sample_app.utils.get_cognito_public_keys")
    @patch("rag_sample_app.utils.jwt.decode")
    @patch("django.contrib.auth.get_user_model")
    def test_error_creating_user(
        self, mock_get_user_model, mock_jwt_decode, mock_get_cognito_public_keys
    ):
        # モックのJWTデコードの戻り値を設定
        mock_jwt_decode.return_value = {
            "cognito:username": "testuser",
            "email": "testuser@example.com",
        }
        mock_get_cognito_public_keys.return_value = {"1234example=": "public_key"}

        with patch.object(User.objects, "get_or_create") as mock_method:
            mock_method.side_effect = IntegrityError()

            # リクエストを作成
            request = self.factory.get(
                "/api/some-endpoint/", HTTP_AUTHORIZATION="Bearer " + SAMPLE_TOKEN
            )

            # デコレータ適用後のレスポンスを取得
            response = jwt_required(lambda r: JsonResponse({"success": "True"}))(
                request
            )

            # レスポンスのステータスコードと内容を確認
            self.assertEqual(response.status_code, 500)
            response_data = json.loads(response.content)
            self.assertEqual(
                response_data, {"error": "Error creating or retrieving user"}
            )

    @patch("rag_sample_app.utils.requests.get")
    def test_get_cognito_public_keys(self, mock_requests_get):
        mock_response = Mock()
        mock_response.json.return_value = JWKS_MOCK_RESPONSE
        mock_requests_get.return_value = mock_response
        keys = get_cognito_public_keys()

        # 結果の確認
        self.assertIn("test_kid_1", keys)
        self.assertIn("test_kid_2", keys)
        self.assertEqual(len(keys), 2)

    # 環境変数のテスト
    @patch("os.getenv")
    @patch("rag_sample_app.utils.load_dotenv")
    def test_load_production_env(self, mock_load_dotenv, mock_getenv):
        # ENVが"production"であることをシミュレート
        mock_getenv.return_value = "production"

        # テスト対象のコードを実行
        load_environment()

        # 正しいファイルが読み込まれたか確認
        mock_load_dotenv.assert_called_once_with(".env.production")

    @patch("os.getenv")
    @patch("rag_sample_app.utils.load_dotenv")
    def test_load_development_env(self, mock_load_dotenv, mock_getenv):
        # ENVが設定されていない（デフォルトは "development"）
        mock_getenv.return_value = None

        # テスト対象のコードを実行
        load_environment()

        # 正しいファイルが読み込まれたか確認
        mock_load_dotenv.assert_called_once_with(".env.development")

    @patch("os.getenv")
    @patch("rag_sample_app.utils.load_dotenv")
    def test_load_staging_env(self, mock_load_dotenv, mock_getenv):
        # ENVが"staging"であることをシミュレート
        mock_getenv.return_value = "staging"

        # テスト対象のコードを実行
        load_environment()

        # 正しいファイルが読み込まれたか確認
        mock_load_dotenv.assert_called_once_with(".env.development")
