from django.test import TestCase, RequestFactory
from unittest.mock import patch, MagicMock
from django.http import JsonResponse
import jwt
from rag_sample_app.utils import jwt_required, get_cognito_public_keys
from django.contrib.auth import get_user_model
import json  # 追加

User = get_user_model()

SAMPLE_TOKEN = "eyJraWQiOiIxMjM0ZXhhbXBsZT0iLCJhbGciOiJSUzI1NiIsImt0eSI6IlJTQSIsImUiOiJBUUFCIiwibiI6IjEyMzQ1Njc4OTAiLCJ1c2UiOiJzaWcifQ.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMn0.qpldgWTqr6dA_vZCZcmnJgV7JPanhBzEloQA9CQuyLMLfi9u1T0y8Kr6uK4j-WiDHvqtzo5zoFBuwqO-o1adnAnTKmqKj2RHU3bXqXKtawLkMC-E_cwGrr_XBQQSMnfw8OX2C8tFr5nxr1Bi8KD2G4T4_9pqv6fz3STDTPeMOSZ-kx-p2lJYJVexxPfSg1j69Yc5Jd6nT7eJakzu09CTwcBdlKMGMgfKjzuUPWWc9gnO21PQgYPTP8UAohM_mvNyejYRlrluJBrG01faOj_WMpLR2rv9tg0s-HdjoR3FGlmMnJnssu3v5YF1wnPS2HPNaAZuu_12NDR5BjH_ulOiXA"

class JWTRequiredDecoratorTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch('rag_sample_app.utils.get_cognito_public_keys')
    def test_missing_authorization_header(self, mock_get_cognito_public_keys):
        request = self.factory.get('/api/some-endpoint/')
        response = jwt_required(lambda r: JsonResponse({'success': 'True'}))(request)
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data, {'error': 'Authorization header missing'})

    @patch('rag_sample_app.utils.get_cognito_public_keys')
    def test_invalid_authorization_header_format(self, mock_get_cognito_public_keys):
        request = self.factory.get('/api/some-endpoint/', HTTP_AUTHORIZATION='InvalidTokenFormat')
        response = jwt_required(lambda r: JsonResponse({'success': 'True'}))(request)
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data, {'error': 'Invalid Authorization header format'})

    @patch('rag_sample_app.utils.get_cognito_public_keys')
    def test_invalid_token_type(self, mock_get_cognito_public_keys):
        request = self.factory.get('/api/some-endpoint/', HTTP_AUTHORIZATION='Basic '+SAMPLE_TOKEN)
        response = jwt_required(lambda r: JsonResponse({'success': 'True'}))(request)
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data, {'error': 'Invalid token type'})

    @patch('rag_sample_app.utils.jwt.decode')
    @patch('rag_sample_app.utils.get_cognito_public_keys')
    def test_expired_token(self, mock_get_cognito_public_keys, mock_jwt_decode):
        mock_jwt_decode.side_effect = jwt.ExpiredSignatureError()
        request = self.factory.get('/api/some-endpoint/', HTTP_AUTHORIZATION='Bearer '+SAMPLE_TOKEN)
        response = jwt_required(lambda r: JsonResponse({'success': 'True'}))(request)
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data, {'error': 'Token has expired'})

    @patch('rag_sample_app.utils.jwt.decode')
    @patch('rag_sample_app.utils.get_cognito_public_keys')
    def test_invalid_token(self, mock_get_cognito_public_keys, mock_jwt_decode):
        mock_jwt_decode.side_effect = jwt.InvalidTokenError('Invalid token')
        invalid_token = "eyJraWQiOiIxMjM0ZXhhbXBsZT0iLCJhbGciOiJSUzI1NiIsImt0eSI6IlJTQSIsImUiOiJBUUFCIiwibiI6IjEyMzQ1Njc4OTAiLCJ1c2UiOiJzaWcifQ.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMn0.qpldgWTqr6dA_vZCZcmnJgV7JPanhBzEloQA9CQuyLMLfi9u1T0y8Kr6uK4j-WiDHvqtzo5zoFBuwqO-o1adnAnTKmqKj2RHU3bXqXKtawLkMC-E_cwGrr_XBQQSMnfw8OX2C8tFr5nxr1Bi8KD2G4T4_9pqv6fz3STDTPeMOSZ-kx-p2lJYJVexxPfSg1j69Yc5Jd6nT7eJakzu09CTwcBdlKMGMgfKjzuUPWWc9gnO21PQgYPTP8UAohM_mvNyejYRlrluJBrG01faOj_WMpLR2rv9tg0s-HdjoR3FGlmMnJnssu3v5YF1wnPS2HPNaAZuu_12NDR5BjH_ulOiXA"
        request = self.factory.get('/api/some-endpoint/', HTTP_AUTHORIZATION='Bearer '+invalid_token)
        response = jwt_required(lambda r: JsonResponse({'success': 'True'}))(request)
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data, {'error': 'Invalid token', 'details': 'Invalid token'})

    @patch('rag_sample_app.utils.get_cognito_public_keys')
    @patch('rag_sample_app.utils.jwt.decode')
    def test_valid_token_creates_user(self, mock_jwt_decode, mock_get_cognito_public_keys):
        # モックのCognitoのパブリックキーとJWTデコードの戻り値を設定
        mock_jwt_decode.return_value = {
            'cognito:username': 'testuser',
            'email': 'testuser@example.com'
        }
        mock_get_cognito_public_keys.return_value = {'kid': 'mocked_public_key'}

        request = self.factory.get('/api/some-endpoint/', HTTP_AUTHORIZATION='Bearer '+SAMPLE_TOKEN)

        # 初期ユーザーデータの存在確認
        self.assertEqual(User.objects.filter(username='testuser').count(), 0)

        # デコレータ適用後のレスポンス
        response = jwt_required(lambda r: JsonResponse({'success': 'True'}))(request)

        # ユーザーが作成されていることの確認
        self.assertEqual(User.objects.filter(username='testuser').count(), 1)

        # レスポンスの確認
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data, {'success': 'True'})

    @patch('rag_sample_app.utils.get_cognito_public_keys')
    @patch('rag_sample_app.utils.jwt.decode')
    def test_valid_token_existing_user(self, mock_jwt_decode, mock_get_cognito_public_keys):
        # モックのCognitoのパブリックキーとJWTデコードの戻り値を設定
        mock_jwt_decode.return_value = {
            'cognito:username': 'existinguser',
            'email': 'existinguser@example.com'
        }
        mock_get_cognito_public_keys.return_value = {'kid': 'mocked_public_key'}

        # 既存ユーザーを作成
        user = User.objects.create(username='existinguser', email='existinguser@example.com')

        request = self.factory.get('/api/some-endpoint/', HTTP_AUTHORIZATION='Bearer '+SAMPLE_TOKEN)

        # デコレータ適用後のレスポンス
        response = jwt_required(lambda r: JsonResponse({'success': 'True'}))(request)

        # ユーザーが再作成されていないことを確認
        self.assertEqual(User.objects.filter(username='existinguser').count(), 1)

        # レスポンスの確認
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data, {'success': 'True'})