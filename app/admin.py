from django.contrib import admin
from .models import User, Workshop, Vehicle, Maintenance, MaintenanceItem, Notification

# Aqui estamos dizendo ao Django para mostrar essas tabelas no painel de administração
admin.site.register(User)
admin.site.register(Workshop)
admin.site.register(Vehicle)
admin.site.register(Maintenance)
admin.site.register(MaintenanceItem)
admin.site.register(Notification)