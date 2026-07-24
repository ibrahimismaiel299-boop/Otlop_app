from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# استيراد كافة الدوال والـ Views المعتمدة من تطبيق accounts بدون أي نقص
from accounts.views import (
    check_incoming_call_api, edit_post_view, end_voice_call_api, home_view, providers_map_view, save_fcm_token_view, signup_view, login_view, logout_view, 
    load_cities_view, profile_view, delete_comment_view, 
    add_rating_view, send_friend_request_view, accept_friend_request_view, 
    chat_rooms_list_view, chat_detail_view, public_profile_view, mark_notifications_read_view,
    post_action_view, check_live_updates_view, check_new_messages_view, reject_friend_request_view,
    check_unread_messages_count_view, friends_list_view,
    all_providers_view, delete_post_view, trigger_voice_call_view, update_live_location_view, remove_friend_view, google_local_mock_view
)

urlpatterns = [
    # ⚙️ لوحة الإدارة للآدمن والسوبر يوزر
    path('admin/', admin.site.core_urls if hasattr(admin.site, 'core_urls') else admin.site.urls),
    
    # 🚀 حقن محرك مسارات Allauth العالمية لتشغيل ربط الـ Gmail بنقرة واحدة 🚀
    path('accounts/', include('allauth.urls')), 
    
    # 🎯 دعم مسارات التايم لاين والنشر المباشر لمنع التجميد فوريًا 🎯
    path('', home_view, name='home'),
    path('home/', home_view, name='home_redirect'),  
    
    # مسارات الحسابات المعتمدة للبراند
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('friend/remove/<int:user_id>/', remove_friend_view, name='remove_friend'),
    
    # روابط جلب البيانات الجغرافية والإشعارات عبر الـ AJAX لايف
    path('ajax/load-cities/', load_cities_view, name='ajax_load_cities'),
    path('notifications/read/', mark_notifications_read_view, name='mark_notifications_read'),
    # مسارات التحكم في الحسابات والملفات الشخصية (تعديل وعرض عام)
    path('profile/', profile_view, name='profile'),
    path('user/<int:user_id>/', public_profile_view, name='public_profile'),
    
    # مسارات التفاعل الاجتماعي (التعليقات والتقييمات وحذف الردود)
    path('comment/delete/<int:comment_id>/', delete_comment_view, name='delete_comment'),
    path('rating/add/', add_rating_view, name='add_rating'),
    
    # مسارات طلبات الصداقة والربط الاجتماعي لايف
    path('friend-request/send/<int:user_id>/', send_friend_request_view, name='send_friend_request'),
    path('friend-request/accept/<int:request_id>/', accept_friend_request_view, name='accept_friend_request'),
    
    # مسارات غرف الشات والمحادثات المغلقة الفورية
    path('chats/', chat_rooms_list_view, name='chat_rooms_list'),
    path('chats/<int:user_id>/', chat_detail_view, name='chat_detail'),
    path('post/action/<int:post_id>/<str:action_type>/', post_action_view, name='post_action'),
    
    # محركات التحديث والـ Polling الدوري اللحظي للعدادات
    path('live/updates/', check_live_updates_view, name='check_live_updates'),
    path('live/messages/<int:user_id>/', check_new_messages_view, name='check_new_messages'),
    path('friend-request/reject/<int:request_id>/', reject_friend_request_view, name='reject_friend_request'),
    path('live/messages-count/', check_unread_messages_count_view, name='check_unread_messages_count'),
    path('friends/', friends_list_view, name='friends_list'),
    path('providers/', all_providers_view, name='providers_directory'),
    
    # إدارة المنشورات والبوستات (حذف وتعديل)
    path('post/delete/<int:post_id>/', delete_post_view, name='delete_post'),
    path('post/edit/<int:post_id>/', edit_post_view, name='edit_post'),
    
    # محركات الـ VoIP والمكالمات الصوتية واللوكيشن الجغرافي السحابي المطور
    path('api/location/update/', update_live_location_view, name='update_live_location'),
    path('call/trigger/<int:receiver_id>/', trigger_voice_call_view, name='trigger_voice_call'),
    path('api/call/check-incoming/', check_incoming_call_api, name='check_incoming_call'),
    path('api/call/end/<str:room_id>/', end_voice_call_api, name='end_voice_call_api'),
    path('providers/map/', providers_map_view, name='providers_map'),
    path('api/save-token/', save_fcm_token_view, name='save_fcm_token'),
    path('accounts/google/login/local-mock/', google_local_mock_view, name='google_local_mock'),
    
]

# تفعيل مسار الصور وملفات الميديا في بيئة التطوير
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

