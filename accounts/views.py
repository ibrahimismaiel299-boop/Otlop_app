from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import models # استيراد هام جداً لتشغيل الـ models.Q في الشات والتصفية!
from .forms import UserSignupForm, UserLoginForm, UserProfileForm, PostForm
from .models import User, Governorate, City, Category, Post, Comment, Rating, ChatMessage, FriendRequest, Notification, PostAction, VoiceCall
import math
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone


@login_required
def delete_comment_view(request, comment_id):
    """دالة حصنية لحذف التعليق؛ تمنح الصلاحية للمالك وللمدير العام إذا كان التعليق مسيئاً"""
    comment = get_object_or_404(Comment, id=comment_id)
    # التحقق: إذا كان الحاذف هو المالك، أو إذا كان الحساب إدارياً (مدير أو مشرف)
    if comment.user == request.user or request.user.is_staff or request.user.is_superuser:
        comment.delete()
    return redirect('home')

@login_required
def add_rating_view(request):
    """دالة لاستقبال تقييم النجوم عبر نقرة سريعة من العميل وحفظها برمجياً"""
    if request.method == 'POST':
        provider_id = request.POST.get('provider_id')
        stars = request.POST.get('stars')
        if provider_id and stars:
            provider = get_object_or_404(User, id=provider_id)
            # تحديث التقييم إذا كان موجوداً مسبقاً أو إنشاء تقييم جديد (Update or Create)
            Rating.objects.update_or_create(
                from_user=request.user,
                to_provider=provider,
                defaults={'stars': int(stars)}
            )
            return JsonResponse({'status': 'success', 'avg_rating': provider.get_average_rating})
    return JsonResponse({'status': 'error'}, status=400)

# بقية الدوال (signup_view, login_view, logout_view, load_cities_view, profile_view) تظل ثابتة ومستقرة كما هي تماماً...

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home') # منع المستخدم المسجل بالفعل من دخول صفحة التسجيل
        
    if request.method == 'POST':
        form = UserSignupForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user) # تسجيل دخول تلقائي للمستخدم فور إنشاء حسابه بنجاح
            return redirect('home')
    else:
        form = UserSignupForm()
        # السر هنا: نقوم بتفريغ قائمة المدن تماماً عند تحميل الصفحة لأول مرة 
        # لكي لا تظهر كل مدن مصر دفعة واحدة، وينتظر الكود اختيار المحافظة
        form.fields['city'].queryset = City.objects.none()
        
    return render(request, 'accounts/signup.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home') # إذا كان مسجلاً بالفعل يذهب للرئيسية
        
    error_message = None
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password) # فحص الحساب مشفراً في السيرفر
            
            if user is not None:
                login(request, user)
                
                # 🌟 تفعيل الدخول الدائم للأبد بداخل ذاكرة الهاتف (تذكرني) 🌟
                request.session.set_expiry(0) # 0 تعني تنتهي فقط عندما يختار المستخدم "خروج" يدوياً
                
                return redirect('home')

            else:
                error_message = "خطأ في اسم المستخدم أو كلمة المرور! تأكد من البيانات."
    else:
        form = UserLoginForm()
        
    return render(request, 'accounts/login.html', {'form': form, 'error_message': error_message})

def logout_view(request):
    logout(request) # تدمير الجلسة ومسح الكاش من المتصفح فورا لحماية الحساب
    return redirect('home')

def load_cities_view(request):
    """دالة ذكية لاستقبال رقم المحافظة عبر AJAX وإرجاع المدن التابعة لها فقط"""
    governorate_id = request.GET.get('governorate_id')
    cities = City.objects.filter(governorate_id=governorate_id)
    
    # تحويل جينات المدن لقائمة بسيطة تحتوي على الـ ID والاسم العربي لإرسالها للمتصفح
    cities_list = list(cities.values('id', 'name_ar'))
    return JsonResponse(cities_list, safe=False)


@login_required(login_url='login')
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        # تمرير instance=user يجعل دجانجو يقوم بتحديث الحساب الحالي بدلاً من إنشاء حساب جديد
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = UserProfileForm(instance=user)
        
    return render(request, 'accounts/profile.html', {'form': form, 'user': user})

# دالة لتعليم الإشعارات كمقروءة عند فتح لوحة التنبيهات
@login_required
def mark_notifications_read_view(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})

# ضع هذه الدوال المصححة تماماً في نهاية ملف accounts/views.py

@login_required
def send_friend_request_view(request, user_id):
    """دالة لإرسال طلب صداقة فوري للمخدم"""
    to_user = get_object_or_404(User, id=user_id)
    if request.user != to_user:
        # منع تكرار الطلب إذا كان موجوداً مسبقاً
        FriendRequest.objects.get_or_create(from_user=request.user, to_user=to_user)
    return redirect('home')

@login_required
def accept_friend_request_view(request, request_id):
    """دالة لقبول طلب الصداقة الوارد وتغيير حالته لأصدقاء"""
    freq = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)
    freq.status = 'accepted'
    freq.save()
    return redirect('home')

@login_required
def chat_rooms_list_view(request):
    """لوحة الشات الرئيسية لعرض كافة المستخدمين لبدء محادثة مغلقة"""
    users = User.objects.exclude(id=request.user.id)
    return render(request, 'accounts/chat_list.html', {'users': users})

@login_required
def chat_detail_view(request, user_id):
    """شاشة المحادثة الخاصة والمغلقة مصلحة ومؤمنة مئة بالمئة"""
    other_user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        message_text = request.POST.get('message')
        if message_text:
            ChatMessage.objects.create(sender=request.user, receiver=other_user, message=message_text)
            return redirect('chat_detail', user_id=user_id)
            
    # تم تصحيح اسم الموديل هنا بدقة لـ ChatMessage لإنهاء مشكلة التجميد
    messages = ChatMessage.objects.filter(
        (models.Q(sender=request.user) & models.Q(receiver=other_user)) |
        (models.Q(sender=other_user) & models.Q(receiver=request.user))
    )
    
    return render(request, 'accounts/chat_detail.html', {'other_user': other_user, 'chat_messages': messages})

# تحديث دالة البروفايل العام في ملف accounts/views.py لفحص حالة الصداقة وتمريرها
def public_profile_view(request, user_id):
    """عرض الملف الشخصي العام لأي فني شاملاً منشوراته وحالة الصداقة معه"""
    if request.user.is_authenticated and request.user.id == user_id:
        return redirect('profile')
        
    target_user = get_object_or_404(User, id=user_id)
    user_posts = Post.objects.filter(user=target_user)
    
    # 💡 فحص حالة الصداقة برمجياً بين الزائر وصاحب البروفايل 💡
    friend_status = None
    if request.user.is_authenticated:
        rel = FriendRequest.objects.filter(
            (models.Q(from_user=request.user) & models.Q(to_user=target_user)) |
            (models.Q(from_user=target_user) & models.Q(to_user=request.user))
        ).first()
        if rel:
            friend_status = rel.status # ستكون 'pending' أو 'accepted'
            
    return render(request, 'accounts/public_profile.html', {
        'target_user': target_user,
        'user_posts': user_posts,
        'friend_status': friend_status # تمرير الحالة لزر الواجهة الأمامية
    })

# accounts/views.py

@login_required
def post_action_view(request, post_id, action_type):
    """دالة تفاعلية لاستقبال الإعجابات وعدم الإعجابات وتحديث العدادات فوراً وبث حي"""
    post_obj = get_object_or_404(Post, id=post_id)
    if action_type in ['like', 'dislike']:
        # إذا كان المستخدم ضغط على نفس الزر سابقاً، نقوم بإلغاء التفاعل (Toggle)
        existing_action = PostAction.objects.filter(user=request.user, post=post_obj).first()
        if existing_action:
            if existing_action.action_type == action_type:
                existing_action.delete()
            else:
                existing_action.action_type = action_type
                existing_action.save()
        else:
            PostAction.objects.create(user=request.user, post=post_obj, action_type=action_type)
            
    # 🚀 التحديث السحري: إجبار السيرفر على جلب الأعداد "الحية والجديدة" مباشرة من الجدول المحدث 🚀
    fresh_likes = PostAction.objects.filter(post=post_obj, action_type='like').count()
    fresh_dislikes = PostAction.objects.filter(post=post_obj, action_type='dislike').count()
            
    return JsonResponse({
        'status': 'success',
        'likes': fresh_likes,      # ضخ الأعداد الحية الحقيقية فوريًا
        'dislikes': fresh_dislikes # ضخ الأعداد الحية الحقيقية فوريًا
    })

# أضف هذه الدوال في نهاية ملف views.py للتشغيل اللحظي

@login_required
def check_live_updates_view(request):
    """دالة ذكية تفحص وجود إشعارات أو طلبات صداقة جديدة كل بضع ثوانٍ خلف الكواليس"""
    unread_notifs = request.user.notifications.filter(is_read=False)
    pending_reqs = request.user.received_friend_requests.filter(status='pending')
    
    # تحويل البيانات لصيغة بسيطة يفهمها الجافا سكريبت
    notifs_data = [{'id': n.id, 'text': f"{n.sender.username} {n.get_notification_type_display()}"} for n in unread_notifs]
    reqs_data = [{'id': r.id, 'sender': r.from_user.username} for r in pending_reqs]
    
    return JsonResponse({
        'unread_count': unread_notifs.count(),
        'notifications': notifs_data,
        'pending_requests': reqs_data
    })

@login_required
def check_new_messages_view(request, user_id):
    """دالة تفحص وجود رسائل شات جديدة بينك وبين الشخص اللي فاتح محادثته حالياً"""
    other_user = get_object_or_404(User, id=user_id)
    # جلب الرسائل غير المقروءة المرسلة من الطرف الآخر لك
    new_msgs = ChatMessage.objects.filter(sender=other_user, receiver=request.user, is_read=False)
    
    msgs_data = [{'id': m.id, 'message': m.message} for m in new_msgs]
    # تعليم الرسائل كمقروءة فور جلبها للشاشة
    new_msgs.update(is_read=True)
    
    return JsonResponse({'new_messages': msgs_data})

@login_required
def reject_friend_request_view(request, request_id):
    """دالة لرفض طلب الصداقة وحذفه لبيئة نظيفة"""
    freq = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)
    freq.delete() # حذف الطلب تماماً عند الرفض
    return redirect('home')

# أضف هذه الدوال في نهاية ملف views.py لتشغيل عداد الشات وقائمة الأصدقاء

@login_required
def check_unread_messages_count_view(request):
    """دالة تحسب إجمالي الرسائل غير المقروءة الواردة للمستخدم لعرضها فوق أيقونة الشات"""
    count = ChatMessage.objects.filter(receiver=request.user, is_read=False).count()
    return JsonResponse({'unread_messages_count': count})

@login_required
def friends_list_view(request):
    """دالة لجلب وعرض قائمة الأصدقاء الحاليين للمستخدم (الطلبات المقبولة)"""
    # جلب الطلبات المقبولة سواء كان المستخدم هو المرسل أو المستقبل
    friends_relations = FriendRequest.objects.filter(
        (models.Q(from_user=request.user) | models.Q(to_user=request.user)) & 
        models.Q(status='accepted')
    )
    
    # استخراج حسابات الأصدقاء الفعليين من العلاقات
    friends = []
    for rel in friends_relations:
        if rel.from_user == request.user:
            friends.append(rel.to_user)
        else:
            friends.append(rel.from_user)
            
    return render(request, 'accounts/friends_list.html', {'friends': friends})

# accounts/views.py [جزء 1 من 2]
import math
from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.contrib.auth.decorators import login_required
from .models import Category, Post, User, Comment, FriendRequest, Governorate
from .forms import PostForm # تأكد من اسم الفورم عندك

def home_view(request):
    """دالة الرئيسية الشاملة المحدثة لتشغيل واجهة الأقسام والـ Subcategories والـ Live GPS"""
    # 1. معالجة عمليات الـ POST وحفظ المنشورات والتعليقات بدون ريفريش
    if request.user.is_authenticated and request.method == 'POST':
        if 'submit_post' in request.POST:
            form = PostForm(request.POST, request.FILES) 
            if form.is_valid():
                post = form.save(commit=False)
                post.user = request.user
                post.save()
                return redirect('home')
        elif 'submit_comment' in request.POST:
            post_id = request.POST.get('post_id')
            comment_content = request.POST.get('comment_content')
            parent_id = request.POST.get('parent_id')
            
            if comment_content and post_id:
                post_obj = get_object_or_404(Post, id=post_id)
                parent_obj = get_object_or_404(Comment, id=parent_id) if parent_id else None
                Comment.objects.create(post=post_obj, user=request.user, content=comment_content, parent=parent_obj)
                return redirect('home')

    # 2. تهيئة استمارة المنشور الافتراضية
    post_form = PostForm()
    if hasattr(post_form.fields, 'get') and 'category' in post_form.fields:
        post_form.fields['category'].queryset = Category.objects.all()
            
    # 3. جلب العدادات والإشعارات اللحظية للمسجلين
    unread_notifications, pending_friend_requests = [], []
    if request.user.is_authenticated:
        unread_notifications = request.user.notifications.filter(is_read=False)
        pending_friend_requests = request.user.received_friend_requests.filter(status='pending')
# accounts/views.py [جزء 2 من 2 والختامي]

    # 4. جلب الأقسام الرئيسية (التي ليس لها parent) والمحافظات الحية للشبكة الفخمة
    category_choices = Category.objects.filter(parent=None)
    gov_choices = Governorate.objects.all()
    selected_category = request.GET.get('category')
    
    # 5. تجميع التايم لاين وتفعيل الفلترة الشجرية العميقة للأقسام والـ Subcategories
    posts = Post.objects.all().order_by('-created_at')
    
    if request.user.is_authenticated and request.user.user_type == 'customer' and not selected_category:
        user_interests_ids = request.user.interests.values_list('id', flat=True)
        if user_interests_ids.exists():
            posts = posts.filter(category_id__in=user_interests_ids)

    # ميكانيكية دحرجة وفحص الأقسام الفرعية عند النقر
    subcategories = []
    category_obj = None
    if selected_category:
        category_obj = get_object_or_404(Category, id=selected_category)
        subcategories = category_obj.children.all() # جلب الأقسام الفرعية التابعة له
        
        sub_categories_ids = [category_obj.id]
        for child1 in subcategories:
            sub_categories_ids.append(child1.id)
            for child2 in child1.children.all():
                sub_categories_ids.append(child2.id)
        posts = posts.filter(category_id__in=sub_categories_ids)

    # 6. 🧭 رادار حساب المسافات الجغرافية التلقائي لاكتشاف أقرب الفنيين المتاحين حول العميل 🧭
    nearby_providers = []
    client_lat = request.GET.get('user_lat') or request.session.get('user_lat')
    client_lng = request.GET.get('user_lng') or request.session.get('user_lng')

    if client_lat and client_lng:
        c_lat, c_lng = float(client_lat), float(client_lng)
        # جلب الفنيين المتاحين أونلاين الحين والذين يملكون إحداثيات موقع صريحة بالسيرفر
        active_providers = User.objects.filter(user_type='provider', is_active_now=True, latitude__isnull=False, longitude__isnull=False)
        
        R = 6371.0 # نصف قطر الأرض بالكيلومترات
        for p in active_providers:
            dlat = math.radians(p.latitude - c_lat)
            dlon = math.radians(p.longitude - c_lng)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(c_lat)) * math.cos(math.radians(p.latitude)) * math.sin(dlon/2)**2
            distance = R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))
            
            # فلترة وتجهيز مقدمي الخدمة المتواجدين في نطاق 15 كم فقط من العميل
            if distance <= 15.0:
                p.computed_distance = round(distance, 1) # حقن المسافة في كائن اليوزر ديناميكياً
                nearby_providers.append(p)

    # 7. فحص ومطالعة علاقات الصداقة لحجب وتثبيت أزرار التفاعل بالتايم لاين
    for post in posts:
        post.friend_status = None
        if request.user.is_authenticated:
            rel = FriendRequest.objects.filter(
                (models.Q(from_user=request.user) & models.Q(to_user=post.user)) |
                (models.Q(from_user=post.user) & models.Q(to_user=request.user))
            ).first()
            if rel: 
                post.friend_status = rel.status

    # 8. 🔒 حزمة الـ Context الأصلية والمعدلة بالكامل لتصميم الشبكة الفخمة 🔒
    context = {
        'gov_choices': gov_choices,
        'category_choices': category_choices,
        'selected_category': int(selected_category) if selected_category else None,
        'category_obj': category_obj,
        'subcategories': subcategories,
        'posts': posts,
        'post_form': post_form,
        'unread_notifications': unread_notifications,
        'pending_requests': pending_friend_requests,
        'nearby_providers': nearby_providers, # تجميع أقرب الفنيين المتاحين
    }
    return render(request, 'accounts/home.html', context)



# 2. 🚀 دالة صفحة دليل الفنيين المستقلة الجديدة تماماً (تستقبل البحث الذكي والفلترة) 🚀
def all_providers_view(request):
    selected_gov = request.GET.get('governorate')
    search_query = request.GET.get('q', '').strip()

    providers = User.objects.filter(user_type='provider')
    
    if selected_gov:
        providers = providers.filter(governorate_id=selected_gov)
        
    if search_query:
        providers = providers.filter(
            models.Q(username__icontains=search_query) |       
            models.Q(phone_number__icontains=search_query) |   
            models.Q(category__name_ar__icontains=search_query) 
        ).distinct()

    context = {
        'providers': providers,
        'gov_choices': Governorate.objects.all(),
        'selected_gov': int(selected_gov) if selected_gov else None,
        'search_query': search_query,
    }
    return render(request, 'accounts/providers_directory.html', context)
# 🗑️ دالة حذف المنشور الحصنية (تتحقق أمنياً أن الحاذف هو صاحب البوست) 🗑️
@login_required
def delete_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.user == request.user:
        post.delete()
    return redirect('home')

# 📝 دالة تعديل المنشور الفورية 📝
@login_required
def edit_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.user != request.user:
        return redirect('home')
        
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            post.content = content
            # التقاط الميديا المحدثة إن وجدت
            if request.FILES.get('image'): post.image = request.FILES.get('image')
            if request.FILES.get('video'): post.video = request.FILES.get('video')
            post.save()
            return redirect('home')
    return redirect('home')



# 🚀 أ) API استقبال وتحديث الموقع الجغرافي لايف من الموبايل 🚀
@csrf_exempt
@login_required
def update_live_location_view(request):
    if request.method == 'POST':
        # استقبال حالة الزر والإحداثيات القادمة من نظام الـ GPS بهاتف الفني
        is_active = request.POST.get('is_active_now') # 'true' or 'false'
        lat = request.POST.get('latitude')
        lng = request.POST.get('longitude')
        
        user = request.user
        if is_active is not None:
            user.is_active_now = (is_active.lower() == 'true')
            
        if lat and lng:
            user.latitude = float(lat)
            user.longitude = float(lng)
            user.last_location_update = timezone.now()
            
        user.save()
        return JsonResponse({
            "status": "success", 
            "is_active_now": user.is_active_now,
            "msg": "تم تحديث موقعك الجغرافي وحالة الإتاحة لايف بنجاح 🟢"
        })
    return JsonResponse({"status": "error", "msg": "طلب غير مسموح به"}, status=400)

# 🚀 ب) دالة حساب المسافة الرياضية (Haversine Formula) بالملي 🚀
def calculate_distance(lat1, lon1, lat2, lon2):
    # نصف قطر الكرة الأرضية بالكيلومترات
    R = 6371.0 
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c # المسافة الدقيقة بالكيلومترات

import uuid
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse

@login_required
def trigger_voice_call_view(request, receiver_id):
    """دالة تحويل العميل تلقائياً إلى مكالمة صوتية مشفرة عبر غرف الشات"""
    receiver_user = get_object_or_404(User, id=receiver_id)
    
    # حظر أمني: منع الاتصال إذا كان الفني أطفأ زر الإتاحة
    if not receiver_user.is_active_now:
        return JsonResponse({"status": "error", "msg": "عذراً، مقدم الخدمة غير متاح للاتصال حالياً!"}, status=400)
        
    # توليد معرف مشفر فريد لغرفة الاتصال الصوتي عبر الإنترنت WebRTC
    generated_room = f"call_{uuid.uuid4().hex[:12]}"
    
    # تسجيل المكالمة في قاعدة البيانات لإطلاق الرنين بجهاز الفني
    VoiceCall.objects.create(
        caller=request.user,
        receiver=receiver_user,
        room_id=generated_room,
        status='ringing'
    )
    
    # توجيه العميل فوراً لغرفة الشات المفتوحة مع حقن وسم بدء الاتصال الصوتي
    return redirect(f"/chats/{receiver_user.id}/?initiate_call={generated_room}")

@login_required
def check_incoming_call_api(request):
    """رادار يفحص بالثانية وجود مكالمة صوتية 'جاري الرنين' موجهة للحساب الحالي"""
    incoming = VoiceCall.objects.filter(receiver=request.user, status='ringing').last()
    if incoming:
        return JsonResponse({
            "status": "incoming",
            "caller_name": incoming.caller.username,
            "room_id": incoming.room_id
        })
    return JsonResponse({"status": "no_calls"})

@csrf_exempt
@login_required
def end_voice_call_api(request, room_id):
    """API حاسم لتحديث حالة المكالمة فوراً في قاعدة البيانات إلى منتهية لكسر حلقة الرنين"""
    if request.method == 'POST':
        action = request.POST.get('action') # 'rejected' أو 'ended'
        # البحث عن المكالمة المعلقة وتحديث حالتها فوريّاً
        calls = VoiceCall.objects.filter(room_id=room_id)
        if calls.exists():
            for call in calls:
                call.status = action if action in ['rejected', 'ended'] else 'ended'
                call.save()
            return JsonResponse({"status": "success", "msg": "تم إنهاء المكالمة وتطهير جداول قاعدة البيانات 🟢"})
    return JsonResponse({"status": "error", "msg": "طلب غير مسموح به"}, status=400)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import User

# accounts/views.py

def providers_map_view(request):
    """دالة جلب الفنيين المتاحين لايف الحين وعرض إحداثياتهم الجغرافية على الخريطة للجميع مع صمام أمان للزوار"""
    # جلب الفنيين المشغلين لزر "متاح الآن" والذين يملكون إحداثيات موقع صريحة
    active_providers = User.objects.filter(
        user_type='provider', 
        is_active_now=True,
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    return render(request, 'accounts/providers_map.html', {
        'providers': active_providers,
        'is_logged_in': request.user.is_authenticated  # تمرير حالة تسجيل الدخول فوريّاً للفرونت إند
    })
