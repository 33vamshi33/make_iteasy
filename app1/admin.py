from django.contrib import admin
from app1.models import User,Customer,Broker,connection,feedback,Message
# Register your models here.


admin.site.register(User)
admin.site.register(Customer)
admin.site.register(Broker)
admin.site.register(connection)
admin.site.register(feedback)
admin.site.register(Message)
