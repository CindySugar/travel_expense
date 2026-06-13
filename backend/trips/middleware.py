from django.http import HttpResponse


class ApiCorsMiddleware:
    allowed_origins = {
        'http://127.0.0.1:5173',
        'http://localhost:5173',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/') and request.method == 'OPTIONS':
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if request.path.startswith('/api/'):
            origin = request.headers.get('Origin')
            if origin in self.allowed_origins:
                response['Access-Control-Allow-Origin'] = origin
                response['Access-Control-Allow-Credentials'] = 'true'
                response['Vary'] = 'Origin'
            response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PATCH, DELETE, OPTIONS'

        return response
