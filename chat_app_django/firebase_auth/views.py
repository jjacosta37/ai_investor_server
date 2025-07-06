from rest_framework.decorators import api_view
from firebase_admin import auth
from rest_framework.response import Response


# Create your views here.

@api_view(['GET'])
def delete_user(request):
    current_user = request.user
    uid = current_user.username
    try:
        current_user.delete()
        auth.delete_user(uid)
    except Exception as e:
        return Response({"Exception": str(e)})
    return Response({})
