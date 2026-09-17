from .models import BusinessLock
def lock_domain(key):
    """Deve ser chamado dentro de transaction.atomic; serializa alterações no PostgreSQL."""
    BusinessLock.objects.get_or_create(key=key)
    return BusinessLock.objects.select_for_update().get(key=key)
