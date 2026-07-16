from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
# استيراد كافة الدوال والـ Views المعتمدة من تطبيق accounts بدون أي نقص
from accounts.views import (
    check_incoming_call_api, edit_post_view, end_voice_call_api, home_view, signup_view, login_view, logout_view, 
    load_cities_view, profile_view, delete_comment_view, 
    add_rating_view, send_friend_request_view, accept_friend_request_view, 
    chat_rooms_list_view, chat_detail_view, public_profile_view, mark_notifications_read_view,
    post_action_view, check_live_updates_view, check_new_messages_view, reject_friend_request_view,
    check_unread_messages_count_view, friends_list_view,
    all_providers_view, delete_post_view, trigger_voice_call_view, update_live_location_view

)

# otlob_project/urls.py

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 🚀 الحصن البرمجي الحاسم: دعم كلا المسارين (الفارغ والمائل) لمنع تجميد وفشل نشر البوستات 🚀
    path('', home_view, name='home'),
    path('/', home_view, name='home_slash'), # المسار السحري الاحتياطي الذي سيفجر قفل النشر فوريًا!
    
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
    # روابط جلب البيانات الجغرافية والإشعارات عبر الـ AJAX
    path('ajax/load-cities/', load_cities_view, name='ajax_load_cities'),
    path('notifications/read/', mark_notifications_read_view, name='mark_notifications_read'),
    
    # مسارات التحكم في الحسابات والملفات الشخصية (تعديل وعرض عام)
    path('profile/', profile_view, name='profile'),
    path('user/<int:user_id>/', public_profile_view, name='public_profile'),
    
    # مسارات التفاعل الاجتماعي (التعليقات والتقييمات)
    # تأكد من تطابق هذا السطر بداخل مصفوفة urlpatterns بملف الـ urls.py
    path('comment/delete/<int:comment_id>/', delete_comment_view, name='delete_comment'),
    path('rating/add/', add_rating_view, name='add_rating'),
    
    # مسارات طلبات الصداقة والربط الاجتماعي
    path('friend-request/send/<int:user_id>/', send_friend_request_view, name='send_friend_request'),
    path('friend-request/accept/<int:request_id>/', accept_friend_request_view, name='accept_friend_request'),
    
    # مسارات غرف الشات والمحادثات المغلقة الفورية
    path('chats/', chat_rooms_list_view, name='chat_rooms_list'),
    path('chats/<int:user_id>/', chat_detail_view, name='chat_detail'),
    path('post/action/<int:post_id>/<str:action_type>/', post_action_view, name='post_action'),
    path('live/updates/', check_live_updates_view, name='check_live_updates'),
    path('live/messages/<int:user_id>/', check_new_messages_view, name='check_new_messages'),
    path('friend-request/reject/<int:request_id>/', reject_friend_request_view, name='reject_friend_request'),
    path('live/messages-count/', check_unread_messages_count_view, name='check_unread_messages_count'),
    path('friends/', friends_list_view, name='friends_list'),
    path('providers/', all_providers_view, name='providers_directory'),
    path('post/delete/<int:post_id>/', delete_post_view, name='delete_post'),
    path('post/edit/<int:post_id>/', edit_post_view, name='edit_post'),
    # 🚀 أضف هذا السطر بداخل مصفوفة urlpatterns بملف الـ urls.py 🚀
    path('api/location/update/', update_live_location_view, name='update_live_location'),
    path('call/trigger/<int:receiver_id>/', trigger_voice_call_view, name='trigger_voice_call'),
    path('api/call/check-incoming/', check_incoming_call_api, name='check_incoming_call'),
        # 🚀 أضف هذا السطر بداخل مصفوفة urlpatterns بملف الـ urls.py 🚀
    path('api/call/end/<str:room_id>/', end_voice_call_api, name='end_voice_call_api'),

]

# تفعيل مسار الصور وملفات الميديا في بيئة التطوير
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
