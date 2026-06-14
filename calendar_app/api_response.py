from rest_framework.response import Response

def ok(data=None, msg='success', code=200, status_code=200):
    return Response({
        'code': code,
        'msg': msg,
        'data': data if data is not None else {}
    }, status=status_code)

def fail(msg='error', code=400, data=None, status_code=400):
    return Response({
        'code': code,
        'msg': msg,
        'data': data if data is not None else {}
    }, status=status_code)