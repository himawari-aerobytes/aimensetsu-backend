import jwt
import requests
from functools import wraps
from django.http import JsonResponse
from jwt.algorithms import RSAAlgorithm
import os
from dotenv import load_dotenv
from django.contrib.auth import get_user_model
from django.db import IntegrityError

# 開発環境か本番環境かに応じてファイルを指定
environment = os.getenv('ENV', 'development')
if environment == 'production':
    load_dotenv('.env.production')
else:
    load_dotenv('.env.development')

User = get_user_model()  # Djangoのユーザーモデルを取得

COGNITO_REGION = 'ap-northeast-1'
COGNITO_USER_POOL_ID = os.environ["COGNITO_USER_POOL_ID"]
COGNITO_APP_CLIENT_ID = os.environ["COGNITO_CLIENT_ID"]
COGNITO_ISSUER = f'https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}'
COGNITO_JWKS_URL = f'{COGNITO_ISSUER}/.well-known/jwks.json'

def get_cognito_public_keys():
    response = requests.get(COGNITO_JWKS_URL)
    jwks = response.json()
    keys = {}
    for key in jwks['keys']:
        kid = key['kid']
        public_key = RSAAlgorithm.from_jwk(key)
        keys[kid] = public_key
    return keys

def jwt_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        auth_header = request.META.get('HTTP_AUTHORIZATION', None)
        if not auth_header:
            return JsonResponse({'error': 'Authorization header missing'}, status=401)
        try:
            token_type, token = auth_header.split()
            if token_type.lower() != 'bearer':
                raise ValueError('Invalid token type')
        except ValueError:
            return JsonResponse({'error': 'Invalid Authorization header format'}, status=401)

        try:
            public_keys = get_cognito_public_keys()
            headers = jwt.get_unverified_header(token)
            public_key = public_keys.get(headers['kid'])
            
            if public_key is None:
                return JsonResponse({'error': 'Public key not found'}, status=401)

            decoded_token = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=COGNITO_APP_CLIENT_ID,
                issuer=COGNITO_ISSUER
            )

                  # 'cognito:username' または 'sub' からユーザーを取得
            username = decoded_token.get('cognito:username', decoded_token.get('sub'))
            email = decoded_token.get('email', '')

            try:
                # ユーザーが存在しなければ作成
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={'email': email}
                )
                request.user = user

            except IntegrityError:
                return JsonResponse({'error': 'Error creating or retrieving user'}, status=500)

            
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token has expired'}, status=401)
        except jwt.InvalidTokenError as e:
            return JsonResponse({'error': 'Invalid token', 'details': str(e)}, status=401)

        return view_func(request, *args, **kwargs)
    return _wrapped_view
