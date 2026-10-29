from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .models import Perfil


def cargo(usuario):
    if usuario.is_superuser:
        return 'presidente'
    if not usuario.is_authenticated:
        return ''
    try:
        return usuario.perfil.cargo
    except Perfil.DoesNotExist:
        return 'cooperado'


def pode_vender(usuario):
    return cargo(usuario) in ['diretoria', 'presidente']


def pode_gerir(usuario):
    return cargo(usuario) == 'presidente'


def exige_cargo(*cargos):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if cargo(request.user) not in cargos:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


def contexto_acesso(request):
    return {'cargo_atual': cargo(request.user).capitalize(), 'pode_vender': pode_vender(request.user), 'pode_gerir': pode_gerir(request.user)}
