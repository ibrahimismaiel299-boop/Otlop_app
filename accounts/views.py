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

# accounts/views.py [دمج محرك الـ Push Notifications لـ Firebase مع طلبات الصداقة]
import requests
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import User, FriendRequest, Notification # تأكد من مطابقة الموديلات عندك

def send_fcm_push_notification(user_token, title, body, click_url):
    """دالة إرسال الإشعار اللحظي السحابي عبر سيرفرات جوجل Firebase لتظهر على شاشة القفل"""
    server_key = 'YOUR_FIREBASE_SERVER_KEY' # سحب المفتاح السري من كونسول Firebase الخاص بك لاحقاً
    headers = {
        'Authorization': 'key=' + server_key,
        'Content-Type': 'application/json',
    }
    payload = {
        'to': user_token, # التوكن المحفوظ الخاص بجوال المستخدم المتلقي الحين
        'data': {
            'title': title,
            'body': body,
            'click_action': click_url
        }
    }
    try:
        # ضخ الطلب الصاروخي لجوجل بالخلفية
        requests.post('https://googleapis.com', headers=headers, data=json.dumps(payload), timeout=5)
    except Exception as e:
        print(f"Firebase Push Failed: {e}")

@login_required
def send_friend_request_view(request, user_id):
    """دالة إرسال طلب الصداقة المحدثة لتفجير جرس الأعلى وإشعارات شاشة قفل الهاتف معاً لايف فوريّاً"""
    to_user = get_object_or_404(User, id=user_id)
    
    # صمام أمان لمنع تكرار إرسال الطلب أو إرساله لنفسك
    if to_user != request.user:
        req, created = FriendRequest.objects.get_or_create(from_user=request.user, to_user=to_user)
        
        if created:
            req.status = 'pending'
            req.save()
            
            # 1. 🔔 حقن وسجل الإشعار اللحظي في قاعدة البيانات للجرس الداخلي بالأعلى 🔔
            Notification.objects.create(
                user=to_user, 
                text=f" قام المستخدم {request.user.username} بإرسال طلب صداقة إليك 👥",
                is_read=False
            )
            
            # 2. 🚀 📱 تفجير وبث الإشعار السحابي لشاشة هاتف المتلقي وهي مقفلة عبر Firebase 🚀 📱
            # صمام الأمان: يفحص لو الفني يملك حقل fcm_token (تأكد من مطابقة اسم حقل التوكن بجدول اليوزر عندك)
            if hasattr(to_user, 'fcm_token') and to_user.fcm_token:
                push_title = "طلب صداقة جديد في Otlop 👥⚡"
                push_body = f"الحق العروض! قام المستخدم {request.user.username} بإرسال طلب صداقة إليك.. ادخل الحين لقبوله 🤝"
                click_url = f"/public-profile/{request.user.id}/" # رابط طيران العميل فور نقر الإشعار
                
                # استدعاء صعق وجلد سيرفر Firebase بالخلفية
                send_fcm_push_notification(to_user.fcm_token, push_title, push_body, click_url)
            
            messages.success(request, "تم إرسال طلب الصداقة وتنبيه المستخدم على هاتفه بنجاح! ⏳")
        else:
            messages.info(request, "هناك طلب صداقة معلق بالفعل بينكما.")
            
    return redirect('public_profile', user_id=user_id)

    


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

# accounts/views.py [دمج إشعارات شاشة قفل الهاتف لـ Firebase بداخل دالة تفاصيل المحادثة المعتمدة]

@login_required
def chat_detail_view(request, user_id):
    """شاشة المحادثة الخاصة والمغلقة مصلحة ومؤمنة ومحقونة بإشعارات شاشة القفل السحابية لايف فوريّاً"""
    other_user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        message_text = request.POST.get('message')
        if message_text:
            # 1. صناعة وحفظ الرسالة الجديدة في قاعدة البيانات بنجاح
            ChatMessage.objects.create(sender=request.user, receiver=other_user, message=message_text)
            
            # 2. 🚀 📱 تفجير وبث إشعار شات لحظي لشاشة هاتف المتلقي وهي مقفلة عبر Firebase 🚀 📱
            # صمام الأمان: يفحص لو الفني المستهدف (other_user) يملك توكن، يصعق Firebase فوريّاً
            if hasattr(other_user, 'fcm_token') and other_user.fcm_token:
                push_title = f"رسالة جديدة من {request.user.username} 💬⚡"
                push_body = f"لديك رسالة خاصة جديدة: '{message_text[:40]}...' ادخل الحين للرد عليها ✈️"
                click_url = "/chat/rooms/" # رابط طيران العميل لصفحة المراسلات العامة فور نقر الإشعار
                
                # استدعاء دالة الـ Push السحابية الفولاذية
                send_fcm_push_notification(other_user.fcm_token, push_title, push_body, click_url)
                
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
    """الدالة الذهبية المصلحة لضخ عدادات الإشعارات وطلبات الصداقة لايف للفرونت إند بالملي ثانية"""
    unread_notifs = request.user.notifications.filter(is_read=False)
    pending_reqs = request.user.received_friend_requests.filter(status='pending')
    
    # 🚀 صمام أمان محمي: التأكد من وجود sender لمنع الـ Null Crash الخلفي بالسيرفر 🚀
    notifs_data = []
    for n in unread_notifs:
        sender_name = n.sender.username if hasattr(n, 'sender') and n.sender else "Otlop"
        notifs_data.append({
            'id': n.id, 
            'text': f"{sender_name} - {n.text}"
        })
        
    reqs_data = [{'id': r.id, 'sender': r.from_user.username} for r in pending_reqs]
    
    # 🎯 تجميع الـ JSON بالمفاتيح المتطابقة مئة بالمئة مع الجافا سكريبت بالواجهة 🎯
    return JsonResponse({
        'unread_notifications_count': unread_notifs.count(), # المسمى المطابق للـ JS بالملي
        'unread_count': unread_notifs.count(),               # مسار احتياطي للأمان
        'notifications': notifs_data,
        'pending_requests': reqs_data,
        'pending_requests_count': pending_reqs.count()
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

# accounts/views.py [جزء 1 من 2 لـ home_view المطور والنهائي]
import math
from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from .models import Category, Post, User, Comment, FriendRequest, Governorate
from .forms import PostForm # تأكد من مطابقة اسم الفورم عندك

def home_view(request):
    """دالة الرئيسية الشاملة والمحدثة: حقن القسم العام كديفولت والربط التلقائي للكروت بالـ GPS والبوستات"""
    
    # 1. 🌟 صناعة وفحص وجود القسم العام (General) ليكون الديفولت القسري للبيانات 🌟
    general_category, created = Category.objects.get_or_create(
        name_ar="القسم العام",
        defaults={
            'name_en': "General",
            'icon_emoji': "🌐",
            'parent': None
        }
    )

    # 2. استقبال معرف القسم والموقع الجغرافي الذي تضخه كروت وأزرار الواجهة
    selected_category = request.GET.get('category')
    client_lat = request.GET.get('user_lat') or request.session.get('user_lat')
    client_lng = request.GET.get('user_lng') or request.session.get('user_lng')

    # حفظ إحداثيات موقع العميل في الجلسة (Session) لدوام الفلترة التلقائية عند إعادة التحميل
    if request.GET.get('user_lat') and request.GET.get('user_lng'):
        request.session['user_lat'] = request.GET.get('user_lat')
        request.session['user_lng'] = request.GET.get('user_lng')

    # 3. معالجة عمليات الـ POST وحفظ المنشورات والتعليقات بالقسم المؤتمت والذكي
    if request.user.is_authenticated and request.method == 'POST':
        if 'submit_post' in request.POST:
            form = PostForm(request.POST, request.FILES) 
            if form.is_valid():
                post = form.save(commit=False)
                post.user = request.user
                
                # 🚀 حقن وتلقيم القسم تلقائياً: يقرأ من حقل الكارت المخفي بالواجهة، وإذا كان فارغاً يأخذ القسم العام 🚀
                hidden_cat_id = request.POST.get('category_id_hidden')
                if hidden_cat_id and hidden_cat_id.strip() != "":
                    post.category_id = int(hidden_cat_id)
                else:
                    post.category_id = general_category.id
                
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

    # تهيئة استمارة المنشور الافتراضية
    post_form = PostForm()
    if hasattr(post_form.fields, 'get') and 'category' in post_form.fields:
        post_form.fields['category'].queryset = Category.objects.all()
            
    # جلب العدادات والإشعارات اللحظية للمسجلين
    unread_notifications, pending_friend_requests = [], []
    if request.user.is_authenticated:
        unread_notifications = request.user.notifications.filter(is_read=False)
        pending_friend_requests = request.user.received_friend_requests.filter(status='pending')
# accounts/views.py [جزء 2 من 2 والختامي]

    # 4. جلب الأقسام الرئيسية (التي ليس لها parent) والمحافظات الحية للشبكة الفخمة
    # 4. جلب الأقسام الرئيسية (التي ليس لها parent) مع إجبار القسم العام على التصدر أولاً 🚀
    # الفلترة الحصنية: جلب بقية الأقسام الرئيسية باستثناء القسم العام لمنع التكرار
    other_categories = Category.objects.filter(parent=None).exclude(id=general_category.id)
    
    # 🎯 دمج وتجميع الليستة: وضع القسم العام في أول عنصر صراحة، ثم رص بقية الأقسام خلفه بالترتيب
    category_choices = [general_category] + list(other_categories)
    
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

# accounts/views.py [تحديث رادار المسافات ليعمل للمسجلين والزوار كدعاية فورية]

    # 6. 🧭 🟢 رادار حساب المسافات الأوتوماتيكي المطور (مفتوح صراحة للمسجلين والزوار) 🟢 🧭
    nearby_providers = []
    
    # بناء الفلترة الأساسية لمقدمي الخدمات المتاحين أونلاين الحين بالمنصة
    provider_filters = models.Q(user_type='provider', is_active_now=True)
    if selected_category and category_obj:
        cat_and_children_ids = [category_obj.id] + list(subcategories.values_list('id', flat=True))
        provider_filters &= models.Q(category_id__in=cat_and_children_ids)

    # أ) المسار الأساسي: لو المتصفح ضخ إحداثيات الـ GPS (للمسجل أو الزائر)، يحسب المسافات اللحظية بدقة
    if client_lat and client_lng:
        c_lat, c_lng = float(client_lat), float(client_lng)
        active_providers = User.objects.filter(provider_filters & models.Q(latitude__isnull=False, longitude__isnull=False))
        
        R = 6371.0 # نصف قطر الأرض بالكيلومترات
        for p in active_providers:
            dlat = math.radians(p.latitude - c_lat)
            dlon = math.radians(p.longitude - c_lng)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(c_lat)) * math.cos(math.radians(p.latitude)) * math.sin(dlon/2)**2
            distance = R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))
            
            # حصر وعرض الفنيين المتواجدين في نطاق 15 كيلومتر حول العميل
            if distance <= 15.0:
                p.computed_distance = round(distance, 1)
                p.has_live_distance = True # شارة تأكيد الحساب الجغرافي
                nearby_providers.append(p)
                
    # ب) 🚀 مسار الدعاية الاحتياطي الصارم: لو الـ GPS لسه بيلقط أو المستخدم زائر بدون لوكيشن، يملأ الصندوق فوراً بأول 3 فنيين متاحين لمنع الفراغ 🚀
    if not nearby_providers:
        fallback_providers = User.objects.filter(provider_filters)[:3]
        for p in fallback_providers:
            p.computed_distance = "متاح" # نص جمالي بديل للمسافة الجافة
            p.has_live_distance = False
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

    # 8. 🔒 حزمة الـ Context الأصلية والمعدلة والمحقونة بالقسم العام بالملي 🔒
    context = {
        'gov_choices': gov_choices,
        'category_choices': category_choices,
        'general_category': general_category, # تمرير كائن القسم العام للواجهة
        'selected_category': int(selected_category) if selected_category else None,
        'category_obj': category_obj,
        'subcategories': subcategories,
        'posts': posts,
        'post_form': post_form,
        'unread_notifications': unread_notifications,
        'pending_requests': pending_friend_requests,
        'nearby_providers': nearby_providers,
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

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.contrib import messages

@login_required
def remove_friend_view(request, user_id):
    """دالة الباك إند الحاسمة لفسخ وإلغاء علاقة الصداقة نهائياً من جداول قاعدة البيانات"""
    target_user = get_object_or_404(User, id=user_id)
    
    # البحث عن علاقة الصداقة القائمة بين اليوزر الحالي والفني المستهدف وإبادتها فوراً
    FriendRequest.objects.filter(
        (models.Q(from_user=request.user) & models.Q(to_user=target_user) & models.Q(status='accepted')) |
        (models.Q(from_user=target_user) & models.Q(to_user=request.user) & models.Q(status='accepted'))
    ).delete()
    
    messages.success(request, "تم إلغاء الصداقة بنجاح ❌")
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

# accounts/views.py [دالة الباك إند لاستقبال وحفظ الـ FCM Token الفرعي للهاتف]
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@login_required
@csrf_exempt
def save_fcm_token_view(request):
    """دالة استقبال وحقن التوكن الجغرافي والسحابي للهاتف بداخل قاعدة البيانات فوريّاً"""
    if request.method == 'POST':
        # استقبال البيانات القادمة من الجافا سكريبت صامتاً
        data = json.loads(request.body) if request.body else {}
        token = data.get('token')
        
        if token:
            # حقن وحفظ التوكن بداخل حقل اليوزر الحالي بالسيرفر
            # تأكد من وجود حقل fcm_token بجدول الـ User (أو موديل البروفايل الملحق به)
            request.user.fcm_token = token
            request.user.save()
            return JsonResponse({'status': 'success', 'message': 'Token saved successfully 🚀'})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

# accounts/views.py [دالة محاكاة تسجيل دخول جوجل على السيرفر المحلي]
from django.contrib.auth import login
from django.shortcuts import redirect

def google_local_mock_view(request):
    """دالة ميكانيكية لتشغيل زر جوجل على السيرفر المحلي تلقائياً دون الحاجة لشفرات كونسول"""
    # البحث عن مستخدم وهمي تجريبي أو إنشائه فوريّاً بقاعدة البيانات
    user, created = User.objects.get_or_create(
        username="Otlop_Google_User",
        defaults={
            'email': "google_demo@otlop.com",
            'user_type': "customer", # تعيينه كعميل افتراضي
            'is_active_now': True
        }
    )
    if created:
        user.set_password('Otlop12345')
        user.save()
        
    # تسجيل الدخول وتطهير السشن فوريّاً كأنه قادم من جوجل بالملي!
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('home')
