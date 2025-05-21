from django.contrib import admin
from app1.models import User,Customer,Broker,connection,feedback,Message, BlogCategory, BlogPost # Added BlogCategory, BlogPost
# Register your models here.

@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'author', 'category', 'status', 'published_date')
    list_filter = ('status', 'category', 'author')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_date'
    ordering = ('status', 'published_date')


admin.site.register(User) # Assuming default User admin is fine
admin.site.register(Customer)
admin.site.register(Broker)
admin.site.register(connection)
admin.site.register(feedback)
admin.site.register(Message)
