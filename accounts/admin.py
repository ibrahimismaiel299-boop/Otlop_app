from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Governorate, City, Category

# تسجيل جدول المحافظات للتحكم به
@admin.register(Governorate)
class GovernorateAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_ar', 'name_en')
    search_fields = ('name_ar', 'name_en')

# تسجيل جدول المدن للتحكم به
@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_ar', 'governorate')
    list_filter = ('governorate',)
    search_fields = ('name_ar', 'name_en')

from django.contrib import admin
from .models import Category # تأكد من استيراد الموديل المحدث

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    # 🌟 عرض الأسطر الأساسية: الاسم، والأيقونة، والبروفايل الشجري (القسم الأب)
    list_display = ('id', 'name_ar', 'parent', 'icon_emoji', 'created_at')
    
    # تفعيل شريط الفلترة الجانبي بناءً على الأقسام الرئيسية والأبوية لسهولة الإدارة
    list_filter = ('parent', 'created_at')
    
    # تفعيل شريط البحث الذكي بالاسم العربي أو الإنجليزي في لوحة التحكم
    search_fields = ('name_ar', 'name_en')
    
    # ترتيب الأقسام: الأحدث أولاً
    ordering = ('-created_at',)


# تعديل شاشات المستخدمين لتشمل التخصص والموقع الجديدين
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'phone_number', 'user_type', 'category', 'governorate', 'city', 'verification_status', 'is_verified_provider')
    list_filter = ('user_type', 'verification_status', 'governorate', 'category')
    
    fieldsets = UserAdmin.fieldsets + (
        ('بيانات التخصص والموقع الجغرافي', {
            'fields': ('phone_number', 'user_type', 'category', 'governorate', 'city', 'address_details')
        }),
        ('بيانات التوثيق والأمان', {
            'fields': ('national_id', 'id_front_image', 'id_back_image', 'verification_status')
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('البيانات الأساسية للمنصة', {
            'fields': ('phone_number', 'user_type', 'category', 'governorate', 'city', 'verification_status'),
        }),
    )

admin.site.register(User, CustomUserAdmin)
